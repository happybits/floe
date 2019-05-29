import os
import unittest
import uuid
import floe
import webtest
import json
import wsgiadapter
import logging
import socket
import floe.restapi
import floe.connector
import time
import pymysql

wsgiadapter.logger.addHandler(logging.NullHandler())

mysql_user = os.getenv('MYSQL_USER', 'root')
mysql_pass = os.getenv('MYSQL_PASSWORD', None)

mysql_auth = "%s:%s" % (mysql_user, mysql_pass) \
    if mysql_pass is not None else mysql_user

table_prefix_variable = int(time.time())

os.environ['FLOE_URL_TEST_FILE'] = 'file://.test_floe'

os.environ['FLOE_URL_TEST_REST_BOGUS'] = 'http://test-floe/bogus'
os.environ['FLOE_URL_TEST_REST_FILE'] = 'http://test-floe/test_file'
os.environ['FLOE_URL_TEST_REST_BROKEN'] = 'http://test-floe/broken'

adapter = wsgiadapter.WSGIAdapter(floe.floe_server())
floe.restapi.RestClientFloe.session.mount('http://test-floe/', adapter)  # noqa


def drop_table(pool, table_name):
    statement = "DROP table {}".format(table_name)
    try:
        with pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement)
    except pymysql.Error as e:
        raise e


def is_local_mysql_running():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 3306))
    return True if result == 0 else False


codeship_build = os.getenv('CODESHIP_BUILD')

mysql_test_enable = True if \
    os.getenv('MYSQL_TEST_ENABLE', is_local_mysql_running()) \
    else False
MYSQL_TEST = unittest.skipIf(codeship_build or not mysql_test_enable,
                             'mysql test disabled on local and codeship')

BLOB_MAX_CHAR_LEN = 65535
MEDIUM_BLOB_MAX_CHAR_LEN = 16777215


def xid():
    return uuid.uuid4().hex


class BrokenFloe(object):

    def get(self, key):
        raise floe.FloeReadException('failed to read')

    def get_multi(self, keys):
        raise floe.FloeReadException('failed to read')

    def set(self, key, bin_data):
        raise floe.FloeWriteException('failed to write')

    def set_multi(self, mapping):
        raise floe.FloeWriteException('failed to write')

    def delete(self, key):
        raise floe.FloeDeleteException('failed to delete')

    def delete_multi(self, keys):
        raise floe.FloeDeleteException('failed to delete')

    def flush(self):
        pass

    def ids(self):
        raise floe.FloeReadException('failed to read')


floe.connector._CONNECTIONS['BROKEN'] = BrokenFloe()


class FileFloeTest(unittest.TestCase):
    def init_floe(self):
        return floe.connect('test_file')

    def setUp(self):
        self.floe = self.init_floe()
        self.floe.flush()

    def tearDown(self):
        self.floe.flush()

    def test_main(self):
        store = self.floe
        foo = xid()
        bar = xid()
        bazz = xid()

        foo_test_data = os.urandom(4096)
        store.set(foo, foo_test_data)
        self.assertEqual(store.get(foo), foo_test_data)

        foo_test_data = os.urandom(500)
        bazz_test_data = os.urandom(200)
        store.set_multi({foo: foo_test_data, bazz: bazz_test_data})
        self.assertEqual(store.get(foo), foo_test_data)
        self.assertEqual(store.get(bazz), bazz_test_data)
        self.assertEqual(store.get_multi([foo, bar, bazz]),
                         {foo: foo_test_data, bazz: bazz_test_data})
        ids = {i for i in store.ids()}
        self.assertEqual(ids, {bazz, foo})
        store.delete(foo)
        self.assertEqual(store.get_multi([foo, bar, bazz]),
                         {bazz: bazz_test_data})
        store.delete_multi([foo, bar, bazz])
        self.assertEqual(store.get_multi([foo, bar, bazz]), {})

        self.assertRaises(floe.FloeInvalidKeyException,
                          lambda: store.get('foo/bar'))

        self.assertRaises(floe.FloeInvalidKeyException,
                          lambda: store.set('foo/bar', '1'))

        self.assertRaises(floe.FloeInvalidKeyException,
                          lambda: store.delete('foo/bar'))

        self.assertRaises(floe.FloeInvalidKeyException,
                          lambda: store.get('foo/bar'))

        self.assertRaises(floe.FloeInvalidKeyException,
                          lambda: store.set('foo/bar', '1'))

        self.assertRaises(floe.FloeInvalidKeyException,
                          lambda: store.delete('foo/bar'))


