"""
End-to-end tests exercising the full API flow.

These tests run against the Django test client with a real SQLite DB,
verifying the complete lifecycle:

  Register → Login → Create Genre → Create Book → Search → Autocomplete →
  Reserve → Extend → Return → Rate → Analytics → Health → Export

Run with:
    pytest tests/e2e/ -v
"""

import pytest

from rest_framework.test import APIClient

import apps.search.trie_service as trie_module


@pytest.fixture(autouse=True)
def reset_trie():
    """Reset trie singleton before each test so it rebuilds from current DB."""
    trie_module._trie = None
    yield
    trie_module._trie = None


@pytest.fixture
def anon_client():
    """Unauthenticated API client (never gets credentials set on it)."""
    return APIClient()


@pytest.fixture
def auth_client(db):
    """Register, login, and return an authenticated API client."""
    client = APIClient()
    client.post(
        "/api/v1/users/register/",
        {
            "username": "e2e_user",
            "email": "e2e@test.com",
            "password": "e2epassword123",
        },
    )
    response = client.post(
        "/api/v1/users/login/",
        {
            "username": "e2e_user",
            "password": "e2epassword123",
        },
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


@pytest.fixture
def genre(auth_client):
    """Create a genre."""
    response = auth_client.post(
        "/api/v1/genres/",
        {
            "name": "Science Fiction",
            "slug": "sci-fi",
        },
    )
    assert response.status_code == 201, f"Genre creation failed: {response.data}"
    return response.data


@pytest.fixture
def book(auth_client, genre):
    """Create a book."""
    response = auth_client.post(
        "/api/v1/books/",
        {
            "title": "Dune",
            "author": "Frank Herbert",
            "isbn": "9780441172719",
            "publication_date": "1965-08-01",
            "genre": genre["id"],
            "copies_total": 5,
            "copies_available": 5,
        },
    )
    assert response.status_code == 201, f"Book creation failed: {response.data}"
    return response.data


class TestE2EUserFlow:
    """Test the complete user registration and authentication flow."""

    def test_register_login_profile(self, anon_client, db):
        # 1. Register
        reg = anon_client.post(
            "/api/v1/users/register/",
            {
                "username": "flow_user",
                "email": "flow@test.com",
                "password": "flowpass123",
            },
        )
        assert reg.status_code == 201
        assert reg.data["username"] == "flow_user"
        assert reg.data["role"] == "member"
        assert "password" not in reg.data

        # 2. Login
        login = anon_client.post(
            "/api/v1/users/login/",
            {
                "username": "flow_user",
                "password": "flowpass123",
            },
        )
        assert login.status_code == 200
        assert "access" in login.data
        assert "refresh" in login.data
        token = login.data["access"]

        # 3. Profile
        anon_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        profile = anon_client.get("/api/v1/users/me/")
        assert profile.status_code == 200
        assert profile.data["username"] == "flow_user"
        assert profile.data["email"] == "flow@test.com"

        # 4. Update profile
        update = anon_client.patch("/api/v1/users/me/", {"email": "new@test.com"})
        assert update.status_code == 200
        assert update.data["email"] == "new@test.com"

    def test_unauthenticated_access_denied(self, anon_client, db):
        response = anon_client.get("/api/v1/users/me/")
        assert response.status_code == 401

    def test_invalid_token_rejected(self, anon_client, db):
        anon_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        response = anon_client.get("/api/v1/users/me/")
        assert response.status_code == 401

    def test_token_refresh(self, anon_client, db):
        anon_client.post(
            "/api/v1/users/register/",
            {
                "username": "refresh_user",
                "email": "refresh@test.com",
                "password": "refreshpass123",
            },
        )
        login = anon_client.post(
            "/api/v1/users/login/",
            {
                "username": "refresh_user",
                "password": "refreshpass123",
            },
        )
        refresh_token = login.data["refresh"]

        refresh = anon_client.post(
            "/api/v1/users/token/refresh/",
            {
                "refresh": refresh_token,
            },
        )
        assert refresh.status_code == 200
        assert "access" in refresh.data


class TestE2EBookFlow:
    """Test the complete book CRUD and search flow."""

    def test_create_and_list_books(self, auth_client, genre):
        books_data = [
            {
                "title": "Dune",
                "author": "Frank Herbert",
                "isbn": "9780441172719",
                "publication_date": "1965-08-01",
                "genre": genre["id"],
                "copies_total": 5,
                "copies_available": 5,
            },
            {
                "title": "Foundation",
                "author": "Isaac Asimov",
                "isbn": "9780553293357",
                "publication_date": "1951-01-01",
                "genre": genre["id"],
                "copies_total": 3,
                "copies_available": 3,
            },
            {
                "title": "Neuromancer",
                "author": "William Gibson",
                "isbn": "9780441569595",
                "publication_date": "1984-07-01",
                "genre": genre["id"],
                "copies_total": 2,
                "copies_available": 2,
            },
        ]
        book_ids = []
        for data in books_data:
            response = auth_client.post("/api/v1/books/", data)
            assert response.status_code == 201
            book_ids.append(response.data["id"])

        # List all books
        response = auth_client.get("/api/v1/books/")
        assert response.status_code == 200
        assert response.data["count"] == 3

        # Get single book
        response = auth_client.get(f"/api/v1/books/{book_ids[0]}/")
        assert response.status_code == 200
        assert response.data["title"] == "Dune"
        assert response.data["genre_name"] == "Science Fiction"

    def test_book_search_filter(self, auth_client, genre):
        auth_client.post(
            "/api/v1/books/",
            {
                "title": "Django for APIs",
                "author": "William Vincent",
                "publication_date": "2022-01-01",
                "genre": genre["id"],
                "copies_total": 3,
                "copies_available": 3,
            },
        )
        auth_client.post(
            "/api/v1/books/",
            {
                "title": "Flask Web Development",
                "author": "Miguel Grinberg",
                "publication_date": "2018-01-01",
                "genre": genre["id"],
                "copies_total": 2,
                "copies_available": 2,
            },
        )

        response = auth_client.get("/api/v1/books/?search=Django")
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "Django for APIs"

    def test_genre_filter(self, auth_client):
        g1 = auth_client.post("/api/v1/genres/", {"name": "Fantasy", "slug": "fantasy"})
        g2 = auth_client.post("/api/v1/genres/", {"name": "Mystery", "slug": "mystery"})

        auth_client.post(
            "/api/v1/books/",
            {
                "title": "The Hobbit",
                "author": "Tolkien",
                "publication_date": "1937-09-21",
                "genre": g1.data["id"],
                "copies_total": 4,
                "copies_available": 4,
            },
        )
        auth_client.post(
            "/api/v1/books/",
            {
                "title": "Gone Girl",
                "author": "Flynn",
                "publication_date": "2012-06-05",
                "genre": g2.data["id"],
                "copies_total": 2,
                "copies_available": 2,
            },
        )

        response = auth_client.get("/api/v1/books/?genre=fantasy")
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "The Hobbit"


class TestE2ESearchFlow:
    """Test full-text search and autocomplete endpoints."""

    def test_search_endpoint_with_pg_fallback(self, auth_client, book):
        from unittest.mock import patch

        with patch("apps.search.es_client.search_books", return_value=None):
            response = auth_client.get("/api/v1/search/?q=Dune")
        assert response.status_code == 200
        assert response.data["source"] == "postgresql"
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "Dune"

    def test_search_no_results(self, auth_client, book):
        response = auth_client.get("/api/v1/search/?q=nonexistent")
        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_search_requires_query(self, auth_client):
        response = auth_client.get("/api/v1/search/")
        assert response.status_code == 400

    def test_autocomplete(self, auth_client, book):
        response = auth_client.get("/api/v1/search/autocomplete/?q=Du")
        assert response.status_code == 200
        assert len(response.data["suggestions"]) >= 1
        assert any("Dune" in s for s in response.data["suggestions"])

    def test_autocomplete_case_insensitive(self, auth_client, book):
        response = auth_client.get("/api/v1/search/autocomplete/?q=dun")
        assert response.status_code == 200
        assert any("Dune" in s for s in response.data["suggestions"])


class TestE2EReservationFlow:
    """Test the complete book reservation lifecycle."""

    def test_full_reservation_lifecycle(self, auth_client, book):
        book_id = book["id"]

        # 1. Reserve the book
        reserve = auth_client.post("/api/v1/reservations/", {"book": book_id})
        assert reserve.status_code == 201, f"Reserve failed: {reserve.data}"
        reservation_id = reserve.data["id"]
        assert reserve.data["status"] == "active"
        assert reserve.data["book_title"] == "Dune"

        # 2. Verify copies decreased
        book_detail = auth_client.get(f"/api/v1/books/{book_id}/")
        assert book_detail.data["copies_available"] == 4

        # 3. Extend reservation
        extend = auth_client.post(
            f"/api/v1/reservations/{reservation_id}/extend/",
            {"days": 7},
        )
        assert extend.status_code == 200

        # 4. Return the book
        return_resp = auth_client.post(
            f"/api/v1/reservations/{reservation_id}/return_book/",
        )
        assert return_resp.status_code == 200
        assert return_resp.data["status"] == "returned"
        assert return_resp.data["returned_at"] is not None

        # 5. Verify copies restored
        book_detail = auth_client.get(f"/api/v1/books/{book_id}/")
        assert book_detail.data["copies_available"] == 5

    def test_cannot_reserve_twice(self, auth_client, book):
        auth_client.post("/api/v1/reservations/", {"book": book["id"]})
        duplicate = auth_client.post("/api/v1/reservations/", {"book": book["id"]})
        assert duplicate.status_code == 400

    def test_cannot_reserve_no_copies(self, auth_client, genre):
        book_resp = auth_client.post(
            "/api/v1/books/",
            {
                "title": "Rare Book",
                "author": "Unknown",
                "publication_date": "2020-01-01",
                "genre": genre["id"],
                "copies_total": 0,
                "copies_available": 0,
            },
        )
        reserve = auth_client.post(
            "/api/v1/reservations/", {"book": book_resp.data["id"]}
        )
        assert reserve.status_code == 400

    def test_cannot_return_already_returned(self, auth_client, book):
        reserve = auth_client.post("/api/v1/reservations/", {"book": book["id"]})
        assert reserve.status_code == 201
        rid = reserve.data["id"]
        auth_client.post(f"/api/v1/reservations/{rid}/return_book/")
        double_return = auth_client.post(f"/api/v1/reservations/{rid}/return_book/")
        assert double_return.status_code == 400

    def test_list_only_own_reservations(self, auth_client, book):
        # auth_client user reserves a book
        auth_client.post("/api/v1/reservations/", {"book": book["id"]})

        # Create a second user with a separate client
        other_client = APIClient()
        other_client.post(
            "/api/v1/users/register/",
            {
                "username": "other_user",
                "email": "other@test.com",
                "password": "otherpass123",
            },
        )
        login = other_client.post(
            "/api/v1/users/login/",
            {
                "username": "other_user",
                "password": "otherpass123",
            },
        )
        other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        # Other user should see no reservations
        response = other_client.get("/api/v1/reservations/")
        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_unauthenticated_cannot_reserve(self, anon_client, book):
        response = anon_client.post("/api/v1/reservations/", {"book": book["id"]})
        assert response.status_code == 401


class TestE2ERatingFlow:
    """Test book rating flow and its effect on analytics."""

    def test_rate_book_and_check_analytics(self, auth_client, book):
        book_id = book["id"]

        # 1. Rate the book
        rate = auth_client.post(
            f"/api/v1/books/{book_id}/rate/",
            {
                "rate": 85,
                "review": "Excellent sci-fi classic!",
            },
        )
        assert rate.status_code == 201
        assert rate.data["rate"] == 85
        assert rate.data["review"] == "Excellent sci-fi classic!"

        # 2. Check the book now has a rating
        detail = auth_client.get(f"/api/v1/books/{book_id}/")
        assert detail.data["get_rating"] == 85.0

        # 3. Check analytics endpoint
        analytics = auth_client.get("/api/v1/analytics/top/")
        assert analytics.status_code == 200

    def test_cannot_rate_unauthenticated(self, anon_client, book):
        response = anon_client.post(f"/api/v1/books/{book['id']}/rate/", {"rate": 50})
        assert response.status_code == 401

    def test_duplicate_rating_rejected(self, auth_client, book):
        auth_client.post(f"/api/v1/books/{book['id']}/rate/", {"rate": 80})
        duplicate = auth_client.post(f"/api/v1/books/{book['id']}/rate/", {"rate": 90})
        assert duplicate.status_code == 400


class TestE2EHealthCheck:
    """Test health check endpoint."""

    def test_health_check_returns_status(self, anon_client, db):
        response = anon_client.get("/health/")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]
        assert "kafka" in data["services"]
        assert "elasticsearch" in data["services"]

    def test_database_is_up(self, anon_client, db):
        response = anon_client.get("/health/")
        data = response.json()
        assert data["services"]["database"]["status"] == "up"
        assert "latency_ms" in data["services"]["database"]


