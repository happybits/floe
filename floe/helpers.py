import time
import re
from itertools import islice
from .exceptions import FloeInvalidKeyException


KEY_PATTERN = re.compile(r'^([A-Za-z0-9_\-\.]+)$')


def current_time():
    return time.time()


def validate_key(key):
    if not KEY_PATTERN.match(key):
        raise FloeInvalidKeyException(key)

def validate_data(value):
    if len(value) > MYSQL_BLOB_MAX_VALUE:
        raise FloeInvalidKeyException('TODO REMOVE ME')

def chunks(iterable, size):
    iterable = iter(iterable)
    return iter(lambda: list(islice(iterable, size)), [])
