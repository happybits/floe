import json
import falcon
from .helpers import chunks
from .exceptions import FloeException, FloeWriteException, \
    FloeDeleteException, FloeConfigurationException, FloeInvalidKeyException, \
    FloeOperationalException, FloeReadException
from .connector import get_connection
from .instrumentation import wrap_app, app_trace


class RestServerFloeIndex(object):
    CHUNK_SIZE = 100
    OK_RESPONSE = 'OK'

    @app_trace
    def on_get(self, req, resp, domain):
        cs = get_connection(domain)

        def generator():
            for keys in chunks(cs.ids(), self.CHUNK_SIZE):
                yield json.dumps([k for k in keys]).encode('utf-8')
                yield b'\n'

        # not setting because wsgiref doesn't natively support it and
        # uwsgi will automatically handle this for us.
        # resp.append_header('Transfer-Encoding', 'chunked')
        resp.stream = generator()

    @app_trace
    def on_delete(self, req, resp, domain):
        cs = get_connection(domain)
        cs.flush()
        resp.body = self.OK_RESPONSE


class RestServerFloeResource(object):

    OK_RESPONSE = 'OK'

    @app_trace
    def on_get(self, req, resp, domain, key):
        cs = get_connection(domain)
        response = cs.get(key)
        resp.body = b'' if response is None else response

    @app_trace
    def on_put(self, req, resp, domain, key):
        cs = get_connection(domain)
        cs.set(key, req.stream.read())
        resp.body = self.OK_RESPONSE

    @app_trace
    def on_delete(self, req, resp, domain, key):
        cs = get_connection(domain)
        cs.delete(key)
        resp.body = self.OK_RESPONSE


class RestServerFloeLanding(object):

    @app_trace
    def on_get(self, req, resp):
        resp.content_type = 'text/plain'
        resp.body = 'Floe Microservice'


def format_error(ex, resp, code='INTERNAL',
                 status=falcon.HTTP_INTERNAL_SERVER_ERROR):
    resp.status = status
    resp.append_header('X-ERR', code)
    resp.content_type = 'text/plain'
    resp.body = str(ex.message)


def generic_error_handler(ex, req, resp, params):
    format_error(ex, resp, code='INTERNAL',
                 status=falcon.HTTP_INTERNAL_SERVER_ERROR)


def configuration_error_handler(ex, req, resp, params):
    format_error(ex, resp, code='CONFIGURATION', status=falcon.HTTP_400)


def operational_error_handler(ex, req, resp, params):
    format_error(ex, resp, code='OPERATIONAL',
                 status=falcon.HTTP_INTERNAL_SERVER_ERROR)


def read_error_handler(ex, req, resp, params):
    format_error(ex, resp, code='READ',
                 status=falcon.HTTP_INTERNAL_SERVER_ERROR)


def write_error_handler(ex, req, resp, params):
    format_error(ex, resp, code='WRITE',
                 status=falcon.HTTP_INTERNAL_SERVER_ERROR)


def delete_error_handler(ex, req, resp, params):
    format_error(ex, resp, code='DELETE',
                 status=falcon.HTTP_INTERNAL_SERVER_ERROR)


def invalid_key_handler(ex, req, resp, params):
    format_error(ex, resp, code='INVALID-KEY', status=falcon.HTTP_400)


def floe_server(routes=None):
    app = falcon.API(media_type='binary/octet-stream')
    app.add_route('/{domain}/{key}', RestServerFloeResource())
    app.add_route('/{domain}', RestServerFloeIndex())
    app.add_route('/', RestServerFloeLanding())
    if routes:
        for uri, handler in routes.items():
            app.add_route(uri, handler)
    app.add_error_handler(FloeException, configuration_error_handler)
    app.add_error_handler(FloeInvalidKeyException, invalid_key_handler)
    app.add_error_handler(FloeOperationalException, operational_error_handler)
    app.add_error_handler(FloeReadException, read_error_handler)
    app.add_error_handler(FloeWriteException, write_error_handler)
    app.add_error_handler(FloeDeleteException, delete_error_handler)
    app.add_error_handler(FloeConfigurationException,
                          configuration_error_handler)
    return wrap_app(app)