class TestE2EExport:
    """Test CSV export endpoint."""

    def test_export_books_csv(self, auth_client, book):
        response = auth_client.get("/api/v1/books/export/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        content = b"".join(response.streaming_content).decode()
        assert "title" in content
        assert "Dune" in content
        assert "Frank Herbert" in content


class TestE2EFullJourney:
    """
    Complete end-to-end journey testing the entire system.

    Simulates a realistic user workflow:
    register → login → browse → search → reserve → rate → check analytics → return
    """

    def test_complete_user_journey(self, db, monkeypatch):
        from apps.search import es_client

        monkeypatch.setattr(es_client, "search_books", lambda query, size=20: None)
        client = APIClient()

        # === Setup: Register and authenticate ===
        client.post(
            "/api/v1/users/register/",
            {
                "username": "journey_user",
                "email": "journey@library.com",
                "password": "journey_pass123",
            },
        )
        login = client.post(
            "/api/v1/users/login/",
            {
                "username": "journey_user",
                "password": "journey_pass123",
            },
        )
        token = login.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # === Step 1: Create content ===
        genre = client.post(
            "/api/v1/genres/",
            {
                "name": "Programming",
                "slug": "programming",
            },
        )
        assert genre.status_code == 201

        book1 = client.post(
            "/api/v1/books/",
            {
                "title": "Clean Code",
                "author": "Robert C. Martin",
                "isbn": "9780132350884",
                "publication_date": "2008-08-01",
                "genre": genre.data["id"],
                "copies_total": 3,
                "copies_available": 3,
            },
        )
        assert book1.status_code == 201

        book2 = client.post(
            "/api/v1/books/",
            {
                "title": "Clean Architecture",
                "author": "Robert C. Martin",
                "isbn": "9780134494166",
                "publication_date": "2017-09-20",
                "genre": genre.data["id"],
                "copies_total": 2,
                "copies_available": 2,
            },
        )
        assert book2.status_code == 201

        # === Step 2: Browse and search ===
        books_list = client.get("/api/v1/books/")
        assert books_list.status_code == 200
        assert books_list.data["count"] == 2

        search = client.get("/api/v1/search/?q=Clean")
        assert search.status_code == 200
        assert search.data["count"] == 2

        # Reset trie so it picks up the new books
        trie_module._trie = None
        autocomplete = client.get("/api/v1/search/autocomplete/?q=Clea")
        assert autocomplete.status_code == 200
        assert len(autocomplete.data["suggestions"]) >= 2

        # === Step 3: Reserve a book ===
        reservation = client.post(
            "/api/v1/reservations/",
            {
                "book": book1.data["id"],
            },
        )
        assert reservation.status_code == 201
        reservation_id = reservation.data["id"]

        # Copies should decrease
        book_detail = client.get(f"/api/v1/books/{book1.data['id']}/")
        assert book_detail.data["copies_available"] == 2

        # === Step 4: Rate the book ===
        rate = client.post(
            f"/api/v1/books/{book1.data['id']}/rate/",
            {
                "rate": 92,
                "review": "Must read for every developer",
            },
        )
        assert rate.status_code == 201

        # === Step 5: Check analytics ===
        analytics = client.get("/api/v1/analytics/top/")
        assert analytics.status_code == 200

        # === Step 6: Extend and return ===
        extend = client.post(
            f"/api/v1/reservations/{reservation_id}/extend/",
            {
                "days": 14,
            },
        )
        assert extend.status_code == 200

        return_resp = client.post(
            f"/api/v1/reservations/{reservation_id}/return_book/",
        )
        assert return_resp.status_code == 200
        assert return_resp.data["status"] == "returned"

        # Copies should be restored
        book_detail = client.get(f"/api/v1/books/{book1.data['id']}/")
        assert book_detail.data["copies_available"] == 3

        # === Step 7: Health check ===
        health = client.get("/health/")
        assert health.status_code in (200, 503)
        assert health.json()["services"]["database"]["status"] == "up"

        # === Step 8: Export ===
        export = client.get("/api/v1/books/export/")
        assert export.status_code == 200
        csv_content = b"".join(export.streaming_content).decode()
        assert "Clean Code" in csv_content

        # === Step 9: Verify profile still accessible ===
        profile = client.get("/api/v1/users/me/")
        assert profile.status_code == 200
        assert profile.data["username"] == "journey_user"
