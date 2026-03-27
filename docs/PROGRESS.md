# EventPulse — Project Progress

> **Status:** ✅ Backend Complete · ✅ Frontend Complete · ✅ Deployed · ✅ JS SDK Live · ✅ npm Package Published · ✅ Python SDK Published · ✅ Documentation Complete

---

## Table of Contents

* [Project Milestones](https://claude.ai/chat/ae3fc84a-960c-4de3-b0a1-d188d272ee27#project-milestones)
* [Database Migrations](https://claude.ai/chat/ae3fc84a-960c-4de3-b0a1-d188d272ee27#database-migrations)
* [API Endpoint Inventory](https://claude.ai/chat/ae3fc84a-960c-4de3-b0a1-d188d272ee27#api-endpoint-inventory)
* [Security &amp; Middleware](https://claude.ai/chat/ae3fc84a-960c-4de3-b0a1-d188d272ee27#security--middleware)
* [Frontend Architecture](https://claude.ai/chat/ae3fc84a-960c-4de3-b0a1-d188d272ee27#frontend-architecture)
* [SDK Architecture](https://claude.ai/chat/ae3fc84a-960c-4de3-b0a1-d188d272ee27#sdk-architecture)
* [Completed Features](https://claude.ai/chat/ae3fc84a-960c-4de3-b0a1-d188d272ee27#completed-features)
* [Pending](https://claude.ai/chat/ae3fc84a-960c-4de3-b0a1-d188d272ee27#pending)

---

## Project Milestones

### Phase 1 — Project Initialization (Backend)

* [X] Repository scaffolded with `backend/` layout, `.gitignore`, and `.dockerignore`
* [X] Virtual environment configured (`venv`) with `requirements.txt` pinned
* [X] `.env.example` committed with all required variables documented
* [X] `python-dotenv` integrated via `pydantic-settings` (`BaseSettings`)
* [X] FastAPI application instance created in `app/main.py`
* [X] Uvicorn configured as the ASGI development server on port `8002`
* [X] Gunicorn configured as the production ASGI server (4 `UvicornWorker` processes)

### Phase 2 — Database & ORM Setup

* [X] Async SQLAlchemy engine created with connection pooling (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`)
* [X] Single `Base` declarative class established in `app/models/base.py`
* [X] `TimestampMixin` created and applied to all models (`created_at`, `updated_at`)
* [X] `AsyncSessionLocal` session factory configured with `expire_on_commit=False`
* [X] `get_db` FastAPI dependency implemented with commit/rollback/close lifecycle
* [X] Alembic initialized with full async support (`asyncpg` driver in `env.py`)
* [X] `alembic.ini` connected; `DATABASE_URL` sourced from `settings` at runtime
* [X] Sync URL auto-derived from async URL for Alembic compatibility

### Phase 3 — Data Models

* [X] `User` model implemented (`users` table)
* [X] `APIKey` model implemented (`api_keys` table) with FK to `users`
* [X] `Event` model implemented (`events` table) with JSONB properties and composite indexes
* [X] `Aggregate` model implemented (`aggregates` table) with UPSERT constraint
* [X] `Alert` model implemented (`alerts` table)
* [X] `AlertHistory` model implemented (`alert_history` table)
* [X] All models registered in `app/models/__init__.py` and `alembic/env.py`

### Phase 4 — Authentication System

* [X] Password hashing via `bcrypt` (`passlib.CryptContext`)
* [X] JWT access token creation and signing (`python-jose`, `HS256`)
* [X] JWT refresh token creation with separate `type: refresh` claim
* [X] `decode_token` function with `JWTError` handling
* [X] `get_current_user` FastAPI dependency (Bearer token → DB user lookup)
* [X] `get_current_active_admin` dependency (role-based guard)
* [X] API key generation (`secrets.token_hex(32)`, prefixed `ep_live_*`)
* [X] API key hashing (`SHA-256`) and verification

### Phase 5 — API Routers

* [X] `auth` router: registration, login, token refresh, profile management
* [X] `api_keys` router: CRUD + revocation + stats
* [X] `ingest` router: single event and batch event ingestion (Redis queue)
* [X] `metrics` router: overview, top events, active users, time series (paginated)
* [X] `alerts` router: full CRUD, test, enable/disable, history
* [X] `admin` router: manual task triggers, task status polling
* [X] `websockets` router: live feed WebSocket endpoint + connection stats
* [X] `health` router: liveness, readiness, detailed, and protected probes
* [X] All routers registered in `app/main.py` under `/api/v1/` prefix

### Phase 6 — Background Tasks (APScheduler)

> **Note:** Celery (worker + beat) was replaced with APScheduler running inside the FastAPI process to reduce free-tier service count from 5 → 3 (api + postgres + redis).

* [X] APScheduler integrated into FastAPI (`AsyncIOScheduler`)
* [X] Event batch processor: dequeues events from Redis → bulk inserts into PostgreSQL every 5 seconds
* [X] Aggregate computation: per-minute and per-hour metrics computed on schedule
* [X] Cleanup task: removes aggregates older than 30 days (runs daily)
* [X] Alert evaluation: checks all enabled alerts every 60 seconds
* [X] Task retry logic with re-queue on failure (`_requeue_events`)
* [X] Scheduler starts on FastAPI `startup` event and stops on `shutdown`

### Phase 7 — Real-Time WebSocket Layer

* [X] `ConnectionManager` implemented with per-client connection limits (max 100)
* [X] Channel-based subscription model (`events`, `metrics`, `alerts`)
* [X] `WebSocketBroadcaster` subscribing to Redis Pub/Sub (`events:*`, `metrics:*`, `alerts:*`, `rate_limit:*`)
* [X] Broadcaster started as a background `asyncio.Task` on application startup
* [X] Exponential backoff reconnect logic for Redis connection failures
* [X] Client message handlers: `ping/pong`, `subscribe`, `unsubscribe`, `get_stats`

### Phase 8 — Notifications & Alerting

* [X] `AlertService`: expression evaluation, cooldown enforcement, history recording
* [X] `AlertNotificationService`: multi-channel dispatch (WebSocket + optional Email)
* [X] `EmailService`: SMTP client with HTML template generation and TLS support
* [X] Alert severity levels: `info`, `warning`, `error`, `critical`
* [X] Configurable cooldown periods per alert (0–3600 seconds)

### Phase 9 — Rate Limiting

* [X] Redis-based rate limiter using Lua script for atomic sliding-window enforcement
* [X] Lua script loaded into Redis on startup with SHA caching (`EVALSHA`)
* [X] `check_rate_limit` FastAPI dependency returning `X-RateLimit-*` headers
* [X] HTTP 429 response with `Retry-After` header on limit exceeded
* [X] Rate-limit exceeded event published to WebSocket clients via Redis Pub/Sub
* [X] Fail-open behavior on Redis errors (prevents service disruption)

### Phase 10 — Logging & Observability

* [X] Structured `JSONFormatter` for production (compatible with ELK/CloudWatch)
* [X] Human-readable formatter for development
* [X] Per-request HTTP middleware logging method, path, status, and duration
* [X] `X-Process-Time` response header injected by middleware
* [X] Separate log files: daily app log and daily error log
* [X] Sentry integration (`sentry-sdk[fastapi]`) with conditional initialization
* [X] Global exception handler returning structured JSON error responses

### Phase 11 — Containerization & Deployment

* [X] `Dockerfile` (development): single-stage, runs `alembic upgrade head` before Uvicorn
* [X] `Dockerfile.prod` (production): multi-stage build, non-root `appuser`, Gunicorn entrypoint
* [X] `docker-compose.yml`: services (`postgres`, `redis`, `api`) with health checks
* [X] PowerShell management scripts: `start.ps1`, `stop.ps1`, `logs.ps1`
* [X] Render deployment instructions documented in `README.md`

### Phase 12 — Testing Infrastructure

* [X] `pytest.ini` configured with `asyncio_mode = auto` and test path discovery
* [X] `conftest.py` with isolated test database engine and session fixtures
* [X] `get_db` dependency override pattern for test isolation
* [X] `AsyncClient` (httpx) fixture for API integration tests
* [X] Stress test script (`tests/stress_test.py`) with concurrent thread pool execution
* [X] System verification script (`tests/verify_system.ps1`)

---

### Phase 13 — Frontend Scaffolding & Configuration

* [X] React 18 + Vite 5 project initialized in `frontend/` directory
* [X] Tailwind CSS 3 integrated with custom primary color palette and animation extensions
* [X] ESLint configured (React, React Hooks, React Refresh plugins)
* [X] `vite.config.js` configured with dev server on port `3000` and proxy for `/api`
* [X] `frontend/.env.example` pattern established; `VITE_API_URL` and `VITE_WS_URL` sourced from environment
* [X] Global CSS set up with Tailwind directives, custom scrollbar styles, and animations

### Phase 14 — App Configuration & Routing

* [X] Centralized `src/config.js` with all runtime constants
* [X] React Router v6 route tree: public (`/login`, `/register`) + protected routes
* [X] `ProtectedRoute` component with JWT guard and network-error resilience
* [X] Provider nesting: `AuthProvider` → `NotificationProvider` → `APIKeyProvider` → `WebSocketProvider`

### Phase 15 — State Management (React Context)

* [X] `AuthContext`: JWT login/logout/register, user fetch, token management
* [X] `APIKeyContext`: selected API key with localStorage persistence and cross-key isolation
* [X] `NotificationContext`: toast queue with auto-dismiss
* [X] `WebSocketContext`: generational connection management, rate limit handling, reconnect logic

### Phase 16 — Custom Hooks

* [X] `useAuth`, `useAPIKey`, `useWebSocket`, `useNotification` — context consumers
* [X] `useAPI` — generic async executor with loading/error state
* [X] `useLocalStorage` — React state synced to localStorage with JSON serialization

### Phase 17 — API Service Layer

* [X] `APIClient` singleton with JWT + API key auth headers
* [X] Full method coverage: auth, api-keys, metrics, alerts, ingestion, health

### Phase 18 — Utility Modules

* [X] `formatters.js`: date, number, string, clipboard helpers
* [X] `validators.js`: email, password, form, API key validation

### Phase 19 — Common UI Components

* [X] Badge, Button, Card, EmptyState, Input, Modal, Select, Spinner, Toast/ToastContainer

### Phase 20 — Layout Components

* [X] Layout, Navbar, Sidebar, ProtectedRoute — responsive mobile-first design

### Phase 21 — Dashboard Components

* [X] MetricCard, TimeSeriesChart (Recharts LineChart), TopEventsChart (Recharts BarChart)

### Phase 22 — Pages

* [X] Login, Register, Dashboard, API Keys, Live Feed, Events Browser, Alerts

### Phase 23 — Frontend Deployment

* [X] Frontend deployed on **Vercel**
* [X] Backend deployed on **Render** (single free web service)
* [X] Database on **Supabase** (PostgreSQL, free tier)
* [X] Redis on **Upstash** (serverless Redis, free tier)
* [X] All services communicating with production environment variables
* [X] CORS configured, WebSockets active end-to-end

---

### Phase 24 — JS Drop-in SDK

* [X] `eventpulse.js` written as a self-contained IIFE (~3KB)
* [X] Auto-initializes from `<script data-api-key="ep_live_...">` tag
* [X] Auto-tracks `page_view` on load and `click` on interactive elements
* [X] SPA support — patches `history.pushState` and `replaceState` for React Router / Vue Router / Next.js
* [X] Session ID generation and persistence via `sessionStorage`
* [X] Base properties on every event: `url`, `path`, `referrer`, `title`, `session_id`, `user_agent`, `screen`, `language`
* [X] Event buffering with configurable flush interval (default 5s) and max buffer size (50)
* [X] Retry logic with max 3 retries on failed batch flush
* [X] `sendBeacon` used on `beforeunload` / `visibilitychange` for reliable page-leave tracking
* [X] Public API: `EventPulse.track(name, props)`, `EventPulse.identify(userId)`, `EventPulse.flush()`
* [X] Hosted on Render at `https://eventpulse-analytics-backend.onrender.com/static/eventpulse.js`
* [X] Tested on WorkScribe (live site) — events confirmed in Live Feed dashboard

### Phase 25 — npm Package (`eventpulse-analytics`)

* [X] Package scaffolded at `eventpulse-analytics/` in project root
* [X] `src/core.ts` — `EventPulseClient` class with `track()`, `identify()`, `page()`, `flush()`, `destroy()`
* [X] `src/react/provider.tsx` — `<EventPulseProvider>` wraps app, initializes client once on mount
* [X] `src/react/hooks.ts` — `useEventPulse()` hook (track, identify, page) and `usePageView()` auto-tracker
* [X] `src/vue/plugin.ts` — `EventPulsePlugin` for `app.use(EventPulsePlugin, { apiKey, endpoint })`; exposes client via `$eventpulse` and `inject('eventpulse')`
* [X] `src/index.ts` — unified exports for core, React, and Vue
* [X] Built with Vite library mode — outputs ESM (`eventpulse-analytics.es.js`) + UMD (`eventpulse-analytics.umd.js`)
* [X] TypeScript declarations generated (`dist/*.d.ts`) via `vite-plugin-dts`
* [X] React and Vue declared as peer dependencies (not bundled)
* [X] Tested locally via `npm link` against a Vite React test app
* [X] Events confirmed arriving in EventPulse Live Feed from test app
* [X] `README.md` written with full usage docs for React, Vue, plain JS, and drop-in script
* [X] **Published to npm** — `npm install eventpulse-analytics` works globally
* [X] npm page live at `https://www.npmjs.com/package/eventpulse-analytics`
* [X] `eventpulse-analytics/` committed to GitHub repository
* [X] `eventpulse-test-app/` deleted / gitignored (was for local testing only)

### Phase 26 — Python SDK (`eventpulse-python`)

* [X] Package scaffolded at `eventpulse-python/` in project root
* [X] `eventpulse/client.py` — `EventPulseClient` class with `track()`, `identify()`, `page()`, `flush()`, `shutdown()`
* [X] Background thread flusher — non-blocking, flushes every 5s (mirrors JS `setInterval`)
* [X] Exponential back-off retry logic (up to 3 attempts) with re-queue on total failure
* [X] `eventpulse/django.py` — `EventPulseMiddleware` for Django; auto-tracks every request as `page_view`; auto-identifies authenticated users
* [X] `eventpulse/fastapi.py` — `EventPulseMiddleware` for FastAPI/Starlette; auto-tracks every request as `page_view`
* [X] Zero runtime dependencies — stdlib only (`urllib`, `threading`, `json`)
* [X] Context manager support (`with EventPulseClient(...) as ep:`)
* [X] `pyproject.toml` with optional extras: `django`, `fastapi`, `dev`
* [X] 11 unit tests — all passing (`pytest tests/ -v`)
* [X] `README.md` written with full usage docs for plain Python, Django, and FastAPI
* [X] **Published to PyPI** — `pip install eventpulse-python` works globally
* [X] PyPI page live at `https://pypi.org/project/eventpulse-python/1.0.0/`
* [X] `eventpulse-python/` committed to GitHub repository

### Phase 27 — Documentation

* [X] `docs/` directory created and committed to GitHub
* [X] `docs/README.md` — documentation index linking all quick start guides
* [X] `docs/quick-start-html.md` — plain HTML drop-in script guide
* [X] `docs/quick-start-react.md` — React + TypeScript integration guide
* [X] `docs/quick-start-vue.md` — Vue 3 plugin integration guide
* [X] `docs/quick-start-python.md` — plain Python client guide
* [X] `docs/quick-start-django.md` — Django middleware guide
* [X] `docs/quick-start-fastapi.md` — FastAPI middleware guide
* [X] All 7 files committed and pushed (`14debfb`) — `git commit -m "docs: add quick start guides for all SDKs"`

---

## SDK Architecture

```
eventpulse-analytics/          # npm package (JS/TS)
├── src/
│   ├── core.ts                # EventPulseClient — batching, flush, retry, identify
│   ├── react/
│   │   ├── provider.tsx       # <EventPulseProvider apiKey endpoint>
│   │   └── hooks.ts           # useEventPulse(), usePageView()
│   ├── vue/
│   │   └── plugin.ts          # app.use(EventPulsePlugin, { apiKey, endpoint })
│   └── index.ts               # All exports
├── dist/                      # Built output (ESM + UMD + .d.ts)
├── README.md
├── package.json
├── vite.config.ts
└── tsconfig.json

eventpulse-python/             # PyPI package (Python)
├── eventpulse/
│   ├── __init__.py            # EventPulseClient export
│   ├── client.py              # Core — background thread, batching, retry
│   ├── django.py              # Django middleware
│   └── fastapi.py             # FastAPI/Starlette middleware
├── tests/
│   └── test_client.py         # 11 unit tests
├── README.md
└── pyproject.toml

backend/static/eventpulse.js   # Drop-in JS snippet (no install needed)

docs/                          # Quick start guides
├── README.md                  # Docs index
├── quick-start-html.md
├── quick-start-react.md
├── quick-start-vue.md
├── quick-start-python.md
├── quick-start-django.md
└── quick-start-fastapi.md
```

### Usage — React

```jsx
// main.jsx
import { EventPulseProvider } from 'eventpulse-analytics'

<EventPulseProvider apiKey="ep_live_xxx" endpoint="https://your-backend.onrender.com">
  <App />
</EventPulseProvider>

// Any component
import { useEventPulse } from 'eventpulse-analytics'
const { track, identify } = useEventPulse()
track('button_click', { button: 'signup' })
```

### Usage — Vue

```js
import { EventPulsePlugin } from 'eventpulse-analytics'
app.use(EventPulsePlugin, { apiKey: 'ep_live_xxx', endpoint: 'https://...' })
// In components: this.$eventpulse.track('event_name')
```

### Usage — Python (Django)

```python
# settings.py
MIDDLEWARE = ['eventpulse.django.EventPulseMiddleware', ...]
EVENTPULSE_API_KEY = 'ep_live_xxx'
```

### Usage — Python (FastAPI)

```python
from eventpulse.fastapi import EventPulseMiddleware
app.add_middleware(EventPulseMiddleware, api_key='ep_live_xxx')
```

### Usage — Plain HTML

```html
<script src="https://eventpulse-analytics-backend.onrender.com/static/eventpulse.js"
        data-api-key="ep_live_xxx"></script>
```

---

## Database Migrations

| Revision         | Description                   | Tables / Changes                                                        |
| ---------------- | ----------------------------- | ----------------------------------------------------------------------- |
| `405c286eaca1` | Initial full schema           | Creates `users`table                                                  |
| `ec58312128bc` | Add API keys table            | Creates `api_keys`table; FK →`users.id`                            |
| `f22717a1db4d` | Add events table with indexes | Creates `events`table (BigSerial PK, JSONB `properties`); 7 indexes |
| `50a37bce1d12` | Add aggregates table          | Creates `aggregates`table with UNIQUE constraint                      |
| `bc45ac0e7528` | Add alerts and alert history  | Creates `alerts`and `alert_history`tables                           |
| `44b69d9393f0` | Performance index             | Adds `idx_aggregates_client_metric_time`composite index               |

---

## API Endpoint Inventory

All endpoints are prefixed with `/api/v1/`.

### Authentication — `/auth`

| Method    | Path               | Auth          | Description                 |
| --------- | ------------------ | ------------- | --------------------------- |
| `POST`  | `/auth/register` | None          | Register new user           |
| `POST`  | `/auth/login`    | None          | Login, receive JWT tokens   |
| `POST`  | `/auth/refresh`  | Refresh Token | Get new access token        |
| `GET`   | `/auth/me`       | JWT           | Get current user profile    |
| `PATCH` | `/auth/me`       | JWT           | Update current user profile |

### API Keys — `/api-keys`

| Method     | Path                          | Auth | Description          |
| ---------- | ----------------------------- | ---- | -------------------- |
| `POST`   | `/api-keys/`                | JWT  | Create new API key   |
| `GET`    | `/api-keys/`                | JWT  | List all API keys    |
| `GET`    | `/api-keys/{key_id}`        | JWT  | Get specific API key |
| `PATCH`  | `/api-keys/{key_id}/revoke` | JWT  | Revoke API key       |
| `DELETE` | `/api-keys/{key_id}`        | JWT  | Delete API key       |

### Event Ingestion — `/ingest`

| Method   | Path                     | Auth    | Description               |
| -------- | ------------------------ | ------- | ------------------------- |
| `POST` | `/ingest/events`       | API Key | Ingest single event       |
| `POST` | `/ingest/events/batch` | API Key | Ingest up to 1,000 events |
| `GET`  | `/ingest/status`       | API Key | Pipeline and queue status |

### Metrics — `/metrics`

| Method  | Path                                   | Auth    | Description              |
| ------- | -------------------------------------- | ------- | ------------------------ |
| `GET` | `/metrics/overview`                  | API Key | Dashboard overview       |
| `GET` | `/metrics/top-events`                | API Key | Top N events by count    |
| `GET` | `/metrics/active-users`              | API Key | Unique active user count |
| `GET` | `/metrics/time-series/{metric_name}` | API Key | Time series data         |
| `GET` | `/metrics/events`                    | API Key | Paginated raw events     |

### Alerts — `/alerts`

| Method     | Path                           | Auth    | Description        |
| ---------- | ------------------------------ | ------- | ------------------ |
| `POST`   | `/alerts/`                   | API Key | Create alert       |
| `GET`    | `/alerts/`                   | API Key | List alerts        |
| `PATCH`  | `/alerts/{alert_id}`         | API Key | Update alert       |
| `DELETE` | `/alerts/{alert_id}`         | API Key | Delete alert       |
| `POST`   | `/alerts/{alert_id}/test`    | API Key | Dry-run evaluation |
| `GET`    | `/alerts/{alert_id}/history` | API Key | Trigger history    |
| `POST`   | `/alerts/{alert_id}/enable`  | API Key | Enable alert       |
| `POST`   | `/alerts/{alert_id}/disable` | API Key | Disable alert      |

### WebSockets — `/ws`

| Method  | Path                     | Auth    | Description             |
| ------- | ------------------------ | ------- | ----------------------- |
| `WS`  | `/ws/live/{client_id}` | API Key | Real-time live feed     |
| `GET` | `/ws/connections`      | None    | Active connection stats |

### Health — `/health`

| Method  | Path                 | Auth | Description        |
| ------- | -------------------- | ---- | ------------------ |
| `GET` | `/health/`         | None | Basic health check |
| `GET` | `/health/detailed` | None | Detailed health    |
| `GET` | `/health/live`     | None | Liveness probe     |
| `GET` | `/health/ready`    | None | Readiness probe    |

---

## Security & Middleware

| Layer      | Mechanism                 | Applies To                                   |
| ---------- | ------------------------- | -------------------------------------------- |
| JWT Bearer | `python-jose`/`HS256` | `/auth`,`/api-keys`,`/admin`           |
| API Key    | SHA-256 hash lookup       | `/ingest`,`/metrics`,`/alerts`,`/ws` |

* API keys stored as SHA-256 hashes; plain key shown once at creation
* Passwords hashed with bcrypt (72 byte limit enforced)
* Redis sliding-window rate limiter via atomic Lua script
* CORS: `allow_origins=["*"]` (to be tightened in production)
* Structured JSON logging in production, human-readable in development

---

## Frontend Architecture

| Library          | Version | Role                |
| ---------------- | ------- | ------------------- |
| React            | 18.3.1  | UI framework        |
| React Router DOM | 6.30.3  | Client-side routing |
| Vite             | 5.4.x   | Build tool          |
| Tailwind CSS     | 3.4.x   | Styling             |
| Recharts         | 2.15.x  | Charts              |
| Lucide React     | 0.294.0 | Icons               |
| date-fns         | 2.30.0  | Date formatting     |

---

## Completed Features

### Backend

* [X] User auth (JWT register/login/refresh)
* [X] API key management (generate, hash, revoke, delete)
* [X] High-throughput batch event ingestion via Redis queue
* [X] APScheduler background tasks (ingest, aggregate, alerts, cleanup)
* [X] Real-time WebSocket streaming via Redis Pub/Sub
* [X] Dashboard metrics API (overview, time series, top events, active users)
* [X] Alert engine with expression evaluation, cooldown, history
* [X] Atomic Redis rate limiting with WebSocket notification
* [X] Structured logging + Sentry integration
* [X] Health probes (liveness, readiness)
* [X] Deployed on Render + Supabase + Upstash

### Frontend

* [X] Login / Register with real-time password validation
* [X] Dashboard with metric cards, charts, auto-refresh
* [X] API Key management UI (create, select, revoke, delete)
* [X] Real-time Live Feed (WebSocket, pause/resume, CSV export)
* [X] Events Browser (paginated, filtered, expandable rows)
* [X] Alerts UI (full CRUD, dry-run test, history modal)
* [X] Generational WebSocket client (stale-message safe)
* [X] Reusable component library (Badge, Button, Card, Modal, etc.)
* [X] Deployed on Vercel

### SDKs

* [X] JS drop-in snippet (`eventpulse.js`) — hosted on Render, tested on live site
* [X] npm package (`eventpulse-analytics` v1.0.0) — React + Vue + TypeScript, published to npm
* [X] Python SDK (`eventpulse-python` v1.0.0) — Django + FastAPI + plain Python, published to PyPI

### Documentation

* [X] `docs/` directory with 7 quick start guides committed to GitHub
* [X] Covers all integration paths: plain HTML, React, Vue, Python, Django, FastAPI

---

## Pending

> 🎉 All planned features and documentation are complete. The items below are optional future improvements.

| Item               | Description                                                      | Priority |
| ------------------ | ---------------------------------------------------------------- | -------- |
| 🔒 CORS hardening  | Replace `allow_origins=["*"]`with explicit origin allowlist    | Medium   |
| 📊 Funnel analysis | Multi-step event funnel visualization on the dashboard           | Low      |
| 🔔 Webhook alerts  | Send alert notifications to a user-configured webhook URL        | Low      |
| 📦 SDK v1.1.0      | Ship `usePageView()`auto-tracking as default in React provider | Low      |
| 🧪 E2E tests       | Playwright tests covering login → ingest → dashboard flow      | Low      |

---

## How It Works — The User Flow

**1. They sign up on your EventPulse platform**
Go to your Vercel URL → Register → Login

**2. They create an API key**
Go to API Keys page → Create New Key → copy `ep_live_xxx`

**3. They install your package in their project**

```bash
# JavaScript / TypeScript
npm install eventpulse-analytics

# Python
pip install eventpulse-python
```

**4. They add your provider / middleware — one time, done**

```jsx
// React
import { EventPulseProvider } from 'eventpulse-analytics'

<EventPulseProvider apiKey="ep_live_THEIR_KEY" endpoint="https://eventpulse-analytics-backend.onrender.com">
  <App />
</EventPulseProvider>
```

```python
# Django — settings.py
MIDDLEWARE = ['eventpulse.django.EventPulseMiddleware', ...]
EVENTPULSE_API_KEY = 'ep_live_THEIR_KEY'
```

**5. They log into EventPulse dashboard and see their app's data**

---

**The analogy:**
It's exactly like Google Analytics — you get a tracking ID, paste one snippet, and data starts flowing. Your npm and PyPI packages are that snippet, for React/Vue and Python apps respectively.
