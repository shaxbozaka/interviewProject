"""
Token Bucket rate limiter implementation.

DSA: Token Bucket Algorithm
- Tokens are added at a fixed rate (tokens_per_second)
- Bucket has a maximum capacity (burst)
- Each request consumes one token
- If no tokens available, request is rejected

Time complexity: O(1) per request
Space complexity: O(1) per bucket, O(n) for n distinct clients

Thread-safe via threading.Lock.
"""

import threading
import time


class TokenBucket:
    """
    A single token bucket for rate limiting.

    Args:
        rate: Tokens added per second (sustained rate)
        burst: Maximum tokens the bucket can hold (burst capacity)
    """

    __slots__ = ("rate", "burst", "_tokens", "_last_refill", "_lock")

    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        Returns True if tokens were available, False otherwise.
        """
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens (approximate, for monitoring)."""
        with self._lock:
            self._refill()
            return self._tokens

    def wait_time(self, tokens: int = 1) -> float:
        """Estimated seconds to wait before `tokens` become available."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                return 0.0
            deficit = tokens - self._tokens
            return deficit / self.rate


class RateLimiter:
    """
    Per-client rate limiter using token buckets.

    Each unique client key gets its own bucket.
    Stale buckets are cleaned up periodically.
    """

    def __init__(self, rate: float, burst: int, cleanup_interval: float = 60.0):
        self.rate = rate
        self.burst = burst
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.monotonic()

    def allow(self, key: str, tokens: int = 1) -> bool:
        """Check if a request from `key` should be allowed."""
        bucket = self._get_bucket(key)
        return bucket.consume(tokens)

    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        with self._lock:
            self._maybe_cleanup()
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(self.rate, self.burst)
            return self._buckets[key]

    def _maybe_cleanup(self) -> None:
        """Remove stale buckets that haven't been used recently."""
        now = time.monotonic()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        # Remove buckets that are full (idle clients)
        stale_keys = [
            key
            for key, bucket in self._buckets.items()
            if bucket.available_tokens >= bucket.burst
        ]
        for key in stale_keys:
            del self._buckets[key]

    @property
    def active_clients(self) -> int:
        """Number of tracked client buckets."""
        return len(self._buckets)
