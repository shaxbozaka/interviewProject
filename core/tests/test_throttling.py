from unittest.mock import MagicMock

import pytest

from core.throttling import TokenBucketThrottle, BurstThrottle, StrictThrottle, _limiters


@pytest.fixture(autouse=True)
def clear_limiters():
    """Clear global limiter state between tests."""
    _limiters.clear()
    yield
    _limiters.clear()


class TestTokenBucketThrottle:
    def _make_request(self, user=None, ip='127.0.0.1'):
        request = MagicMock()
        request.META = {'REMOTE_ADDR': ip}
        if user is not None:
            request.user = user
        else:
            anon = MagicMock()
            anon.is_authenticated = False
            request.user = anon
        return request

    def test_authenticated_user_ident(self):
        throttle = TokenBucketThrottle()
        user = MagicMock()
        user.is_authenticated = True
        user.pk = 42
        request = self._make_request(user=user)
        ident = throttle.get_ident(request)
        assert ident == 'user:42'

    def test_anonymous_user_ident(self):
        throttle = TokenBucketThrottle()
        request = self._make_request(ip='10.0.0.1')
        ident = throttle.get_ident(request)
        assert ident == 'ip:10.0.0.1'

    def test_xff_header_ident(self):
        throttle = TokenBucketThrottle()
        request = MagicMock()
        request.user.is_authenticated = False
        request.META = {
            'HTTP_X_FORWARDED_FOR': '203.0.113.50, 70.41.3.18',
            'REMOTE_ADDR': '127.0.0.1',
        }
        ident = throttle.get_ident(request)
        assert ident == 'ip:203.0.113.50'

    def test_allow_request_within_limit(self):
        throttle = BurstThrottle()
        request = self._make_request(ip='1.2.3.4')
        view = MagicMock()
        assert throttle.allow_request(request, view) is True

    def test_strict_throttle_lower_burst(self):
        throttle = StrictThrottle()
        request = self._make_request(ip='1.2.3.4')
        view = MagicMock()
        allowed = 0
        for _ in range(10):
            if throttle.allow_request(request, view):
                allowed += 1
        assert allowed == 5  # burst limit

    def test_wait_returns_positive_when_limited(self):
        throttle = StrictThrottle()
        request = self._make_request(ip='5.5.5.5')
        view = MagicMock()
        for _ in range(5):
            throttle.allow_request(request, view)
        throttle.allow_request(request, view)  # should be denied
        wait = throttle.wait()
        assert wait > 0
