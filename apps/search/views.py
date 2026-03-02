import logging

from django.db import models
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.books.models import Book
from apps.books.serializers import BookSerializer
from core.tracing import trace_step
from . import es_client
from .trie_service import get_trie

logger = logging.getLogger(__name__)


class BookSearchView(APIView):
    """
    Full-text search via Elasticsearch with PostgreSQL LIKE fallback.

    GET /api/v1/search/?q=django
    """

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"detail": 'Query parameter "q" is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        trace_step(f'BookSearchView: q="{query}"', "logic")
        book_ids = es_client.search_books(query)

        if book_ids is not None:
            books = Book.objects.filter(id__in=book_ids)
            id_order = {bid: idx for idx, bid in enumerate(book_ids)}
            books = sorted(books, key=lambda b: id_order.get(b.id, 0))
            source = "elasticsearch"
            trace_step(
                f'Elasticsearch: {len(book_ids)} results for "{query}"', "search"
            )
        else:
            books = Book.objects.filter(
                models.Q(title__icontains=query) | models.Q(author__icontains=query)
            )[:20]
            source = "postgresql"
            trace_step(
                f'ES unavailable → PostgreSQL LIKE fallback for "{query}"', "search"
            )

        serializer = BookSerializer(books, many=True)
        trace_step(
            f"Search complete: {len(serializer.data)} results via {source}", "search"
        )
        return Response(
            {
                "source": source,
                "count": len(serializer.data),
                "results": serializer.data,
            }
        )


class AutocompleteView(APIView):
    """
    Trie-based autocomplete for book titles.

    GET /api/v1/search/autocomplete/?q=har
    Returns: ["Harry Potter and the ...", "Harmony in ...", ...]
    """

    permission_classes = [AllowAny]

    def get(self, request):
        prefix = request.query_params.get("q", "").strip()
        if not prefix:
            return Response(
                {"detail": 'Query parameter "q" is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = min(int(request.query_params.get("limit", 10)), 50)
        trie = get_trie()
        trace_step(f'Trie.autocomplete("{prefix}", limit={limit})', "search")
        suggestions = trie.autocomplete(prefix, limit=limit)
        trace_step(f"Trie: {len(suggestions)} suggestions returned", "search")

        return Response(
            {
                "query": prefix,
                "suggestions": suggestions,
            }
        )
