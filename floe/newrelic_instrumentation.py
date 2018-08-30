import functools
import sys
import falcon
from newrelic.agent import (
    callable_name,
    FunctionTrace,
    current_transaction,
    set_transaction_name,
    record_exception,
    initialize,
    WSGIApplicationWrapper,
)

EMPTY_EXC_INFO = (None, None, None)


def trace(f, group=None, txn_name=None):
    if txn_name is None:
        txn_name = callable_name(f, ".")

    @functools.wraps(f)
    def inner(*args, **kwargs):
        with FunctionTrace(
            transaction=current_transaction(),
            name=txn_name,
            group=group

        ):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                if not isinstance(e, falcon.HTTPNotFound):
                    record_exception(*sys.exc_info())
                raise

    return inner


def app_trace(f):
    @functools.wraps(f)
    def inner(resource, req, resp, *args, **kwargs):
        txn_name = "%s:%s" % (
            callable_name(resource, separator='.'), f.__name__)
        set_transaction_name(txn_name)
        with FunctionTrace(transaction=current_transaction(), name=txn_name):
            try:
                return f(resource, req, resp, *args, **kwargs)
            except Exception as e:
                if not isinstance(e, falcon.HTTPNotFound):
                    record_exception(*sys.exc_info())
                raise

    return inner


def wrap_app(app):
    return WSGIApplicationWrapper(app)


# kick off new-relic monitoring.
initialize()
