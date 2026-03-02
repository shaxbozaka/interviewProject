import pytest

from core.caching import _l1_cache


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear L1 and L2 caches before each test to prevent stale data."""
    _l1_cache.clear()
    from django.core.cache import cache

    cache.clear()
    yield
    _l1_cache.clear()
    cache.clear()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
        email="test@example.com",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
