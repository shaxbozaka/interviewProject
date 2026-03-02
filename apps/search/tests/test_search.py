from datetime import date
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.books.models import Book, Genre
from apps.search.trie_service import refresh_trie, get_trie, _trie
import apps.search.trie_service as trie_module


@pytest.fixture
def genre(db):
    return Genre.objects.create(name='Fiction', slug='fiction')


@pytest.fixture
def books(db, genre):
    books = []
    data = [
        ('Harry Potter and the Sorcerer Stone', 'J.K. Rowling', 5),
        ('Harry Potter and the Chamber of Secrets', 'J.K. Rowling', 3),
        ('The Hobbit', 'J.R.R. Tolkien', 4),
        ('Django for Beginners', 'William Vincent', 2),
        ('Designing Data-Intensive Applications', 'Martin Kleppmann', 6),
    ]
    for title, author, copies in data:
        books.append(Book.objects.create(
            title=title,
            author=author,
            genre=genre,
            publication_date=date(2020, 1, 1),
            copies_total=copies,
            copies_available=copies,
        ))
    return books


@pytest.fixture(autouse=True)
def reset_trie():
    """Reset trie singleton before each test."""
    trie_module._trie = None
    yield
    trie_module._trie = None


class TestBookSearchView:
    def test_search_requires_query(self, api_client):
        response = api_client.get('/api/v1/search/')
        assert response.status_code == 400
        assert 'q' in response.data['detail']

    def test_search_empty_query(self, api_client):
        response = api_client.get('/api/v1/search/?q=')
        assert response.status_code == 400

    @patch('apps.search.views.es_client.search_books', return_value=None)
    def test_search_fallback_to_postgresql(self, mock_es, api_client, books):
        response = api_client.get('/api/v1/search/?q=Harry')
        assert response.status_code == 200
        assert response.data['source'] == 'postgresql'
        assert response.data['count'] == 2

    @patch('apps.search.views.es_client.search_books')
    def test_search_with_elasticsearch(self, mock_es, api_client, books):
        harry_ids = [b.id for b in books if 'Harry' in b.title]
        mock_es.return_value = harry_ids
        response = api_client.get('/api/v1/search/?q=Harry')
        assert response.status_code == 200
        assert response.data['source'] == 'elasticsearch'
        assert response.data['count'] == 2

    @patch('apps.search.views.es_client.search_books', return_value=None)
    def test_search_no_results(self, mock_es, api_client, books):
        response = api_client.get('/api/v1/search/?q=nonexistentbook')
        assert response.status_code == 200
        assert response.data['count'] == 0

    @patch('apps.search.views.es_client.search_books', return_value=None)
    def test_search_by_author(self, mock_es, api_client, books):
        response = api_client.get('/api/v1/search/?q=Tolkien')
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['title'] == 'The Hobbit'


class TestAutocompleteView:
    def test_autocomplete_requires_query(self, api_client):
        response = api_client.get('/api/v1/search/autocomplete/')
        assert response.status_code == 400

    def test_autocomplete_returns_suggestions(self, api_client, books):
        response = api_client.get('/api/v1/search/autocomplete/?q=Harry')
        assert response.status_code == 200
        assert len(response.data['suggestions']) == 2
        for suggestion in response.data['suggestions']:
            assert 'Harry Potter' in suggestion

    def test_autocomplete_respects_limit(self, api_client, books):
        response = api_client.get('/api/v1/search/autocomplete/?q=Harry&limit=1')
        assert response.status_code == 200
        assert len(response.data['suggestions']) == 1

    def test_autocomplete_case_insensitive(self, api_client, books):
        response = api_client.get('/api/v1/search/autocomplete/?q=harry')
        assert response.status_code == 200
        assert len(response.data['suggestions']) == 2

    def test_autocomplete_no_match(self, api_client, books):
        response = api_client.get('/api/v1/search/autocomplete/?q=zzzzz')
        assert response.status_code == 200
        assert response.data['suggestions'] == []

    def test_autocomplete_includes_authors(self, api_client, books):
        response = api_client.get('/api/v1/search/autocomplete/?q=J.K.')
        assert response.status_code == 200
        assert 'J.K. Rowling' in response.data['suggestions']

    def test_autocomplete_ordered_by_weight(self, api_client, books):
        response = api_client.get('/api/v1/search/autocomplete/?q=Harry')
        assert response.status_code == 200
        suggestions = response.data['suggestions']
        assert len(suggestions) == 2
        # "Sorcerer" book has copies_total=5, "Chamber" has 3
        assert 'Sorcerer' in suggestions[0]


class TestTrieService:
    def test_get_trie_builds_from_books(self, books):
        trie = get_trie()
        assert len(trie) > 0
        assert trie.search('Harry Potter and the Sorcerer Stone') is True

    def test_refresh_trie_rebuilds(self, books):
        trie = get_trie()
        Book.objects.create(
            title='New Book',
            author='New Author',
            publication_date=date(2024, 1, 1),
            copies_total=1,
            copies_available=1,
        )
        refresh_trie()
        trie = get_trie()
        assert trie.search('New Book') is True

    def test_trie_singleton(self, books):
        trie1 = get_trie()
        trie2 = get_trie()
        assert trie1 is trie2
