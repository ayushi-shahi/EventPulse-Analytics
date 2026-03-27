# EventPulse Analytics

> A self-hosted, real-time analytics platform — like a mini Mixpanel or Google Analytics — that you own and deploy yourself.

---

## Overview

EventPulse lets you track events from any web or backend application and visualize them in a real-time dashboard — all on infrastructure you control.

* **Sign up** on your EventPulse dashboard
* **Create an API key** (`ep_live_...`)
* **Add one snippet** to your app (React, Vue, plain HTML, Django, FastAPI, or plain Python)
* **Watch events flow in live** on your dashboard

No data leaves your deployment. No vendor lock-in.

---

## Live Demo

| Service                      | URL                                                                    |
| ---------------------------- | ---------------------------------------------------------------------- |
| **Backend API**        | https://eventpulse-analytics-backend.onrender.com                      |
| **API Docs (Swagger)** | https://eventpulse-analytics-backend.onrender.com/docs                 |
| **JS Drop-in SDK**     | https://eventpulse-analytics-backend.onrender.com/static/eventpulse.js |
| **npm package**        | https://www.npmjs.com/package/eventpulse-analytics                     |
| **PyPI package**       | https://pypi.org/project/eventpulse-python/1.0.0/                      |

---

## Features

### Backend

* **JWT Authentication** — register, login, refresh tokens, profile management
* **API Key System** — `ep_live_*` prefixed keys, SHA-256 hashed, with revocation
* **High-Throughput Event Ingestion** — batch up to 1,000 events per request via Redis queue
* **Background Processing** — APScheduler tasks for ingestion, aggregation, cleanup, and alert evaluation
* **Real-Time WebSocket Feed** — live event stream via Redis Pub/Sub, channel-based subscriptions
* **Metrics API** — overview, time series, top events, active users (all paginated)
* **Alerts Engine** — expression-based rules, cooldown enforcement, severity levels, trigger history
* **Rate Limiting** — atomic sliding-window via Lua script in Redis, with `X-RateLimit-*` headers
* **Observability** — structured JSON logging, Sentry integration, health probes

### Frontend

* **Dashboard** — metric cards, time series chart, top events chart, auto-refresh
* **Live Feed** — real-time WebSocket event stream with pause/resume and CSV export
* **Events Browser** — paginated, filterable event table with expandable row details
* **Alerts UI** — full CRUD, dry-run test, alert history modal
* **API Key Management** — create, select, revoke, and delete keys from the UI
* **Responsive design** — mobile-first, built with Tailwind CSS

### SDKs

| SDK                            | Install                              | Targets                       |
| ------------------------------ | ------------------------------------ | ----------------------------- |
| **JS Drop-in**           | `<script src="...">`               | Any HTML page, no build step  |
| **eventpulse-analytics** | `npm install eventpulse-analytics` | React, Vue 3, TypeScript      |
| **eventpulse-python**    | `pip install eventpulse-python`    | Plain Python, Django, FastAPI |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Apps                          │
│   React / Vue / Plain HTML / Django / FastAPI / Python      │
└───────────────────────┬─────────────────────────────────────┘
                        │  HTTPS  (X-API-Key header)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Render)                   │
