import time
from core.cache import LRUCache


class TestLRUCacheBasicOperations:
    def test_put_and_get(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        assert cache.get("a") == 1

    def test_get_missing_key_returns_none(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        assert cache.get("missing") is None

    def test_put_updates_existing_key(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        cache.put("a", 2)
        assert cache.get("a") == 2
        assert cache.size == 1

    def test_delete_key(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        assert cache.delete("a") is True
        assert cache.get("a") is None

    def test_delete_missing_key_returns_false(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        assert cache.delete("missing") is False

    def test_clear(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert cache.size == 0
        assert cache.get("a") is None

    def test_contains(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        assert "a" in cache
        assert "b" not in cache

    def test_size(self):
        cache = LRUCache(capacity=5, default_ttl=None)
        for i in range(3):
            cache.put(str(i), i)
        assert cache.size == 3


class TestLRUEviction:
    def test_evicts_lru_when_at_capacity(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)  # should evict 'a'
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_access_prevents_eviction(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")  # 'a' is now most recently used
        cache.put("d", 4)  # should evict 'b' (not 'a')
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_update_prevents_eviction(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("a", 10)  # update 'a', now most recently used
        cache.put("d", 4)  # should evict 'b'
        assert cache.get("a") == 10
        assert cache.get("b") is None

    def test_eviction_order(self):
        """Verify strict LRU order: oldest untouched key evicts first."""
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        # Access order: c (most recent), b, a (least recent)
        cache.put("d", 4)  # evicts 'a'
        cache.put("e", 5)  # evicts 'b'
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4
        assert cache.get("e") == 5


class TestLRUTTL:
    def test_expired_entry_returns_none(self):
        cache = LRUCache(capacity=3, default_ttl=0.1)
        cache.put("a", 1)
        time.sleep(0.15)
        assert cache.get("a") is None

    def test_non_expired_entry_returns_value(self):
        cache = LRUCache(capacity=3, default_ttl=10.0)
        cache.put("a", 1)
        assert cache.get("a") == 1

    def test_per_key_ttl_overrides_default(self):
        cache = LRUCache(capacity=3, default_ttl=10.0)
        cache.put("a", 1, ttl=0.1)
        time.sleep(0.15)
        assert cache.get("a") is None

    def test_no_ttl_never_expires(self):
        cache = LRUCache(capacity=3, default_ttl=None)
        cache.put("a", 1)
        # Can't really test "never" but verify it works without ttl
        assert cache.get("a") == 1


class TestLRURepr:
    def test_repr(self):
        cache = LRUCache(capacity=5, default_ttl=None)
        cache.put("a", 1)
        assert repr(cache) == "LRUCache(capacity=5, size=1)"
