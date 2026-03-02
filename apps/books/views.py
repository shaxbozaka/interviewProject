from rest_framework import viewsets, filters
from django.db.models import Avg

from .models import Book
from .serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author', 'publication_date', 'get_rating']
    ordering = ['-get_rating']

    def get_queryset(self):
        return Book.objects.annotate(
            get_rating=Avg('ratings__rate')
        ).order_by(*self.ordering)
    
    