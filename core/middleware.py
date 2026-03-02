import logging
import time

from django.db import connection

from core.tracing import start_trace, end_trace, trace_step, set_trace_user

logger = logging.getLogger('django.db.slow_queries')


# Paths we don't trace (too noisy)
_SKIP_PREFIXES = ('/static/', '/favicon', '/api/v1/dashboard/traces/')


class TracingMiddleware:
    """Wraps every request in a trace that captures processing steps."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return self.get_response(request)

        user_id = None
        if hasattr(request, 'user') and hasattr(request.user, 'id') and request.user.is_authenticated:
            user_id = request.user.id

        trace = start_trace(request.method, path, user_id)
        trace_step(f'{request.method} {path}', 'request')

        response = self.get_response(request)

        # Capture user_id after JWT auth middleware ran
        if not trace.user_id and hasattr(request, 'user') and hasattr(request.user, 'id') and request.user.is_authenticated:
            set_trace_user(request.user.id)

        trace_step(f'Response {response.status_code}', 'response')
        end_trace(response.status_code)
        return response


class SlowQueryLogMiddleware:
    """
    Logs database queries that exceed a threshold.
    Useful for identifying N+1 queries and slow operations.
    """

    THRESHOLD_MS = 100  # Log queries slower than 100ms

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Reset query log
        initial_queries = len(connection.queries)
        start = time.monotonic()

        response = self.get_response(request)

        duration_ms = (time.monotonic() - start) * 1000
        queries = connection.queries[initial_queries:]
        total_queries = len(queries)

        slow_queries = [
            q for q in queries
            if float(q.get('time', 0)) * 1000 > self.THRESHOLD_MS
        ]

        if slow_queries:
            for q in slow_queries:
                logger.warning(
                    'Slow query (%.1fms): %s',
                    float(q['time']) * 1000,
                    q['sql'][:200],
                )

        if total_queries > 10:
            logger.warning(
                '%s %s — %d queries in %.1fms (possible N+1)',
                request.method,
                request.path,
                total_queries,
                duration_ms,
            )

        return response
