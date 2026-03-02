from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db.models import Avg

from .models import Book, Genre
from .serializers import BookSerializer, GenreSerializer, RatingSerializer


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
        queryset = Book.objects.annotate(
            get_rating=Avg('ratings__rate')
        )
        genre = self.request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(genre__slug=genre)
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        book = self.get_object()
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(book=book, user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
