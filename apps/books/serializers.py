from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import Book


class BookSerializer(ModelSerializer):
    get_rating = serializers.FloatField(read_only=True, default=None)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'publication_date', 'available', 'get_rating']
        read_only_fields = ['id', 'get_rating']

