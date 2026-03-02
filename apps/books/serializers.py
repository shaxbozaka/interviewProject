from rest_framework.serializers import ModelSerializer

from .models import Book


class BookSerializer(ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'publication_date', 'available', 'get_rating']
        read_only_fields = ['id', 'get_rating']

