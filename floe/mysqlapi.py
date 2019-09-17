import pymysql
import warnings
from contextlib import contextmanager
from .helpers import current_time, sanitize_key
from .exceptions import FloeReadException, \
    FloeWriteException, FloeDeleteException, \
    FloeDataOverflowException, FloeConfigurationException

warnings.filterwarnings('ignore', category=pymysql.Warning)

DEFAULT_MAX_CHAR_LEN = 65535
ALLOWED_BIN_DATA_TYPES = ['blob', 'mediumblob', 'longblob']


class MySQLPool(object):
    """
    utility class that does mysql connection pooling.
    Thread-safe. Will allocate a connection and only release it back when you
    are done with it.
    """
    exception_class = pymysql.Error

    def __init__(self, pool_size=5, inactive_timeout=120, **kwargs):
        self.inactive_timeout = inactive_timeout
        self.pool_size = pool_size
        self.pool = []
        self.conn_kwargs = kwargs

    @contextmanager
    def connection(self):
        conn = self._allocate()
        try:
            yield conn
            self._release(conn)
        except self.exception_class:
            raise

    def _allocate(self):
        try:
            while True:
                conn, ts = self.pool.pop()
                if ts + self.inactive_timeout > current_time():
                    return conn

                conn.close()
        except IndexError:
            pass

        return self._create_connection()

    def _release(self, conn):
        if len(self.pool) > self.pool_size:
            conn.close()
            return

        self.pool.append((conn, current_time()))

    def _create_connection(self):
        return pymysql.connect(**self.conn_kwargs)

    def close(self):
        try:
            while True:
                conn, _ = self.pool.pop()
                try:
                    conn.close()
                except (AttributeError, TypeError):
                    continue

        except IndexError:
            return

    def __del__(self):
        self.close()


class MySQLConnection(object):
    exception_class = pymysql.Error

    def __init__(self, **kwargs):
        self.conn_kwargs = kwargs

    @contextmanager
    def connection(self):
        conn = pymysql.connect(**self.conn_kwargs)
        try:
            yield conn
        finally:
            conn.close()


