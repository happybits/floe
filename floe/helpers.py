import time
import re
from itertools import islice
from .exceptions import FloeInvalidKeyException


KEY_PATTERN = re.compile(r'^([A-Za-z0-9_\-\.]+)$')


def current_time():
    return time.time()


def sanitize_key(key):
    if not key:
        raise FloeInvalidKeyException(key)

    key = str(key)
    if not KEY_PATTERN.match(key):
        raise FloeInvalidKeyException(key)
    return key


def chunks(iterable, size):
    iterable = iter(iterable)
    return iter(lambda: list(islice(iterable, size)), [])
