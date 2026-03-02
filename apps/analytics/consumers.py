import logging
from django.db.models import Avg, Count

logger = logging.getLogger(__name__)


def update_book_analytics(book_id: int):
    from apps.books.models import Book
    from .models import BookAnalytics

    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        logger.warning("Book %d not found for analytics update", book_id)
        return

    analytics, _ = BookAnalytics.objects.get_or_create(book=book)

    rating_data = book.ratings.aggregate(
        avg=Avg("rate"),
        count=Count("id"),
    )
    analytics.avg_rating = rating_data["avg"] or 0.0
    analytics.total_ratings = rating_data["count"]
    analytics.total_reservations = book.reservations.count()
    analytics.calculate_popularity()
    analytics.save()

    logger.info(
        "Updated analytics for book %d: score=%.2f", book_id, analytics.popularity_score
    )
