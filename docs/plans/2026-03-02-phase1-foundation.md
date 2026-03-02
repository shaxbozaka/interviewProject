# Phase 1: Foundation — Git, Docker, PostgreSQL

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the existing Django library app into a properly structured, containerized project with PostgreSQL replacing SQLite.

**Architecture:** Restructure from flat layout (hello/, library/) to organized layout (config/settings/, apps/books/). Containerize everything with Docker Compose. PostgreSQL + Redis as core infrastructure.

**Tech Stack:** Django 6.0.2, Python 3.13, PostgreSQL 16, Redis 7, Docker, Nginx, Gunicorn

---

### Task 1: Initialize Git repository

**Files:**
- Create: `.gitignore`

**Step 1: Initialize git**

```bash
cd /Users/shaxbozaka/interviewProject
git init
```

**Step 2: Create .gitignore**

Create `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
*.so
*.egg-info/
dist/
build/
.eggs/

# Virtual env
venv/
.venv/
env/

# Django
db.sqlite3
*.log
media/
staticfiles/

# Docker
.docker/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.*
!.env.example

# OS
.DS_Store
Thumbs.db

# Profiling
*.prof
*.lprof
```

**Step 3: Commit**

```bash
git add .gitignore
git commit -m "feat: initialize git repository with .gitignore"
```

---

### Task 2: Fix manage.py

The current `manage.py` contains `pip install memory_profiler` instead of actual Django management code.

**Files:**
- Modify: `manage.py`

**Step 1: Write the correct manage.py**

Replace `manage.py` with:

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

Note: Points to `config.settings.development` — we'll create that in Task 5.

