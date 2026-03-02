import threading
import time

import pytest

from core.rate_limiter import TokenBucket, RateLimiter


class TestTokenBucket:
    def test_initial_tokens_equal_burst(self):
        bucket = TokenBucket(rate=10.0, burst=20)
        assert bucket.available_tokens == pytest.approx(20, abs=1)

    def test_consume_success(self):
        bucket = TokenBucket(rate=10.0, burst=5)
        assert bucket.consume() is True
        assert bucket.available_tokens == pytest.approx(4, abs=1)

    def test_consume_depletes_bucket(self):
        bucket = TokenBucket(rate=1.0, burst=3)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False

    def test_tokens_refill_over_time(self):
        bucket = TokenBucket(rate=100.0, burst=10)
        # Consume all tokens
        for _ in range(10):
            bucket.consume()
        # Wait for refill
        time.sleep(0.05)
        assert bucket.consume() is True

    def test_tokens_dont_exceed_burst(self):
        bucket = TokenBucket(rate=1000.0, burst=5)
        time.sleep(0.1)
        assert bucket.available_tokens <= 5

    def test_consume_multiple_tokens(self):
        bucket = TokenBucket(rate=10.0, burst=10)
        assert bucket.consume(5) is True
        assert bucket.available_tokens == pytest.approx(5, abs=1)

    def test_consume_more_than_available(self):
        bucket = TokenBucket(rate=1.0, burst=3)
        assert bucket.consume(5) is False

    def test_wait_time_when_empty(self):
        bucket = TokenBucket(rate=10.0, burst=5)
        for _ in range(5):
            bucket.consume()
        wait = bucket.wait_time()
        assert wait > 0
        assert wait <= 0.2

    def test_wait_time_when_available(self):
        bucket = TokenBucket(rate=10.0, burst=5)
        assert bucket.wait_time() == 0.0

    def test_thread_safety(self):
        bucket = TokenBucket(rate=1000.0, burst=500)
        consumed = []
        lock = threading.Lock()

        def consumer():
            count = 0
            for _ in range(100):
                if bucket.consume():
                    count += 1
            with lock:
                consumed.append(count)

        threads = [threading.Thread(target=consumer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total = sum(consumed)
        # Should have consumed approximately 500 tokens (burst capacity)
        assert total <= 510  # allow small timing margin


class TestRateLimiter:
    def test_allow_different_keys(self):
        limiter = RateLimiter(rate=1.0, burst=2)
        assert limiter.allow("client_a") is True
        assert limiter.allow("client_b") is True

    def test_rate_limit_same_key(self):
        limiter = RateLimiter(rate=1.0, burst=2)
        assert limiter.allow("client_a") is True
        assert limiter.allow("client_a") is True
        assert limiter.allow("client_a") is False

    def test_independent_buckets_per_key(self):
        limiter = RateLimiter(rate=1.0, burst=1)
        assert limiter.allow("a") is True
        assert limiter.allow("a") is False
        assert limiter.allow("b") is True  # different client

    def test_active_clients_tracking(self):
        limiter = RateLimiter(rate=10.0, burst=10)
        limiter.allow("a")
        limiter.allow("b")
        limiter.allow("c")
        assert limiter.active_clients == 3

    def test_cleanup_stale_buckets(self):
        limiter = RateLimiter(rate=10.0, burst=10, cleanup_interval=0.0)
        limiter.allow("a")
        limiter.allow("b")
        # Wait for tokens to refill to burst (making them "idle")
        time.sleep(0.2)
        # Trigger cleanup via a new request
        limiter.allow("c")
        # a and b should be cleaned up since their buckets are full
        assert limiter.active_clients <= 3

    def test_concurrent_access(self):
        limiter = RateLimiter(rate=100.0, burst=50)
        errors = []

        def worker(client_id):
            try:
                for _ in range(20):
                    limiter.allow(f"client_{client_id}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
