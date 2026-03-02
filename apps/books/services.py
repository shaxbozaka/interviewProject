from django.db import models
from django.db.models import Avg, QuerySet

from .models import Book, Rating


class BookRepository:
    """Encapsulates all Book data access logic."""

    @staticmethod
    def get_all_with_ratings() -> QuerySet:
        return Book.objects.annotate(
            get_rating=Avg('ratings__rate')
        )

    @staticmethod
    def get_by_id(book_id: int) -> Book:
        return Book.objects.get(pk=book_id)

    @staticmethod
    def get_by_genre(queryset: QuerySet, genre_slug: str) -> QuerySet:
        return queryset.filter(genre__slug=genre_slug)

    @staticmethod
    def search(queryset: QuerySet, query: str) -> QuerySet:
        return queryset.filter(
            models.Q(title__icontains=query) | models.Q(author__icontains=query)
        )

    @staticmethod
    def create_rating(book: Book, user, rate: int, review: str = '') -> Rating:
        return Rating.objects.create(
            book=book, user=user, rate=rate, review=review,
        )
