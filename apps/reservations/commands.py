from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.analytics.models import AuditLog
from apps.analytics.tasks import update_book_analytics_task
from apps.notifications.tasks import (
    send_reservation_confirmation,
    send_return_confirmation,
)
from core.caching import cache_invalidate_pattern
from core.events import publish_event
from core.tracing import trace_step

from .models import Reservation


class ReserveBookCommand:
    """Command to reserve a book for a user."""

    def __init__(self, user, book, loan_days: int = 14):
        self.user = user
        self.book = book
        self.loan_days = loan_days

    def validate(self):
        trace_step(
            f"ReserveBookCommand.validate() book={self.book.id} user={self.user.id}",
            "logic",
        )
        if self.book.copies_available <= 0:
            trace_step("REJECT: no copies available", "error")
            raise ValidationError({"book": "No copies available."})
        active = Reservation.objects.filter(
            user=self.user,
            book=self.book,
            status=Reservation.Status.ACTIVE,
        ).exists()
        if active:
            trace_step("REJECT: already has active reservation", "error")
            raise ValidationError(
                {"book": "You already have an active reservation for this book."}
            )
        trace_step("Validation passed", "logic")

    def execute(self) -> Reservation:
        trace_step("ReserveBookCommand.execute()", "logic")
        self.validate()
        self.book.copies_available -= 1
        self.book.save()
        trace_step(
            f"DB: Book #{self.book.id} copies_available decremented to {self.book.copies_available}",
            "db",
        )
        cache_invalidate_pattern("books")
        trace_step(
            'Cache: invalidated "books" pattern (L1 cleared + Redis keys deleted)',
            "cache",
        )
        reservation = Reservation.objects.create(
            user=self.user,
            book=self.book,
            status=Reservation.Status.ACTIVE,
            due_date=timezone.now() + timedelta(days=self.loan_days),
        )
        trace_step(
            f"DB: Reservation #{reservation.id} created (status=ACTIVE, due={self.loan_days}d)",
            "db",
        )
        send_reservation_confirmation.delay(self.user.id, self.book.title)
        trace_step(
            f"Celery: send_reservation_confirmation.delay(user={self.user.id}) → RabbitMQ",
            "task",
        )
        publish_event(
            topic="book-events",
            event_type="book.reserved",
            data={"book_id": self.book.id, "user_id": self.user.id},
            key=str(self.book.id),
        )
        trace_step('Kafka: publish "book.reserved" → topic:book-events', "event")
        update_book_analytics_task.delay(self.book.id)
        trace_step(
            f"Celery: update_book_analytics_task.delay(book={self.book.id}) → RabbitMQ",
            "task",
        )
        AuditLog.objects.create(
            action=AuditLog.Action.CREATE,
            entity_type="reservation",
            entity_id=reservation.id,
            user_id=self.user.id,
            changes={
                "book_id": self.book.id,
                "book_title": self.book.title,
                "event": "book.reserved",
                "pipeline": [
                    "kafka:book-events",
                    "celery:send_reservation_confirmation",
                    "celery:update_book_analytics",
                ],
            },
        )
        trace_step("DB: AuditLog entry created with pipeline trace", "db")
        return reservation


class ReturnBookCommand:
    """Command to return a reserved book."""

    def __init__(self, reservation: Reservation):
        self.reservation = reservation

    def validate(self):
        trace_step(
            f"ReturnBookCommand.validate() reservation={self.reservation.id}", "logic"
        )
        if self.reservation.status == Reservation.Status.RETURNED:
            trace_step("REJECT: book already returned", "error")
            raise ValidationError({"detail": "Book already returned."})
        trace_step("Validation passed", "logic")

    def execute(self) -> Reservation:
        trace_step("ReturnBookCommand.execute()", "logic")
        self.validate()
        self.reservation.status = Reservation.Status.RETURNED
        self.reservation.returned_at = timezone.now()
        self.reservation.save()
        trace_step(f"DB: Reservation #{self.reservation.id} status → RETURNED", "db")
        self.reservation.book.copies_available += 1
        self.reservation.book.save()
        trace_step(
            f"DB: Book #{self.reservation.book.id} copies_available incremented to {self.reservation.book.copies_available}",
            "db",
        )
        cache_invalidate_pattern("books")
        trace_step('Cache: invalidated "books" pattern', "cache")
        send_return_confirmation.delay(
            self.reservation.user.id,
            self.reservation.book.title,
        )
        trace_step(
            f"Celery: send_return_confirmation.delay(user={self.reservation.user.id}) → RabbitMQ",
            "task",
        )
        publish_event(
            topic="book-events",
            event_type="book.returned",
            data={
                "book_id": self.reservation.book.id,
                "user_id": self.reservation.user.id,
            },
            key=str(self.reservation.book.id),
        )
        trace_step('Kafka: publish "book.returned" → topic:book-events', "event")
        update_book_analytics_task.delay(self.reservation.book.id)
        trace_step(
            f"Celery: update_book_analytics_task.delay(book={self.reservation.book.id}) → RabbitMQ",
            "task",
        )
        AuditLog.objects.create(
            action=AuditLog.Action.UPDATE,
            entity_type="reservation",
            entity_id=self.reservation.id,
            user_id=self.reservation.user.id,
            changes={
                "book_id": self.reservation.book.id,
                "book_title": self.reservation.book.title,
                "event": "book.returned",
                "pipeline": [
                    "kafka:book-events",
                    "celery:send_return_confirmation",
                    "celery:update_book_analytics",
                ],
            },
        )
        trace_step("DB: AuditLog entry created", "db")
        return self.reservation


class ExtendReservationCommand:
    """Command to extend a reservation's due date."""

    def __init__(self, reservation: Reservation, extra_days: int = 7):
        self.reservation = reservation
        self.extra_days = extra_days

    def validate(self):
        trace_step(
            f"ExtendReservationCommand.validate() reservation={self.reservation.id}",
            "logic",
        )
        if self.reservation.status != Reservation.Status.ACTIVE:
            trace_step("REJECT: reservation not active", "error")
            raise ValidationError({"detail": "Can only extend active reservations."})
        trace_step("Validation passed", "logic")

    def execute(self) -> Reservation:
        trace_step("ExtendReservationCommand.execute()", "logic")
        self.validate()
        self.reservation.due_date += timedelta(days=self.extra_days)
        self.reservation.save()
        trace_step(
            f"DB: Reservation #{self.reservation.id} due_date extended +{self.extra_days}d",
            "db",
        )
        return self.reservation
