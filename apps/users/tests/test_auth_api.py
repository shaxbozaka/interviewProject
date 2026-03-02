import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestRegistration:
    def test_register_user(self, api_client):
        url = reverse("user-register")
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepass123",
        }
        response = api_client.post(url, data)
        assert response.status_code == 201
        assert response.data["username"] == "testuser"
        assert "password" not in response.data
        assert User.objects.count() == 1

    def test_register_short_password_fails(self, api_client):
        url = reverse("user-register")
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "short",
        }
        response = api_client.post(url, data)
        assert response.status_code == 400

    def test_register_default_role_is_member(self, api_client):
        url = reverse("user-register")
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepass123",
        }
        api_client.post(url, data)
        user = User.objects.get(username="testuser")
        assert user.role == "member"


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_tokens(self, api_client):
        User.objects.create_user(username="testuser", password="securepass123")
        url = reverse("token-obtain")
        data = {"username": "testuser", "password": "securepass123"}
        response = api_client.post(url, data)
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password_fails(self, api_client):
        User.objects.create_user(username="testuser", password="securepass123")
        url = reverse("token-obtain")
        data = {"username": "testuser", "password": "wrongpass"}
        response = api_client.post(url, data)
        assert response.status_code == 401


@pytest.mark.django_db
class TestProfile:
    def test_get_profile_authenticated(self, api_client):
        user = User.objects.create_user(
            username="testuser", password="securepass123", email="test@example.com"
        )
        api_client.force_authenticate(user=user)
        url = reverse("user-profile")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["username"] == "testuser"

    def test_get_profile_unauthenticated_fails(self, api_client):
        url = reverse("user-profile")
        response = api_client.get(url)
        assert response.status_code == 401

    def test_update_profile(self, api_client):
        user = User.objects.create_user(
            username="testuser", password="securepass123", email="old@example.com"
        )
        api_client.force_authenticate(user=user)
        url = reverse("user-profile")
        response = api_client.patch(url, {"email": "new@example.com"})
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.email == "new@example.com"


@pytest.mark.django_db
class TestPermissions:
    def test_member_cannot_access_librarian_endpoint(self, api_client):
        """Placeholder -- will test once we add librarian-only views in Phase 3."""
        user = User.objects.create_user(
            username="member", password="pass12345678", role="member"
        )
        assert user.role == "member"

    def test_librarian_role_assignment(self, api_client):
        user = User.objects.create_user(
            username="librarian", password="pass12345678", role="librarian"
        )
        assert user.role == "librarian"
