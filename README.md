# Library Management System

A full-stack library management system built with Django REST Framework, demonstrating production-grade architecture: design patterns, custom data structures, async processing, event streaming, full-text search, and containerized deployment.

**Live:** [library.shaxbozaka.cc](https://library.shaxbozaka.cc)

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0 / DRF 3.16 / Python 3.13 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 (two-tier: in-process LRU + Redis) |
| Search | Elasticsearch 7.17 with PostgreSQL fallback |
| Message Broker | RabbitMQ 3 |
| Event Streaming | Apache Kafka |
| Task Queue | Celery with Beat scheduler |
| Web Server | Nginx + Gunicorn |
| Orchestration | Docker Compose / Kubernetes |

## Features

### User-Facing Library (`/`)
- Browse 5,000 real books sourced from [Open Library](https://openlibrary.org)
- Full-text search with Elasticsearch (auto-fallback to PostgreSQL)
- Trie-based autocomplete
- Book detail pages with descriptions and "Read This Book" links to Archive.org
- User registration, JWT authentication
- Reserve, return, and extend book loans
- Rate books (1-100 scale) with reviews
- Genre filtering, sorting, cursor-based pagination

### Admin Dashboard (`/dashboard/`)
- Live request traces with step-by-step timing
- System health monitoring (DB, Redis, Kafka, ES)
- Cache performance metrics (L1 hit rate, Redis stats)
- Rate limit testing visualization
- Architecture overview

## Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Repository | `apps/books/services.py` | Data access abstraction with two-tier caching |
| Command | `apps/reservations/commands.py` | `ReserveBookCommand`, `ReturnBookCommand`, `ExtendReservationCommand` |
| Factory + Strategy | `apps/notifications/` | Polymorphic notification channels (email, in-app, push) |
| Circuit Breaker | `core/resilience.py` | Fault tolerance with CLOSED/OPEN/HALF_OPEN states |
| Retry with Backoff | `core/resilience.py` | Exponential backoff with jitter |
| CQRS | `apps/analytics/` | Denormalized read model updated via Kafka consumers |

## Custom Data Structures

| Structure | File | Complexity |
|-----------|------|-----------|
| LRU Cache | `core/cache.py` | Doubly-linked list + hashmap, O(1) get/put, TTL, thread-safe |
| Two-Tier Cache | `core/caching.py` | L1 in-process LRU (60s) + L2 Redis (5min), pattern invalidation |
| Trie | `core/trie.py` | Prefix tree for autocomplete, weight-based ranking, thread-safe |
| Token Bucket | `core/rate_limiter.py` | Per-client rate limiting with stale bucket cleanup |

## API

All endpoints under `/api/v1/`:

```
POST   /users/register/          Register new user
POST   /users/login/             JWT token (access + refresh)
GET    /users/me/                Current user profile

GET    /books/                   List books (cursor pagination, genre filter, ordering)
GET    /books/:id/               Book detail
POST   /books/:id/rate/          Rate a book (1-100 + review)
GET    /books/export/            Stream CSV export

GET    /genres/                  List genres (by slug)
GET    /search/?q=               Full-text search (ES/PG)
GET    /search/autocomplete/?q=  Trie-based autocomplete

POST   /reservations/            Reserve a book
POST   /reservations/:id/return_book/  Return a book
POST   /reservations/:id/extend/       Extend reservation

GET    /analytics/top/           Top 20 books by popularity
GET    /health/                  Service health check
```

## Quick Start

```bash
# Clone
git clone https://github.com/shaxbozaka/interviewProject.git
cd interviewProject

# Copy environment file
cp .env.example .env

# Start all services
docker compose up -d

# Run migrations and seed data
docker compose exec web python manage.py migrate
docker compose exec web python scripts/seed_massive.py
docker compose exec web python manage.py reindex_books

# Populate with real books from Open Library
docker compose exec web python manage.py populate_real_books
```

The app is now running at `http://localhost:8888`.

## Testing

```bash
# Run all tests (uses SQLite in-memory, no Docker services needed)
pytest --cov=apps --cov=core --cov-report=term-missing -v

# Run a specific test
pytest apps/books/tests/test_books_api.py -v

# Linting
ruff check .
ruff format --check .
```

## Production Deployment

### Docker Compose

```bash
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
./k8s/deploy.sh              # full deploy
./k8s/deploy.sh --seed       # with seed data
./k8s/deploy.sh --destroy    # teardown
```

K8s manifests include HPA auto-scaling (2-10 web replicas based on CPU/memory).

## Architecture

```
                         +-----------+
                         |   Nginx   |  rate limiting, static files
                         +-----+-----+
                               |
                         +-----+-----+
                         |  Gunicorn  |  Django/DRF
                         +-----+-----+
                               |
          +--------+-----------+-----------+--------+
          |        |           |           |        |
     +----+---+ +--+--+ +-----+------+ +--+---+ +--+--+
     |Postgres| |Redis | |Elasticsearch| |Kafka | | RMQ |
     |  (DB)  | |(L2)  | |  (search)  | |(events)|(broker)|
     +--------+ +------+ +------------+ +------+ +------+
                                                     |
                                              +------+------+
                                              | Celery      |
                                              | Workers     |
                                              +-------------+
```

## License

MIT
