# Quick Start — Python (Django)

## Step 1 — Install

```bash
pip install eventpulse-python
```

## Step 2 — Add Middleware

In `settings.py`:

```python
MIDDLEWARE = [
    # ... your existing middleware ...
    'eventpulse.django.EventPulseMiddleware',
]

EVENTPULSE_API_KEY = 'ep_live_YOUR_KEY'

# Optional — defaults to the production backend
EVENTPULSE_ENDPOINT = 'https://eventpulse-analytics-backend.onrender.com'
```

Every HTTP request is now automatically tracked as a `page_view` event with:

* `url`, `path`, `method`, `status_code`
* `referrer`, `user_agent`
* `user_id` (auto-set for authenticated Django users)

## Step 3 — Manual Tracking in Views

```python
from eventpulse import EventPulseClient

ep = EventPulseClient(api_key='ep_live_YOUR_KEY')

def checkout(request):
    ep.identify(str(request.user.id))
    ep.track('checkout_started', {
        'plan': 'pro',
        'amount': 49.99,
    })
    # ... your view logic
```

> **Tip:** Create the client once as a module-level singleton — it manages its own background thread.

## Step 4 — Shutdown on App Exit (Optional)

For scripts or management commands, call `shutdown()` to flush remaining events:

```python
ep.shutdown()
```

In Django, the middleware's background thread is daemon-managed and flushes automatically.

## Verify It's Working

Open your EventPulse dashboard → **Live Feed** — events appear within 5 seconds.
