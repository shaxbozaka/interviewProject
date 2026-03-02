"""
Resiliency patterns: Circuit Breaker + Retry with Exponential Backoff.

Circuit Breaker states:
  CLOSED  → Normal operation. Failures increment counter.
  OPEN    → Fail-fast. After `recovery_timeout`, transitions to HALF_OPEN.
  HALF_OPEN → Allows one trial request. Success → CLOSED, failure → OPEN.

Retry:
  Exponential backoff with jitter: delay = base_delay * 2^attempt + random jitter.
"""

import enum
import functools
import logging
import random
import threading
import time

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when the circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit Breaker implementation.

    Args:
        failure_threshold: Number of consecutive failures before opening
        recovery_timeout: Seconds to wait before trying again (half-open)
        expected_exceptions: Tuple of exception types that count as failures
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
            return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def call(self, func, *args, **kwargs):
        """Execute func through the circuit breaker."""
        state = self.state
        if state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker is open (failures={self._failure_count})"
            )

        try:
            result = func(*args, **kwargs)
        except self.expected_exceptions:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    def _on_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker OPEN after %d failures",
                    self._failure_count,
                )

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    fallback=None,
):
    """
    Decorator that wraps a function with a circuit breaker.

    Args:
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before half-open
        expected_exceptions: Exception types that count as failures
        fallback: Optional callable to invoke when circuit is open
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exceptions=expected_exceptions,
    )

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerError:
                if fallback is not None:
                    return fallback(*args, **kwargs)
                raise

        wrapper.breaker = breaker
        return wrapper

    return decorator


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    jitter: bool = True,
):
    """
    Decorator for retry with exponential backoff.

    Delay formula: min(base_delay * 2^attempt + jitter, max_delay)
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except expected_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    delay = min(base_delay * (2**attempt), max_delay)
                    if jitter:
                        delay += random.uniform(0, delay * 0.1)
                    logger.warning(
                        "Retry %d/%d for %s after %.2fs: %s",
                        attempt + 1,
                        max_retries,
                        func.__name__,
                        delay,
                        e,
                    )
                    time.sleep(delay)
            raise last_exception

        wrapper.max_retries = max_retries
        return wrapper

    return decorator
