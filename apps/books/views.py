from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from core.exports import streaming_csv_response
from .models import Book, Genre
from .serializers import BookSerializer, GenreSerializer, RatingSerializer
from .services import BookRepository


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    lookup_field = 'slug'


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author', 'isbn']
    ordering_fields = ['title', 'author', 'publication_date']
    ordering = ['-publication_date']

    def get_queryset(self):
        queryset = BookRepository.get_all_with_ratings()
        genre = self.request.query_params.get('genre')
        if genre:
            queryset = BookRepository.get_by_genre(queryset, genre)
        return queryset

    @action(detail=False, methods=['get'], url_path='export')
    def export_csv(self, request):
        """Stream all books as CSV using lazy generator (code optimization demo)."""
        queryset = Book.objects.all()
        fields = ['title', 'author', 'isbn', 'publication_date', 'copies_total', 'copies_available']
        return streaming_csv_response(queryset, fields, 'books_export.csv')

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        book = self.get_object()
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating = BookRepository.create_rating(
            book=book, user=request.user,
            rate=serializer.validated_data['rate'],
            review=serializer.validated_data.get('review', ''),
        )
        return Response(RatingSerializer(rating).data, status=status.HTTP_201_CREATED)
