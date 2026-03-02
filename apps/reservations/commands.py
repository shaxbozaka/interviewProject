from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import ValidationError

from apps.notifications.tasks import send_reservation_confirmation, send_return_confirmation
from core.caching import cache_invalidate_pattern
from core.events import publish_event
from apps.analytics.tasks import update_book_analytics_task
from .models import Reservation


class ReserveBookCommand:
    """Command to reserve a book for a user."""

    def __init__(self, user, book, loan_days: int = 14):
        self.user = user
        self.book = book
        self.loan_days = loan_days

    def validate(self):
        if self.book.copies_available <= 0:
            raise ValidationError({'book': 'No copies available.'})
        active = Reservation.objects.filter(
            user=self.user, book=self.book, status=Reservation.Status.ACTIVE,
        ).exists()
        if active:
            raise ValidationError({'book': 'You already have an active reservation for this book.'})

    def execute(self) -> Reservation:
        self.validate()
        self.book.copies_available -= 1
        self.book.save()
        cache_invalidate_pattern('books')
        reservation = Reservation.objects.create(
            user=self.user,
            book=self.book,
            status=Reservation.Status.ACTIVE,
            due_date=timezone.now() + timedelta(days=self.loan_days),
        )
        send_reservation_confirmation.delay(self.user.id, self.book.title)
        publish_event(
            topic='book-events',
            event_type='book.reserved',
            data={'book_id': self.book.id, 'user_id': self.user.id},
            key=str(self.book.id),
        )
        update_book_analytics_task.delay(self.book.id)
        return reservation


class ReturnBookCommand:
    """Command to return a reserved book."""

    def __init__(self, reservation: Reservation):
        self.reservation = reservation

    def validate(self):
        if self.reservation.status == Reservation.Status.RETURNED:
            raise ValidationError({'detail': 'Book already returned.'})

    def execute(self) -> Reservation:
        self.validate()
        self.reservation.status = Reservation.Status.RETURNED
        self.reservation.returned_at = timezone.now()
        self.reservation.save()
        self.reservation.book.copies_available += 1
        self.reservation.book.save()
        cache_invalidate_pattern('books')
        send_return_confirmation.delay(
            self.reservation.user.id, self.reservation.book.title,
        )
        publish_event(
            topic='book-events',
            event_type='book.returned',
            data={'book_id': self.reservation.book.id, 'user_id': self.reservation.user.id},
            key=str(self.reservation.book.id),
        )
        update_book_analytics_task.delay(self.reservation.book.id)
        return self.reservation


class ExtendReservationCommand:
    """Command to extend a reservation's due date."""

    def __init__(self, reservation: Reservation, extra_days: int = 7):
        self.reservation = reservation
        self.extra_days = extra_days

    def validate(self):
        if self.reservation.status != Reservation.Status.ACTIVE:
            raise ValidationError({'detail': 'Can only extend active reservations.'})

    def execute(self) -> Reservation:
        self.validate()
        self.reservation.due_date += timedelta(days=self.extra_days)
        self.reservation.save()
        return self.reservation
