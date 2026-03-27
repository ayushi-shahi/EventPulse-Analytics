# EventPulse Documentation

> Real-time analytics platform — track events from any app, any language.

## Quick Start Guides

| Guide                                                           | Install                               |
| --------------------------------------------------------------- | ------------------------------------- |
| [Plain HTML](https://claude.ai/chat/quick-start-html.md)           | No install — paste a `<script>`tag |
| [React](https://claude.ai/chat/quick-start-react.md)               | `npm install eventpulse-analytics`  |
| [Vue 3](https://claude.ai/chat/quick-start-vue.md)                 | `npm install eventpulse-analytics`  |
| [Python — Django](https://claude.ai/chat/quick-start-django.md)   | `pip install eventpulse-python`     |
| [Python — FastAPI](https://claude.ai/chat/quick-start-fastapi.md) | `pip install eventpulse-python`     |
| [Python — Script](https://claude.ai/chat/quick-start-python.md)   | `pip install eventpulse-python`     |

## Production URLs

| Service              | URL                                                                        |
| -------------------- | -------------------------------------------------------------------------- |
| Frontend (Vercel)    | Your Vercel URL                                                            |
| Backend API (Render) | `https://eventpulse-analytics-backend.onrender.com`                      |
| JS Drop-in SDK       | `https://eventpulse-analytics-backend.onrender.com/static/eventpulse.js` |
| npm package          | `https://www.npmjs.com/package/eventpulse-analytics`                     |
| PyPI package         | `https://pypi.org/project/eventpulse-python/`                            |

## How It Works

1. **Sign up** on the EventPulse dashboard
2. **Create an API key** — format: `ep_live_<64 hex chars>`
3. **Install the SDK** for your stack (see guides above)
4. **Track events** — data appears in your dashboard in real time

## Event Format

All SDKs send events to:

```
POST /api/v1/ingest/events/batch
X-API-Key: ep_live_YOUR_KEY
Content-Type: application/json
```

```json
{
  "events": [
    {
      "event_name": "signup",
      "user_id": "user_123",
      "properties": { "plan": "pro" },
      "client_time": "2026-03-27T10:00:00.000Z"
    }
  ]
}
```
