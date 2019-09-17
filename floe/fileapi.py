import os
import errno
import shutil
import re
from .exceptions import FloeWriteException
from .helpers import sanitize_key


class FileFloe(object):
    """
    An implementation of cold storage for hbom.
    """

    def __init__(self, directory):
        """
        specify the directory of where the data is stored
        """
        self.dir = directory

    def _resolve_path(self, key):
        parts = [self.dir]
        length = len(key)
        if length > 2:
            parts.append(key[0:2])

        if length > 4:
            parts.append(key[2:4])

        if length > 6:
            parts.append(key[4:6])

        parts.append("%s.bin" % key)

        return os.path.join(*parts)

    @classmethod
    def _mkdirs(cls, dir_name):
        # there's a race condition where the directory doesn't exist
        # and then hit an error when trying to create the directory because
        # another process is doing the same thing at the exact same time.
        # if that's the case, swallow the error.
        if os.path.exists(dir_name):
            return
        try:
            os.makedirs(dir_name)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def get(self, key):
        """
        get the value of a given key
        :param pk:
        :return:
        """
        key = sanitize_key(key)
        try:
            with open(self._resolve_path(key), 'rb+') as fp:
                return fp.read()
        except (OSError, IOError):
            return None

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
        result = {k: self.get(k) for k in keys}
        return {k: v for k, v in result.items() if v is not None}

    def set(self, key, bin_data):
        """
        set a given key
        :param key:
        :param bin_data:
        :return:
        """
        key = sanitize_key(key)
        path = self._resolve_path(key)
        self._mkdirs(os.path.dirname(path))
        try:
            with open(path, 'wb+') as fp:
                fp.write(bin_data)
        except (IOError):
            raise FloeWriteException()

    def set_multi(self, mapping):
        """
        set a series of keys based on the dictionary passed in
        :param mapping: dict
        :return:
        """
        mapping = {sanitize_key(key): value for key, value in mapping.items()}

        for key, value in mapping.items():
            self.set(key, value)

    def delete(self, key):
        """
        delete a given key
        :param key:
        :return:
        """
        key = sanitize_key(key)
        try:
            os.unlink(self._resolve_path(key))
        except OSError:
            pass

    def delete_multi(self, keys):
        """
        delete a set of given keys
        :param keys:
        :return:
        """
        keys = [sanitize_key(key) for key in keys]

        for key in keys:
            self.delete(key)

    def flush(self):
        """
        remove all keys from a given database
        :return:
        """
        try:
            for subdir in os.listdir(self.dir):
                shutil.rmtree(os.path.join(self.dir, subdir),
                              ignore_errors=True)
        except OSError:
            pass

    def ids(self):
        """
        return a generator that iterates through all ids in cold storage
        no particular order. useful for a script to crawl through stuff that
        has been frozen and thaw it.
        :return:
        """
        pattern = re.compile(r'^([A-Za-z0-9_\-\.]+)\.bin$')
        try:
            for info in os.walk(self.dir):
                for f in info[2]:
                    match = pattern.match(f)
                    if not match:
                        continue
                    yield match.group(1)
        except OSError:
            pass