│                                                             │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │  /auth   │  │  /ingest  │  │ /metrics │  │ /alerts  │  │
│  └──────────┘  └─────┬─────┘  └────┬─────┘  └──────────┘  │
│                      │             │                        │
│  ┌───────────────────▼─────────────▼──────────────────┐    │
│  │              APScheduler (in-process)               │    │
│  │  • Event batch processor (5s)                       │    │
│  │  • Aggregate computation (per-minute / per-hour)    │    │
│  │  • Alert evaluation (60s)                           │    │
│  │  • Cleanup task (daily)                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌──────────────┐     ┌──────────────────────────────┐     │
│  │  /ws/live    │────▶│   Redis Pub/Sub Broadcaster   │     │
│  │  WebSocket   │     │   (events / metrics / alerts) │     │
│  └──────────────┘     └──────────────────────────────┘     │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────┐        ┌──────────────────┐
│   PostgreSQL    │        │      Redis        │
│   (Supabase)    │        │    (Upstash)      │
│                 │        │                  │
│  users          │        │  event queue     │
│  api_keys       │        │  rate limiter    │
│  events         │        │  pub/sub         │
│  aggregates     │        └──────────────────┘
│  alerts         │
│  alert_history  │
└─────────────────┘
```

**Event flow:**

1. SDK sends batch → `POST /api/v1/ingest/events/batch`
2. Events are pushed to a Redis list (queue)
3. APScheduler dequeues and bulk-inserts into PostgreSQL every 5 seconds
4. Aggregates are computed and written; dashboard metrics refresh
5. New events are published to Redis Pub/Sub → WebSocket clients receive them live

---

## Tech Stack

| Layer                      | Technology                                                     |
| -------------------------- | -------------------------------------------------------------- |
| **Backend**          | Python 3.11, FastAPI, SQLAlchemy (async), Alembic, APScheduler |
| **Database**         | PostgreSQL (Supabase)                                          |
| **Cache / Queue**    | Redis (Upstash)                                                |
| **Auth**             | JWT (`python-jose`), bcrypt (`passlib`)                    |
| **Frontend**         | React 18, Vite 5, Tailwind CSS 3, Recharts, React Router v6    |
| **JS SDK**           | Vanilla JS IIFE (~3KB, no dependencies)                        |
| **npm package**      | TypeScript, Vite library mode, ESM + UMD output                |
| **Python SDK**       | stdlib only (`urllib`,`threading`,`json`)                |
| **Backend hosting**  | Render                                                         |
| **Frontend hosting** | Vercel                                                         |
| **Monitoring**       | Sentry                                                         |

---

## Getting Started

### Prerequisites

* Python 3.11+
* Node.js 18+
* Docker & Docker Compose (for local stack)
* A PostgreSQL database (local or Supabase)
* A Redis instance (local or Upstash)

### Local Development

**1. Clone the repository**

```bash
git clone https://github.com/ayushi-shahi/EventPulse-Analytics.git
cd EventPulse-Analytics
```

**2. Start the full local stack with Docker**

```bash
docker-compose up --build
```

This starts PostgreSQL, Redis, and the FastAPI backend with migrations applied automatically.

**3. Or run the backend manually**

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8002
```

**4. Start the frontend**

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

**5. Open the API docs**

```
http://localhost:8002/docs
```

---

### Environment Variables

Copy `.env.example` to `.env` in the `backend/` directory and fill in your values:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379

# JWT
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# App
ENVIRONMENT=development         # or production
ALLOWED_ORIGINS=http://localhost:3000

# Optional
SENTRY_DSN=
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
```

Copy `frontend/.env.example` to `frontend/.env`:

```env
VITE_API_URL=http://localhost:8002
VITE_WS_URL=ws://localhost:8002
```

---

## SDKs & Integration

### Plain HTML — Drop-in Script

No installation required. Add one `<script>` tag to your HTML:

```html
<script
  src="https://eventpulse-analytics-backend.onrender.com/static/eventpulse.js"
  data-api-key="ep_live_YOUR_KEY"
  data-endpoint="https://eventpulse-analytics-backend.onrender.com">
</script>
```

Auto-tracks `page_view` on load and `click` on interactive elements. Works with React Router, Vue Router, and Next.js.

```js
// Manual tracking
EventPulse.track('button_click', { button: 'signup' })
EventPulse.identify('user_123')
EventPulse.flush()
```

📄 [Full HTML quick start guide](docs/quick-start-html.md)

---

### React / TypeScript

```bash
npm install eventpulse-analytics
```

```jsx
// main.jsx / main.tsx
import { EventPulseProvider } from 'eventpulse-analytics'

<EventPulseProvider
  apiKey="ep_live_YOUR_KEY"
  endpoint="https://eventpulse-analytics-backend.onrender.com"
