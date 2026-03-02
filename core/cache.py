import threading
import time
from typing import Any


class Node:
    """Doubly linked list node for LRU cache."""

    __slots__ = ('key', 'value', 'expires_at', 'prev', 'next')

    def __init__(self, key: str, value: Any, expires_at: float | None = None):
        self.key = key
        self.value = value
        self.expires_at = expires_at
        self.prev: Node | None = None
        self.next: Node | None = None


class LRUCache:
    """
    Least Recently Used cache using doubly linked list + hashmap.

    Time complexity: O(1) for get, put, delete.
    Space complexity: O(capacity).

    The doubly linked list maintains access order (most recent at head).
    The hashmap provides O(1) key lookup to the corresponding node.
    When capacity is exceeded, the tail node (least recently used) is evicted.
    """

    def __init__(self, capacity: int = 128, default_ttl: float | None = 60.0):
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._cache: dict[str, Node] = {}
        self._lock = threading.Lock()

        # Sentinel nodes to avoid edge cases
        self._head = Node('', None)  # Most recently used
        self._tail = Node('', None)  # Least recently used
        self._head.next = self._tail
        self._tail.prev = self._head

    def _remove_node(self, node: Node) -> None:
        """Remove a node from the linked list. O(1)."""
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_head(self, node: Node) -> None:
        """Add a node right after the head sentinel. O(1)."""
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node
        self._head.next = node

    def _move_to_head(self, node: Node) -> None:
        """Move an existing node to the head (most recently used). O(1)."""
        self._remove_node(node)
        self._add_to_head(node)

    def _evict_tail(self) -> Node | None:
        """Remove and return the tail node (least recently used). O(1)."""
        node = self._tail.prev
        if node is self._head:
            return None
        self._remove_node(node)
        return node

    def _is_expired(self, node: Node) -> bool:
        """Check if a node's TTL has expired."""
        if node.expires_at is None:
            return False
        return time.monotonic() > node.expires_at

    def get(self, key: str) -> Any | None:
        """
        Get value by key. Returns None if not found or expired.
        Moves accessed node to head (most recently used).
        """
        with self._lock:
            node = self._cache.get(key)
            if node is None:
                return None
            if self._is_expired(node):
                self._remove_node(node)
                del self._cache[key]
                return None
            self._move_to_head(node)
            return node.value

    def put(self, key: str, value: Any, ttl: float | None = None) -> None:
        """
        Add or update a key-value pair.
        If at capacity, evicts the least recently used entry.
        """
        if ttl is None:
            ttl = self.default_ttl

        expires_at = time.monotonic() + ttl if ttl is not None else None

        with self._lock:
            if key in self._cache:
                node = self._cache[key]
                node.value = value
                node.expires_at = expires_at
                self._move_to_head(node)
                return

            node = Node(key, value, expires_at)
            self._cache[key] = node
            self._add_to_head(node)

            if len(self._cache) > self.capacity:
                evicted = self._evict_tail()
                if evicted:
                    del self._cache[evicted.key]

    def delete(self, key: str) -> bool:
        """Remove a key. Returns True if found and removed."""
        with self._lock:
            node = self._cache.get(key)
            if node is None:
                return False
            self._remove_node(node)
            del self._cache[key]
            return True

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._cache.clear()
            self._head.next = self._tail
            self._tail.prev = self._head

    @property
    def size(self) -> int:
        """Current number of entries (including expired but not yet evicted)."""
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Support 'key in cache' syntax."""
        return self.get(key) is not None

    def __repr__(self) -> str:
        return f'LRUCache(capacity={self.capacity}, size={self.size})'
