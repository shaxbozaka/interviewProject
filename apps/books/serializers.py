from rest_framework import serializers
from .models import Book, Genre, Rating


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug"]


class RatingSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Rating
        fields = ["id", "rate", "review", "username", "created_at"]
        read_only_fields = ["id", "username", "created_at"]


class BookSerializer(serializers.ModelSerializer):
    get_rating = serializers.FloatField(read_only=True, default=None)
    genre_name = serializers.CharField(source="genre.name", read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "isbn",
            "publication_date",
            "genre",
            "genre_name",
            "available",
            "description",
            "read_url",
            "copies_total",
            "copies_available",
            "get_rating",
        ]
        read_only_fields = ["id", "get_rating", "genre_name"]
