from os import getenv
from .exceptions import FloeConfigurationException
from .fileapi import FileFloe
from .restapi import RestClientFloe

try:
    from .mysqlapi import MySQLFloe
except ImportError:
    MySQLFloe = None

try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs


# a pool of cached connections.
_CONNECTIONS = {

}


def get_connection(name):
    """
    this returns a single connection object based on the name to a floe
    api. this allows for more efficient connection pooling and reuse of objects

    :param name:
    :return:
    """
    name = name.upper()
    try:
        return _CONNECTIONS[name]
    except KeyError:
        obj = connect(name)
        _CONNECTIONS[name] = obj
        return obj


def connect(name):
    """
    factory method of getting a connection to cold storage based on a dsn name.
    We look it up in an environmental variable.
    So far we support mysql, file, and rest types.

    Here are some example environmental vars you could use:

        FLOE_URL_FOO='file://.floe'
        FLOE_URL_BAR='file:///tmp/floe'
        FLOE_URL_BAZZ='mysql://root:pass@127.0.0.1:3306/test?table=bazz'
        FLOE_URL_QUUX='http://127.0.0.1:995/my_namespace'

    now you can connect to them using the names,
        'foo', 'bar', 'bazz', and 'quux' respectively.

    :param name: string
    :return: Floe object
    """
    name = name.upper()
    url = getenv('FLOE_URL_%s' % name)
    if not url:
        raise FloeConfigurationException('%s not configured' % name)

    dsn = urlparse(url)
    if dsn.scheme == 'file':
        directory = url[7:]
        return FileFloe(directory=directory)

    if dsn.scheme == 'mysql':
        if MySQLFloe is None:
            FloeConfigurationException('mysql dependencies missing')

        conn_kwargs = {}

        if dsn.hostname:
            conn_kwargs['host'] = dsn.hostname

        if dsn.port:
            conn_kwargs['port'] = dsn.port

        if dsn.username:
            conn_kwargs['user'] = dsn.username

        if dsn.password:
            conn_kwargs['passwd'] = dsn.password

        if dsn.path:
            conn_kwargs['db'] = dsn.path[1:]

        table = name.lower()
        if dsn.query:
            conn_kwargs.update(
                {k: v[-1] for k, v in parse_qs(dsn.query).items()})
            if 'table' in conn_kwargs:
                table = conn_kwargs['table']
                del conn_kwargs['table']

        conn_kwargs['binary_prefix'] = True

        return MySQLFloe(table=table, **conn_kwargs)

    if dsn.scheme in ['http', 'https']:
        return RestClientFloe(url)

    raise FloeConfigurationException('invalid scheme for %s' % name)
