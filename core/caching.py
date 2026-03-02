import hashlib
import json
import logging

from django.core.cache import cache as redis_cache

from .cache import LRUCache
from .tracing import trace_step

logger = logging.getLogger(__name__)

# Global L1 cache instance (in-process, per worker)
_l1_cache = LRUCache(capacity=256, default_ttl=60.0)


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a deterministic cache key from prefix and arguments."""
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    hash_suffix = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"{prefix}:{hash_suffix}"


def cache_get(key: str):
    """Two-tier cache get: L1 (LRU) -> L2 (Redis) -> None."""
    # Try L1 first
    value = _l1_cache.get(key)
    if value is not None:
        logger.debug("L1 cache hit: %s", key)
        trace_step(f"Cache L1 HIT: {key}", "cache")
        return value

    # Try L2 (Redis)
    value = redis_cache.get(key)
    if value is not None:
        logger.debug("L2 cache hit: %s", key)
        trace_step(f"Cache L1 MISS → L2 (Redis) HIT: {key}", "cache")
        # Promote to L1
        _l1_cache.put(key, value)
        return value

    logger.debug("Cache miss: %s", key)
    trace_step(f"Cache MISS (L1 + L2): {key}", "cache")
    return None


def cache_set(key: str, value, l1_ttl: float = 60.0, l2_ttl: int = 300):
    """Set value in both L1 and L2 cache."""
    _l1_cache.put(key, value, ttl=l1_ttl)
    redis_cache.set(key, value, timeout=l2_ttl)


def cache_delete(key: str):
    """Delete from both cache layers."""
    _l1_cache.delete(key)
    redis_cache.delete(key)


def cache_invalidate_pattern(prefix: str):
    """
    Invalidate all keys matching a prefix.
    L1: cleared entirely (simpler than pattern matching).
    L2: uses Redis key deletion if available.
    """
    _l1_cache.clear()
    try:
        redis_cache.delete_pattern(f"{prefix}:*")
    except (AttributeError, Exception):
        # Fallback: django's LocMemCache doesn't support delete_pattern
        pass


def get_l1_cache() -> LRUCache:
    """Access the L1 cache instance (for testing/monitoring)."""
    return _l1_cache
