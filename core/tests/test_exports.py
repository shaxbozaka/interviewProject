from datetime import date

import pytest

from apps.books.models import Book, Genre
from core.exports import queryset_to_csv_generator


@pytest.fixture
def genre(db):
    return Genre.objects.create(name="Fiction", slug="fiction")


@pytest.fixture
def books(db, genre):
    for i in range(5):
        Book.objects.create(
            title=f"Book {i}",
            author=f"Author {i}",
            genre=genre,
            publication_date=date(2020, 1, 1),
            copies_total=3,
            copies_available=3,
        )


class TestCsvExport:
    def test_generator_yields_header_and_rows(self, books):
        fields = ["title", "author"]
        rows = list(queryset_to_csv_generator(Book.objects.all(), fields))
        assert len(rows) == 6  # 1 header + 5 data rows
        assert "title,author" in rows[0]

    def test_generator_yields_correct_data(self, books):
        fields = ["title", "author"]
        rows = list(queryset_to_csv_generator(Book.objects.all(), fields))
        data_rows = rows[1:]
        assert any("Book 0" in row for row in data_rows)

    def test_empty_queryset(self, db):
        fields = ["title", "author"]
        rows = list(queryset_to_csv_generator(Book.objects.none(), fields))
        assert len(rows) == 1  # just the header


class TestExportEndpoint:
    def test_export_csv_endpoint(self, api_client, books):
        response = api_client.get("/api/v1/books/export/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "books_export.csv" in response["Content-Disposition"]
        content = b"".join(response.streaming_content).decode()
        assert "title" in content
        assert "Book 0" in content
