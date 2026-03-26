# EventPulse — Technology Stack

> A complete inventory of every technology, library, and tool used in the EventPulse backend, with version constraints, purpose, and configuration notes.

---

## Table of Contents

- [Language & Runtime](#language--runtime)
- [Web Framework](#web-framework)
- [Database & ORM](#database--orm)
- [Caching & Message Bus](#caching--message-bus)
- [Background Task Processing](#background-task-processing)
- [Security](#security)
- [Real-Time Communication](#real-time-communication)
- [Validation & Configuration](#validation--configuration)
- [Observability](#observability)
- [HTTP Client & Networking](#http-client--networking)
- [Testing](#testing)
- [Containerization & Deployment](#containerization--deployment)
- [Development Tooling](#development-tooling)
- [Infrastructure Services](#infrastructure-services)

---

## Language & Runtime

| Component | Version | Notes |
|---|---|---|
| **Python** | `3.11+` | Required. Uses `match` statements (3.10+), `X \| Y` union syntax (3.10+), `asyncio.run()` isolation per task |
| **ASGI** | — | Application follows the ASGI spec; served by Uvicorn (dev) or Gunicorn + UvicornWorker (prod) |

Python 3.11 is specified in `FROM python:3.11-slim` in both Dockerfiles. The `asyncio_mode = auto` setting in `pytest.ini` requires 3.8+ but full compatibility is validated against 3.11.

---

## Web Framework

| Library | Version | Purpose |
|---|---|---|
| **FastAPI** | `>=0.110.0` | Primary HTTP and WebSocket framework |
| **Uvicorn** | `>=0.27.0` | ASGI server for development (`--reload`) |
| **Gunicorn** | `>=21.2.0` | Production process manager (4 workers, `UvicornWorker` class) |
| **python-multipart** | `>=0.0.9` | Form data parsing (required by FastAPI) |

FastAPI provides automatic OpenAPI documentation at `/docs` (Swagger UI) and `/redoc`. The `lifespan` context manager pattern (introduced in Starlette 0.20) is used throughout, replacing the deprecated `@app.on_event` decorator.

**Routing prefix:** All versioned endpoints are mounted under `/api/v1/` to support future API versioning without breaking changes.

---

## Database & ORM

| Library | Version | Purpose |
|---|---|---|
| **PostgreSQL** | `15+` | Primary relational database (Docker image: `postgres:15-alpine`) |
| **SQLAlchemy** | `>=2.0.25` | Async ORM and query builder |
| **asyncpg** | `>=0.29.0` | High-performance async PostgreSQL driver (used at runtime) |
| **psycopg2-binary** | `>=2.9.9` | Sync PostgreSQL driver (used by Alembic for migration execution) |
| **Alembic** | `>=1.13.1` | Database schema migration management |

### SQLAlchemy Configuration

The async engine is configured with production-grade connection pool settings:

```python
engine = create_async_engine(
    settings.DATABASE_URL,   # postgresql+asyncpg://...
    pool_size=10,            # baseline connections kept open
    max_overflow=20,         # additional connections under load (total: 30)
    pool_pre_ping=True,      # validate connections before use
    pool_recycle=3600,       # recycle connections hourly (avoids stale connections)
    echo=settings.DB_ECHO,   # SQL logging toggle via env var
)
```

### Alembic — Async Migration Support

Alembic is configured for async execution in `alembic/env.py` by using `create_async_engine` with `asyncio.run()`. The `DATABASE_URL` is sourced from `settings` at runtime. A derived sync URL (`postgresql://...`) is auto-computed from the async URL for compatibility with Alembic's offline mode.

**Migration chain:**

```
405c286eaca1  →  ec58312128bc  →  f22717a1db4d  →  50a37bce1d12  →  bc45ac0e7528  →  44b69d9393f0
   (users)         (api_keys)       (events)        (aggregates)    (alerts +          (perf index)
                                                                    alert_history)
```

Migrations run automatically on container startup via:
```
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app ..."]
```

---

## Caching & Message Bus

| Library | Version | Purpose |
|---|---|---|
| **Redis** | `7+` | Caching, event queue, rate limiter, Pub/Sub message bus, Celery broker & result backend |
| **redis-py** | `>=5.0.1` | Async Redis client (`redis.asyncio`) for application code |
| **hiredis** | `>=2.3.2` | C-accelerated Redis protocol parser (auto-used by redis-py) |

Redis serves four distinct roles:

| Role | Key Pattern | Description |
|---|---|---|
| **Event Queue** | `event_queue` (list) | RPUSH by ingest API; RPOP by Celery ingest task |
| **Rate Limiter** | `rate_limit:{api_key_id}` (sorted set) | Sliding-window counter per API key |
| **Pub/Sub Bus** | `events:*`, `metrics:*`, `alerts:*`, `rate_limit:*` | Broadcast from Celery workers to WebSocket broadcaster |
| **Celery Backend** | Internal Celery keys | Task result storage (`CELERY_RESULT_BACKEND`) |

Redis databases:
- `redis://...redis.../0` — application (queue, rate limiter, Pub/Sub)
- `redis://...redis.../1` — Celery result backend (separate DB to avoid key collisions)

---

## Background Task Processing

| Library | Version | Purpose |
|---|---|---|
| **Celery** | `>=5.3.6` | Distributed task queue and periodic scheduler |
| **kombu** | `>=5.3.5` | Messaging library underlying Celery |

### Celery Configuration

```python
celery_app.conf.update(
    task_serializer="json",          # never pickle — security
    task_acks_late=True,             # ACK after completion (no lost tasks)
    task_reject_on_worker_lost=True, # re-queue on worker crash
    worker_prefetch_multiplier=1,    # one task per slot — fair under async load
    result_expires=3600,             # clean up task results after 1 hour
    broker_connection_retry_on_startup=True,
)
```

### Beat Schedule (Periodic Tasks)

| Task | Interval | Description |
|---|---|---|
| `process_event_batch` | Every 5s | Dequeue 100 events from Redis → bulk INSERT into PostgreSQL |
| `compute_minute_aggregates` | Every 60s | Compute `events_per_minute`, `active_users_1m` for all clients |
| `compute_hourly_aggregates` | Every 3600s | Compute `events_per_hour`, `active_users_1h`, `top_events_1h` |
| `cleanup_old_aggregates` | Every 86400s | Delete aggregates older than 30 days |
| `evaluate_alerts` | Every 60s | Evaluate all enabled alert conditions, trigger notifications |

### Docker Services

| Service | Command |
|---|---|
| `eventpulse_worker` | `celery -A worker.celery_app worker --loglevel=info --concurrency=2` |
| `eventpulse_beat` | `celery -A beat.celery_app beat --loglevel=info` |

---

## Security

| Library | Version | Purpose |
|---|---|---|
| **python-jose** | `>=3.3.0` | JWT token encoding and decoding (`[cryptography]` extra) |
| **passlib** | `>=1.7.4` | Password hashing abstraction (`[bcrypt]` extra) |
| **bcrypt** | `==4.0.1` | Pinned bcrypt implementation (passlib backend) |
| **python-dotenv** | `>=1.0.0` | `.env` file loading (via `pydantic-settings`) |

### JWT Tokens

- Algorithm: **HS256** (HMAC-SHA256), configured via `ALGORITHM` env var
- `SECRET_KEY`: 32-byte random hex string (`openssl rand -hex 32`)
- Access token TTL: `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60)
- Refresh token TTL: `REFRESH_TOKEN_EXPIRE_DAYS` (default: 7)
- Token type claim (`"type": "access"` | `"refresh"`) enforced on validation

### Password Hashing

- Algorithm: **bcrypt** via `passlib.CryptContext(schemes=["bcrypt"])`
- Input byte-length capped at 72 bytes (bcrypt maximum enforced in `get_password_hash`)
- Constant-time comparison via `pwd_context.verify()`

### API Key Security

- Generated with `secrets.token_hex(32)` — 256 bits of entropy
- Format: `ep_live_<64 hex chars>` (prefix allows easy identification in logs/configs)
- Stored as **SHA-256 hash** in `api_keys.key_hash` (unique, indexed)
- Plain key is returned once at creation and never persisted

---

## Real-Time Communication

| Library | Version | Purpose |
|---|---|---|
| **websockets** | `>=12.0` | WebSocket protocol implementation (used by FastAPI/Starlette internally) |

FastAPI's native WebSocket support (`fastapi.WebSocket`) is used for endpoint definition and connection management. The `ConnectionManager` class in `app/websockets/manager.py` maintains the `active_connections` dictionary and handles per-client/per-connection routing.

WebSocket endpoint: `ws://host/api/v1/ws/live/{client_id}?token=<api_key>`

Supported client → server messages: `ping`, `subscribe`, `unsubscribe`, `get_stats`

Supported server → client message types: `connected`, `event`, `metric`, `alert`, `rate_limit_exceeded`, `error`, `pong`

---

## Validation & Configuration

| Library | Version | Purpose |
|---|---|---|
| **Pydantic** | `>=2.6.0` | Request/response validation, schema definition, type enforcement |
| **pydantic-settings** | `>=2.2.0` | `BaseSettings` for environment variable loading and `.env` file support |
| **email-validator** | `>=2.1.0` | `EmailStr` validation for user registration (Pydantic extra) |

### Settings Architecture

All configuration is centralized in `app/config.py` as a `pydantic_settings.BaseSettings` subclass. Settings are loaded from environment variables (with `.env` fallback). Computed fields (`@computed_field`) derive values at instantiation:

- `sync_database_url` — replaces `postgresql+asyncpg://` with `postgresql://` for Alembic
- `celery_broker` — falls back to `REDIS_URL` if `CELERY_BROKER_URL` is not explicitly set
- `celery_backend` — same fallback pattern
- `access_token_expire` — returns `timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)`
- `refresh_token_expire` — returns `timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)`

`model_config = SettingsConfigDict(extra="allow")` permits additional env vars without validation errors, supporting future extension without `Settings` class modification.

---

## Observability

| Library | Version | Purpose |
|---|---|---|
| **sentry-sdk** | `>=1.39.2` | Error tracking and performance monitoring (`[fastapi]` extra) |
| **prometheus-client** | `>=0.19.0` | Prometheus metrics exposition (available for future dashboarding) |
| **python-dateutil** | `>=2.8.2` | Timezone-aware datetime parsing |
| **pytz** | `>=2024.1` | Timezone definitions |

### Sentry Integration

Sentry is initialized only when `SENTRY_DSN` is present in the environment:

```python
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
```

This makes Sentry purely opt-in for local development while requiring zero code changes for production activation.

### Structured Logging

`app/logging_config.py` configures the root logger with environment-aware formatters:

| Environment | Format | Output |
|---|---|---|
| `production` | JSON (`JSONFormatter`) | stdout + `logs/eventpulse_YYYYMMDD.log` |
| `development` | Human-readable | stdout + `logs/eventpulse_YYYYMMDD.log` |
| Any | Error-only | `logs/errors_YYYYMMDD.log` |

JSON log fields: `timestamp`, `level`, `logger`, `message`, `module`, `function`, `line`, optional `exception`.

---

## HTTP Client & Networking

| Library | Version | Purpose |
|---|---|---|
| **httpx** | `>=0.26.0` | Async HTTP client (used in tests via `AsyncClient`) |
| **aiohttp** | `>=3.9.1` | Async HTTP client (available for service-to-service calls) |
| **requests** | `>=2.31.0` | Sync HTTP client (used in development scripts and stress tests) |

---

## Testing

| Library | Version | Purpose |
|---|---|---|
| **pytest** | `>=7.4.4` | Test runner and assertion framework |
| **pytest-asyncio** | `>=0.23.3` | Async test support (`asyncio_mode = auto`) |
| **pytest-cov** | `>=4.1.0` | Code coverage reporting (`--cov=app --cov-report=html`) |
| **faker** | `>=22.0.0` | Realistic fake data generation for fixtures |

### Test Architecture

Tests use a separate database (`TEST_DATABASE_URL`) with schema created per-function and dropped after each test, guaranteeing isolation. The `get_db` FastAPI dependency is overridden via `app.dependency_overrides` to inject the test session.

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run only unit tests
pytest tests/unit/ -v

# Run integration tests
pytest -m integration -v
```

---

## Containerization & Deployment

| Tool | Version | Purpose |
|---|---|---|
| **Docker** | 20.10+ | Container runtime |
| **Docker Compose** | V2 | Multi-service orchestration |

### Docker Images

| File | Base Image | Stage | Entrypoint |
|---|---|---|---|
| `Dockerfile` | `python:3.11-slim` | Single-stage (dev) | `alembic upgrade head && uvicorn app.main:app` |
| `Dockerfile.prod` | `python:3.11-slim` (build + final) | Multi-stage (prod) | `gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker` |

The production image uses a multi-stage build: the `builder` stage installs wheels; the final stage copies only the pre-built wheels (no gcc, no pip cache) reducing image size and attack surface. The app runs as `appuser` (UID 1000).

### Docker Compose Services

| Service | Image | Port | Health Check |
|---|---|---|---|
| `eventpulse_postgres` | `postgres:15-alpine` | `5434:5432` | `pg_isready` |
| `eventpulse_redis` | `redis:7-alpine` | `6381:6379` | `redis-cli ping` |
| `eventpulse_api` | Local build | `8002:8000` | `GET /api/v1/health/live` |
| `eventpulse_worker` | Local build | — | Redis TCP socket connect |
| `eventpulse_beat` | Local build | — | Redis TCP socket connect |

All health checks include `start_period` to prevent false negatives during initialization.

### Deployment Targets

**Local (Docker Compose):**
```bash
docker-compose up --build        # development
docker-compose -f docker-compose.prod.yml up --build -d   # production
```

**Render:**
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add PostgreSQL 15 and Redis add-ons from Render marketplace
- Set all required environment variables in Render dashboard

**Kubernetes:** Liveness (`/health/live`) and readiness (`/health/ready`) probes are implemented and ready for `livenessProbe` / `readinessProbe` configuration in deployment manifests.

---

## Development Tooling

| Tool | Version | Purpose |
|---|---|---|
| **black** | `>=23.12.1` | Opinionated Python code formatter |
| **flake8** | `>=7.0.0` | Python linting and style enforcement |
| **mypy** | `>=1.8.0` | Static type checking |
| **pre-commit** | `>=3.6.0` | Git hook management for linting/formatting on commit |

---

## Infrastructure Services

### External Services (Optional)

| Service | Configuration Variable | Purpose |
|---|---|---|
| **Sentry** | `SENTRY_DSN` | Error tracking and performance tracing |
| **SMTP Server** | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Alert email notifications |
| **Elasticsearch** | `ELASTICSEARCH_URL` | (Planned) Full-text event search |
| **Prometheus** | — | Metrics exposition via `prometheus-client` |

### Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ | — | JWT signing key (32-byte hex) |
| `ALGORITHM` | ✗ | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✗ | `60` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ✗ | `7` | Refresh token TTL |
| `DATABASE_URL` | ✅ | — | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | ✅ | — | `redis://host:6379/0` |
| `APP_ENV` | ✗ | `development` | Switches log format and Sentry environment |
| `DEBUG` | ✗ | `True` | FastAPI debug mode |
| `LOG_LEVEL` | ✗ | `INFO` | Root logger level |
| `SENTRY_DSN` | ✗ | — | Enables Sentry when set |
| `SMTP_HOST` | ✗ | — | Enables email notifications when set |
