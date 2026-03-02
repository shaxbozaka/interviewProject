from django.db import IntegrityError, models
from django.db.models import Avg, QuerySet
from rest_framework.exceptions import ValidationError

from core.caching import cache_get, cache_set, cache_invalidate_pattern, make_cache_key
from core.events import publish_event
from apps.analytics.tasks import update_book_analytics_task
from .models import Book, Rating

BOOK_CACHE_PREFIX = 'books'


class BookRepository:
    """Encapsulates all Book data access logic with caching."""

    @staticmethod
    def get_all_with_ratings() -> QuerySet:
        """Returns annotated queryset. NOT cached (querysets are lazy)."""
        return Book.objects.annotate(
            get_rating=Avg('ratings__rate')
        )

    @staticmethod
    def get_by_id(book_id: int) -> Book:
        cache_key = make_cache_key(BOOK_CACHE_PREFIX, 'detail', book_id)
        cached = cache_get(cache_key)
        if cached is not None:
            return cached
        book = Book.objects.get(pk=book_id)
        cache_set(cache_key, book, l1_ttl=60.0, l2_ttl=300)
        return book

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
        try:
            rating = Rating.objects.create(
                book=book, user=user, rate=rate, review=review,
            )
        except IntegrityError:
            raise ValidationError({'detail': 'You have already rated this book.'})
        # Invalidate book caches since rating affects get_rating
        cache_invalidate_pattern(BOOK_CACHE_PREFIX)
        publish_event(
            topic='book-events',
            event_type='book.rated',
            data={'book_id': book.id, 'user_id': user.id, 'rate': rate},
            key=str(book.id),
        )
        update_book_analytics_task.delay(book.id)
        return rating
