import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.books.models import Book
from apps.reservations.models import Reservation

User = get_user_model()


@pytest.mark.django_db
class TestReservationAPI:
    def test_create_reservation(self, authenticated_client, user):
        book = Book.objects.create(
            title='Test Book', author='Author',
            publication_date='2024-01-01', copies_available=3, copies_total=3,
        )
        url = reverse('reservation-list')
        response = authenticated_client.post(url, {'book': book.pk, 'due_date': '2024-02-01T00:00:00Z'})
        assert response.status_code == 201
        assert response.data['status'] == 'active'
        book.refresh_from_db()
        assert book.copies_available == 2

    def test_create_reservation_no_copies_fails(self, authenticated_client, user):
        book = Book.objects.create(
            title='Test Book', author='Author',
            publication_date='2024-01-01', copies_available=0, copies_total=1,
        )
        url = reverse('reservation-list')
        response = authenticated_client.post(url, {'book': book.pk, 'due_date': '2024-02-01T00:00:00Z'})
        assert response.status_code == 400

    def test_return_book(self, authenticated_client, user):
        book = Book.objects.create(
            title='Test Book', author='Author',
            publication_date='2024-01-01', copies_available=2, copies_total=3,
        )
        reservation = Reservation.objects.create(
            user=user, book=book, status='active',
            due_date='2024-02-01T00:00:00Z',
        )
        url = reverse('reservation-return-book', kwargs={'pk': reservation.pk})
        response = authenticated_client.post(url)
        assert response.status_code == 200
        assert response.data['status'] == 'returned'
        book.refresh_from_db()
        assert book.copies_available == 3

    def test_return_already_returned_fails(self, authenticated_client, user):
        book = Book.objects.create(
            title='Test Book', author='Author',
            publication_date='2024-01-01', copies_available=3, copies_total=3,
        )
        reservation = Reservation.objects.create(
            user=user, book=book, status='returned',
            due_date='2024-02-01T00:00:00Z',
        )
        url = reverse('reservation-return-book', kwargs={'pk': reservation.pk})
        response = authenticated_client.post(url)
        assert response.status_code == 400

    def test_unauthenticated_cannot_reserve(self, api_client):
        url = reverse('reservation-list')
        response = api_client.post(url, {'book': 1})
        assert response.status_code == 401

    def test_list_only_own_reservations(self, api_client):
        user1 = User.objects.create_user(username='user1', password='pass12345678')
        user2 = User.objects.create_user(username='user2', password='pass12345678')
        book = Book.objects.create(
            title='Test', author='Author',
            publication_date='2024-01-01', copies_available=5, copies_total=5,
        )
        Reservation.objects.create(user=user1, book=book, status='active', due_date='2024-02-01T00:00:00Z')
        Reservation.objects.create(user=user2, book=book, status='active', due_date='2024-02-01T00:00:00Z')
        api_client.force_authenticate(user=user1)
        url = reverse('reservation-list')
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data['results']) == 1
