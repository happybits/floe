try:
    from .newrelic_instrumentation import trace, wrap_app, app_trace
except ImportError:
    def trace(f, group=None, txn_name=None):
        return f

    def wrap_app(app):
        return app

    def app_trace(f):
        return f
