# eventpulse-python

Official Python SDK for [EventPulse Analytics](https://github.com/ayushi-shahi/EventPulse-Analytics).

## Install

```bash
pip install eventpulse-python
```

## Quick Start

```python
from eventpulse import EventPulseClient

client = EventPulseClient(api_key="ep_live_YOUR_KEY")

client.track("signup", {"plan": "pro"})
client.identify("user_123")
client.page("https://yourapp.com/pricing")

# flush & stop background thread on app exit
client.shutdown()
```

Or use as a context manager:

```python
with EventPulseClient(api_key="ep_live_YOUR_KEY") as client:
    client.track("purchase", {"amount": 49.99})
```

## Django

Add to `settings.py`:

```python
MIDDLEWARE = [
    ...
    "eventpulse.django.EventPulseMiddleware",
]

EVENTPULSE_API_KEY = "ep_live_YOUR_KEY"
# optional:
EVENTPULSE_ENDPOINT = "https://eventpulse-analytics-backend.onrender.com"
```

Every request is auto-tracked as a `page_view` with url, path, method, status code, referrer, and user agent. Authenticated Django users are identified automatically.

## FastAPI / Starlette

```python
from fastapi import FastAPI
from eventpulse.fastapi import EventPulseMiddleware

app = FastAPI()
app.add_middleware(EventPulseMiddleware, api_key="ep_live_YOUR_KEY")
```

## Manual tracking in Django/FastAPI views

```python
from eventpulse import EventPulseClient

ep = EventPulseClient(api_key="ep_live_YOUR_KEY")

@app.post("/checkout")
async def checkout(item: Item, user_id: str):
    ep.identify(user_id)
    ep.track("checkout", {"item": item.name, "price": item.price})
    ...
```

## Options

| Parameter          | Default        | Description                                                |
| ------------------ | -------------- | ---------------------------------------------------------- |
| `api_key`        | required       | Your `ep_live_*`API key                                  |
| `endpoint`       | production URL | Override for local dev                                     |
| `batch_interval` | `5.0`        | Seconds between auto-flushes                               |
| `max_queue_size` | `1000`       | Max queued events before oldest is dropped                 |
| `max_retries`    | `3`          | Retry attempts on network failure (exponential back-off)   |
| `async_mode`     | `True`       | Background thread flushing. Set `False`for scripts/tests |

## Event format

Sent to `POST /api/v1/ingest/events/batch` as:

```json
{
  "events": [
    {
      "event_name": "signup",
      "user_id": "user_123",
      "properties": { "plan": "pro" },
      "client_time": "2026-03-27T10:00:00+00:00"
    }
  ]
}
```

Header: `X-API-Key: ep_live_YOUR_KEY`

## Zero dependencies

The core SDK uses Python stdlib only (`urllib`, `threading`, `json`). Framework integrations (`django`, `starlette`) require those packages as extras.
