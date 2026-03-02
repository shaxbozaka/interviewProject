# Library Management System -- Full Design

## Goal

Expand the existing Django library app into a production-grade system that demonstrates:
Python, database management, system design patterns, deployment/infra, DSA, highload, version control, application design patterns, and code optimization.

Serves dual purpose: deep learning + interview portfolio piece.

## Architecture

Microservices-inspired modular monolith. Single Django project, but each domain is a separate app with clear boundaries. Infrastructure runs in Docker Compose.

```
                         ┌──────────┐
                         │  Nginx   │
                         │ Rate Limit│
                         │ Load Bal. │
                         └────┬─────┘
                              │
                    ┌─────────▼─────────┐
                    │   Django API       │
                    │  (Gunicorn)        │
                    │  ┌──────────────┐  │
                    │  │ LRU Cache    │  │
                    │  │ (custom DSA) │  │
                    │  └──────────────┘  │
                    └──┬────┬────┬───┬──┘
                       │    │    │   │
          ┌────────────▼┐ ┌▼────▼┐ ┌▼──────────────┐
          │ PostgreSQL  │ │Redis │ │ Elasticsearch  │
          │ + Replica   │ │      │ │                │
          └─────────────┘ └──────┘ └────────────────┘
                       │    │
              ┌────────▼┐ ┌▼────────────┐
              │RabbitMQ │ │   Kafka      │
              └────┬────┘ └────┬────────┘
                   │           │
              ┌────▼────┐ ┌───▼──────────┐
              │ Celery  │ │Kafka Consumer│
              │ Workers │ │  Service     │
              └─────────┘ └──────────────┘
```

## Message Brokers: Kafka vs RabbitMQ

Both included to learn their differences side by side.

### RabbitMQ (via Celery)
- Pattern: work queue -- message consumed by one worker, then gone
- Used for: reservation processing, email notifications, overdue reminders
- Learning: routing keys, dead-letter queues, retry policies

### Kafka
- Pattern: event stream -- multiple consumers, messages retained and replayable
- Used for: audit log, analytics feed, search index updates, activity stream
- Learning: topics, partitions, consumer groups, offset management

## Data Models

### User
- id, username, email, password, role (enum: member/librarian/admin), created_at
- Custom Django user model with JWT authentication

### Book (expanded from existing)
- id, title, author, isbn, publication_date, available, genre (FK), copies_total, copies_available

### Genre
- id, name, slug

### Rating (expanded from existing)
- id, user_id (FK), book_id (FK), rate (1-100), review (text), created_at
- Unique constraint: one rating per user per book

### Reservation
- id, user_id (FK), book_id (FK), reserved_at, due_date, returned_at, status (enum: pending/active/returned/overdue)

### AuditLog (event sourcing lite)
- id, action (enum: create/update/delete), entity_type, entity_id, user_id, changes (JSONField), timestamp

### BookAnalytics (CQRS read model)
- book_id (FK), avg_rating, total_ratings, total_reservations, popularity_score, last_updated
- Denormalized, updated asynchronously via Kafka consumers

### Database techniques
- Indexes on isbn, genre, status, (book_id + user_id) composite
- Check constraints on rate range, copies >= 0
- PostgreSQL partitioning on AuditLog by month
- Read replica for analytics queries
- Connection pooling via PgBouncer

## API Endpoints

```
/api/v1/books/                  GET, POST
/api/v1/books/:id/              GET, PUT, DELETE
/api/v1/books/:id/rate/         POST          → Kafka event
/api/v1/books/search/           GET           → Elasticsearch (fallback: PG LIKE)
/api/v1/books/autocomplete/     GET           → Trie-based
/api/v1/reservations/           GET, POST     → RabbitMQ task
/api/v1/reservations/:id/return/ POST
/api/v1/users/                  GET, POST
/api/v1/users/me/               GET
/api/v1/analytics/top/          GET           → CQRS read model
/health/                        GET           → DB, Redis, Kafka, ES checks
```

## Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Repository | apps/*/services.py | Abstract DB access behind service layer |
| Strategy | apps/books/recommendations.py | Swappable recommendation algorithms |
| Observer | core/signals.py | Django signals fire events to Kafka/RabbitMQ |
| Command | apps/reservations/commands.py | Reserve, return, extend as command objects |
| Factory | apps/notifications/factory.py | Create email/push/in-app notifications |
| Circuit Breaker | core/resilience.py | Wrap external service calls |

