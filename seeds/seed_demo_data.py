"""
EventPulse — Demo Data Generator
================================

Populates the platform with events that look like they came from a real B2B
SaaS product, so every dashboard, chart and filter has something meaningful to
show.

Why this shape:
  * 14 distinct event types spanning acquisition -> activation -> revenue ->
    reliability, so funnels and breakdowns are possible rather than just counts
  * every event carries rich properties (device, browser, os, country, plan,
    referrer, utm, path, latency, revenue...) so property-level analysis works
  * traffic follows a real diurnal curve, dips at weekends and trends upward
    over the window — a flat random scatter looks obviously synthetic
  * a burst of events in the last hour so the "Last Hour" period is never empty

API keys are created through the live API rather than inserted directly,
because keys are stored as SHA-256 hashes — generating them any other way
would produce a key that cannot actually authenticate.

Usage:
    python seeds/seed_demo_data.py

Environment:
    EP_API       default https://eventpulse-analytics-backend.onrender.com/api/v1
    EP_EMAIL     account to own the demo keys
    EP_PASSWORD
    DATABASE_URL asyncpg URL for the bulk event insert
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import httpx

API = os.environ.get("EP_API", "https://eventpulse-analytics-backend.onrender.com/api/v1")
EMAIL = os.environ.get("EP_EMAIL", "ayushishahi14072004@gmail.com")
PASSWORD = os.environ.get("EP_PASSWORD", "String@12345")
DB_URL = os.environ.get("DATABASE_URL", "")

# Anchored to the DATABASE clock in main(), never the local one.
#
# The machine running this script can be minutes or hours out of step with the
# database server. Timestamps generated from a skewed local clock land outside
# the window the API queries, so "Last Hour" renders empty even though rows
# exist — which looks like a broken dashboard rather than a clock problem.
NOW = datetime.now(timezone.utc)
DAYS = 30

# Deterministic output so re-running produces a comparable dataset.
random.seed(20260815)


# ── Dimension pools ───────────────────────────────────────────────────────────
def weighted(pairs):
    vals, wts = zip(*pairs)
    return random.choices(vals, weights=wts, k=1)[0]


DEVICES = [("desktop", 62), ("mobile", 31), ("tablet", 7)]
BROWSERS = [("Chrome", 64), ("Safari", 19), ("Firefox", 8), ("Edge", 7), ("Opera", 2)]
OS_BY_DEVICE = {
    "desktop": [("Windows", 58), ("macOS", 31), ("Linux", 11)],
    "mobile": [("Android", 61), ("iOS", 39)],
    "tablet": [("iPadOS", 72), ("Android", 28)],
}
GEO = [
    ("IN", "Mumbai", 26), ("IN", "Bengaluru", 14), ("US", "San Francisco", 12),
    ("US", "New York", 9), ("GB", "London", 8), ("DE", "Berlin", 6),
    ("CA", "Toronto", 5), ("AU", "Sydney", 4), ("SG", "Singapore", 4),
    ("BR", "Sao Paulo", 4), ("NL", "Amsterdam", 3), ("JP", "Tokyo", 3),
    ("FR", "Paris", 2),
]
REFERRERS = [
    ("google.com", 34), ("direct", 26), ("github.com", 11), ("producthunt.com", 8),
    ("twitter.com", 7), ("linkedin.com", 6), ("news.ycombinator.com", 5),
    ("dev.to", 3),
]
UTM_SOURCE = [("google", 30), ("newsletter", 18), ("producthunt", 14), ("twitter", 12),
              ("linkedin", 10), ("none", 16)]
UTM_CAMPAIGN = [("launch_q3", 26), ("docs_seo", 22), ("retargeting", 18),
                ("webinar_aug", 16), ("none", 18)]
PATHS = [
    ("/", 18), ("/pricing", 12), ("/docs", 15), ("/dashboard", 16), ("/projects", 11),
    ("/projects/board", 8), ("/settings", 6), ("/billing", 5), ("/integrations", 5),
    ("/changelog", 4),
]
PLANS = [("free", 54), ("starter", 24), ("pro", 17), ("enterprise", 5)]
PLAN_MRR = {"free": 0, "starter": 29, "pro": 99, "enterprise": 499}
FEATURES = [
    ("board_drag_drop", 18), ("filter_applied", 15), ("comment_added", 13),
    ("doc_linked", 11), ("sprint_started", 9), ("export_csv", 8),
    ("keyboard_shortcut", 8), ("bulk_edit", 7), ("dark_mode_toggle", 6),
    ("integration_connected", 5),
]
ERROR_TYPES = [
    ("ValidationError", 31), ("TimeoutError", 22), ("PermissionDenied", 17),
    ("RateLimited", 12), ("UpstreamUnavailable", 10), ("UnhandledException", 8),
]
ENDPOINTS = [
    ("/api/v1/projects", 22), ("/api/v1/tasks", 28), ("/api/v1/search", 14),
    ("/api/v1/comments", 12), ("/api/v1/auth/login", 10), ("/api/v1/export", 8),
    ("/api/v1/webhooks", 6),
]
CANCEL_REASONS = [("too_expensive", 30), ("missing_features", 24), ("switched_tool", 20),
                  ("no_longer_needed", 16), ("other", 10)]


class Visitor:
    """A stable identity so repeat users, plans and devices stay consistent."""

    def __init__(self, idx: int):
        self.user_id = f"usr_{idx:05d}"
        self.device = weighted(DEVICES)
        self.browser = weighted(BROWSERS)
        self.os = weighted(OS_BY_DEVICE[self.device])
        country, city, _ = random.choices(GEO, weights=[g[2] for g in GEO], k=1)[0]
        self.country, self.city = country, city
        self.referrer = weighted(REFERRERS)
        self.utm_source = weighted(UTM_SOURCE)
        self.utm_campaign = weighted(UTM_CAMPAIGN)
        self.plan = weighted(PLANS)
        self.session_id = f"ses_{random.getrandbits(48):012x}"
        # Power law: a few users generate a lot of the traffic.
        self.weight = max(1, int(random.paretovariate(1.4)))

    def base(self) -> dict:
        return {
            "device": self.device,
            "browser": self.browser,
            "os": self.os,
            "country": self.country,
            "city": self.city,
            "session_id": self.session_id,
        }

    def new_session(self) -> None:
        self.session_id = f"ses_{random.getrandbits(48):012x}"


def traffic_multiplier(ts: datetime) -> float:
    """
    Shape the volume so it reads like real product usage:
    a working-hours hump, quieter weekends, and gentle growth over the window.
    """
    hour = ts.hour
    # Diurnal curve peaking around 14:00 UTC.
    diurnal = 0.25 + 0.75 * max(0.0, math.sin((hour - 3) / 24 * math.pi))
    weekend = 0.55 if ts.weekday() >= 5 else 1.0
    age_days = (NOW - ts).total_seconds() / 86400
    growth = 1.0 - 0.35 * (age_days / DAYS)  # older = quieter
    return diurnal * weekend * growth


def make_event(v: Visitor, ts: datetime) -> tuple[str, dict]:
    """Pick an event type for this visitor and build its properties."""
    name = weighted([
        ("page_view", 34), ("api_request", 16), ("feature_used", 14),
        ("session_start", 9), ("search_performed", 6), ("login", 5),
        ("error_occurred", 4), ("signup_started", 3), ("signup_completed", 2),
        ("checkout_started", 2), ("purchase_completed", 2), ("user_invited", 1),
        ("export_generated", 1), ("subscription_cancelled", 1),
    ])
    p = v.base()
    p["plan"] = v.plan

    if name == "page_view":
        p |= {"path": weighted(PATHS), "referrer": v.referrer,
              "utm_source": v.utm_source, "utm_campaign": v.utm_campaign,
              "load_ms": max(80, int(random.gauss(680, 260)))}
    elif name == "session_start":
        v.new_session()
        p = v.base() | {"plan": v.plan, "referrer": v.referrer,
                        "utm_source": v.utm_source, "is_returning": random.random() < 0.62}
    elif name == "api_request":
        status = weighted([(200, 88), (201, 5), (400, 3), (401, 2), (429, 1), (500, 1)])
        p |= {"endpoint": weighted(ENDPOINTS),
              "method": weighted([("GET", 72), ("POST", 20), ("PATCH", 5), ("DELETE", 3)]),
              "status_code": status,
              "latency_ms": max(4, int(random.lognormvariate(3.9, 0.7)))}
    elif name == "feature_used":
        p |= {"feature": weighted(FEATURES),
              "surface": weighted([("board", 38), ("backlog", 22), ("wiki", 20),
                                   ("settings", 12), ("search", 8)])}
    elif name == "search_performed":
        p |= {"query_length": random.randint(2, 28),
              "results": weighted([(0, 12), (1, 18), (5, 34), (20, 26), (100, 10)]),
              "surface": weighted([("command_palette", 64), ("search_page", 36)])}
    elif name == "login":
        p |= {"method": weighted([("password", 68), ("google", 32)]),
              "is_first_login_today": random.random() < 0.4}
    elif name == "error_occurred":
        p |= {"error_type": weighted(ERROR_TYPES),
              "severity": weighted([("warning", 58), ("error", 34), ("critical", 8)]),
              "path": weighted(PATHS),
              "status_code": weighted([(400, 34), (403, 20), (429, 16), (500, 20), (503, 10)])}
    elif name == "signup_started":
        p |= {"plan_intent": weighted(PLANS), "utm_source": v.utm_source,
              "referrer": v.referrer}
    elif name == "signup_completed":
        p |= {"plan": v.plan, "utm_source": v.utm_source,
              "utm_campaign": v.utm_campaign, "referrer": v.referrer,
              "seconds_to_complete": random.randint(35, 420)}
    elif name == "checkout_started":
        plan = weighted([("starter", 44), ("pro", 40), ("enterprise", 16)])
        seats = random.randint(1, 25)
        p |= {"plan": plan, "seats": seats, "mrr": PLAN_MRR[plan] * seats,
              "currency": "USD", "billing_period": weighted([("monthly", 68), ("annual", 32)])}
    elif name == "purchase_completed":
        plan = weighted([("starter", 46), ("pro", 39), ("enterprise", 15)])
        seats = random.randint(1, 25)
        period = weighted([("monthly", 66), ("annual", 34)])
        mrr = PLAN_MRR[plan] * seats
        p |= {"plan": plan, "seats": seats, "currency": "USD",
              "billing_period": period,
              "revenue": round(mrr * (10 if period == "annual" else 1), 2),
              "payment_method": weighted([("card", 82), ("upi", 11), ("invoice", 7)])}
    elif name == "user_invited":
        p |= {"role": weighted([("member", 62), ("admin", 26), ("viewer", 12)]),
              "seats_after": random.randint(2, 30)}
    elif name == "export_generated":
        p |= {"format": weighted([("csv", 58), ("pdf", 27), ("json", 15)]),
              "rows": random.randint(20, 5000),
              "duration_ms": random.randint(120, 9000)}
    elif name == "subscription_cancelled":
        p |= {"reason": weighted(CANCEL_REASONS),
              "tenure_days": random.randint(14, 700),
              "mrr_lost": PLAN_MRR[v.plan] * random.randint(1, 12)}

    return name, p


def build_events(client_id: str, visitors: list[Visitor], target: int) -> list[tuple]:
    """Generate `target` rows shaped over the last DAYS days."""
    # Pre-compute a per-hour weight curve, then distribute events across it.
    hours = [NOW - timedelta(hours=h) for h in range(DAYS * 24)]
    weights = [traffic_multiplier(t) for t in hours]
    total_w = sum(weights)

    pool = []
    for v in visitors:
        pool.extend([v] * v.weight)

    rows: list[tuple] = []
    for hour_ts, w in zip(hours, weights):
        n = int(round(target * (w / total_w)))
        for _ in range(n):
            v = random.choice(pool)
            ts = hour_ts - timedelta(seconds=random.randint(0, 3599))
            name, props = make_event(v, ts)
            received = ts + timedelta(milliseconds=random.randint(30, 1500))
            rows.append((client_id, v.user_id, name, props, ts, received))

    # Guarantee the "Last Hour" view is populated.
    for _ in range(max(60, target // 400)):
        v = random.choice(pool)
        ts = NOW - timedelta(seconds=random.randint(30, 3500))
        name, props = make_event(v, ts)
        rows.append((client_id, v.user_id, name, props, ts,
                     ts + timedelta(milliseconds=random.randint(30, 900))))

    rows.sort(key=lambda r: r[4])
    return rows


async def get_token(client: httpx.AsyncClient) -> str:
    r = await client.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        # First run against a fresh database: create the account.
        reg = await client.post(f"{API}/auth/register", json={
            "email": EMAIL, "password": PASSWORD, "full_name": "Ayushi Shahi"})
        if reg.status_code not in (200, 201):
            sys.exit(f"cannot register or log in: {reg.status_code} {reg.text[:200]}")
        r = await client.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return r.json()["access_token"]


async def ensure_key(client: httpx.AsyncClient, token: str, name: str) -> tuple[str, str]:
    """Return (api_key_id, plaintext_key), creating the key if needed."""
    h = {"Authorization": f"Bearer {token}"}
    existing = (await client.get(f"{API}/api-keys/", headers=h)).json()
    items = existing if isinstance(existing, list) else existing.get("items", [])
    for k in items:
        if k.get("client_name") == name:
            return k["id"], ""
    r = await client.post(f"{API}/api-keys/", headers=h, json={"client_name": name})
    if r.status_code not in (200, 201):
        sys.exit(f"could not create key {name}: {r.status_code} {r.text[:200]}")
    d = r.json()
    return d["id"], d.get("key") or d.get("api_key") or ""


async def main() -> None:
    if not DB_URL:
        sys.exit("DATABASE_URL is required")

    print(f"\nSeeding EventPulse demo data -> {API}\n")

    # Imported here, not at module scope: generate_live_events.py reuses this
    # module purely for the event taxonomy and talks to the API over HTTP, so
    # requiring a database driver would make the scheduled job install (and
    # fail on) a dependency it never uses.
    import asyncpg

    dsn = DB_URL.replace("postgresql+asyncpg://", "postgresql://").split("?")[0]
    conn = await asyncpg.connect(dsn, ssl="require")
    # COPY streams in binary, so a text codec is never consulted. jsonb's binary
    # wire format is a single version byte (always 1) followed by the JSON text.
    await conn.set_type_codec(
        "jsonb",
        encoder=lambda v: b"\x01" + json.dumps(v, separators=(",", ":")).encode(),
        decoder=lambda b: json.loads(b[1:].decode()),
        schema="pg_catalog",
        format="binary",
    )

    # Pin every generated timestamp to the database's clock, not this machine's.
    global NOW
    db_now = await conn.fetchval("SELECT now()")
    skew_min = (db_now - NOW).total_seconds() / 60
    NOW = db_now
    if abs(skew_min) > 2:
        print(f"  clock skew   : local is {skew_min:+.0f} min off the DB; using DB time")

    async with httpx.AsyncClient(timeout=120) as client:
        token = await get_token(client)
        prod_id, prod_key = await ensure_key(client, token, "Production Web App")
        stg_id, stg_key = await ensure_key(client, token, "Staging")
    print(f"  api keys: Production Web App ({prod_id[:8]}…), Staging ({stg_id[:8]}…)")

    visitors = [Visitor(i) for i in range(900)]
    prod_rows = build_events(prod_id, visitors, 42000)
    stg_rows = build_events(stg_id, visitors[:120], 3500)
    print(f"  generated: {len(prod_rows):,} production + {len(stg_rows):,} staging events")

    try:
        await conn.execute("DELETE FROM events WHERE client_id = ANY($1::uuid[])",
                           [prod_id, stg_id])
        for label, rows in (("production", prod_rows), ("staging", stg_rows)):
            await conn.copy_records_to_table(
                "events",
                records=rows,
                columns=["client_id", "user_id", "event_name", "properties",
                         "event_time", "received_at"],
            )
            print(f"  inserted {label}: {len(rows):,}")

        await seed_aggregates(conn, [prod_id, stg_id])
        await seed_alerts(conn, prod_id)

        total = await conn.fetchval("SELECT count(*) FROM events")
        names = await conn.fetch(
            "SELECT event_name, count(*) c FROM events GROUP BY 1 ORDER BY c DESC")
        users = await conn.fetchval("SELECT count(DISTINCT user_id) FROM events")
        last_hour = await conn.fetchval(
            "SELECT count(*) FROM events WHERE event_time > now() - interval '1 hour'")
    finally:
        await conn.close()

    print(f"\n  events total : {total:,}")
    print(f"  unique users : {users:,}")
    print(f"  last hour    : {last_hour:,}")
    print("  event types  :")
    for r in names:
        print(f"    {r['event_name']:<24} {r['c']:>7,}")
    if prod_key:
        print(f"\n  production key (shown once): {prod_key}")
    if stg_key:
        print(f"  staging key    (shown once): {stg_key}")
    print()


async def seed_alerts(conn, client_id: str) -> None:
    """A few alerts, one of which has fired, so Alert History is not empty."""
    await conn.execute("DELETE FROM alert_history WHERE client_id = $1::uuid", client_id)
    await conn.execute("DELETE FROM alerts WHERE client_id = $1::uuid", client_id)

    # `expression` is a structured AlertExpression, not a free-text rule:
    # {metric, operator, threshold, window}. A string here passes the insert but
    # fails response validation with a 500 on every list request.
    specs = [
        ("Traffic spike", "Ingestion rate well above the normal baseline.",
         {"metric": "events_per_minute", "operator": ">", "threshold": 120.0, "window": "1m"},
         "warning", True, 3),
        ("Ingestion stalled", "Almost no events arriving — likely a broken SDK or outage.",
         {"metric": "events_per_minute", "operator": "<", "threshold": 1.0, "window": "5m"},
         "critical", True, 1),
        ("Active user surge", "Unusually high concurrent usage.",
         {"metric": "active_users_1h", "operator": ">", "threshold": 750.0, "window": "1h"},
         "info", True, 0),
        ("Sustained heavy load", "Hourly volume above the plan's comfortable ceiling.",
         {"metric": "events_per_hour", "operator": ">", "threshold": 5000.0, "window": "1h"},
         "error", False, 0),
    ]
    for name, desc, expr, sev, enabled, fired in specs:
        row = await conn.fetchrow(
            """INSERT INTO alerts (id, client_id, name, description, expression, severity,
                                   enabled, trigger_count, cooldown_seconds, notification_channels,
                                   last_triggered, created_at, updated_at)
               VALUES (gen_random_uuid(), $1::uuid, $2, $3, $4, $5, $6, $7, 300, $8,
                       $9, now(), now())
               RETURNING id""",
            client_id, name, desc, expr, sev, enabled, fired,
            # JSONB column: hand asyncpg the dict itself. Passing json.dumps(...)
            # here would be double-encoded by the jsonb codec into a JSON *string*,
            # and the API then fails to read it as an object.
            {"websocket": True, "email": ["alerts@example.com"]},
            (NOW - timedelta(hours=5)) if fired else None,
        )
        for i in range(fired):
            await conn.execute(
                """INSERT INTO alert_history (id, alert_id, client_id, triggered_at, severity,
                                              message, context, notification_sent,
                                              created_at, updated_at)
                   VALUES (gen_random_uuid(), $1::uuid, $2::uuid, $3, $4, $5, $6, true,
                           now(), now())""",
                row["id"], client_id, NOW - timedelta(hours=5 + i * 7), sev,
                f"{name}: threshold exceeded",
                {"observed": 50 + i * 17, "threshold": 50},
            )
    print("  alerts: 4 (1 firing history)")


async def seed_aggregates(conn, client_ids: list[str]) -> None:
    """
    Build the aggregates that power the time-series charts.

    Computed FROM the events just inserted rather than invented, so the chart
    and the event counts always agree. Per-minute series covers the last 6
    hours (what the dashboard shows); per-hour covers the full 30 days.
    """
    specs = [
        ("events_per_minute", "minute", "6 hours", "count(*)::float"),
        ("events_per_hour", "hour", "30 days", "count(*)::float"),
        ("active_users_1m", "minute", "6 hours", "count(DISTINCT user_id)::float"),
        ("active_users_1h", "hour", "30 days", "count(DISTINCT user_id)::float"),
    ]
    await conn.execute("DELETE FROM aggregates WHERE client_id = ANY($1::uuid[])", client_ids)

    total = 0
    for metric, unit, window, agg in specs:
        result = await conn.execute(
            f"""
            INSERT INTO aggregates (id, client_id, metric_name, interval_start,
                                    interval_end, value, meta_data, created_at, updated_at)
            SELECT gen_random_uuid(), client_id, '{metric}',
                   date_trunc('{unit}', event_time),
                   date_trunc('{unit}', event_time) + interval '1 {unit}',
                   {agg}, NULL, now(), now()
            FROM events
            WHERE client_id = ANY($1::uuid[])
              AND event_time > now() - interval '{window}'
            GROUP BY client_id, date_trunc('{unit}', event_time)
            ON CONFLICT (client_id, metric_name, interval_start)
            DO UPDATE SET value = EXCLUDED.value
            """,
            client_ids,
        )
        n = int(result.split()[-1]) if result and result.split()[-1].isdigit() else 0
        total += n
        print(f"  aggregate {metric:<18} {n:>5} intervals")
    print(f"  aggregates total: {total:,}")


if __name__ == "__main__":
    asyncio.run(main())
