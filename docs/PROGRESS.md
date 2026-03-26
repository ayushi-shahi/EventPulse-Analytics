# EventPulse — Project Progress

> **Status:** ✅ Backend Complete · ✅ Frontend Complete — Full-stack platform delivered, tested, and deployed.

---

## Table of Contents

- [Project Milestones](#project-milestones)
- [Database Migrations](#database-migrations)
- [API Endpoint Inventory](#api-endpoint-inventory)
- [Security & Middleware](#security--middleware)
- [Frontend Architecture](#frontend-architecture)
- [Completed Features](#completed-features)

---

## Project Milestones

### Phase 1 — Project Initialization (Backend)
- [x] Repository scaffolded with `backend/` layout, `.gitignore`, and `.dockerignore`
- [x] Virtual environment configured (`venv`) with `requirements.txt` pinned
- [x] `.env.example` committed with all required variables documented
- [x] `python-dotenv` integrated via `pydantic-settings` (`BaseSettings`)
- [x] FastAPI application instance created in `app/main.py`
- [x] Uvicorn configured as the ASGI development server on port `8002`
- [x] Gunicorn configured as the production ASGI server (4 `UvicornWorker` processes)

### Phase 2 — Database & ORM Setup
- [x] Async SQLAlchemy engine created with connection pooling (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`)
- [x] Single `Base` declarative class established in `app/models/base.py`
- [x] `TimestampMixin` created and applied to all models (`created_at`, `updated_at`)
- [x] `AsyncSessionLocal` session factory configured with `expire_on_commit=False`
- [x] `get_db` FastAPI dependency implemented with commit/rollback/close lifecycle
- [x] Alembic initialized with full async support (`asyncpg` driver in `env.py`)
- [x] `alembic.ini` connected; `DATABASE_URL` sourced from `settings` at runtime
- [x] Sync URL auto-derived from async URL for Alembic compatibility

### Phase 3 — Data Models
- [x] `User` model implemented (`users` table)
- [x] `APIKey` model implemented (`api_keys` table) with FK to `users`
- [x] `Event` model implemented (`events` table) with JSONB properties and composite indexes
- [x] `Aggregate` model implemented (`aggregates` table) with UPSERT constraint
- [x] `Alert` model implemented (`alerts` table)
- [x] `AlertHistory` model implemented (`alert_history` table)
- [x] All models registered in `app/models/__init__.py` and `alembic/env.py`

### Phase 4 — Authentication System
- [x] Password hashing via `bcrypt` (`passlib.CryptContext`)
- [x] JWT access token creation and signing (`python-jose`, `HS256`)
- [x] JWT refresh token creation with separate `type: refresh` claim
- [x] `decode_token` function with `JWTError` handling
- [x] `get_current_user` FastAPI dependency (Bearer token → DB user lookup)
- [x] `get_current_active_admin` dependency (role-based guard)
- [x] API key generation (`secrets.token_hex(32)`, prefixed `ep_live_*`)
- [x] API key hashing (`SHA-256`) and verification

### Phase 5 — API Routers
- [x] `auth` router: registration, login, token refresh, profile management
- [x] `api_keys` router: CRUD + revocation + stats
- [x] `ingest` router: single event and batch event ingestion (Redis queue)
- [x] `metrics` router: overview, top events, active users, time series (paginated)
- [x] `alerts` router: full CRUD, test, enable/disable, history
- [x] `admin` router: manual Celery task triggers, task status polling
- [x] `websockets` router: live feed WebSocket endpoint + connection stats
- [x] `health` router: liveness, readiness, detailed, and protected probes
- [x] All routers registered in `app/main.py` under `/api/v1/` prefix

### Phase 6 — Background Tasks (Celery)
- [x] Celery application factory in `app/tasks/celery_app.py` (Redis broker + backend)
- [x] `tasks_ingest.py`: dequeue events from Redis → bulk insert into PostgreSQL
- [x] `tasks_aggregates.py`: compute per-minute and per-hour metrics for all clients
- [x] `tasks_aggregates.py`: cleanup task to delete aggregates older than 30 days
- [x] `tasks_alerts.py`: evaluate all enabled alerts every 60 seconds
- [x] Celery Beat schedule configured (5s ingest, 60s metrics, 3600s hourly, 86400s cleanup)
- [x] `worker.py` and `beat.py` startup scripts created
- [x] Task retry logic with re-queue on failure (`_requeue_events`)

### Phase 7 — Real-Time WebSocket Layer
- [x] `ConnectionManager` implemented with per-client connection limits (max 100)
- [x] Channel-based subscription model (`events`, `metrics`, `alerts`)
- [x] `WebSocketBroadcaster` subscribing to Redis Pub/Sub (`events:*`, `metrics:*`, `alerts:*`, `rate_limit:*`)
- [x] Broadcaster started as a background `asyncio.Task` on application startup
- [x] Exponential backoff reconnect logic for Redis connection failures
- [x] Client message handlers: `ping/pong`, `subscribe`, `unsubscribe`, `get_stats`

### Phase 8 — Notifications & Alerting
- [x] `AlertService`: expression evaluation, cooldown enforcement, history recording
- [x] `AlertNotificationService`: multi-channel dispatch (WebSocket + optional Email)
- [x] `EmailService`: SMTP client with HTML template generation and TLS support
- [x] Alert severity levels: `info`, `warning`, `error`, `critical`
- [x] Configurable cooldown periods per alert (0–3600 seconds)

### Phase 9 — Rate Limiting
- [x] Redis-based rate limiter using Lua script for atomic sliding-window enforcement
- [x] Lua script loaded into Redis on startup with SHA caching (`EVALSHA`)
- [x] `check_rate_limit` FastAPI dependency returning `X-RateLimit-*` headers
- [x] HTTP 429 response with `Retry-After` header on limit exceeded
- [x] Rate-limit exceeded event published to WebSocket clients via Redis Pub/Sub
- [x] Fail-open behavior on Redis errors (prevents service disruption)

### Phase 10 — Logging & Observability
- [x] Structured `JSONFormatter` for production (compatible with ELK/CloudWatch)
- [x] Human-readable formatter for development
- [x] Per-request HTTP middleware logging method, path, status, and duration
- [x] `X-Process-Time` response header injected by middleware
- [x] Separate log files: daily app log and daily error log
- [x] Sentry integration (`sentry-sdk[fastapi]`) with conditional initialization
- [x] Global exception handler returning structured JSON error responses

### Phase 11 — Containerization & Deployment
- [x] `Dockerfile` (development): single-stage, runs `alembic upgrade head` before Uvicorn
- [x] `Dockerfile.prod` (production): multi-stage build, non-root `appuser`, Gunicorn entrypoint
- [x] `docker-compose.yml`: 5 services (`postgres`, `redis`, `api`, `worker`, `beat`) with health checks
- [x] `docker-compose.prod.yml`: production compose with resource limits and `restart: always`
- [x] All health checks use lightweight probes (Redis TCP socket ping, HTTP liveness endpoint)
- [x] PowerShell management scripts: `start.ps1`, `stop.ps1`, `logs.ps1`
- [x] Render deployment instructions documented in `README.md`

### Phase 12 — Testing Infrastructure
- [x] `pytest.ini` configured with `asyncio_mode = auto` and test path discovery
- [x] `conftest.py` with isolated test database engine and session fixtures
- [x] `get_db` dependency override pattern for test isolation
- [x] `AsyncClient` (httpx) fixture for API integration tests
- [x] Stress test script (`tests/stress_test.py`) with concurrent thread pool execution
- [x] System verification script (`tests/verify_system.ps1`)

---

### Phase 13 — Frontend Scaffolding & Configuration
- [x] React 18 + Vite 5 project initialized in `frontend/` directory (`eventpulse-frontend`)
- [x] Tailwind CSS 3 integrated with `postcss.config.js` and `tailwind.config.js` (custom primary color palette and animation extensions)
- [x] ESLint configured via both `frontend/.eslintrc.cjs` and flat `eslint.config.js` (React, React Hooks, React Refresh plugins)
- [x] `vite.config.js` configured with dev server on port `3000` and proxy for `/api` → `http://localhost:8002`
- [x] `render.yaml` created for static frontend deployment on Render (build command, publish dir, env vars)
- [x] `frontend/.env.example` pattern established; `VITE_API_URL` and `VITE_WS_URL` sourced from environment at build time via `import.meta.env`
- [x] `frontend/index.html` entry point configured with app title `EventPulse Analytics`
- [x] `frontend/src/main.jsx` bootstraps React 18 with `createRoot` and `StrictMode`
- [x] Global CSS (`src/index.css`) set up with Tailwind directives, custom scrollbar styles, and slide-in animation keyframe
- [x] Extended animation library in `src/styles/animations.css`: `fade-in`, `slide-down`, `shake`, `pulse-slow`, `glow`, `spin-slow`, `border-pulse`, `bounce-subtle`, `gradient-text`

### Phase 14 — App Configuration & Routing
- [x] Centralized `src/config.js` exports all runtime constants: `API_CONFIG` (base URL, WebSocket URL, timeout), `APP_CONFIG` (refresh interval, page sizes, toast duration), `CHART_COLORS`, `SEVERITY_COLORS`, `EVENT_COLORS` palette (8 colours for charts), `PERIOD_OPTIONS`, `METRIC_OPTIONS`, `OPERATOR_OPTIONS`, `SEVERITY_OPTIONS`
- [x] `src/App.jsx` defines the full client-side route tree using React Router v6 (`BrowserRouter`, `Routes`, `Route`, `Navigate`)
- [x] Route structure: public routes (`/login`, `/register`) + protected layout routes (`/dashboard`, `/live-feed`, `/events`, `/metrics`, `/alerts`, `/api-keys`, `/settings`)
- [x] `ProtectedRoute` component guards all authenticated pages — redirects to `/login` if no JWT token, allows access with token even during transient user-fetch failures (network-error resilience)
- [x] Provider nesting order established: `AuthProvider` → `NotificationProvider` → `APIKeyProvider` → `WebSocketProvider` → `Routes`
- [x] Index route redirects to `/dashboard` via `<Navigate to="dashboard" replace />`
- [x] Catch-all `*` route redirects to `/dashboard` (no 404 page)

### Phase 15 — State Management (React Context)
- [x] **`AuthContext`** (`src/context/AuthContext.jsx`): manages `user`, `loading`, `error` state; `login()` clears previous user data then calls `/auth/login` and sets JWT in `localStorage`; `register()` auto-logs in after registration; `logout()` removes token and clears all user-specific localStorage keys; `fetchUser()` distinguishes network errors (keep token, surface error) from 401s (remove token, clear data); `isAuthenticated` derived from user object or token+loading state; `clearAllUserData()` helper removes `selected_api_key`, `selected_api_key_metadata`, `selected_api_key_id`, and `api_key_secret_by_id`
- [x] **`APIKeyContext`** (`src/context/APIKeyContext.jsx`): `selectedAPIKey` state lazy-initialised from `localStorage` (survives page refresh); `selectAPIKey()` normalises key object and persists to `localStorage` under three keys (`API_KEY`, `META`, legacy `LEGACY_ID`); `clearAPIKey()` removes all storage keys; `updateAPIKeys()` uses a ref to avoid stale closure — clears selection if the selected key no longer appears in the updated list; auth-loading guard (`authLoading`) prevents false logout on session rehydration; `prevUserRef` tracks genuine `user → null` transitions to distinguish logout from initial load; `hasSelectedKey` boolean and `getAPIKeyString()` helper exported for consumers
- [x] **`NotificationContext`** (`src/context/NotificationContext.jsx`): in-memory notification queue with auto-incrementing IDs; `addNotification(message, type, duration)` schedules `removeNotification` via `setTimeout`; convenience aliases: `success()`, `error()`, `warning()`, `info()`; `clearNotifications()` wipes all toasts at once
- [x] **`WebSocketContext`** (`src/context/WebSocketContext.jsx`): generational connection management — every `connect()` call increments `generationRef` so all callbacks from the previous socket are silently dropped (fixes stale-message contamination after key switches); `_hardClose()` strips all handlers before calling `ws.close()` to prevent ghost reconnect loops; `connect()` resets all event/metric/alert state for the new key before opening the socket; `disconnect()` bumps generation then hard-closes; reconnect with up to 5 attempts and 3-second delay (generation-gated to prevent reconnect after key change); 30-second ping/pong keepalive; `rateLimitExceeded` state stops event ingestion and disconnects; `handleMessage` dispatches on `type`: `connected`, `event`, `metric`, `alert`, `rate_limit_exceeded`/`error`, `pong`; `MAX_EVENTS_STORED` capped at 10,000 events in memory; 10-second auto-dismiss for `currentAlert`

### Phase 16 — Custom Hooks
- [x] **`useAuth`** (`src/hooks/useAuth.js`): consumes `AuthContext`, throws if used outside provider
- [x] **`useAPIKey`** (`src/hooks/useAPIKey.js`): consumes `APIKeyContext`, throws if used outside provider
- [x] **`useWebSocket`** (`src/hooks/useWebSocket.js`): consumes `WebSocketContext`, throws if used outside provider
- [x] **`useNotification`** (`src/hooks/useNotification.js`): consumes `NotificationContext`, throws if used outside provider
- [x] **`useAPI`** (`src/hooks/useAPI.js`): generic async executor with `loading` and `error` state; `execute(apiCall, options)` accepts `onSuccess`, `onError`, `showErrorNotification`, `showSuccessNotification`, `successMessage` options; calls `useNotification().error` automatically on failure; `resetError()` helper
- [x] **`useLocalStorage`** (`src/hooks/useLocalStorage.js`): React state synced to `localStorage` with JSON serialization; lazy initial read; `setValue` accepts function updater pattern; `removeValue` restores to `initialValue`

### Phase 17 — API Service Layer
- [x] `src/services/api.js` implements `APIClient` singleton class with `this.baseURL` from `API_CONFIG.BASE_URL` and `this.timeout` (30s)
- [x] `getToken()` / `setToken()` / `removeToken()` manage JWT in `localStorage` under key `token`
- [x] `getSelectedAPIKey()` reads `selected_api_key` from `localStorage`
- [x] `getHeaders(useAPIKey)` builds request headers: JWT `Authorization: Bearer` for user routes, `X-API-Key` for API-key-authenticated routes
- [x] `request(endpoint, options)` wraps `fetch` with `AbortController` timeout, JSON/text response parsing, empty-body handling for 204/205, structured error objects with `.status`, `.isAPIKeyError`, `.isRateLimitExceeded` flags; network errors rethrown as `NETWORK_ERROR` code; abort rethrown as `TIMEOUT` code
- [x] **Auth methods:** `register()`, `login()` (sets token on success), `refreshToken()`, `getCurrentUser()`, `logout()`
- [x] **API Key methods:** `createAPIKey()`, `getAPIKeys()`, `getAPIKeyDetails()`, `revokeAPIKey()`, `deleteAPIKey()`
- [x] **Metrics methods:** `getOverviewMetrics(period)`, `getTimeSeries(metricName, startTime, endTime, interval)`, `getTopEvents(period, limit)`, `getActiveUsers(window)`, `getEvents(params)` — all use `useAPIKey: true`
- [x] **Alert methods:** `createAlert()`, `getAlerts()`, `getAlert()`, `updateAlert()`, `deleteAlert()`, `testAlert()`, `getAlertHistory()`, `enableAlert()`, `disableAlert()` — all use `useAPIKey: true`
- [x] **Ingestion methods:** `ingestEvent()`, `ingestEventBatch()`, `getIngestionStatus()` — use API key auth
- [x] **Health methods:** `getHealth()`, `getDetailedHealth()`

### Phase 18 — Utility Modules
- [x] **`src/utils/formatters.js`**: `formatDate(date, formatStr)` using `date-fns` `format`/`parseISO`; `formatRelativeTime()` with `formatDistanceToNow`; `formatNumber()` using `Intl.NumberFormat`; `formatCompactNumber()` with K/M/B suffixes; `formatPercentage(value, decimals)`; `formatBytes(bytes, decimals)`; `truncate(str, maxLength)`; `formatJSON(obj, indent)` safe JSON stringify; `formatAPIKey(key)` shows first 8 + last 8 chars; `formatDuration(seconds)` → s/m/h/d; `formatRate(value, unit, decimals)`; `getInitials(email)` extracts up to 2 chars from email prefix; `copyToClipboard(text)` with `navigator.clipboard` and `execCommand` fallback
- [x] **`src/utils/validators.js`**: `validateEmail(email)` regex; `validatePassword(password)` returns `{isValid, errors[]}` checking length ≥ 8, uppercase, lowercase, digit; `validateRequired(value, fieldName)`; `validateNumber(value, min, max)`; `validateLength(value, min, max)`; `validateURL(url)` via `new URL()`; `validateJSON(str)` via `JSON.parse`; `validateAPIKey(key)` checks `ep_live_` prefix and minimum length; `validateForm(data, rules)` composable multi-field validator

### Phase 19 — Common UI Components
- [x] **`Badge`** (`src/components/common/Badge.jsx`): 8 variants (`default`, `primary`, `success`, `danger`, `warning`, `info`, `purple`, `pink`), 4 sizes (`xs`–`lg`), optional `rounded-full` vs `rounded` toggle
- [x] **`Button`** (`src/components/common/Button.jsx`): 7 variants (`primary`, `secondary`, `success`, `danger`, `warning`, `outline`, `ghost`, `link`), 5 sizes (`xs`–`xl`), `loading` state with `Loader2` spinner, optional `icon` prop with left/right position, `fullWidth` prop, `disabled` during loading
- [x] **`Card`** (`src/components/common/Card.jsx`): optional `title`, `subtitle`, `actions` header section with separator; `hover` shadow transition; configurable `padding`, `className`, `headerClassName`, `bodyClassName`
- [x] **`EmptyState`** (`src/components/common/EmptyState.jsx`): centered layout with icon, title, description, optional action button (accepts either a rendered `action` node or `onAction` + `actionLabel` pair); default icon `Inbox`
- [x] **`Input`** (`src/components/common/Input.jsx`): `forwardRef`-wrapped; supports `label` with required asterisk, `icon` with left/right position, `error` display with `AlertCircle` icon, `helperText`, `disabled` greying; adjusts padding automatically for icon position
- [x] **`Modal`** (`src/components/common/Modal.jsx`): `fixed` overlay with backdrop blur; ESC key close; overlay click close (configurable); 5 size variants (`sm`–`full`); scrollable body with `max-h` constraint; optional footer slot; prevents body scroll while open via `overflow: hidden`
- [x] **`Select`** (`src/components/common/Select.jsx`): `forwardRef`-wrapped; `ChevronDown` icon overlay; `options` array of `{value, label}`; placeholder option disabled; error and helper text support; `appearance-none` for custom styling
- [x] **`Spinner`** (`src/components/common/Spinner.jsx`): `Loader2` with `animate-spin`; ping background circle; 5 sizes, 5 colour variants; optional message with `animate-pulse`; `fullScreen` mode with backdrop blur
- [x] **`Toast` / `ToastContainer`** (`src/components/common/Toast.jsx`): `Toast` auto-dismisses via `setTimeout` on `duration` prop; 4 type configs (`success`, `error`, `warning`, `info`) each with bg, text, icon, iconColor; `ToastContainer` renders fixed top-right stack; `slide-in` animation class

### Phase 20 — Layout Components
- [x] **`Layout`** (`src/components/layout/Layout.jsx`): root shell with `Navbar` + `Sidebar` + `<Outlet />`; sidebar open state managed locally; `ToastContainer` wired to `useNotification`; main content padded with `pt-16` (navbar height) and `lg:pl-64` (sidebar width)
- [x] **`Navbar`** (`src/components/layout/Navbar.jsx`): fixed top bar (height `h-16`, `z-40`); left: hamburger (mobile only) + logo (`EP` monogram + text); centre (hidden on mobile): selected API key name + masked key string in blue pill, or "No API Key Selected" warning badge; right: notification bell with red dot, user avatar with initials + email dropdown (Settings, API Keys, Logout); dropdown closes on overlay click
- [x] **`Sidebar`** (`src/components/layout/Sidebar.jsx`): fixed left (`w-64`), translates off-screen on mobile, always visible `lg:translate-x-0`; 6 nav items with icons: Dashboard (`LayoutDashboard`), Live Feed (`Radio`), Events (`Activity`), Metrics (`BarChart2`), Alerts (`Bell`), API Keys (`Key`); `NavLink` applies `bg-blue-50 text-blue-700` active style; mobile overlay backdrop; footer copyright note; closes on nav item click (mobile)
- [x] **`ProtectedRoute`** (`src/components/layout/ProtectedRoute.jsx`): renders `Spinner` during auth loading; redirects to `/login` only when both `user` and `token` are absent; allows access when token exists but user fetch is pending (handles network error on refresh)

### Phase 21 — Dashboard Components
- [x] **`MetricCard`** (`src/components/dashboard/MetricCard.jsx`): displays title, large value (auto-formatted with `formatCompactNumber`), optional trend icon (`TrendingUp`/`TrendingDown`/`Minus`) with colour coding (`positive`=green, `negative`=red, `neutral`=gray), optional subtitle; `loading` prop renders a full animated skeleton placeholder; 6 icon colour variants
- [x] **`TimeSeriesChart`** (`src/components/dashboard/TimeSeriesChart.jsx`): Recharts `LineChart` with `ResponsiveContainer`; custom tooltip showing formatted date and value; `CartesianGrid` with dashed strokes; `XAxis` uses `formatDate(item, 'HH:mm')`; `YAxis` ticks formatted with `formatNumber`; single `Line` with `dot={false}` and `activeDot`; spinner and empty-state fallbacks
- [x] **`TopEventsChart`** (`src/components/dashboard/TopEventsChart.jsx`): Recharts `BarChart`; each bar `Cell` coloured from `EVENT_COLORS` palette (cycles for >8 events); `XAxis` angled `-45°` with `height={80}` for long event names; custom tooltip shows count and percentage; spinner and empty-state fallbacks

### Phase 22 — Page: Login & Register
- [x] **`Login`** (`src/pages/Login.jsx`): full-screen centered layout; `EP` logo with hover scale; email + password `Input` components with icon; client-side validation via `validateEmail`; `useAuth().login()` on submit; displays `authError` from context; links to `/register`; redirects to `/dashboard` if already authenticated
- [x] **`Register`** (`src/pages/Register.jsx`): same layout as Login; adds confirm-password field; real-time `validatePassword` feedback panel (shown as each requirement passes/fails with `CheckCircle`/`XCircle`); `useAuth().register()` auto-logs in; links to `/login`

### Phase 23 — Page: Dashboard
- [x] **`Dashboard`** (`src/pages/Dashboard.jsx`): guards against no API key with centred `EmptyState`; separate `apiKeyError` state shown as a styled error card with "Go to API Keys" and "Try Again" actions; rate-limit warning banner wired to `useWebSocket().rateLimitExceeded`; period selector (`Select` with `PERIOD_OPTIONS`) and manual refresh button; 4 `MetricCard`s (Total Events, Events/min, Active Users, Event Types) in responsive 2→4 column grid; `TimeSeriesChart` + `TopEventsChart` in a 1→2 column grid; auto-refreshes every 30 seconds (`APP_CONFIG.REFRESH_INTERVAL`) via `setInterval` (clears on unmount or API key error); `fetchOverview` and `fetchTimeSeries` wrapped in `useCallback` with stable deps

### Phase 24 — Page: API Keys
- [x] **`APIKeys`** (`src/pages/APIKeys.jsx`): lists all API keys for the authenticated user via `apiClient.getAPIKeys()`; each key card shows: key ID (copyable), client name, creation date, rate limit, active/revoked badge; "Select" button triggers `startSelectKey()` which checks `localStorage` for a cached secret — if found selects immediately, otherwise opens the "Enter API Key" modal for the user to paste the plain key (security: backend never re-exposes it); "Revoke" button with confirmation; "Delete" button removes key and clears selection if it was selected; "Create API Key" opens modal with `client_name` and `rate_limit` fields; on successful creation: plain key displayed in one-time reveal modal with copy button and yellow security warning; plain key auto-persisted to `localStorage` under `api_key_secret_by_id` map (keyed by ID); `updateAPIKeys()` called after every mutation to keep `APIKeyContext` in sync

### Phase 25 — Page: Live Feed
- [x] **`LiveFeed`** (`src/pages/LiveFeed.jsx`): connects WebSocket on mount via `useWebSocket().connect(id, apiKey)` using `selectedAPIKey?.id` as the dep to detect key changes (prevents duplicate connects on re-renders); local pause state with snapshot — on `isPaused: false → true` transition, current `events` array is frozen into `pausedEvents` so the display does not update while paused; auto-pauses on `rateLimitExceeded`; resumes by calling `resetRateLimit()` then reconnecting; rate-limit banner with "Clear Error & Resume" CTA; alert banner with severity-coded border and auto-dismiss; header card shows connection status badge, Pause/Resume, Export CSV, Clear buttons; 4 stat cards: total events (shows frozen count when paused), status, auto-scroll toggle checkbox, connection pulse indicator; event stream in `h-[500px]` overflow-y scroll container with `ref` for auto-scroll; each event card colour-coded by `event_name` (page_view=blue, click=green, error=red, purchase=purple, others=gray); properties shown in collapsible `<details>` with count; CSV export uses `\uFEFF` BOM for Excel UTF-8 compatibility; `generationRef` and `prevKeyIdRef` prevent stale state from previous key sessions

### Phase 26 — Page: Events Browser
- [x] **`Events`** (`src/pages/Events.jsx`): paginated event table with server-side filtering; `prevKeyIdRef` detects API key changes and resets events, pagination, and filters before fetching for the new key; filter fields: event name, user ID, start/end datetime-local inputs; "Apply Filters" resets to page 1 then fetches; "Clear" resets filter state and fetches; results table columns: event name (badge), user ID, event time, received at, details toggle; expandable row shows full event ID, client ID, and pretty-printed JSONB properties; offset pagination with page number buttons (sliding window of 5), Previous/Next; shows "X to Y of Z results" count; CSV export of current page events; key-change guard wipes displayed events immediately to prevent cross-key data leakage

### Phase 27 — Page: Alerts
- [x] **`Alerts`** (`src/pages/Alerts.jsx`): full CRUD UI for alert management; alert cards show: name, enabled/disabled badge, severity badge, condition expression (`metric operator threshold`), cooldown, trigger count, last triggered date; icon action buttons: toggle enable/disable (`Play`/`Pause`), dry-run test (`TestTube`), view history (`History`), edit (`Edit2`), delete (`Trash2`); "Create Alert" / "Edit Alert" unified modal with fields: name, description, metric (`Select` from `METRIC_OPTIONS`), operator (`Select` from `OPERATOR_OPTIONS`), threshold (`Input[number]`), severity, cooldown seconds, WebSocket notification checkbox, email addresses textarea; alert history modal shows paginated trigger records with severity badge, message, current value vs threshold, and notification-sent status badge; test result shown as warning/success toast ("Alert would trigger" / "Alert would NOT trigger"); empty state shown when no API key selected or no alerts exist

### Phase 28 — Frontend Deployment Configuration
- [x] `render.yaml` configures Render static site: `rootDir: frontend`, `buildCommand: npm install && npm run build`, `staticPublishPath: dist`; production env vars `VITE_API_URL` pointing to `https://eventpulse-backend-6la6.onrender.com/api/v1` and `VITE_WS_URL` pointing to `wss://` equivalent
- [x] `package.json` scripts: `dev` (Vite dev server), `build` (production bundle to `dist/`), `preview` (serve production build locally), `lint` (ESLint with zero-warning policy)
- [x] Vite dev proxy routes `/api/*` to `http://localhost:8002` eliminating CORS issues in development
- [x] Production bundle uses Vite code-splitting via React Router lazy loading; output directory `dist/` gitignored

---

## Database Migrations

All migrations are managed by Alembic. The chain is fully linear with no branches.

| Revision | Description | Tables / Changes |
|---|---|---|
| `405c286eaca1` | Initial full schema | Creates `users` table; unique index on `email` |
| `ec58312128bc` | Add API keys table | Creates `api_keys` table; FK → `users.id` (`SET NULL`); unique index on `key_hash` |
| `f22717a1db4d` | Add events table with indexes | Creates `events` table (BigSerial PK, JSONB `properties`); 7 indexes including composite `idx_client_event_time` and `idx_client_event_name_time` |
| `50a37bce1d12` | Add aggregates table | Creates `aggregates` table with UNIQUE constraint on `(client_id, metric_name, interval_start)` |
| `bc45ac0e7528` | Add alerts and alert history | Creates `alerts` table (JSONB `expression`, `notification_channels`) and `alert_history` table; FK `alert_history.alert_id → alerts.id` (`CASCADE`) |
| `44b69d9393f0` | Performance index | Adds `idx_aggregates_client_metric_time` composite index on `(client_id, metric_name, interval_start)` |

---

## API Endpoint Inventory

All endpoints are prefixed with `/api/v1/`.

### Authentication — `/auth`

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `POST` | `/auth/register` | None | Register new user account |
| `POST` | `/auth/login` | None | Login and receive JWT access + refresh tokens |
| `POST` | `/auth/refresh` | Refresh Token | Exchange refresh token for new access token |
| `GET` | `/auth/me` | JWT | Get current authenticated user profile |
| `PATCH` | `/auth/me` | JWT | Update current user profile |

### API Keys — `/api-keys`

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `POST` | `/api-keys/` | JWT | Create new API key (returns plain key once) |
| `GET` | `/api-keys/` | JWT | List all API keys for the current user |
| `GET` | `/api-keys/{key_id}` | JWT | Get details for a specific API key |
| `PATCH` | `/api-keys/{key_id}/revoke` | JWT | Revoke an API key (sets `is_active=False`) |
| `DELETE` | `/api-keys/{key_id}` | JWT | Permanently delete an API key |

### Event Ingestion — `/ingest`

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `POST` | `/ingest/events` | API Key + Rate Limit | Ingest a single event (202 Accepted, queued) |
| `POST` | `/ingest/events/batch` | API Key + Rate Limit | Ingest up to 1,000 events in one request |
| `GET` | `/ingest/status` | API Key + Rate Limit | Get ingestion pipeline and queue status |
| `GET` | `/ingest/test-redis` | None | Test Redis connectivity (dev utility) |

### Metrics — `/metrics`

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `GET` | `/metrics/overview` | API Key | Dashboard overview (totals, EPM, active users, top events) |
| `GET` | `/metrics/top-events` | API Key | Top N events by count for a time period |
| `GET` | `/metrics/active-users` | API Key | Unique active user count for a time window |
| `GET` | `/metrics/time-series/{metric_name}` | API Key | Time series data points for a named metric |
| `GET` | `/metrics/time-series/{metric_name}/paginated` | API Key | Cursor-paginated time series data |
| `GET` | `/metrics/events` | API Key | Raw events with offset pagination and filters |

### Alerts — `/alerts`

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `POST` | `/alerts/` | API Key | Create a new alert with expression and channels |
| `GET` | `/alerts/` | API Key | List all alerts (filterable by `enabled`) |
| `GET` | `/alerts/{alert_id}` | API Key | Get a specific alert |
| `PATCH` | `/alerts/{alert_id}` | API Key | Update alert fields (partial update) |
| `DELETE` | `/alerts/{alert_id}` | API Key | Delete alert and its full history |
| `POST` | `/alerts/{alert_id}/test` | API Key | Dry-run evaluation (no notifications sent) |
| `GET` | `/alerts/{alert_id}/history` | API Key | Paginated trigger history for an alert |
| `POST` | `/alerts/{alert_id}/enable` | API Key | Enable alert (shortcut for PATCH) |
| `POST` | `/alerts/{alert_id}/disable` | API Key | Disable alert (shortcut for PATCH) |

### Admin — `/admin`

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `POST` | `/admin/trigger-event-processing` | JWT (Admin) | Manually trigger event batch processing |
| `POST` | `/admin/process-queue` | JWT (Admin) | Drain multiple queue batches (catch-up) |
| `POST` | `/admin/compute-aggregates` | JWT (Admin) | Trigger minute or hourly aggregate computation |
| `POST` | `/admin/cleanup-aggregates` | JWT (Admin) | Trigger old aggregate data cleanup |
| `GET` | `/admin/task-status/{task_id}` | JWT (Admin) | Poll status of a Celery task by ID |

### WebSockets — `/ws`

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `WS` | `/ws/live/{client_id}` | API Key (`?token=`) | Real-time live feed: events, metrics, alerts |
| `GET` | `/ws/connections` | None | Get active WebSocket connection statistics |

### Health — `/health`

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `GET` | `/health/` | None | Basic health check (DB + Redis status) |
| `GET` | `/health/detailed` | None | Detailed health with queue length and metrics |
| `GET` | `/health/live` | None | Kubernetes liveness probe |
| `GET` | `/health/ready` | None | Kubernetes readiness probe (DB + Redis) |
| `GET` | `/health/protected` | API Key | Authenticated connectivity probe |

### Root

| Method | Path | Auth | Description |
|--------|------|:----:|---|
| `GET` | `/` | None | API info: name, version, environment, docs link |

---

## Security & Middleware

### Authentication Layers

| Layer | Mechanism | Applies To |
|---|---|---|
| JWT Bearer | `python-jose` / `HS256` | Platform users (`/auth`, `/api-keys`, `/admin`) |
| API Key | SHA-256 hash lookup | Client apps (`/ingest`, `/metrics`, `/alerts`, `/ws`) |

- JWT tokens carry `sub` (user UUID) and `type` (`access` or `refresh`) claims
- Access tokens expire per `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 min)
- Refresh tokens expire per `REFRESH_TOKEN_EXPIRE_DAYS` (default: 7 days)
- API keys are stored as SHA-256 hashes; the plain key is shown exactly once at creation and never stored
- API key header formats supported: `X-API-Key: <key>` and `Authorization: ApiKey <key>`

### Password Security

- Passwords hashed with **bcrypt** via `passlib.CryptContext`
- Input byte-length enforced to 72 bytes before hashing (bcrypt maximum, applied in code)
- `verify_password` uses constant-time comparison internally

### Rate Limiting

- Redis sliding-window algorithm via **atomic Lua script** (`EVALSHA` — single round-trip, no race conditions)
- Rate limit is per API key and configurable at key creation (default: 1,000 req/min)
- Enforced headers on every response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`
- Rate limit exceeded events published to WebSocket clients via Redis Pub/Sub
- Fail-open on Redis errors to prevent total service disruption

### CORS

- `CORSMiddleware` applied globally: `allow_origins=["*"]`, all methods and headers permitted
- Designed to be tightened per-environment in production deployments

### HTTP Middleware

- Custom `log_requests` middleware logs every request and response with method, path, status code, and wall-clock duration
- `X-Process-Time` header injected into every response
- Global unhandled `exception_handler` returns structured JSON `500` with error type and request path

### Container Security (Production)

- Production image (`Dockerfile.prod`) runs as non-root user `appuser` (UID 1000)
- Multi-stage build: gcc and other build tools absent from the final runtime image

---

## Frontend Architecture

### Tech Stack

| Library | Version | Role |
|---|---|---|
| React | 18.3.1 | UI framework |
| React Router DOM | 6.30.3 | Client-side routing |
| Vite | 5.4.x | Build tool and dev server |
| Tailwind CSS | 3.4.x | Utility-first styling |
| Recharts | 2.15.x | Chart components (LineChart, BarChart) |
| Lucide React | 0.294.0 | Icon library |
| date-fns | 2.30.0 | Date formatting and manipulation |

### Directory Structure

```
frontend/src/
├── App.jsx                  # Root component, route definitions, provider nesting
├── main.jsx                 # React 18 createRoot entry point
├── config.js                # Centralised constants (API URLs, colours, options)
├── index.css                # Tailwind directives, global resets, scrollbar, slide-in
├── styles/
│   └── animations.css       # Custom keyframe animations
├── context/
│   ├── AuthContext.jsx       # JWT auth state, login/logout, user fetch
│   ├── APIKeyContext.jsx     # Selected API key, localStorage persistence
│   ├── NotificationContext.jsx  # Toast notification queue
│   └── WebSocketContext.jsx  # WebSocket lifecycle, generational management
├── hooks/
│   ├── useAuth.js            # AuthContext consumer
│   ├── useAPIKey.js          # APIKeyContext consumer
│   ├── useWebSocket.js       # WebSocketContext consumer
│   ├── useNotification.js    # NotificationContext consumer
│   ├── useAPI.js             # Generic async executor with loading/error state
│   └── useLocalStorage.js    # localStorage ↔ React state sync
├── services/
│   └── api.js               # APIClient singleton (all HTTP calls)
├── utils/
│   ├── formatters.js         # Date, number, string, clipboard helpers
│   └── validators.js         # Email, password, form validation
├── components/
│   ├── common/
│   │   ├── Badge.jsx
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── EmptyState.jsx
│   │   ├── Input.jsx
│   │   ├── Modal.jsx
│   │   ├── Select.jsx
│   │   ├── Spinner.jsx
│   │   └── Toast.jsx
│   ├── dashboard/
│   │   ├── MetricCard.jsx
│   │   ├── TimeSeriesChart.jsx
│   │   └── TopEventsChart.jsx
│   └── layout/
│       ├── Layout.jsx
│       ├── Navbar.jsx
│       ├── Sidebar.jsx
│       └── ProtectedRoute.jsx
└── pages/
    ├── Login.jsx
    ├── Register.jsx
    ├── Dashboard.jsx
    ├── APIKeys.jsx
    ├── LiveFeed.jsx
    ├── Events.jsx
    └── Alerts.jsx
```

### Key Design Decisions

- **Generational WebSocket management:** every `connect()` call increments a generation counter; all callbacks capture their generation at open-time and discard messages if the counter has since advanced — eliminates stale-message contamination when switching API keys
- **Lazy localStorage init:** `APIKeyContext` reads from `localStorage` in the `useState` initializer so the selected key is available synchronously on first render, preventing a flash of "no key selected" after page refresh
- **Auth-loading guard:** `APIKeyContext` waits for `authLoading` to settle before acting on `user === null`, preventing false logout during session rehydration
- **Cross-key data isolation:** `Events` page uses `prevKeyIdRef` to detect key identity changes and resets all state (events, pagination, filters) before issuing the first fetch for the new key
- **API key secret handling:** the backend returns the plain key only once; the frontend persists it to `localStorage` under a per-ID map (`api_key_secret_by_id`); if missing, a paste modal prompts the user to supply it
- **Rate limit UX:** the Live Feed page surfaces a prominent red banner with actionable CTAs when the WebSocket signals `rate_limit_exceeded`; the event stream auto-pauses and the banner persists until explicitly dismissed

---

## Completed Features

### Backend
- [x] **User Authentication System** — JWT register/login/refresh flow with `user` / `admin` role-based access control
- [x] **API Key Management** — Secure key generation (`ep_live_*`), SHA-256 hashed storage, revocation, and per-key rate limits
- [x] **High-Throughput Event Ingestion** — Single and batch ingestion (up to 1,000 events/request) with Redis queuing targeting 10,000+ events/second
- [x] **Async Background Processing** — Celery workers bulk-insert events from the Redis queue into PostgreSQL every 5 seconds
- [x] **Automated Metric Aggregation** — Per-minute (`events_per_minute`, `active_users_1m`) and per-hour (`events_per_hour`, `active_users_1h`, `top_events_1h`) aggregates via Celery Beat UPSERT
- [x] **Real-Time WebSocket Streaming** — Live event, metric, and alert delivery via Redis Pub/Sub relay to connected clients
- [x] **Dashboard Metrics API** — Overview, top events, active users, and flexible time-series with both offset and cursor-based pagination
- [x] **Smart Alert Engine** — CRUD alert management with JSONB expression evaluation, configurable cooldown periods, and persistent trigger history
- [x] **Multi-Channel Alert Notifications** — WebSocket delivery (default) and SMTP email with HTML templates and severity color coding
- [x] **Atomic Redis Rate Limiting** — Sliding-window rate limiter using Lua scripting for race-condition-free enforcement with WebSocket notification on breach
- [x] **Admin Control Panel** — Manually trigger or poll any Celery task via authenticated admin API endpoints
- [x] **Structured Logging** — JSON-formatted logs in production (ELK/CloudWatch-compatible), human-readable in development, with separate daily error log
- [x] **Sentry Error Tracking** — Optional Sentry integration (`FastApiIntegration`, `SqlalchemyIntegration`) conditionally initialized via `SENTRY_DSN`
- [x] **Full Docker Containerization** — Development and production Compose stacks with health checks for all 5 services
- [x] **Kubernetes-Ready Health Probes** — Dedicated `/health/live` (liveness) and `/health/ready` (readiness) endpoints
- [x] **Automated Data Retention** — Daily Celery task removes aggregates older than 30 days (configurable via `days_to_keep`)
- [x] **WebSocket Connection Management** — Per-client connection limits (100 max), channel subscriptions, and graceful Redis reconnection with exponential backoff
- [x] **Test Infrastructure** — pytest with `asyncio_mode = auto`, isolated test DB engine, `AsyncClient` integration fixtures, and concurrency stress testing

### Frontend
- [x] **Login & Registration Pages** — JWT auth forms with real-time password strength validation and inline error display
- [x] **Protected Routing** — Token-based route guard with graceful handling of network errors during session rehydration
- [x] **Analytics Dashboard** — 4 metric cards, events-per-minute line chart, top-events bar chart; auto-refreshes every 30s; period selector; manual refresh
- [x] **API Key Management UI** — Full key lifecycle: create (with one-time plain-key reveal), select (with localStorage secret caching), revoke, delete; paste-modal for re-selecting keys whose secret wasn't cached
- [x] **Real-Time Live Feed** — WebSocket-powered event stream with pause/resume (snapshot freeze), auto-scroll toggle, rate-limit banner, alert banner, event colour coding by type, CSV export with Excel BOM
- [x] **Event Browser** — Paginated event table with server-side filters (event name, user ID, date range), expandable rows showing JSONB properties, offset pagination with sliding page window, CSV export
- [x] **Alert Management UI** — Full CRUD with expression builder (metric, operator, threshold), severity selector, cooldown config, notification channels (WebSocket + email), dry-run test, trigger history modal, enable/disable toggle
- [x] **Generational WebSocket Client** — Correct cleanup on API key switch: generation counter, hard-close with handler stripping, state reset before reconnect — eliminates stale-message cross-contamination
- [x] **Reusable Component Library** — Badge, Button, Card, EmptyState, Input, Modal, Select, Spinner, Toast/ToastContainer; all responsive and accessible
- [x] **Toast Notification System** — Contextual toasts (success/error/warning/info) with auto-dismiss, manual close, and fixed top-right stack
- [x] **Responsive Layout** — Mobile-first design: hamburger sidebar on mobile (`<lg`), fixed navbar, collapsible sidebar overlay with backdrop
- [x] **Render Static Deployment** — `render.yaml` pre-configured for one-click frontend deployment alongside the backend service
