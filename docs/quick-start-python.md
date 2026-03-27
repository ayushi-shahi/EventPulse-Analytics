# Quick Start — Python (Script)

## Step 1 — Install

```bash
pip install eventpulse-python
```

## Step 2 — Initialize the Client

```python
from eventpulse import EventPulseClient

ep = EventPulseClient(api_key='ep_live_YOUR_KEY')
```

## Step 3 — Track Events

```python
# Associate a user
ep.identify('user_123')

# Track a custom event
ep.track('export_started', {
    'format': 'csv',
    'rows': 1500,
})
```

## Step 4 — Flush and Shutdown

Always call `shutdown()` at the end of your script to flush remaining events:

```python
ep.shutdown()
```

Or use the context manager — it flushes automatically on exit:

```python
with EventPulseClient(api_key='ep_live_YOUR_KEY') as ep:
    ep.identify('user_123')
    ep.track('script_ran', {'version': '1.0'})
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
