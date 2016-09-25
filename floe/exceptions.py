__all__ = [
    'FloeException',
    'FloeConfigurationException',
    'FloeOperationalException',
    'FloeDeleteException',
    'FloeReadException',
    'FloeWriteException',
    'FloeInvalidKeyException'
]


class FloeException(Exception):
    def __init__(self, message):
        self.message = message


class FloeInvalidKeyException(FloeException):
    pass


class FloeConfigurationException(FloeException):
    pass


class FloeOperationalException(FloeException):
    pass


class FloeWriteException(FloeOperationalException):
    pass


class FloeReadException(FloeOperationalException):
    pass


class FloeDeleteException(FloeOperationalException):
    pass
