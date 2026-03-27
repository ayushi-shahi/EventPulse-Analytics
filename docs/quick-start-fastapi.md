# Quick Start — Python (FastAPI)

## Step 1 — Install

```bash
pip install eventpulse-python
```

## Step 2 — Add Middleware

```python
from fastapi import FastAPI
from eventpulse.fastapi import EventPulseMiddleware

app = FastAPI()

app.add_middleware(
    EventPulseMiddleware,
    api_key='ep_live_YOUR_KEY',
    # endpoint='https://eventpulse-analytics-backend.onrender.com'  # optional
)
```

Every request is automatically tracked as a `page_view` event with:

* `url`, `path`, `method`, `status_code`
* `referrer`, `user_agent`

## Step 3 — Manual Tracking in Routes

```python
from fastapi import FastAPI, Depends
from eventpulse import EventPulseClient

app = FastAPI()
ep = EventPulseClient(api_key='ep_live_YOUR_KEY')

@app.post('/checkout')
async def checkout(user_id: str, plan: str):
    ep.identify(user_id)
    ep.track('checkout_started', {'plan': plan, 'amount': 49.99})
    return {'status': 'ok'}
```

## Step 4 — Context Manager (for scripts / tests)

```python
from eventpulse import EventPulseClient

with EventPulseClient(api_key='ep_live_YOUR_KEY') as ep:
    ep.track('script_ran', {'version': '1.0'})
# automatically flushes and shuts down on exit
```

## Configuration Options

```python
ep = EventPulseClient(
    api_key='ep_live_YOUR_KEY',
    endpoint='https://eventpulse-analytics-backend.onrender.com',
    batch_interval=5.0,    # flush every 5 seconds
    max_queue_size=1000,   # drop oldest if queue exceeds this
    max_retries=3,         # retry failed flushes with back-off
    async_mode=True,       # background thread (set False for tests)
)
```

## Verify It's Working

Open your EventPulse dashboard → **Live Feed** — events appear within 5 seconds.
