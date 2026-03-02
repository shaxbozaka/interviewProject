import logging
import time

from django.db import connection

logger = logging.getLogger('django.db.slow_queries')


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
