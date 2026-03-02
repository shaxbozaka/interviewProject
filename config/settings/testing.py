"""
Django settings for running tests locally (without Docker/PostgreSQL).

Uses SQLite in-memory database and disables middleware that isn't
needed during testing (debug_toolbar, silk).
"""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use in-memory SQLite so tests run without a PostgreSQL server.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Skip debug_toolbar and silk -- they add middleware overhead and are
# unnecessary for automated tests.
# (development.py adds them, but we inherit directly from base.py.)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Use PageNumberPagination for tests instead of CursorPagination.
# CursorPagination requires ordering by a real database column, but
# the BookViewSet orders by `get_rating` which is an annotation (Avg).
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [],
}

# Celery: run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