class MySQLFloe(object):
    def __init__(self, table, default_partitions=10, pool_size=5,
                 init_disable=False, bin_data_type='mediumblob',
                 dynamic_char_len=False,
                 **conn_kwargs):
        """
        specify the database, table, and connection parameters for mysql.
        This will hold on to the parameters and create the connection
        on-demand. It also waits to create the database and the table until
        the connection is requested. It'll try to use the database, and if it
        hits an error that says no db exists, it'll try to create it.
        This is useful for unit testing scenarios. On production, it's probably
        better to create the database and table in advance.
        :param database:
        :param table:
        :param kwargs:
        """

        self.table = table
        self.max_char_len = DEFAULT_MAX_CHAR_LEN
        conn_kwargs['autocommit'] = True
        conn_kwargs.setdefault('cursorclass', pymysql.cursors.SSCursor)

        pool_size = int(pool_size)
        self.pool = self._create_pool(pool_size=pool_size, **conn_kwargs)

        if not init_disable:
            if bin_data_type.lower() not in ALLOWED_BIN_DATA_TYPES:
                raise FloeConfigurationException(bin_data_type)

            try:
                schema = "CREATE TABLE IF NOT EXISTS {} (" \
                         "`pk` VARBINARY(32) NOT NULL PRIMARY KEY, " \
                         "`bin` {} NOT NULL" \
                         ") ENGINE=InnoDB " \
                         "/*!50100 PARTITION BY KEY (pk) PARTITIONS {} */"
                statement = schema.format(self.table, bin_data_type,
                                          default_partitions)
                with self.pool.connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(statement)
            except pymysql.Error:
                pass

        if dynamic_char_len:
            self._set_max_char_len(**conn_kwargs)

    def _set_max_char_len(self, **conn_kwargs):
        db = conn_kwargs.get('db')
        if not db:
            return

        statement = "SELECT `CHARACTER_MAXIMUM_LENGTH`" \
                    "FROM `INFORMATION_SCHEMA`.`COLUMNS`" \
                    "WHERE `TABLE_SCHEMA` = %s" \
                    "AND `TABLE_NAME` = %s" \
                    "AND `COLUMN_NAME` = 'bin'"

        try:
            with self.pool.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(statement, (db, self.table))
                    for row in cursor.fetchall():
                        self.max_char_len = row[0]
        except pymysql.Error as e:
            raise FloeReadException(e)

    def _validate_data(self, value):
        if len(value) > self.max_char_len:
            raise FloeDataOverflowException(len(value))
        return value

    def _create_pool(self, pool_size=5, **conn_kwargs):
        if pool_size and pool_size > 0:
            return MySQLPool(pool_size=pool_size, **conn_kwargs)
        else:
            return MySQLConnection(**conn_kwargs)

    def reset_pool(self, pool_size=5):
        conn_kwargs = dict(self.pool.conn_kwargs)
        conn_kwargs['pool_size'] = pool_size
        self.pool = self._create_pool(**conn_kwargs)

    def get(self, pk):
        """
        get the value of a given key
        :param pk:
        :return:
        """
        pk = sanitize_key(pk)
        statement = "SELECT `bin` FROM {} WHERE `pk` = %s".format(self.table)
        try:
            with self.pool.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(statement, (pk,))
                    for row in cursor.fetchall():
                        return row[0]
        except pymysql.Error as e:
            raise FloeReadException(e)

    def get_multi(self, keys):
        """
        get the values for a list of keys as a dictionary.
        keys that are not found will be missing from the response.

        :param keys:
        :return:
        """
        if not keys:
            return {}
        keys = [sanitize_key(key) for key in keys]
        statement = "SELECT `pk`, `bin` FROM {} WHERE `pk` IN ({})".format(
            self.table,
            ', '.join(["%s" for _ in keys])
        )
        try:
            with self.pool.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(statement, tuple(keys))
                    return {k.decode('utf-8'): v for k, v in cursor}
        except pymysql.Error as e:
            raise FloeReadException(e)

    def set(self, pk, bin_data):
        """
        set a given key
        :param pk:
        :param bin_data:
        :return:
        """
        return self.set_multi({pk: bin_data})

    def set_multi(self, mapping):
        """
        set a series of keys based on the dictionary passed in
        :param mapping: dict
        :return:
        """
        mapping = {sanitize_key(key): self._validate_data(value) for key, value
                   in mapping.items()}

        statement = "INSERT INTO {} (`pk`, `bin`) VALUES {} " \
                    "ON DUPLICATE KEY UPDATE `bin` = VALUES(`bin`)"
        tuple_list = []
        for key, value in mapping.items():
            tuple_list.append(key)
            tuple_list.append(value)

        statement = statement.format(self.table, ', '.join(
            ["(%s, %s)" for _ in range(0, len(mapping))]))

        try:
            with self.pool.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(statement, tuple(tuple_list))
        except pymysql.Error as e:
            raise FloeWriteException(e)

    def delete(self, key):
        """
        delete a given key
        :param key:
        :return:
        """
        return self.delete_multi([key])

    def delete_multi(self, keys):
        """
        delete a set of given keys
        :param keys:
        :return:
        """
        if not keys:
            return {}

        keys = [sanitize_key(key) for key in keys]

        statement = "DELETE FROM {} WHERE `pk` IN ({})".format(
            self.table,
            ', '.join(["%s" for _ in keys])
        )
        try:
            with self.pool.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(statement, tuple(keys))
        except pymysql.Error as e:
            raise FloeDeleteException(e)

    def flush(self):
        """
        remove all keys from a given database
        :return:
        """
        statement = "TRUNCATE {}".format(self.table)
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement)

    def ids(self):
        statement = "SELECT `pk` FROM {}".format(self.table)
        try:
            with self.pool.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(statement)
                    for k, in cursor:
                        yield k.decode('utf-8')
        except pymysql.Error as e:
            raise FloeReadException(e)

    def drop_table(self):
        statement = "DROP TABLE IF EXISTS {}".format(self.table)
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement)
