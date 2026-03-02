import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from apps.books.models import Book
from apps.reservations.commands import (
    ReserveBookCommand, ReturnBookCommand, ExtendReservationCommand,
)
from apps.reservations.models import Reservation

User = get_user_model()


@pytest.mark.django_db
class TestReserveBookCommand:
    def test_reserve_book_success(self):
        user = User.objects.create_user(username='cmd_user', password='pass12345678')
        book = Book.objects.create(
            title='Cmd Book', author='Author',
            publication_date='2024-01-01', copies_available=3, copies_total=3,
        )
        command = ReserveBookCommand(user=user, book=book)
        reservation = command.execute()
        assert reservation.status == 'active'
        book.refresh_from_db()
        assert book.copies_available == 2

    def test_reserve_no_copies_raises(self):
        user = User.objects.create_user(username='cmd_user', password='pass12345678')
        book = Book.objects.create(
            title='Cmd Book', author='Author',
            publication_date='2024-01-01', copies_available=0, copies_total=1,
        )
        command = ReserveBookCommand(user=user, book=book)
        with pytest.raises(ValidationError):
            command.execute()

    def test_reserve_duplicate_raises(self):
        user = User.objects.create_user(username='cmd_user', password='pass12345678')
        book = Book.objects.create(
            title='Cmd Book', author='Author',
            publication_date='2024-01-01', copies_available=3, copies_total=3,
        )
        ReserveBookCommand(user=user, book=book).execute()
        with pytest.raises(ValidationError):
            ReserveBookCommand(user=user, book=book).execute()


@pytest.mark.django_db
class TestReturnBookCommand:
    def test_return_book_success(self):
        user = User.objects.create_user(username='cmd_user', password='pass12345678')
        book = Book.objects.create(
            title='Cmd Book', author='Author',
            publication_date='2024-01-01', copies_available=3, copies_total=3,
        )
        reservation = ReserveBookCommand(user=user, book=book).execute()
        result = ReturnBookCommand(reservation).execute()
        assert result.status == 'returned'
        book.refresh_from_db()
        assert book.copies_available == 3

    def test_return_already_returned_raises(self):
        user = User.objects.create_user(username='cmd_user', password='pass12345678')
        book = Book.objects.create(
            title='Cmd Book', author='Author',
            publication_date='2024-01-01', copies_available=3, copies_total=3,
        )
        reservation = ReserveBookCommand(user=user, book=book).execute()
        ReturnBookCommand(reservation).execute()
        with pytest.raises(ValidationError):
            ReturnBookCommand(reservation).execute()


@pytest.mark.django_db
class TestExtendReservationCommand:
    def test_extend_reservation_success(self):
        user = User.objects.create_user(username='cmd_user', password='pass12345678')
        book = Book.objects.create(
            title='Cmd Book', author='Author',
            publication_date='2024-01-01', copies_available=3, copies_total=3,
        )
        reservation = ReserveBookCommand(user=user, book=book).execute()
        original_due = reservation.due_date
        result = ExtendReservationCommand(reservation, extra_days=7).execute()
        assert result.due_date > original_due

    def test_extend_returned_raises(self):
        user = User.objects.create_user(username='cmd_user', password='pass12345678')
        book = Book.objects.create(
            title='Cmd Book', author='Author',
            publication_date='2024-01-01', copies_available=3, copies_total=3,
        )
        reservation = ReserveBookCommand(user=user, book=book).execute()
        ReturnBookCommand(reservation).execute()
        with pytest.raises(ValidationError):
            ExtendReservationCommand(reservation).execute()
