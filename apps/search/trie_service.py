"""
Singleton Trie service for autocomplete.

Loads book titles into the Trie on first access, with weights based on
reservation count (popularity). Can be refreshed when books are added/updated.
"""

import logging

from core.trie import Trie

logger = logging.getLogger(__name__)

_trie: Trie | None = None


def get_trie() -> Trie:
    """Get or build the autocomplete trie."""
    global _trie
    if _trie is None:
        _trie = _build_trie()
    return _trie


def refresh_trie() -> None:
    """Rebuild the trie from the database."""
    global _trie
    _trie = _build_trie()
    logger.info("Autocomplete trie refreshed")


def _build_trie() -> Trie:
    """Build a fresh trie from all book titles + authors."""
    from apps.books.models import Book

    trie = Trie()
    items = []
    for book in Book.objects.only("title", "author", "copies_total"):
        items.append((book.title, book.copies_total))
        items.append((book.author, 0))
    trie.bulk_insert(items)
    logger.info("Trie built with %d entries", len(trie))
    return trie