>
  <App />
</EventPulseProvider>
```

```jsx
// Any component
import { useEventPulse } from 'eventpulse-analytics'

const { track, identify } = useEventPulse()

track('button_click', { button: 'signup', plan: 'pro' })
identify('user_123')
```

📄 [Full React quick start guide](docs/quick-start-react.md)

---

### Vue 3

```bash
npm install eventpulse-analytics
```

```js
// main.js
import { EventPulsePlugin } from 'eventpulse-analytics'

app.use(EventPulsePlugin, {
  apiKey: 'ep_live_YOUR_KEY',
  endpoint: 'https://eventpulse-analytics-backend.onrender.com'
})
```

```vue
<script setup>
import { inject } from 'vue'
const eventpulse = inject('eventpulse')

eventpulse.track('page_view', { page: 'home' })
</script>
```

📄 [Full Vue quick start guide](docs/quick-start-vue.md)

---

### Python — Plain

```bash
pip install eventpulse-python
```

```python
from eventpulse import EventPulseClient

ep = EventPulseClient(
    api_key="ep_live_YOUR_KEY",
    endpoint="https://eventpulse-analytics-backend.onrender.com"
)

ep.track("purchase", {"amount": 49.99, "plan": "pro"})
ep.identify("user_123")
ep.shutdown()  # flushes remaining events before exit
```

📄 [Full Python quick start guide](/docs/quick-start-python.md)

---

### Python — Django

```bash
pip install eventpulse-python
```

```python
# settings.py
MIDDLEWARE = [
    'eventpulse.django.EventPulseMiddleware',
    # ... your other middleware
]

EVENTPULSE_API_KEY = 'ep_live_YOUR_KEY'
EVENTPULSE_ENDPOINT = 'https://eventpulse-analytics-backend.onrender.com'
```

Auto-tracks every request as `page_view` and auto-identifies authenticated users.

📄 [Full Django quick start guide](/docs/quick-start-django.md)

---

### Python — FastAPI

```bash
pip install eventpulse-python
```

```python
from fastapi import FastAPI
from eventpulse.fastapi import EventPulseMiddleware

app = FastAPI()

app.add_middleware(
    EventPulseMiddleware,
    api_key="ep_live_YOUR_KEY",
    endpoint="https://eventpulse-analytics-backend.onrender.com"
)
```

📄 [Full FastAPI quick start guide](/docs/quick-start-fastapi.md)

---

## API Reference

All endpoints are prefixed with `/api/v1/`. Interactive docs available at `/docs`.

### Authentication

| Method   | Endpoint           | Auth          | Description               |
| -------- | ------------------ | ------------- | ------------------------- |
| `POST` | `/auth/register` | —            | Register a new user       |
| `POST` | `/auth/login`    | —            | Login, returns JWT tokens |
| `POST` | `/auth/refresh`  | Refresh token | Get a new access token    |
| `GET`  | `/auth/me`       | JWT           | Get current user profile  |

### Event Ingestion

| Method   | Endpoint                 | Auth    | Description               |
| -------- | ------------------------ | ------- | ------------------------- |
| `POST` | `/ingest/events`       | API Key | Ingest a single event     |
| `POST` | `/ingest/events/batch` | API Key | Ingest up to 1,000 events |
| `GET`  | `/ingest/status`       | API Key | Queue and pipeline status |

**Batch ingest payload:**

```json
{
  "events": [
    {
      "name": "button_click",
      "timestamp": "2024-01-01T12:00:00Z",
      "properties": {
        "button": "signup",
        "page": "/landing"
      }
    }
  ]
}
```

Headers required: `X-API-Key: ep_live_<64 hex chars>`

### Metrics

| Method  | Endpoint                          | Auth    | Description              |
| ------- | --------------------------------- | ------- | ------------------------ |
| `GET` | `/metrics/overview`             | API Key | Dashboard summary        |
| `GET` | `/metrics/top-events`           | API Key | Top N events by count    |
| `GET` | `/metrics/active-users`         | API Key | Unique active user count |
| `GET` | `/metrics/time-series/{metric}` | API Key | Time series data         |
| `GET` | `/metrics/events`               | API Key | Paginated raw events     |

### WebSocket Live Feed

```
wss://eventpulse-analytics-backend.onrender.com/api/v1/ws/live/{client_id}?api_key=ep_live_...
```

Subscribe to channels after connecting:

```json
{ "type": "subscribe", "channels": ["events", "metrics", "alerts"] }
```

### Health Probes

| Endpoint                        | Description       |
| ------------------------------- | ----------------- |
| `GET /api/v1/health/`         | Basic liveness    |
| `GET /api/v1/health/detailed` | DB + Redis status |
| `GET /api/v1/health/ready`    | Readiness probe   |

---

## Deployment

The production stack uses three free-tier services:

| Service                 | Provider | Purpose               |
| ----------------------- | -------- | --------------------- |
| **API**           | Render   | FastAPI + APScheduler |
| **Database**      | Supabase | PostgreSQL            |
| **Cache / Queue** | Upstash  | Redis                 |
| **Frontend**      | Vercel   | React SPA             |

### Deploy to Render (Backend)

1. Connect your GitHub repo to Render
2. Set **Build Command:** `pip install -r requirements.txt`
3. Set **Start Command:** `alembic upgrade head && gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
4. Add all environment variables from `.env.example`

