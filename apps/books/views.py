from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from core.caching import cache_get, cache_set, make_cache_key
from core.exports import streaming_csv_response
from core.tracing import trace_step
from .models import Book, Genre
from .serializers import BookSerializer, GenreSerializer, RatingSerializer
from .services import BookRepository

BOOK_LIST_CACHE_KEY = make_cache_key("books", "list", "default")


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all().order_by("name")
    serializer_class = GenreSerializer
    lookup_field = "slug"
    pagination_class = PageNumberPagination


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author", "isbn"]
    ordering_fields = ["title", "author", "publication_date"]
    ordering = ["-publication_date"]

    def get_queryset(self):
        queryset = BookRepository.get_all_with_ratings()
        genre = self.request.query_params.get("genre")
        if genre:
            queryset = BookRepository.get_by_genre(queryset, genre)
        return queryset

    def list(self, request, *args, **kwargs):
        # Cache the full paginated book list response
        genre = request.query_params.get("genre")
        page = request.query_params.get("page", "1")
        search = request.query_params.get("search", "")
        key = make_cache_key("books", "list", genre or "", page, search)

        cached = cache_get(key)
        if cached is not None:
            trace_step("BookViewSet.list() → CACHE HIT (L1/Redis)", "cache")
            return Response(cached)

        trace_step("BookViewSet.list() → CACHE MISS, querying DB", "db")
        response = super().list(request, *args, **kwargs)
        cache_set(key, response.data, l1_ttl=30.0, l2_ttl=120)
        trace_step("BookViewSet.list() → cached response (L1=30s, Redis=120s)", "cache")
        return response

    @action(detail=False, methods=["get"], url_path="export")
    def export_csv(self, request):
        """Stream all books as CSV using lazy generator (code optimization demo)."""
        queryset = Book.objects.all()
        fields = [
            "title",
            "author",
            "isbn",
            "publication_date",
            "copies_total",
            "copies_available",
        ]
        return streaming_csv_response(queryset, fields, "books_export.csv")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        book = self.get_object()
        trace_step(f'BookViewSet.rate() book={book.id} "{book.title}"', "logic")
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating = BookRepository.create_rating(
            book=book,
            user=request.user,
            rate=serializer.validated_data["rate"],
            review=serializer.validated_data.get("review", ""),
        )
        return Response(RatingSerializer(rating).data, status=status.HTTP_201_CREATED)