**Step 2: Move main.py to scripts/**

`main.py` (memory profiler demo) belongs in scripts:

```bash
mv main.py scripts/memory_demo.py
```

**Step 3: Commit**

```bash
git add manage.py scripts/memory_demo.py
git commit -m "fix: restore proper manage.py, move memory demo to scripts"
```

---

### Task 3: Create requirements files

**Files:**
- Create: `requirements/base.txt`
- Create: `requirements/dev.txt`
- Create: `requirements/prod.txt`

**Step 1: Create requirements/base.txt**

```
Django==6.0.2
djangorestframework==3.16.1
django-extensions==4.1

# PostgreSQL
psycopg[binary]==3.2.6

# Redis
django-redis==5.4.0
redis==5.2.1

# Celery
celery[redis]==5.4.0

# JWT Auth
djangorestframework-simplejwt==5.4.0

# CORS
django-cors-headers==4.7.0

# Environment
python-decouple==3.8

# Server
gunicorn==23.0.0
```

**Step 2: Create requirements/dev.txt**

```
-r base.txt

# Testing
pytest==8.3.4
pytest-django==4.9.0
pytest-cov==6.0.0
factory-boy==3.3.1

# Profiling
memory-profiler==0.61.0
django-silk==5.3.2

# Linting
ruff==0.9.0

# Debug
django-debug-toolbar==5.0.1
ipython==9.0.1
```

**Step 3: Create requirements/prod.txt**

```
-r base.txt

# Monitoring
sentry-sdk[django]==2.19.2
```

**Step 4: Commit**

```bash
git add requirements/
git commit -m "feat: add split requirements files (base/dev/prod)"
```

---

### Task 4: Restructure project layout

Rename `hello/` → `config/`, move `library/` → `apps/books/`, update all imports.

**Files:**
- Rename: `hello/` → `config/`
- Move: `library/` → `apps/books/`
- Create: `apps/__init__.py`
- Create: `apps/books/urls.py`
- Modify: `apps/books/apps.py` (update name)
- Modify: `config/urls.py` (update imports)
- Modify: `config/wsgi.py` (update settings path)
- Modify: `config/asgi.py` (update settings path)

**Step 1: Create new directory structure**

```bash
mkdir -p apps
```

**Step 2: Rename hello → config**

```bash
mv hello config
```

**Step 3: Move library → apps/books**

```bash
mv library apps/books
```

**Step 4: Create apps/__init__.py**

Create `apps/__init__.py` (empty file):

```python
```

**Step 5: Update apps/books/apps.py**

```python
from django.apps import AppConfig


class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.books'
    label = 'books'
```

**Step 6: Create apps/books/urls.py**

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import BookViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')

urlpatterns = [
    path('', include(router.urls)),
]
```

**Step 7: Update config/urls.py**

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.books.urls')),
]
```

**Step 8: Update config/wsgi.py**

Change `DJANGO_SETTINGS_MODULE` from `'hello.settings'` to `'config.settings.development'`.

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
application = get_wsgi_application()
```

**Step 9: Update config/asgi.py**

```python
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
application = get_asgi_application()
```

**Step 10: Update apps/books/models.py**

No changes needed — models don't reference the old module name.

**Step 11: Update apps/books/views.py**

Update import path:

```python
from rest_framework import viewsets, filters
from django.db.models import Avg

from .models import Book
from .serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author', 'publication_date', 'get_rating']
    ordering = ['-get_rating']

    def get_queryset(self):
        return Book.objects.annotate(
            get_rating=Avg('ratings__rate')
        ).order_by(*self.ordering)
```

**Step 12: Update apps/books/serializers.py**

No changes needed — already uses relative imports.

**Step 13: Update scripts/script.py**

```python
from apps.books.models import Book, Rating

ratings = [
    {"rate": 5, "book_id": 1},
    {"rate": 2, "book_id": 1},
    {"rate": 3, "book_id": 1},
    {"rate": 1, "book_id": 2},
    {"rate": 2, "book_id": 2},
    {"rate": 5, "book_id": 3},
]
for x in ratings:
    rate = Rating(**x)
    rate.save()
```

**Step 14: Fix migrations**

The existing migrations reference `library` as app label. Since we set `label = 'books'` in the new AppConfig, we need to update migration references.

Update `apps/books/migrations/0001_initial.py`: replace any `app_label = 'library'` references.

Also update `apps/books/migrations/0003_alter_rating_book_and_more.py` if it has ForeignKey references to `'library.Book'` — change to `'books.Book'`.

**Step 15: Commit**

```bash
git add -A
git commit -m "refactor: restructure project layout (hello→config, library→apps/books)"
```

---

### Task 5: Split settings into base/development/production

**Files:**
- Delete: `config/settings.py`
- Create: `config/settings/__init__.py`
- Create: `config/settings/base.py`
- Create: `config/settings/development.py`
- Create: `config/settings/production.py`
- Create: `.env.example`

**Step 1: Create config/settings/__init__.py**

```python
```

**Step 2: Create config/settings/base.py**

```python
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'corsheaders',
    'django_extensions',

    # Local
    'apps.books',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='library_db'),
        'USER': config('DB_USER', default='library_user'),
        'PASSWORD': config('DB_PASSWORD', default='library_pass'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    'PAGE_SIZE': 20,
}

# Redis
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

**Step 3: Create config/settings/development.py**

```python
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS += [  # noqa: F405
    'debug_toolbar',
    'silk',
]

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
MIDDLEWARE.append('silk.middleware.SilkyMiddleware')  # noqa: F405

INTERNAL_IPS = ['127.0.0.1']

CORS_ALLOW_ALL_ORIGINS = True

# Use console email backend in dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Silk profiling
SILKY_PYTHON_PROFILER = True
```

**Step 4: Create config/settings/production.py**

```python
from .base import *  # noqa: F401,F403
from decouple import config

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    cast=lambda v: [s.strip() for s in v.split(',')],
    default='',
)
```

**Step 5: Create .env.example**

```
# Django
SECRET_KEY=change-me-to-a-real-secret-key
DJANGO_SETTINGS_MODULE=config.settings.development

# Database
DB_NAME=library_db
DB_USER=library_user
DB_PASSWORD=library_pass
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Allowed Hosts (production)
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Step 6: Create .env from example (for local dev)**

```bash
cp .env.example .env
```

**Step 7: Delete old config/settings.py**

```bash
rm config/settings.py
```

**Step 8: Commit**

```bash
git add config/settings/ .env.example
git rm config/settings.py
git commit -m "refactor: split settings into base/development/production"
```

---

### Task 6: Create Dockerfile

**Files:**
- Create: `Dockerfile`

**Step 1: Write the Dockerfile**

```dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt
COPY requirements/prod.txt requirements/prod.txt
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

**Step 2: Create .dockerignore**

```
venv/
.venv/
__pycache__/
*.pyc
.git/
.env
db.sqlite3
.DS_Store
*.log
.idea/
.vscode/
node_modules/
```

**Step 3: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add Dockerfile for Django app"
```

---

### Task 7: Create docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

**Step 1: Write docker-compose.yml**

```yaml
services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.development
      - DB_HOST=postgres
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: library_db
      POSTGRES_USER: library_user
      POSTGRES_PASSWORD: library_pass
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U library_user -d library_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose with PostgreSQL and Redis"
```

---

### Task 8: Create Nginx config

**Files:**
- Create: `nginx/nginx.conf`
- Modify: `docker-compose.yml` (add nginx service)

**Step 1: Create nginx/nginx.conf**

```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name localhost;

    client_max_body_size 10M;

    location /static/ {
        alias /app/staticfiles/;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Step 2: Add nginx service to docker-compose.yml**

Add to `services:` section:

```yaml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      - ./staticfiles:/app/staticfiles
    depends_on:
      - web
```

**Step 3: Commit**

```bash
git add nginx/ docker-compose.yml
git commit -m "feat: add Nginx reverse proxy config"
```

---

### Task 9: Create pytest configuration

**Files:**
- Create: `pytest.ini`
- Create: `conftest.py`

**Step 1: Create pytest.ini**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.development
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

**Step 2: Create conftest.py**

```python
import pytest


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()
```

**Step 3: Write test to verify the book API still works**

Create `apps/books/tests/test_books_api.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

```bash
pytest apps/books/tests/test_books_api.py -v
```

Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add pytest.ini conftest.py apps/books/tests/
git commit -m "test: add pytest config and book API smoke tests"
```

---

### Task 10: Verify full Docker stack works

**Step 1: Build and start all services**

```bash
docker compose up --build -d
```

**Step 2: Run migrations inside the container**

```bash
docker compose exec web python manage.py migrate
```

Expected: All migrations apply successfully to PostgreSQL.

**Step 3: Verify the API responds**

```bash
curl http://localhost:8000/api/v1/books/
```

Expected: `200 OK` with empty paginated response.

**Step 4: Verify Nginx proxy**

```bash
curl http://localhost/api/v1/books/
```

Expected: Same `200 OK` response via port 80.

**Step 5: Verify Redis connection**

```bash
docker compose exec web python -c "
import django; django.setup()
from django.core.cache import cache
cache.set('test', 'works')
print(cache.get('test'))
"
```

Expected: Prints `works`.

**Step 6: Run tests inside container**

```bash
docker compose exec web pytest -v
```

Expected: All 3 tests pass.

**Step 7: Seed some data**

```bash
docker compose exec web python manage.py shell -c "
from apps.books.models import Book
Book.objects.create(title='The Pragmatic Programmer', author='David Thomas', publication_date='1999-10-20')
Book.objects.create(title='Clean Code', author='Robert C. Martin', publication_date='2008-08-01')
Book.objects.create(title='Designing Data-Intensive Applications', author='Martin Kleppmann', publication_date='2017-03-16')
print(f'Created {Book.objects.count()} books')
"
```

**Step 8: Final commit**

```bash
git add -A
git commit -m "feat: phase 1 complete — Docker, PostgreSQL, Redis, Nginx foundation"
```

---

## Summary: Files created/modified in Phase 1

```
Created:
  .gitignore
  .dockerignore
  .env.example
  .env
  Dockerfile
  docker-compose.yml
  pytest.ini
  conftest.py
  requirements/base.txt
  requirements/dev.txt
  requirements/prod.txt
  config/settings/__init__.py
  config/settings/base.py
  config/settings/development.py
  config/settings/production.py
  apps/__init__.py
  apps/books/urls.py
  apps/books/tests/__init__.py
  apps/books/tests/test_books_api.py
  nginx/nginx.conf

Modified:
  manage.py                    (restored to proper Django manage.py)
  config/urls.py               (updated imports, api/v1/ prefix)
  config/wsgi.py               (updated settings module path)
  config/asgi.py               (updated settings module path)
  apps/books/apps.py           (updated name to apps.books, label to books)
  apps/books/views.py          (no import changes needed — already relative)
  scripts/script.py            (updated import path)

Deleted:
  config/settings.py           (replaced by settings/ directory)
  main.py                      (moved to scripts/memory_demo.py)
  db.sqlite3                   (no longer needed — using PostgreSQL)
```
