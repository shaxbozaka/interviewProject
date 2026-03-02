# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django REST Framework library management system demonstrating production architecture: design patterns, custom DSA implementations, async processing, event streaming, full-text search, and containerized deployment.

**Stack:** Django 6.0.2 / DRF 3.16.1 / Python 3.13 / PostgreSQL 16 / Redis 7 / Elasticsearch 7.17 / RabbitMQ / Kafka / Celery / Nginx

## Commands

```bash
# Tests (uses pytest + pytest-django + pytest-cov)
pytest --cov=apps --cov=core --cov-report=term-missing -v
pytest apps/books/tests/test_books_api.py::TestBookAPI::test_list_books_returns_200 -v

# Linting (ruff)
ruff check .
ruff format --check .
ruff format .                    # auto-fix

# Django
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py reindex_books   # rebuilds ES index + Trie
python manage.py populate_real_books  # fetch real books from Open Library (updates in-place)

# Seed data
python scripts/seed.py           # small dataset
python scripts/seed_massive.py   # 90K+ records (500 users, 5K books, 50K ratings)

# Profiling
python scripts/benchmark.py profile_queries
python scripts/benchmark.py profile_cache
python scripts/benchmark.py profile_trie
python scripts/benchmark.py memory_report

# Docker
docker compose up -d                                          # development
docker compose -f docker-compose.prod.yml up -d               # production
docker compose exec web python manage.py migrate

# K8s (manifests in k8s/, deploy script)
./k8s/deploy.sh                  # full deploy
./k8s/deploy.sh --seed           # seed + reindex
./k8s/deploy.sh --destroy        # teardown
```

## Settings Modules

- `config.settings.development` — DEBUG=True, debug_toolbar, silk profiler, CORS open
- `config.settings.production` — DEBUG=False, SSL settings from env vars, restricted CORS
- `config.settings.testing` — SQLite in-memory, sync Celery (`CELERY_TASK_ALWAYS_EAGER`), PageNumberPagination, no profiling middleware

Set via `DJANGO_SETTINGS_MODULE` env var. Tests use `testing` (configured in `pytest.ini`).

## Architecture

### App Structure

Each app under `apps/` follows: `models.py` → `services.py` (repository) → `commands.py` (actions) → `serializers.py` → `views.py` → `urls.py`

### Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Repository | `apps/books/services.py`, `apps/reservations/services.py` | Data access abstraction with caching |
| Command | `apps/reservations/commands.py` | `ReserveBookCommand`, `ReturnBookCommand`, `ExtendReservationCommand` — each has `validate()` + `execute()` |
| Factory + Strategy | `apps/notifications/factory.py`, `strategies.py` | Polymorphic notification channels (email, in-app, push) |
| Circuit Breaker | `core/resilience.py` | `@circuit_breaker()` decorator, CLOSED/OPEN/HALF_OPEN states |
| Retry with Backoff | `core/resilience.py` | `@retry_with_backoff()` decorator, exponential + jitter |
| CQRS | `apps/analytics/` | Denormalized `BookAnalytics` read model updated via Kafka consumers |

### Custom DSA (core/)

- **LRU Cache** (`core/cache.py`) — Doubly-linked list + hashmap, O(1) ops, TTL, thread-safe
- **Two-tier Cache** (`core/caching.py`) — L1 in-process LRU (60s) + L2 Redis (5min), pattern invalidation
- **Trie** (`core/trie.py`) — Prefix tree for autocomplete, weight-based ranking, thread-safe
- **Token Bucket** (`core/rate_limiter.py`) — Per-client rate limiting, stale bucket cleanup

### Async & Events

- **Celery** (broker: RabbitMQ, backend: Redis) — notification tasks, analytics updates
- **Kafka** (`core/events.py`) — publishes `book.reserved`, `book.returned`, `book.rated` to `book-events` topic
- **Celery Beat** — `DatabaseScheduler` for periodic tasks

