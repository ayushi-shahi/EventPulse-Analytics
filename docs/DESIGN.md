# EventPulse — Architecture & Internal Design

> This document describes the internal architecture, data flow, and design decisions of the EventPulse backend. It is intended for contributors and engineers onboarding to the codebase.

---

## Table of Contents

- [Architectural Pattern](#architectural-pattern)
- [Application Lifecycle](#application-lifecycle)
- [Data Model](#data-model)
- [Authentication Strategy](#authentication-strategy)
- [Event Ingestion Pipeline](#event-ingestion-pipeline)
- [Metrics & Aggregation System](#metrics--aggregation-system)
- [Alert Engine](#alert-engine)
- [Real-Time WebSocket Layer](#real-time-websocket-layer)
- [Rate Limiting Design](#rate-limiting-design)
- [Validation Layer](#validation-layer)
- [Background Task Architecture](#background-task-architecture)
- [Dependency Injection Pattern](#dependency-injection-pattern)

---

## Architectural Pattern

EventPulse follows a layered, async-first architecture with a clear separation between the HTTP request layer, service logic, and infrastructure (database, cache, message queue).

```
HTTP Client / WebSocket Client
        │
        ▼
┌───────────────────────────────┐
│   FastAPI Router Layer        │  app/api/v1/*.py
│   (Request validation,        │
│    Dependency injection,      │
│    Response serialization)    │
└──────────────┬────────────────┘
               │ Pydantic schemas (in / out)
               ▼
┌───────────────────────────────┐
│   Service Layer               │  app/services/*.py
│   (Business logic, CRUD,      │
│    orchestration)             │
└──────────────┬────────────────┘
               │ SQLAlchemy ORM / raw Redis
               ▼
┌──────────────┬────────────────┐
│  PostgreSQL  │     Redis      │
│  (async via  │  (async via    │
│  asyncpg)    │  redis-py)     │
└──────────────┴────────────────┘
        ▲
        │  asyncio.run() isolation
        │
┌───────────────────────────────┐
│   Celery Worker Layer         │  app/tasks/*.py
│   (Background ingestion,      │
│    aggregation, alerting)     │
└───────────────────────────────┘
```

The request flow for the most common path (event ingestion) is:

1. **Router** (`ingest.py`) receives the HTTP request, Pydantic validates the body
2. **Dependency** (`check_rate_limit`) enforces the per-key sliding-window rate limit via Redis Lua
3. **Service** (`IngestionService`) serializes the event to JSON and pushes it onto a Redis list (`event_queue`)
4. **Response** is returned immediately as `202 Accepted` — the request is non-blocking
5. **Celery Beat** triggers `process_event_batch` every 5 seconds
6. **Task** dequeues events (sync Redis RPOP), then calls `EventProcessor.process_events_batch()` inside `asyncio.run()`
7. **EventProcessor** bulk-inserts rows into `events` via a single `INSERT` statement and publishes to Redis Pub/Sub
8. **WebSocketBroadcaster** receives the Pub/Sub message and forwards it to connected WebSocket clients

---

## Application Lifecycle

Application startup and shutdown are managed by a single `lifespan` async context manager in `app/main.py`, replacing the deprecated `@app.on_event` decorator pattern.

**On startup:**
1. `rate_limiter.initialize()` — connects to Redis, loads Lua script, caches SHA
2. `broadcaster.initialize()` — opens Redis connection and PubSub handle
3. `asyncio.create_task(broadcaster.subscribe_and_broadcast())` — starts the Redis → WebSocket relay loop as a background task

**On shutdown:**
1. Background broadcast task is cancelled and awaited
2. `broadcaster.close()` — releases PubSub and Redis connections
3. `rate_limiter.close()` — releases rate limiter Redis connection

This guarantees clean resource release even if startup raises an exception partway through.

---

## Data Model

### Entities and Relationships

```
┌──────────────────────────────────────────────────────────┐
│ users                                                     │
│  id          UUID  PK                                     │
│  email       VARCHAR(255)  UNIQUE                         │
│  hashed_password  VARCHAR(255)                            │
│  is_active   BOOLEAN                                      │
│  role        VARCHAR(20)  ('user' | 'admin')              │
│  created_at / updated_at                                  │
└──────────────────────────┬───────────────────────────────┘
                           │ 1
                           │ FK: api_keys.user_id → users.id (SET NULL)
                           │ N
┌──────────────────────────▼───────────────────────────────┐
│ api_keys                                                  │
│  id           UUID  PK   ◄──── this is "client_id"        │
│  client_name  VARCHAR(255)                                │
│  key_hash     VARCHAR(255)  UNIQUE INDEX                  │
│  user_id      UUID  FK (nullable)                         │
│  rate_limit   INTEGER  (req/min)                          │
│  is_active    BOOLEAN                                     │
│  created_at / updated_at                                  │
└──────┬────────────────────────────────────────────────────┘
       │  client_id  (app-level join, no DB FK)
       ├──────────────────────────────────────────┐
       │                                          │
       ▼                                          ▼
┌────────────────────────────┐   ┌────────────────────────────────┐
│ events                     │   │ aggregates                     │
│  id         BIGSERIAL  PK  │   │  id           UUID  PK         │
│  client_id  UUID  INDEX    │   │  client_id    UUID  INDEX      │
│  user_id    VARCHAR(255)   │   │  metric_name  VARCHAR(255)     │
│  event_name VARCHAR(255)   │   │  interval_start  TIMESTAMPTZ  │
│  properties JSONB          │   │  interval_end    TIMESTAMPTZ  │
│  event_time TIMESTAMPTZ    │   │  value        FLOAT            │
│  received_at TIMESTAMPTZ   │   │  meta_data    JSONB            │
│                            │   │  UNIQUE(client_id,             │
│  Composite indexes:        │   │         metric_name,           │
│  - (client_id, event_time) │   │         interval_start)        │
│  - (client_id, event_name, │   └────────────────────────────────┘
│     event_time)            │
└────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│ alerts                                         │
│  id           UUID  PK                         │
│  client_id    UUID  INDEX                      │
│  name         VARCHAR(255)                     │
│  expression   JSONB  (metric, operator,        │
│                       threshold, window)       │
│  severity     VARCHAR(20)                      │
│  enabled      BOOLEAN                          │
│  last_triggered  TIMESTAMPTZ                   │
│  trigger_count   INTEGER                       │
│  notification_channels  JSONB                  │
│  cooldown_seconds  INTEGER                     │
└─────────────────────────┬──────────────────────┘
                          │ 1
                          │ app-level join on alert_id
                          │ N
┌─────────────────────────▼──────────────────────┐
│ alert_history                                  │
│  id              UUID  PK                      │
│  alert_id        UUID  INDEX                   │
│  client_id       UUID  INDEX                   │
│  triggered_at    TIMESTAMPTZ  INDEX            │
│  severity        VARCHAR(20)                   │
│  message         VARCHAR(1000)                 │
│  context         JSONB                         │
│  notification_sent  BOOLEAN                    │
└────────────────────────────────────────────────┘
```

### Key Design Decisions

**`api_keys.id` as `client_id`:** Rather than creating a separate `clients` table, the `api_keys.id` UUID is used directly as a client identifier across all analytics tables. This simplifies the schema while allowing one user to own multiple API keys (i.e., multiple logical clients).

**`events` uses `BIGSERIAL`, not `UUID`:** The `events` table is append-only and write-heavy. Using a `BIGSERIAL` integer primary key is more efficient for sequential inserts and index maintenance than a UUID at high throughput.

**No FK on `events.client_id`:** The `events` table has no foreign key constraint on `client_id` (pointing to `api_keys.id`). This is intentional: FK constraints create index lookups on every insert, which would bottleneck the high-throughput ingestion path.

**JSONB for `properties` and `expression`:** Event `properties` are schema-less by design — clients may include any key-value data. Alert `expression` is stored as JSONB to allow flexible condition structures without requiring schema migrations when adding new operators or metric types.

**`uq_client_metric_interval` UPSERT:** The aggregates table uses a unique constraint on `(client_id, metric_name, interval_start)` which allows `INSERT ... ON CONFLICT DO UPDATE` (UPSERT). Celery tasks can safely re-run without creating duplicate aggregate rows.

---

## Authentication Strategy

EventPulse uses two distinct authentication mechanisms, each appropriate to its context.

### Platform Users — JWT Bearer Tokens

Used by humans (developers, admins) who manage the platform via the dashboard or API directly.

```
POST /auth/login
  │
  ├── Look up user by email in DB
  ├── bcrypt.verify(plain_password, hashed_password)
  ├── create_access_token({"sub": user.id, "type": "access"})
  │     └── signed with SECRET_KEY using HS256
  │     └── expires: ACCESS_TOKEN_EXPIRE_MINUTES (default 60)
  └── create_refresh_token({"sub": user.id, "type": "refresh"})
        └── expires: REFRESH_TOKEN_EXPIRE_DAYS (default 7)

Authenticated Request:
  Authorization: Bearer <access_token>
  │
  ├── HTTPBearer extracts token string
  ├── decode_token(token) → payload (or None on JWTError)
  ├── payload["type"] must be "access"
  ├── payload["sub"] → user UUID
  └── DB lookup: SELECT * FROM users WHERE id = user_id
```

Token refresh is explicit: the client must `POST /auth/refresh` with the refresh token. The server validates `type == "refresh"`, verifies the user still exists and is active, and issues a new token pair. There is no implicit token renewal.

### Client Applications — API Keys

Used by programmatic clients (web apps, mobile SDKs, servers) sending events.

```
API Key Creation:
  secrets.token_hex(32) → "ep_live_<64 hex chars>"
  hashlib.sha256(plain_key) → key_hash
  INSERT INTO api_keys (key_hash, ...) — plain key NEVER stored

Authenticated Request:
  X-API-Key: ep_live_...
  │
  ├── hash_api_key(plain_key) → SHA-256 digest
  ├── SELECT * FROM api_keys WHERE key_hash = $1 AND is_active = TRUE
  │     └── O(log n) via unique index on key_hash
  └── Returns APIKey ORM object for downstream use
```

SHA-256 is used (rather than bcrypt) for API key hashing because API keys are long random secrets (256 bits of entropy), making dictionary attacks infeasible. The performance advantage of SHA-256 matters at high ingestion rates where the key is validated on every request.

### Role-Based Access Control

Two roles exist: `user` (default) and `admin`. Admin-only endpoints (the `/admin` router, `GET /auth/users`, `PATCH /auth/users/{id}/disable`) are protected by the `get_current_active_admin` dependency, which extends `get_current_user` with a `role == "admin"` check. Self-disabling is explicitly prevented at the application layer.

---

## Event Ingestion Pipeline

The ingestion path is designed to be non-blocking. The HTTP response returns before any database write occurs.

```
Client
  │
  POST /api/v1/ingest/events
  │
  ▼
check_rate_limit dependency
  ├── hash(api_key) → Redis EVALSHA (Lua sliding window)
  ├── Allowed? → continue
  └── Denied? → HTTP 429 + WebSocket notification

  ▼
IngestionService.enqueue_event()
  ├── Assign server-side received_at timestamp
  ├── Serialize event to JSON
  └── Redis RPUSH "event_queue" <json>

  ▼
HTTP 202 Accepted (immediate response)

                    ┌─── every 5 seconds via Celery Beat ───┐
                    ▼                                        │
  process_event_batch (Celery task)
  ├── Sync Redis RPOP × batch_size (pipeline, 1 round-trip)
  ├── asyncio.run(_insert_events_async())
  │     ├── EventProcessor.process_events_batch()
  │     ├── Parse + validate JSON records
  │     ├── Bulk INSERT INTO events VALUES (...)
  │     └── Publish to Redis Pub/Sub "events:{client_id}"
  └── On failure: LPUSH events back to queue head (no data loss)
```

**Why Redis list as a queue?** A Redis list (`RPUSH` / `RPOP`) provides O(1) push and pop with durability via RDB/AOF persistence. It is simpler than a dedicated message broker for this use case and is already a hard dependency (rate limiter + WebSocket broadcast).

**Sync/Async separation in Celery:** Celery workers run in a synchronous process context. The Redis dequeuing uses the synchronous `redis` client (correct for Celery). The database writes are async (SQLAlchemy `asyncpg`). The separation is explicit: sync Redis RPOP → hand JSON strings to `asyncio.run()` → async bulk INSERT. No async/sync mixing occurs within a single call stack.

---

## Metrics & Aggregation System

Metrics are computed in two modes: on-demand (real-time SQL aggregation for dashboard endpoints) and precomputed (background Celery aggregates for time series).

### On-Demand Metrics

The `MetricsService` computes metrics directly from the `events` table using async SQLAlchemy aggregate queries:

- `compute_events_per_minute` — `COUNT(id)` over a time window, divided by duration in minutes
- `compute_active_users` — `COUNT(DISTINCT user_id)` where `user_id IS NOT NULL`
- `compute_top_events` — `GROUP BY event_name ORDER BY count DESC LIMIT N`
- `get_overview_metrics` — combines all of the above for the dashboard endpoint

### Precomputed Aggregates

Celery Beat triggers aggregate tasks on a schedule:

| Task | Schedule | Metrics Written |
|---|---|---|
| `compute_minute_aggregates` | Every 60s | `events_per_minute`, `active_users_1m` |
| `compute_hourly_aggregates` | Every 3600s | `events_per_hour`, `active_users_1h`, `top_events_1h` |
| `cleanup_old_aggregates` | Every 86400s | Deletes rows where `interval_start < now - 30d` |

Aggregates are stored with an UPSERT (`INSERT ... ON CONFLICT DO UPDATE`) so tasks are idempotent and safe to re-run.

### Time Series Pagination

The `/metrics/time-series/{metric_name}/paginated` endpoint uses cursor-based pagination, encoded as base64 JSON containing the `interval_start` timestamp of the last returned row. This approach is preferred over offset pagination for time-series data because it handles concurrent real-time insertions without skipping or duplicating rows.

---

## Alert Engine

Alerts follow a configuration → evaluation → notification flow.

### Alert Expression Format

```json
{
  "metric": "events_per_minute",
  "operator": ">",
  "threshold": 1000,
  "window": "1m"
}
```

Supported operators: `>`, `<`, `>=`, `<=`, `==`, `!=`

### Evaluation Flow

```
Celery Beat: evaluate_alerts (every 60s)
  │
  ├── SELECT all APIKeys WHERE is_active = TRUE
  └── For each client:
        ├── SELECT all Alerts WHERE client_id = X AND enabled = TRUE
        └── For each alert:
              │
              ├── AlertService.evaluate_alert(alert)
              │     ├── Parse expression (metric, operator, threshold, window)
              │     ├── Query most recent Aggregate for that metric
              │     │     └── Fallback: compute real-time from events table
              │     ├── _evaluate_condition(current_value, operator, threshold)
              │     └── Cooldown check: now - last_triggered < cooldown_seconds?
              │
              ├── should_trigger? → AlertService.trigger_alert()
              │     ├── INSERT INTO alert_history (...)
              │     ├── UPDATE alerts SET last_triggered, trigger_count += 1
              │     └── Return AlertHistory record
              │
              └── AlertNotificationService.send_alert_notification()
                    ├── notification_channels.websocket = True?
                    │     └── broadcaster.publish_alert(client_id, payload)
                    └── notification_channels.email = [...]?
                          └── EmailService.send_alert_email(addresses, ...)
```

The cooldown mechanism prevents alert spam: if an alert fired within `cooldown_seconds` of `last_triggered`, the `should_trigger` flag is overridden to `False` before any notification is sent.

---

## Real-Time WebSocket Layer

The WebSocket system is built on a publish-subscribe model using Redis as the message bus between the Celery processing pipeline and connected browser clients.

```
Celery Worker (EventProcessor)
  └── redis.publish("events:{client_id}", json_payload)
              │
              │  Redis Pub/Sub
              ▼
WebSocketBroadcaster (background asyncio.Task)
  ├── psubscribe("events:*", "metrics:*", "alerts:*", "rate_limit:*")
  ├── Loop: get_message(timeout=1.0)
  └── _handle_redis_message(message)
        ├── Parse channel prefix → determine message type
        └── ConnectionManager.broadcast_to_client(formatted_msg, client_id, channel)
              └── For each WebSocket in active_connections[client_id]:
                    ├── Check subscription: channel in subscriptions[connection_id]?
                    └── websocket.send_json(message)

WebSocket Client
  └── ws://host/api/v1/ws/live/{client_id}?token=<api_key>
        ├── Authentication: API key verified against DB on connect
        ├── Welcome message sent with default subscriptions
        └── Incoming messages handled by handle_client_message()
              ├── "ping" → "pong"
              ├── "subscribe" → update channel set
              ├── "unsubscribe" → remove from channel set
              └── "get_stats" → return ConnectionManager stats
```

**Connection management:** Each client (API key) can have up to 100 simultaneous WebSocket connections. Each connection has a UUID `connection_id` and a `subscriptions` set (default: `{events, metrics, alerts}`). Broadcast is filtered per-connection by this set, allowing clients to reduce noise by unsubscribing from channels they don't need.

**Resilience:** The broadcaster implements exponential backoff reconnection (1s → 2s → 4s → ... → 60s max) on `ConnectionError`. After 10 consecutive failures the loop exits to avoid infinite retry in a broken environment. On reconnect, `psubscribe` is re-issued so no channels are missed.

---

## Rate Limiting Design

The rate limiter uses a Redis sorted set (`ZSET`) as a sliding window counter, implemented as an atomic Lua script.

```lua
-- Simplified logic of the Lua script loaded at startup
local key = KEYS[1]          -- "rate_limit:{api_key_id}"
local now = tonumber(ARGV[1]) -- current Unix timestamp
local window = tonumber(ARGV[2]) -- window in seconds (60)
local limit = tonumber(ARGV[3])  -- per-key limit

ZREMRANGEBYSCORE key '-inf' (now - window)  -- evict old entries
local current = ZCARD key                    -- count in window
if current < limit then
    ZADD key now now                         -- add current request
    EXPIRE key (window * 2)                  -- auto-expire key
    return {1, current+1, limit}             -- allowed
else
    return {0, current, limit}               -- denied
end
```

The Lua script executes atomically on the Redis server — no race conditions are possible between the read (`ZCARD`) and write (`ZADD`). The script SHA is cached on startup via `SCRIPT LOAD` and executed with `EVALSHA`. On `NoScriptError` (e.g., Redis restart flushing scripts), the script is reloaded transparently.

The `check_rate_limit` FastAPI dependency wraps the rate limiter and attaches `rate_limit_info` to `request.state`, making limit metadata available to route handlers for response header injection without a second Redis call.

---

## Validation Layer

All request bodies and response payloads pass through Pydantic v2 schemas defined in `app/schemas/`.

### Schema Organization

| Module | Schemas | Purpose |
|---|---|---|
| `auth.py` | `UserCreate`, `UserLogin`, `UserResponse`, `TokenResponse`, `TokenRefresh`, `UserUpdate` | User registration, login, and profile management |
| `api_key.py` | `APIKeyCreate`, `APIKeyResponse`, `APIKeyWithSecret`, `APIKeyStats` | API key lifecycle; `APIKeyWithSecret` is the creation-only schema that includes the plain key |
| `ingest.py` | `EventCreate`, `EventBatchCreate`, `EventResponse`, `IngestionResponse` | Event ingestion and validation; `@field_validator` enforces 100KB JSON size cap on `properties` |
| `metrics.py` | `OverviewMetrics`, `TimeSeriesMetric`, `TopEventsMetric`, `ActiveUsersMetric`, `PaginatedResponse[T]`, `CursorPaginatedResponse[T]` | Dashboard response types; generic `PaginatedResponse` uses `TypeVar` for type-safe pagination |
| `alert.py` | `AlertExpression`, `NotificationChannels`, `AlertCreate`, `AlertUpdate`, `AlertResponse`, `AlertHistoryResponse`, `AlertTestResponse` | Alert CRUD; `Literal` types enforce valid operators and severity values at schema level |

### Key Validation Patterns

**Input safety:** `EventCreate.properties` runs a `@field_validator` that serializes to JSON and enforces a 100KB size cap, preventing oversized payloads from reaching the database.

**One-way secrets:** `APIKeyWithSecret` includes the `api_key` plain-text field and is returned **only** from the `POST /api-keys/` endpoint. The standard `APIKeyResponse` schema omits it entirely — there is no route that returns a plain key after creation.

**Partial updates:** `AlertUpdate` uses `Optional[...]` for every field. The router iterates `if field is not None` to apply only provided fields, giving true PATCH semantics without overwriting unchanged data.

**Strict enumerations:** `AlertExpression.operator` is typed as `Literal[">", "<", ">=", "<=", "==", "!="]` and `AlertCreate.severity` as `Literal["info", "warning", "error", "critical"]`. Invalid values are rejected at the Pydantic validation layer before reaching any service code.

**`from_attributes = True`:** All response schemas that may be constructed from SQLAlchemy ORM objects include `model_config` with `from_attributes = True` (Pydantic v2 equivalent of `orm_mode`), allowing direct instantiation from ORM instances without manual field mapping.

---

## Background Task Architecture

Celery tasks follow a strict sync/async separation to avoid event loop conflicts:

```
Celery Worker Process (sync context)
│
├── tasks_ingest.process_event_batch
│     ├── _dequeue_events()  ← sync redis.from_url() + RPOP pipeline
│     └── asyncio.run(_insert_events_async())
│           └── EventProcessor.process_events_batch()  ← async, isolated loop
│
├── tasks_aggregates.compute_minute_aggregates
│     └── asyncio.run(_compute_minute_aggregates_async())
│           └── MetricsService queries + save_aggregate()  ← async
│
├── tasks_aggregates.compute_hourly_aggregates
│     └── asyncio.run(_compute_hourly_aggregates_async())
│
├── tasks_aggregates.cleanup_old_aggregates
│     └── asyncio.run(_cleanup_old_aggregates_async())
│
└── tasks_alerts.evaluate_alerts
      └── asyncio.run(_evaluate_alerts_async())
            └── AlertService + AlertNotificationService  ← async
```

Each `asyncio.run()` call creates an isolated event loop for that task invocation. Database sessions are opened inside `AsyncSessionLocal()` context managers within the async functions — no session object is shared across tasks or between sync and async boundaries.

**Reliability features:**
- `task_acks_late = True` — the task is only acknowledged after completion, preventing loss on worker crash
- `task_reject_on_worker_lost = True` — task is re-queued if the worker process dies mid-execution
- `worker_prefetch_multiplier = 1` — one task at a time per worker, preventing memory accumulation under async-heavy workloads
- `_requeue_events()` — on `process_event_batch` failure, events are re-pushed to the queue head with `LPUSH` (preserving order) before the task retries

---

## Dependency Injection Pattern

FastAPI's `Depends()` system is used consistently for all cross-cutting concerns:

```python
# Dependency chain for a rate-limited, authenticated route:

@router.post("/events")
async def ingest_event(
    event: EventCreate,                        # Pydantic body validation
    request: Request,                          # Raw request (for state injection)
    api_key: APIKey = Depends(check_rate_limit), # Rate limit → returns APIKey
    db: AsyncSession = Depends(get_db),        # Session with auto-commit/rollback
    redis_client: Redis = Depends(get_event_redis), # Lazy singleton Redis client
):
```

`check_rate_limit` itself depends on `get_api_key`, creating a transparent chain:

```
check_rate_limit
  └── get_api_key
        └── get_db
```

This ensures that the API key is validated, the rate limit is checked, and the database session is managed — all before the route handler body executes. Route handlers remain focused on business logic.
