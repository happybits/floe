import logging
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

logger = logging.getLogger(__name__)

_CONNECTIONS = {}


def get_connection(name):
    name = name.upper()
    try:
        return _CONNECTIONS[name]
    except KeyError:
        obj = connect(name)
        _CONNECTIONS[name] = obj
        return obj


def connect(name):
    name = name.upper()
    url = getenv('FLOE_URL_%s' % name)
    if not url:
        raise FloeConfigurationException('%s not configured' % name)

    dsn = urlparse(url)

    if dsn.scheme == 'file':
        directory = url[7:]
        logger.debug("Connecting to file backend: %s", directory)
        return FileFloe(directory=directory)

    if dsn.scheme == 'mysql':
        if MySQLFloe is None:
            raise FloeConfigurationException('mysql dependencies missing')

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
        logger.debug("Connecting to MySQL backend: %s/%s",
                     conn_kwargs.get('host', ''), conn_kwargs.get('db', ''))
        return MySQLFloe(table=table, **conn_kwargs)

    if dsn.scheme in ['http', 'https']:
        logger.debug("Connecting to REST backend: %s://%s", dsn.scheme, dsn.hostname)
        return RestClientFloe(url)

    raise FloeConfigurationException('invalid scheme for %s' % name)
