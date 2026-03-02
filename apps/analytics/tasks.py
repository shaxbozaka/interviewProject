from celery import shared_task


@shared_task
def update_book_analytics_task(book_id: int):
    from .consumers import update_book_analytics

    update_book_analytics(book_id)


@shared_task
def rebuild_all_analytics():
    """Rebuild analytics for all books. Run periodically or on demand."""
    from apps.books.models import Book
    from .consumers import update_book_analytics

    for book_id in Book.objects.values_list("id", flat=True):
        update_book_analytics(book_id)
