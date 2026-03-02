import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.books.models import Book, Rating
from apps.analytics.models import BookAnalytics, AuditLog
from apps.analytics.consumers import update_book_analytics

User = get_user_model()


@pytest.mark.django_db
class TestBookAnalytics:
    def test_update_book_analytics(self):
        user = User.objects.create_user(username="analyst", password="pass12345678")
        book = Book.objects.create(
            title="Analytics Book",
            author="Author",
            publication_date="2024-01-01",
            copies_available=3,
            copies_total=3,
        )
        Rating.objects.create(book=book, user=user, rate=80)
        update_book_analytics(book.id)
        analytics = BookAnalytics.objects.get(book=book)
        assert analytics.avg_rating == 80.0
        assert analytics.total_ratings == 1
        assert analytics.popularity_score > 0

    def test_popularity_calculation(self):
        book = Book.objects.create(
            title="Popular Book",
            author="Author",
            publication_date="2024-01-01",
        )
        analytics = BookAnalytics.objects.create(
            book=book,
            avg_rating=90.0,
            total_reservations=10,
        )
        analytics.calculate_popularity()
        assert analytics.popularity_score == (90.0 * 0.7) + (10 * 0.3)

    def test_analytics_for_nonexistent_book(self):
        """Should not crash."""
        update_book_analytics(99999)

    def test_top_books_endpoint(self, api_client):
        book = Book.objects.create(
            title="Top Book",
            author="Author",
            publication_date="2024-01-01",
        )
        BookAnalytics.objects.create(
            book=book,
            avg_rating=95.0,
            popularity_score=70.0,
        )
        url = reverse("analytics-top-books")
        response = api_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestAuditLog:
    def test_create_audit_log(self):
        log = AuditLog.objects.create(
            action="create",
            entity_type="book",
            entity_id=1,
            user_id=1,
            changes={"title": "New Book"},
        )
        assert log.action == "create"
        assert log.changes == {"title": "New Book"}