### Deploy to Vercel (Frontend)

1. Import the `frontend/` directory into Vercel
2. Set **Framework:** Vite
3. Add environment variables:
   ```
   VITE_API_URL=https://eventpulse-analytics-backend.onrender.comVITE_WS_URL=wss://eventpulse-analytics-backend.onrender.com
   ```

---

## Project Structure

```
EventPulse-Analytics/
│
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── main.py                 # App entrypoint, router registration
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── routers/                # API route handlers
│   │   ├── services/               # Business logic (alerts, email, etc.)
│   │   ├── tasks/                  # APScheduler background tasks
│   │   ├── middleware/             # Rate limiter, logging
│   │   └── core/                   # Config, auth, dependencies
│   ├── alembic/                    # Database migrations
│   ├── tests/                      # pytest test suite + stress tests
│   ├── static/
│   │   └── eventpulse.js           # JS drop-in SDK (hosted here)
│   ├── Dockerfile
│   ├── Dockerfile.prod
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── frontend/                       # React application
│   ├── src/
│   │   ├── components/             # Reusable UI components
│   │   ├── pages/                  # Route-level page components
│   │   ├── context/                # React Context providers
│   │   ├── hooks/                  # Custom hooks
│   │   ├── services/               # API client
│   │   └── utils/                  # Formatters, validators
│   └── vite.config.js
│
├── eventpulse-analytics/           # npm package (JS/TS SDK)
│   ├── src/
│   │   ├── core.ts                 # EventPulseClient
│   │   ├── react/                  # <EventPulseProvider>, useEventPulse()
│   │   └── vue/                    # EventPulsePlugin
│   └── dist/                       # ESM + UMD + .d.ts
│
├── eventpulse-python/              # PyPI package (Python SDK)
│   ├── eventpulse/
│   │   ├── client.py               # Core client, background thread
│   │   ├── django.py               # Django middleware
│   │   └── fastapi.py              # FastAPI/Starlette middleware
│   └── tests/
│
└── docs/                           # Quick start guides
    ├── README.md
    ├── quick-start-html.md
    ├── quick-start-react.md
    ├── quick-start-vue.md
    ├── quick-start-python.md
    ├── quick-start-django.md
    └── quick-start-fastapi.md
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: your feature description"`
4. Push to your branch: `git push origin feature/your-feature`
5. Open a Pull Request

Please follow the existing code style. Backend changes should include relevant tests in `tests/`.

---

## License

MIT © [Ayushi Shahi](https://github.com/ayushi-shahi)
