from django.db import IntegrityError, models
from django.db.models import Avg, QuerySet
from rest_framework.exceptions import ValidationError

from apps.analytics.models import AuditLog
from apps.analytics.tasks import update_book_analytics_task
from core.caching import cache_get, cache_set, cache_invalidate_pattern, make_cache_key
from core.events import publish_event
from core.tracing import trace_step

from .models import Book, Rating

BOOK_CACHE_PREFIX = 'books'


class BookRepository:
    """Encapsulates all Book data access logic with caching."""

    @staticmethod
    def get_all_with_ratings() -> QuerySet:
        """Returns annotated queryset. NOT cached (querysets are lazy)."""
        trace_step('BookRepository.get_all_with_ratings() → annotated QuerySet', 'db')
        return Book.objects.annotate(
            get_rating=Avg('ratings__rate')
        )

    @staticmethod
    def get_by_id(book_id: int) -> Book:
        cache_key = make_cache_key(BOOK_CACHE_PREFIX, 'detail', book_id)
        cached = cache_get(cache_key)
        if cached is not None:
            trace_step(f'BookRepository.get_by_id({book_id}) → CACHE HIT', 'cache')
            return cached
        book = Book.objects.get(pk=book_id)
        cache_set(cache_key, book, l1_ttl=60.0, l2_ttl=300)
        trace_step(f'BookRepository.get_by_id({book_id}) → CACHE MISS, fetched from DB, cached', 'db')
        return book

    @staticmethod
    def get_by_genre(queryset: QuerySet, genre_slug: str) -> QuerySet:
        trace_step(f'BookRepository.get_by_genre("{genre_slug}")', 'db')
        return queryset.filter(genre__slug=genre_slug)

    @staticmethod
    def search(queryset: QuerySet, query: str) -> QuerySet:
        trace_step(f'BookRepository.search("{query}")', 'db')
        return queryset.filter(
            models.Q(title__icontains=query) | models.Q(author__icontains=query)
        )

    @staticmethod
    def create_rating(book: Book, user, rate: int, review: str = '') -> Rating:
        trace_step(f'BookRepository.create_rating(book={book.id}, user={user.id}, rate={rate})', 'logic')
        try:
            rating = Rating.objects.create(
                book=book, user=user, rate=rate, review=review,
            )
        except IntegrityError:
            trace_step('REJECT: duplicate rating', 'error')
            raise ValidationError({'detail': 'You have already rated this book.'})
        trace_step(f'DB: Rating #{rating.id} created', 'db')
        cache_invalidate_pattern(BOOK_CACHE_PREFIX)
        trace_step('Cache: invalidated "books" pattern', 'cache')
        publish_event(
            topic='book-events',
            event_type='book.rated',
            data={'book_id': book.id, 'user_id': user.id, 'rate': rate},
            key=str(book.id),
        )
        trace_step('Kafka: publish "book.rated" → topic:book-events', 'event')
        update_book_analytics_task.delay(book.id)
        trace_step(f'Celery: update_book_analytics_task.delay(book={book.id}) → RabbitMQ', 'task')
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            entity_type='rating',
            entity_id=rating.id,
            user_id=user.id,
            changes={
                'book_id': book.id,
                'book_title': book.title,
                'rate': rate,
                'event': 'book.rated',
                'pipeline': ['kafka:book-events', 'celery:update_book_analytics'],
            },
        )
        trace_step('DB: AuditLog entry created', 'db')
        return rating
