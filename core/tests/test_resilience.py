import time
from unittest.mock import patch

import pytest

from core.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    circuit_breaker,
    retry_with_backoff,
)


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_success_keeps_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_failure_increments_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(self._failing_func)
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_raises_error(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: 42)

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        time.sleep(0.15)
        result = cb.call(lambda: 'recovered')
        assert result == 'recovered'
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        time.sleep(0.15)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        cb.call(lambda: 'ok')
        assert cb.failure_count == 0

    def test_manual_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(self._failing_func)
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_only_expected_exceptions_count(self):
        cb = CircuitBreaker(
            failure_threshold=2,
            expected_exceptions=(ValueError,),
        )
        with pytest.raises(TypeError):
            cb.call(self._type_error_func)
        # TypeError is not an expected exception, so failure count should be 0
        assert cb.failure_count == 0

    @staticmethod
    def _failing_func():
        raise ValueError('test failure')

    @staticmethod
    def _type_error_func():
        raise TypeError('type error')


class TestCircuitBreakerDecorator:
    def test_decorator_wraps_function(self):
        @circuit_breaker(failure_threshold=3)
        def my_func():
            return 'hello'

        assert my_func() == 'hello'

    def test_decorator_opens_circuit(self):
        call_count = 0

        @circuit_breaker(failure_threshold=2)
        def my_func():
            nonlocal call_count
            call_count += 1
            raise ValueError('fail')

        with pytest.raises(ValueError):
            my_func()
        with pytest.raises(ValueError):
            my_func()
        with pytest.raises(CircuitBreakerError):
            my_func()
        assert call_count == 2

    def test_decorator_with_fallback(self):
        @circuit_breaker(
            failure_threshold=1,
            fallback=lambda: 'fallback_value',
        )
        def my_func():
            raise ValueError('fail')

        with pytest.raises(ValueError):
            my_func()
        # Circuit is now open, fallback should be called
        result = my_func()
        assert result == 'fallback_value'

    def test_breaker_attribute(self):
        @circuit_breaker(failure_threshold=5)
        def my_func():
            pass

        assert hasattr(my_func, 'breaker')
        assert isinstance(my_func.breaker, CircuitBreaker)


class TestRetryWithBackoff:
    @patch('core.resilience.time.sleep')
    def test_retries_on_failure(self, mock_sleep):
        attempts = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError('not yet')
            return 'success'

        result = flaky()
        assert result == 'success'
        assert attempts == 3

    @patch('core.resilience.time.sleep')
    def test_raises_after_max_retries(self, mock_sleep):
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fail():
            raise ValueError('always')

        with pytest.raises(ValueError, match='always'):
            always_fail()

    @patch('core.resilience.time.sleep')
    def test_exponential_backoff_delays(self, mock_sleep):
        @retry_with_backoff(
            max_retries=3, base_delay=1.0, jitter=False,
        )
        def always_fail():
            raise ValueError('fail')

        with pytest.raises(ValueError):
            always_fail()

        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert delays[0] == 1.0   # 1.0 * 2^0
        assert delays[1] == 2.0   # 1.0 * 2^1
        assert delays[2] == 4.0   # 1.0 * 2^2

    @patch('core.resilience.time.sleep')
    def test_max_delay_cap(self, mock_sleep):
        @retry_with_backoff(
            max_retries=5, base_delay=10.0, max_delay=20.0, jitter=False,
        )
        def always_fail():
            raise ValueError('fail')

        with pytest.raises(ValueError):
            always_fail()

        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert all(d <= 20.0 for d in delays)

    @patch('core.resilience.time.sleep')
    def test_only_retries_expected_exceptions(self, mock_sleep):
        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            expected_exceptions=(ValueError,),
        )
        def raise_type_error():
            raise TypeError('wrong type')

        with pytest.raises(TypeError):
            raise_type_error()
        # Should not have retried
        mock_sleep.assert_not_called()

    def test_no_retry_on_success(self):
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def succeed():
            return 'ok'

        assert succeed() == 'ok'
