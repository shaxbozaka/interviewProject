import pytest
from unittest.mock import patch, MagicMock
from core.caching import (
    cache_get, cache_set, cache_delete,
    cache_invalidate_pattern, make_cache_key, get_l1_cache,
)


class TestMakeCacheKey:
    def test_deterministic(self):
        key1 = make_cache_key('books', 'list', page=1)
        key2 = make_cache_key('books', 'list', page=1)
        assert key1 == key2

    def test_different_args_different_keys(self):
        key1 = make_cache_key('books', 'list', page=1)
        key2 = make_cache_key('books', 'list', page=2)
        assert key1 != key2

    def test_prefix_included(self):
        key = make_cache_key('books', 'detail', 42)
        assert key.startswith('books:')


class TestTwoTierCache:
    def setup_method(self):
        """Clear L1 cache before each test."""
        get_l1_cache().clear()

    def test_set_and_get_from_l1(self):
        cache_set('test_key', 'test_value', l1_ttl=60.0, l2_ttl=300)
        # Should hit L1
        assert cache_get('test_key') == 'test_value'

    def test_l2_fallback_when_l1_misses(self):
        cache_set('test_key', 'test_value', l1_ttl=60.0, l2_ttl=300)
        # Clear L1 only
        get_l1_cache().clear()
        # Should fall through to L2 (LocMemCache in test settings)
        assert cache_get('test_key') == 'test_value'
        # Should now be promoted back to L1
        assert get_l1_cache().get('test_key') == 'test_value'

    def test_delete_removes_from_both(self):
        cache_set('test_key', 'test_value')
        cache_delete('test_key')
        assert cache_get('test_key') is None

    def test_invalidate_pattern_clears_l1(self):
        cache_set('books:123', 'value1')
        cache_set('books:456', 'value2')
        cache_invalidate_pattern('books')
        # L1 should be cleared
        assert get_l1_cache().size == 0

    def test_cache_miss_returns_none(self):
        assert cache_get('nonexistent') is None
