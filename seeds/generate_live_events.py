"""
EventPulse — rolling demo traffic
=================================

Posts a small batch of realistic events through the public ingestion API so a
demo dashboard keeps showing recent activity between real visits. Designed to
run on a schedule (see .github/workflows/demo-traffic.yml).

Why HTTP rather than writing to the database directly:
  * it exercises the real path — API key auth, validation, Redis queue,
    background processor — so a broken pipeline shows up here first
  * it needs no database credentials in CI, only the ingestion key
  * it wakes the free-tier API, which doubles as a keep-alive

Events are spread across the window *ending now* and carry explicit
`event_time` values, so the series looks continuous instead of arriving as one
spike at the top of the hour.

Event shapes, property distributions and the diurnal weighting are imported
from seed_demo_data rather than restated, so the historical seed and the live
trickle can never drift apart.

Usage:
    EVENTPULSE_API_KEY=ep_live_... python seeds/generate_live_events.py

Environment:
    EVENTPULSE_API_KEY   required — the ingestion key to attribute events to
    EVENTPULSE_ENDPOINT  default https://eventpulse-analytics-backend.onrender.com
    WINDOW_MINUTES       default 60   — spread events across this many minutes
    EVENT_COUNT          default 70   — roughly how many events to send
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone

import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Reuse the taxonomy: same event names, same property pools, same weighting.
from seed_demo_data import Visitor, make_event, traffic_multiplier  # noqa: E402

ENDPOINT = os.environ.get(
    "EVENTPULSE_ENDPOINT", "https://eventpulse-analytics-backend.onrender.com"
).rstrip("/")
API_KEY = os.environ.get("EVENTPULSE_API_KEY", "").strip()
WINDOW_MINUTES = int(os.environ.get("WINDOW_MINUTES", "60"))
EVENT_COUNT = int(os.environ.get("EVENT_COUNT", "70"))

BATCH_LIMIT = 500  # the API accepts up to 1000 per request; stay well under


def build_batch() -> list[dict]:
    """Generate events spread over the window, weighted by time of day."""
    # The historical seeder pins its RNG for reproducibility. Live traffic
    # should differ every run, so reseed from the clock.
    random.seed()

    now = datetime.now(timezone.utc)
    # A small, stable-ish cast of users per run, with a few returning ones, so
    # "active users" moves without every event being a brand-new visitor.
    visitors = [Visitor(random.randint(0, 899)) for _ in range(max(6, EVENT_COUNT // 6))]

    # Scale volume by time of day so nights are quieter than afternoons — a
    # perfectly flat trickle is the giveaway that traffic is generated.
    scale = max(0.35, traffic_multiplier(now))
    count = max(5, int(EVENT_COUNT * scale))

    events: list[dict] = []
    for _ in range(count):
        v = random.choice(visitors)
        ts = now - timedelta(
            seconds=random.randint(0, max(1, WINDOW_MINUTES * 60 - 1))
        )
        name, props = make_event(v, ts)
        events.append(
            {
                "event_name": name,
                "user_id": v.user_id,
                "properties": props,
                "event_time": ts.isoformat().replace("+00:00", "Z"),
            }
        )

    events.sort(key=lambda e: e["event_time"])
    return events


def main() -> int:
    if not API_KEY:
        print("EVENTPULSE_API_KEY is not set", file=sys.stderr)
        return 1

    events = build_batch()
    url = f"{ENDPOINT}/api/v1/ingest/events/batch"
    sent = 0

    # The free-tier API sleeps when idle; the first call may wait for a cold
    # start, so allow a generous timeout rather than failing the schedule.
    with httpx.Client(timeout=120) as client:
        for i in range(0, len(events), BATCH_LIMIT):
            chunk = events[i : i + BATCH_LIMIT]
            r = client.post(
                url,
                headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
                json={"events": chunk},
            )
            if r.status_code not in (200, 202):
                print(f"ingest failed: HTTP {r.status_code} {r.text[:200]}", file=sys.stderr)
                return 1
            sent += len(chunk)

    names: dict[str, int] = {}
    for e in events:
        names[e["event_name"]] = names.get(e["event_name"], 0) + 1
    top = ", ".join(f"{n}={c}" for n, c in sorted(names.items(), key=lambda kv: -kv[1])[:5])

    print(f"sent {sent} events over the last {WINDOW_MINUTES}m -> {ENDPOINT}")
    print(f"  mix: {top}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