class MysqlFloe(FileFloeTest):
    def setUp(self):
        self.mysql_tables = [
            '%s_%s' % (table_name, table_prefix_variable)
            for table_name in ['test_floe', 'test_floe_2', 'test_floe_3']
        ]

        for index, table in enumerate(self.mysql_tables):
            environ_key = 'FLOE_URL_%s' % table.upper()
            url = "mysql://%s@127.0.0.1:3306/test?table=%s" % (
                mysql_auth, table)

            if index > 0:
                url += "&dynamic_char_len=True"
            if index > 1:
                url += "&bin_data_type=blob"

            os.environ[environ_key] = url

        super(MysqlFloe, self).setUp()

    def tearDown(self):
        for table in self.mysql_tables:
            store = floe.connect(table)
            drop_table(store.pool, table)

    def init_floe(self):
        return floe.connect(self.mysql_tables[0])

    @MYSQL_TEST
    def test_main(self):
        super(MysqlFloe, self).test_main()

    @MYSQL_TEST
    def test_uppercase(self):
        store = self.floe
        foo = xid()
        foo_upper = foo.upper()

        foo_test_data = os.urandom(10)
        foo_upper_test_data = os.urandom(12)

        self.assertNotEqual(foo_test_data, foo_upper_test_data)
        store.set(foo, foo_test_data)
        store.set(foo_upper, foo_upper_test_data)
        self.assertEqual(store.get(foo), foo_test_data)
        self.assertEqual(store.get(foo_upper), foo_upper_test_data)

    @MYSQL_TEST
    def test_data_overflow_from_sql(self):
        store = floe.connect(self.mysql_tables[1])
        foo = xid()
        foo_smaller = foo.upper()

        foo_data = os.urandom(MEDIUM_BLOB_MAX_CHAR_LEN + 1)

        self.assertRaises(
            floe.FloeDataOverflowException,
            lambda: store.set(foo, foo_data))

        foo_smaller_data = foo_data[:-1]
        store.set(foo_smaller, foo_smaller_data)

        self.assertEqual(store.get(foo_smaller), foo_smaller_data)

    @MYSQL_TEST
    def test_data_overflow(self):
        store = self.floe
        foo = xid()
        foo_smaller = foo.upper()

        foo_data = os.urandom(BLOB_MAX_CHAR_LEN + 1)

        self.assertRaises(
            floe.FloeDataOverflowException,
            lambda: store.set(foo, foo_data))

        foo_smaller_data = foo_data[:-1]
        store.set(foo_smaller, foo_smaller_data)

        self.assertEqual(store.get(foo_smaller), foo_smaller_data)

    @MYSQL_TEST
    def test_custom_bin_data_type(self):
        store = floe.connect(self.mysql_tables[2])
        foo = xid()
        foo_smaller = foo.upper()

        foo_data = os.urandom(BLOB_MAX_CHAR_LEN + 1)

        self.assertRaises(
            floe.FloeDataOverflowException,
            lambda: store.set(foo, foo_data))

        foo_smaller_data = foo_data[:-1]
        store.set(foo_smaller, foo_smaller_data)

        self.assertEqual(store.get(foo_smaller), foo_smaller_data)


class RestServerAdditionalRoute(object):

    def on_get(self, req, resp):
        resp.content_type = 'text/plain'
        resp.body = 'additional'


