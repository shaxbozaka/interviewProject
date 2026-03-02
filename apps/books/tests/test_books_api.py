import pytest
from django.urls import reverse
from apps.books.models import Book


@pytest.mark.django_db
class TestBookAPI:
    def test_list_books_returns_200(self, api_client):
        url = reverse('book-list')
        response = api_client.get(url)
        assert response.status_code == 200

    def test_create_book(self, api_client):
        url = reverse('book-list')
        data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'publication_date': '2024-01-01',
            'available': True,
        }
        response = api_client.post(url, data)
        assert response.status_code == 201
        assert Book.objects.count() == 1

    def test_get_book_detail(self, api_client):
        book = Book.objects.create(
            title='Detail Book',
            author='Author',
            publication_date='2024-01-01',
        )
        url = reverse('book-detail', kwargs={'pk': book.pk})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data['title'] == 'Detail Book'