### Search

`apps/search/es_client.py` queries Elasticsearch with automatic PostgreSQL fallback when ES is unavailable. `apps/search/views.py` exposes `/api/v1/search/?q=` and `/api/v1/search/autocomplete/?q=` (Trie-based).

## Frontend

Two web UIs served by Django:

- **User-facing library** at `/` (`apps/dashboard/templates/dashboard/frontend.html`) — hash-based SPA with browse, search, register/login, reserve/return, rate books
- **Admin dashboard** at `/dashboard/` (`apps/dashboard/templates/dashboard/index.html`) — system monitoring, traces, cache stats, architecture overview

Hash routes: `#/` (home), `#/books` (catalog), `#/books/:id` (detail + read link), `#/search?q=`, `#/login`, `#/register`, `#/my` (profile + reservations)

## API Routes

All under `/api/v1/`:
- `users/` — register, login (JWT), me
- `books/` — CRUD, `<id>/rate/`, `export/csv/` (includes `description`, `read_url` fields)
- `genres/` — list/detail (lookup by slug)
- `reservations/` — create, `<id>/return/`, `<id>/extend/`
- `search/` — full-text search, `autocomplete/`
- `analytics/top/` — top 20 books by popularity (CQRS read model, `pagination_class = None`)
- `dashboard/stats/`, `dashboard/traces/`, `dashboard/cache-stats/`, `dashboard/system-info/`, `dashboard/k8s/`
- `health/` — service health (DB, Redis, Kafka, ES)

Auth: JWT via `Authorization: Bearer <token>`. Token endpoint: `/api/v1/users/login/`.

**Pagination:** Production uses `CursorPagination` (no `count`, navigate via `next`/`previous` URLs). Testing uses `PageNumberPagination`.

## Testing Conventions

- All test classes use `@pytest.mark.django_db`
- Fixtures in `conftest.py`: `api_client`, `user`, `authenticated_client`
- Tests run against SQLite in-memory (no Docker services needed)
- ES/Kafka calls should be mocked: `monkeypatch.setattr(es_client, 'search_books', lambda ...)`
- E2E tests in `tests/e2e/` run against live Docker stack

## Rate Limiting

Two layers:
1. **Nginx** (`nginx/nginx.conf`) — auth: 2r/s, general API: 10r/s, search: 30r/s → returns 429 JSON
2. **DRF** (`core/throttling.py`) — `BurstThrottle` on API views

## Production Deployment

Live at `library.shaxbozaka.cc` via `docker-compose.prod.yml` with 10 services. ES uses 7.17 (lighter than 8.x for memory-constrained servers). K8s manifests in `k8s/` support cluster deployment with HPA auto-scaling.

### Server

Configured via `.env` (`SERVER_HOST`, `SERVER_USER`, `SERVER_PROJECT_PATH`). Credentials in `.env.prod` (not committed).

### Deploy workflow

```bash
# 1. SCP changed files
scp <files> $SERVER_USER@$SERVER_HOST:$SERVER_PROJECT_PATH/<path>

# 2. Rebuild & restart web container
ssh $SERVER_USER@$SERVER_HOST "cd $SERVER_PROJECT_PATH && docker compose -f docker-compose.prod.yml up -d --build web"

# 3. Run migrations (if model changes)
ssh $SERVER_USER@$SERVER_HOST "cd $SERVER_PROJECT_PATH && docker compose -f docker-compose.prod.yml exec web python manage.py migrate"

# 4. Reindex search (if book data changed)
ssh $SERVER_USER@$SERVER_HOST "cd $SERVER_PROJECT_PATH && docker compose -f docker-compose.prod.yml exec web python manage.py reindex_books"
```

### Book data

5000 real books sourced from Open Library API (`populate_real_books` management command). Books include titles, authors, descriptions, publication dates, and `read_url` links to Archive.org / Open Library for reading.
