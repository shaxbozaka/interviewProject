import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

from apps.notifications.factory import NotificationFactory
from apps.notifications.strategies import (
    EmailNotificationStrategy,
    InAppNotificationStrategy,
    PushNotificationStrategy,
)
from apps.notifications.tasks import (
    send_reservation_confirmation,
    send_return_confirmation,
    check_overdue_reservations,
)

User = get_user_model()


class TestNotificationFactory:
    def test_create_email_strategy(self):
        strategy = NotificationFactory.create("email")
        assert isinstance(strategy, EmailNotificationStrategy)

    def test_create_in_app_strategy(self):
        strategy = NotificationFactory.create("in_app")
        assert isinstance(strategy, InAppNotificationStrategy)

    def test_create_push_strategy(self):
        strategy = NotificationFactory.create("push")
        assert isinstance(strategy, PushNotificationStrategy)

    def test_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="Unknown notification channel"):
            NotificationFactory.create("sms")

    def test_available_channels(self):
        channels = NotificationFactory.available_channels()
        assert "email" in channels
        assert "in_app" in channels
        assert "push" in channels

    def test_register_custom_channel(self):
        class SmsStrategy:
            def send(self, recipient, subject, message):
                return True

        NotificationFactory.register("sms", SmsStrategy)
        strategy = NotificationFactory.create("sms")
        assert isinstance(strategy, SmsStrategy)
        # Clean up
        del NotificationFactory._strategies["sms"]


class TestNotificationStrategies:
    @pytest.mark.django_db
    def test_email_strategy_sends(self):
        user = User.objects.create_user(
            username="notify_user",
            password="pass12345678",
            email="test@example.com",
        )
        with patch("django.core.mail.send_mail") as mock_mail:
            strategy = EmailNotificationStrategy()
            result = strategy.send(user, "Test Subject", "Test message")
            assert result is True
            mock_mail.assert_called_once()

    @pytest.mark.django_db
    def test_in_app_strategy_sends(self):
        user = User.objects.create_user(
            username="notify_user",
            password="pass12345678",
        )
        strategy = InAppNotificationStrategy()
        result = strategy.send(user, "Test", "Message")
        assert result is True


@pytest.mark.django_db
class TestNotificationTasks:
    def test_send_reservation_confirmation(self):
        user = User.objects.create_user(
            username="task_user",
            password="pass12345678",
            email="task@example.com",
        )
        with patch("django.core.mail.send_mail"):
            send_reservation_confirmation(user.id, "Test Book")

    def test_send_return_confirmation(self):
        user = User.objects.create_user(
            username="task_user",
            password="pass12345678",
            email="task@example.com",
        )
        with patch("django.core.mail.send_mail"):
            send_return_confirmation(user.id, "Test Book")

    def test_check_overdue_reservations(self):
        from django.utils import timezone
        from datetime import timedelta
        from apps.books.models import Book
        from apps.reservations.models import Reservation

        user = User.objects.create_user(
            username="overdue_user",
            password="pass12345678",
            email="overdue@example.com",
        )
        book = Book.objects.create(
            title="Overdue Book",
            author="Author",
            publication_date="2024-01-01",
            copies_available=3,
            copies_total=3,
        )
        reservation = Reservation.objects.create(
            user=user,
            book=book,
            status="active",
            due_date=timezone.now() - timedelta(days=1),
        )
        with patch("django.core.mail.send_mail"):
            check_overdue_reservations()

        reservation.refresh_from_db()
        assert reservation.status == "overdue"

    def test_confirmation_for_nonexistent_user(self):
        """Should not crash for missing user."""
        send_reservation_confirmation(99999, "Test Book")
