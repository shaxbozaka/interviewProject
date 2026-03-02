"""
Elasticsearch client with lazy initialization and graceful degradation.

If ES is unavailable, search falls back to PostgreSQL LIKE queries.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_client = None
_available = None

INDEX_NAME = "books"

BOOK_MAPPING = {
    "properties": {
        "title": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "suggest": {
                    "type": "completion",
                }
            },
        },
        "author": {
            "type": "text",
            "analyzer": "standard",
        },
        "isbn": {
            "type": "keyword",
        },
        "genre": {
            "type": "keyword",
        },
        "publication_date": {
            "type": "date",
        },
        "available": {
            "type": "boolean",
        },
    }
}


def get_client():
    """Lazy-init the ES client. Returns None if ES is unavailable."""
    global _client, _available
    if _available is False:
        return None
    if _client is not None:
        return _client
    try:
        from elasticsearch import Elasticsearch

        es_url = getattr(settings, "ELASTICSEARCH_URL", "http://localhost:9200")
        _client = Elasticsearch(es_url)
        _client.info()
        _available = True
        logger.info("Elasticsearch connected at %s", es_url)
        return _client
    except Exception as e:
        _available = False
        logger.warning("Elasticsearch unavailable: %s", e)
        return None


def reset_client():
    """Reset client state (useful for testing or reconnection)."""
    global _client, _available
    _client = None
    _available = None


def ensure_index():
    """Create the books index if it doesn't exist."""
    client = get_client()
    if client is None:
        return False
    try:
        if not client.indices.exists(index=INDEX_NAME):
            client.indices.create(index=INDEX_NAME, body={"mappings": BOOK_MAPPING})
            logger.info("Created index: %s", INDEX_NAME)
        return True
    except Exception as e:
        logger.error("Failed to create index: %s", e)
        return False


def index_book(book) -> bool:
    """Index a single book document."""
    client = get_client()
    if client is None:
        return False
    try:
        doc = {
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn or "",
            "genre": book.genre.slug if book.genre else "",
            "publication_date": book.publication_date.isoformat(),
            "available": book.available,
        }
        client.index(index=INDEX_NAME, id=str(book.id), body=doc)
        return True
    except Exception as e:
        logger.error("Failed to index book %s: %s", book.id, e)
        return False


def delete_book(book_id: int) -> bool:
    """Remove a book from the index."""
    client = get_client()
    if client is None:
        return False
    try:
        client.delete(index=INDEX_NAME, id=str(book_id), ignore=[404])
        return True
    except Exception as e:
        logger.error("Failed to delete book %s from index: %s", book_id, e)
        return False


def search_books(query: str, limit: int = 20) -> list[int] | None:
    """
    Full-text search across title and author.
    Returns list of book IDs, or None if ES is unavailable (signals fallback).
    """
    client = get_client()
    if client is None:
        return None
    try:
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "author"],
                    "fuzziness": "AUTO",
                }
            },
            "size": limit,
        }
        response = client.search(index=INDEX_NAME, body=body)
        return [int(hit["_id"]) for hit in response["hits"]["hits"]]
    except Exception as e:
        logger.error("ES search failed: %s", e)
        return None


def reindex_all():
    """Reindex all books from the database."""
    from apps.books.models import Book

    client = get_client()
    if client is None:
        return False
    books = Book.objects.select_related("genre").all()
    for book in books:
        index_book(book)
    logger.info("Reindexed %d books", books.count())
    return True
