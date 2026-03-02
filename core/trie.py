"""
Trie (prefix tree) implementation for autocomplete.

DSA: Trie
- Insert: O(m) where m = length of word
- Search: O(m)
- Prefix search: O(m + k) where k = number of matches
- Space: O(N * m) where N = number of words

Thread-safe via threading.Lock for concurrent read/write.
"""
import threading
from collections import deque


class TrieNode:
    __slots__ = ('children', 'is_end', 'weight', 'value')

    def __init__(self):
        self.children: dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.weight: int = 0
        self.value: str = ''


class Trie:
    def __init__(self):
        self.root = TrieNode()
        self._lock = threading.Lock()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def insert(self, word: str, weight: int = 0) -> None:
        """Insert a word into the trie with an optional weight for ranking."""
        if not word:
            return
        normalized = word.lower().strip()
        with self._lock:
            node = self.root
            for char in normalized:
                if char not in node.children:
                    node.children[char] = TrieNode()
                node = node.children[char]
            if not node.is_end:
                self._size += 1
            node.is_end = True
            node.weight = weight
            node.value = word  # preserve original casing

    def search(self, word: str) -> bool:
        """Return True if the exact word exists in the trie."""
        if not word:
            return False
        normalized = word.lower().strip()
        node = self._find_node(normalized)
        return node is not None and node.is_end

    def starts_with(self, prefix: str) -> bool:
        """Return True if any word in the trie starts with the given prefix."""
        if not prefix:
            return False
        normalized = prefix.lower().strip()
        return self._find_node(normalized) is not None

    def autocomplete(self, prefix: str, limit: int = 10) -> list[str]:
        """
        Return up to `limit` words that start with `prefix`,
        ordered by weight (descending), then alphabetically.
        """
        if not prefix:
            return []
        normalized = prefix.lower().strip()
        node = self._find_node(normalized)
        if node is None:
            return []
        results: list[tuple[int, str]] = []
        self._collect_words(node, results)
        results.sort(key=lambda x: (-x[0], x[1]))
        return [value for _, value in results[:limit]]

    def delete(self, word: str) -> bool:
        """Delete a word from the trie. Returns True if the word was found and deleted."""
        if not word:
            return False
        normalized = word.lower().strip()
        with self._lock:
            return self._delete(self.root, normalized, 0)

    def _find_node(self, normalized: str) -> TrieNode | None:
        """Traverse the trie to find the node at the end of the normalized string."""
        node = self.root
        for char in normalized:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def _collect_words(self, node: TrieNode, results: list[tuple[int, str]]) -> None:
        """BFS to collect all words under a node."""
        queue = deque([node])
        while queue:
            current = queue.popleft()
            if current.is_end:
                results.append((current.weight, current.value))
            for child in current.children.values():
                queue.append(child)

    def _delete(self, node: TrieNode, word: str, depth: int) -> bool:
        """Recursively delete a word. Prunes empty branches."""
        if depth == len(word):
            if not node.is_end:
                return False
            node.is_end = False
            node.value = ''
            node.weight = 0
            self._size -= 1
            return len(node.children) == 0

        char = word[depth]
        if char not in node.children:
            return False

        should_prune = self._delete(node.children[char], word, depth + 1)
        if should_prune:
            del node.children[char]
            return not node.is_end and len(node.children) == 0
        return False

    def bulk_insert(self, items: list[tuple[str, int]]) -> None:
        """Insert multiple (word, weight) pairs efficiently under a single lock."""
        with self._lock:
            for word, weight in items:
                if not word:
                    continue
                normalized = word.lower().strip()
                node = self.root
                for char in normalized:
                    if char not in node.children:
                        node.children[char] = TrieNode()
                    node = node.children[char]
                if not node.is_end:
                    self._size += 1
                node.is_end = True
                node.weight = weight
                node.value = word
