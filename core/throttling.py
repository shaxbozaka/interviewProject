"""
DRF throttle classes backed by the custom token bucket algorithm.

Application-level rate limiting that complements Nginx rate limiting.
Nginx handles L7 (per-IP), this handles per-user and per-endpoint.
"""
from rest_framework.throttling import BaseThrottle

from .rate_limiter import RateLimiter

# Global rate limiters (singleton per rate policy)
_limiters: dict[str, RateLimiter] = {}


def _get_limiter(name: str, rate: float, burst: int) -> RateLimiter:
    if name not in _limiters:
        _limiters[name] = RateLimiter(rate=rate, burst=burst)
    return _limiters[name]


class TokenBucketThrottle(BaseThrottle):
    """
    Base throttle class using token bucket algorithm.

    Subclass and set `rate` (requests/sec) and `burst` (max burst).
    """
    rate = 10.0
    burst = 20
    scope = 'default'

    def get_ident(self, request):
        """Get a unique identifier for the client."""
        if request.user and request.user.is_authenticated:
            return f'user:{request.user.pk}'
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return f'ip:{xff.split(",")[0].strip()}'
        return f'ip:{request.META.get("REMOTE_ADDR", "unknown")}'

    def allow_request(self, request, view):
        self.ident = self.get_ident(request)
        limiter = _get_limiter(self.scope, self.rate, self.burst)
        return limiter.allow(self.ident)

    def wait(self):
        limiter = _get_limiter(self.scope, self.rate, self.burst)
        bucket = limiter._get_bucket(self.ident)
        return bucket.wait_time()


class BurstThrottle(TokenBucketThrottle):
    """High burst, moderate sustained rate — for general API endpoints."""
    rate = 10.0
    burst = 30
    scope = 'burst'


class StrictThrottle(TokenBucketThrottle):
    """Low rate for sensitive endpoints (login, registration)."""
    rate = 2.0
    burst = 5
    scope = 'strict'


class SearchThrottle(TokenBucketThrottle):
    """Higher rate for search/autocomplete endpoints."""
    rate = 30.0
    burst = 50
    scope = 'search'
