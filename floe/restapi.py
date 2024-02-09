import requests
import json
from .exceptions import FloeException, FloeWriteException, \
    FloeDeleteException, FloeConfigurationException, FloeInvalidKeyException, \
    FloeOperationalException, FloeReadException
from .helpers import sanitize_key
from concurrent.futures import ThreadPoolExecutor

FLOE_REST_TIMEOUT = 30
FLOE_TASK_TIMEOUT = 60

class RestClientFloe(object):

    queue_size = 10

    session = requests.Session()

    def __init__(self, base_url):
        self._baseurl = base_url
        self._pool = None

    def raise_exception_from_response(self, resp):
        if resp.status_code == 200:
            return

        if resp.status_code == 404:
            return

        err_code = resp.headers.get('X-ERR', 'INTERNAL')

        if err_code == 'INVALID-KEY':
            raise FloeInvalidKeyException(resp.text)

        if err_code == 'OPERATIONAL':
            raise FloeOperationalException(resp.text)

        if err_code == 'WRITE':
            raise FloeWriteException(resp.text)

        if err_code == 'READ':
            raise FloeReadException(resp.text)

        if err_code == 'DELETE':
            raise FloeDeleteException(resp.text)

        if err_code == 'CONFIGURATION':
            raise FloeConfigurationException(resp.text)

        if resp.status_code == 0:
            raise FloeOperationalException(
                'unable to communicate with the api server')

        if resp.status_code in [502, 503, 504]:
            raise FloeOperationalException(
                'unable to communicate with the api server - %s' % resp.text)

        if resp.status_code == 500:
            raise FloeException('internal error %s' % resp.text)

        raise FloeException(resp.text)

    @property
    def pool(self):
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=self.queue_size)
        return self._pool

    def get(self, key):
        key = sanitize_key(key)
        resp = self.session.get("%s/%s" % (self._baseurl, key), timeout=FLOE_REST_TIMEOUT)
        self.raise_exception_from_response(resp)

        if resp.status_code == 404:
            return None

        if int(resp.headers.get('content-length', 0)) == 0:
            return None

        return resp.content

    def set(self, key, value):
        key = sanitize_key(key)
        resp = self.session.put("%s/%s" % (self._baseurl, key),
                                data=value,
                                headers={
                                    'content-type': 'binary/octet-stream'},
                                timeout=FLOE_REST_TIMEOUT
                                )
        self.raise_exception_from_response(resp)

    def delete(self, key):
        key = sanitize_key(key)
        resp = self.session.delete("%s/%s" % (self._baseurl, key), timeout=FLOE_REST_TIMEOUT)
        self.raise_exception_from_response(resp)

    def get_multi(self, keys):
        keys = [sanitize_key(key) for key in keys]

        def _get(key):
            return key, self.get(key)

        responses = list(self.pool.map(_get, keys, timeout=FLOE_TASK_TIMEOUT))

        return {k: v for k, v in responses if v is not None}

    def set_multi(self, mapping):
        mapping = {sanitize_key(key): value for key, value in mapping.items()}

        def _set(row):
            self.set(*row)

        # Iterate over the results to block until all requests finish
        list(self.pool.map(_set, mapping.items(), timeout=FLOE_TASK_TIMEOUT))

    def delete_multi(self, keys):
        for key in keys:
            sanitize_key(key)

        def _delete(key):
            self.delete(key)

        # Iterate over the results to block until all requests finish
        list(self.pool.map(_delete, keys, timeout=FLOE_TASK_TIMEOUT))

    def ids(self):
        resp = self.session.get(self._baseurl, timeout=FLOE_REST_TIMEOUT)
        self.raise_exception_from_response(resp)

        buffer = b''
        for chunk in resp.iter_content(100):
            if chunk is None:
                continue
            buffer += chunk

            linebreak = buffer.find(b'\n')
            if linebreak == -1:
                continue

            if linebreak > 0:
                for key in json.loads(buffer[0:linebreak].decode('utf-8')):
                    yield key

            buffer = buffer[linebreak+1:]

        if buffer:
            for key in json.loads(buffer.decode('utf-8')):
                yield key

    def flush(self):
        resp = self.session.delete(self._baseurl)
        self.raise_exception_from_response(resp)