## Caching Strategy (3 layers)

| Layer | Tech | What | TTL |
|-------|------|------|-----|
| L1 | Custom LRU (Python) | Hot book objects in-process | 60s |
| L2 | Redis | Query results, analytics, sessions | 5-15 min |
| L3 | Nginx | Static responses, public endpoints | 30s |

Cache invalidation via Kafka events.

## DSA Implementations (from scratch)

- **LRU Cache** (doubly linked list + hashmap) -- core/cache.py
- **Token Bucket** (rate limiting algorithm) -- core/rate_limiter.py
- **Trie** (autocomplete for book search) -- apps/search/trie.py
- **BFS/DFS** (recommendation graph traversal) -- apps/books/recommendations.py

## Resiliency Patterns

- **Circuit Breaker** -- wrap Elasticsearch/Kafka calls; open after N failures, half-open retry after timeout
- **Retry with exponential backoff** -- on transient broker/DB failures
- **Health check endpoint** -- /health/ checks DB, Redis, Kafka, Elasticsearch connectivity
- **Graceful degradation** -- ES down → fallback to PG LIKE search; Redis down → bypass cache

All in core/resilience.py, applied as decorators and middleware.

## Highload Techniques

- Nginx rate limiting + custom token bucket
- Redis caching with invalidation
- PostgreSQL connection pooling (PgBouncer)
- Cursor-based pagination (not offset)
- select_related / prefetch_related for N+1 prevention
- Lazy evaluation with generators for bulk exports
- Gunicorn with multiple workers
- Locust load testing

## Code Optimization

- django-silk for request/query profiling
- memory_profiler for memory analysis
- cProfile for function-level profiling
- Custom middleware to log queries > 100ms
- EXPLAIN ANALYZE on critical queries

## Deployment & Infrastructure

### Docker Compose services
- web (Django + Gunicorn)
- nginx (reverse proxy)
- postgres (primary)
- postgres-replica (read replica)
- redis
- rabbitmq
- kafka + zookeeper
- celery (worker)
- kafka-consumer
- elasticsearch

### CI/CD (GitHub Actions)
- Lint: ruff
- Test: pytest
- Build: Docker image
- Deploy: docker-compose up (staging)

## Git Workflow

- main -- stable, protected
- develop -- integration
- feature/* -- per-feature branches
- Conventional commits: feat:, fix:, refactor:, docs:, test:
- PR reviews required before merge

## Project Structure

```
interviewProject/
├── docker-compose.yml
├── Dockerfile
├── .github/workflows/ci.yml
├── nginx/nginx.conf
├── config/settings/{base,development,production}.py
├── apps/
│   ├── books/        (models, views, serializers, services, commands, tests/)
│   ├── users/        (models, authentication, tests/)
│   ├── reservations/ (models, services, tasks, commands, tests/)
│   ├── analytics/    (models, consumers, tests/)
│   ├── notifications/(factory, strategies, tasks, tests/)
│   └── search/       (indexers, views, trie, tests/)
├── core/
│   ├── cache.py           (LRU cache DSA)
│   ├── rate_limiter.py    (token bucket DSA)
│   ├── resilience.py      (circuit breaker, retry, fallbacks)
│   ├── middleware.py       (slow query logger, profiling)
│   ├── events.py          (Kafka producer helper)
│   └── signals.py         (Observer: Django signals → brokers)
├── scripts/{seed,benchmark}.py
├── tests/{integration/,load/}
├── requirements/{base,dev,prod}.txt
└── manage.py
```

## Implementation Phases

1. Git init + Docker Compose + PostgreSQL migration from SQLite
2. User model + JWT authentication
3. Expand Book/Reservation models + Repository/Command patterns
4. Redis caching + custom LRU cache implementation
5. Celery + RabbitMQ for reservation tasks and notifications
6. Kafka for event streaming + CQRS analytics read model
7. Elasticsearch + Trie autocomplete
8. Nginx + rate limiting + token bucket + load testing
9. Resiliency patterns (circuit breaker, health checks, fallbacks)
10. CI/CD pipeline + profiling/optimization pass
