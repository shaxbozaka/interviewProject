"""
Per-request tracing: captures every processing step of every HTTP request.
Uses contextvars so each thread/async task has its own trace.
Stores last 200 traces in Redis for the dashboard to display.
"""

import contextvars
import json
import logging
import time
import uuid

logger = logging.getLogger(__name__)

_current_trace = contextvars.ContextVar('current_trace', default=None)


class RequestTrace:
    def __init__(self, method, path, user_id=None):
        self.id = uuid.uuid4().hex[:8]
        self.method = method
        self.path = path
        self.user_id = user_id
        self.start = time.time()
        self.steps = []
        self.status_code = None
        self.duration_ms = None

    def step(self, msg, cat='info'):
        elapsed = round((time.time() - self.start) * 1000, 1)
        self.steps.append({'ms': elapsed, 'msg': msg, 'cat': cat})

    def finish(self, status_code):
        self.status_code = status_code
        self.duration_ms = round((time.time() - self.start) * 1000, 1)

    def to_dict(self):
        return {
            'id': self.id,
            'method': self.method,
            'path': self.path,
            'user_id': self.user_id,
            'status': self.status_code,
            'duration_ms': self.duration_ms,
            'ts': self.start,
            'steps': self.steps,
        }


def start_trace(method, path, user_id=None):
    trace = RequestTrace(method, path, user_id)
    _current_trace.set(trace)
    return trace


def trace_step(msg, cat='info'):
    """Add a step to the current request trace. No-op if no trace active."""
    trace = _current_trace.get()
    if trace:
        trace.step(msg, cat)


def end_trace(status_code):
    trace = _current_trace.get()
    if trace:
        trace.finish(status_code)
        _save_trace(trace)
        _current_trace.set(None)
    return trace


def set_trace_user(user_id):
    trace = _current_trace.get()
    if trace:
        trace.user_id = user_id


def _save_trace(trace):
    """Push trace to Redis list (LIFO, capped at 200)."""
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        conn.lpush('req_traces', json.dumps(trace.to_dict()))
        conn.ltrim('req_traces', 0, 199)
    except Exception:
        pass  # tracing must never break the app


def get_recent_traces(count=50):
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        raw = conn.lrange('req_traces', 0, count - 1)
        return [json.loads(r) for r in raw]
    except Exception:
        return []
