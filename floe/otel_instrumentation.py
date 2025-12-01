import functools

try:
    import falcon
    from opentelemetry import trace
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


def app_trace(f):
    if not OTEL_AVAILABLE:
        return f

    @functools.wraps(f)
    def inner(resource, req, resp, *args, **kwargs):
        tracer = trace.get_tracer(__name__)
        span_name = f"{resource.__class__.__name__}.{f.__name__}"
        with tracer.start_as_current_span(span_name) as span:
            try:
                return f(resource, req, resp, *args, **kwargs)
            except Exception as e:
                if not isinstance(e, falcon.HTTPNotFound):
                    span.record_exception(e)
                    span.set_status(trace.StatusCode.ERROR, str(e))
                raise
    return inner