class RestServerTest(unittest.TestCase):

    def init_floe(self):
        return floe.connect('test_file')

    def setUp(self):
        self.floe = self.init_floe()
        self.floe.flush()
        self.app = webtest.TestApp(floe.floe_server(
            routes={'/testroute': RestServerAdditionalRoute()}))

    def tearDown(self):
        self.floe.flush()

    def test_crud(self):
        key = xid()
        res = self.app.get('/test_file/%s' % key, expect_errors=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_length, 0)
        data = os.urandom(100)
        res = self.app.put('/test_file/%s' % key, params=data,
                           headers={'content-type': 'binary/octet-stream'})
        self.assertEqual(res.status_code, 200)
        res = self.app.get('/test_file/%s' % key)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.body, data)
        res = self.app.delete('/test_file/%s' % key)
        self.assertEqual(res.status_code, 200)

    def test_keys(self):
        keys = {xid() for _ in range(0, 120)}
        for key in keys:
            res = self.app.put('/test_file/%s' % key, params=os.urandom(10))

        res = self.app.get('/test_file')
        result_keys = set()
        for line in res.body.decode('utf-8').split('\n'):
            if line:
                result_keys.update(json.loads(line.strip()))

        self.assertEqual(keys, result_keys)

    def test_nested_dirs(self):
        res = self.app.get('/test_file/foo/bar', expect_errors=True)
        self.assertEqual(res.status_code, 404)

    def test_index(self):
        res = self.app.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.body, b'Floe Microservice')

    def test_additional_route(self):
        res = self.app.get('/testroute')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.body, b'additional')


class RestClientFileTest(FileFloeTest):

    def init_floe(self):
        return floe.connect('test_rest_file')


class RestClientMysqlTest(FileFloeTest):
    def setUp(self):
        table = '%s_%s' % ('rest_mysql', table_prefix_variable)
        os.environ['FLOE_URL_TEST_REST_MYSQL'] = 'http://test-floe/%s' % table

        environ_key = 'FLOE_URL_%s' % table.upper()
        url = "mysql://%s@127.0.0.1:3306/test?table=%s" % (
            mysql_auth, table)

        self.table = table
        os.environ[environ_key] = url
        super(RestClientMysqlTest, self).setUp()

    def tearDown(self):
        store = self.floe
        drop_table(store.pool, self.table)

    def init_floe(self):
        return floe.connect(self.table)

    @MYSQL_TEST
    def test_main(self):
        super(RestClientMysqlTest, self).test_main()


class RestClientMisconfigurationTest(unittest.TestCase):
    def init_floe(self):
        return floe.connect('test_rest_bogus')

    def setUp(self):
        self.floe = self.init_floe()

    def test_main(self):
        store = self.floe
        foo = xid()
        self.assertRaises(floe.FloeConfigurationException,
                          lambda: store.get(foo))

        self.assertRaises(floe.FloeConfigurationException,
                          lambda: store.set(foo, '1'))

        self.assertRaises(floe.FloeConfigurationException,
                          lambda: store.delete(foo))

        self.assertRaises(floe.FloeConfigurationException,
                          lambda: [k for k in store.ids()])


class RestClientBrokenTest(unittest.TestCase):
    def init_floe(self):
        return floe.connect('test_rest_broken')

    def setUp(self):
        self.floe = self.init_floe()

    def test_main(self):
        store = self.floe
        foo = xid()
        self.assertRaises(floe.FloeReadException,
                          lambda: store.get(foo))

        self.assertRaises(floe.FloeWriteException,
                          lambda: store.set(foo, '1'))

        self.assertRaises(floe.FloeDeleteException,
                          lambda: store.delete(foo))

        self.assertRaises(floe.FloeReadException,
                          lambda: [k for k in store.ids()])


if __name__ == "__main__":
    unittest.main(verbosity=2)
