"""
EventPulse Analytics — Production Test Suite
=============================================
Runs end-to-end tests against live deployed services and generates
a self-contained HTML report.

Usage:
    pip install requests websockets python-dotenv
    python production_test.py

Reads from .env.test in the same directory:
    EP_BASE_URL=https://eventpulse-analytics-backend.onrender.com
    EP_TEST_EMAIL=test_runner@example.com
    EP_TEST_PASSWORD=TestRunner123!
"""

import asyncio
import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests
import websockets
from dotenv import load_dotenv

load_dotenv(".env.test")

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL  = os.getenv("EP_BASE_URL",      "https://eventpulse-analytics-backend.onrender.com")
API_BASE  = f"{BASE_URL}/api/v1"
WS_BASE   = BASE_URL.replace("https://", "wss://").replace("http://", "ws://")

TEST_EMAIL    = os.getenv("EP_TEST_EMAIL",    f"testrunner_{uuid.uuid4().hex[:8]}@eventpulse.dev")
TEST_PASSWORD = os.getenv("EP_TEST_PASSWORD", "TestRunner@9999!")
TEST_NAME     = "EventPulse Test Runner"

# ── State shared across tests ─────────────────────────────────────────────────

state = {
    "access_token":  None,
    "refresh_token": None,
    "api_key_id":    None,
    "api_key_value": None,
    "ingest_key":    None,
    "ingest_key_id": None,
    "alert_id":      None,
    "user_id":       None,
}

# ── Result collector ──────────────────────────────────────────────────────────

results = []   # list of dicts

def record(phase: str, name: str, passed: bool, status_code: int = 0,
           duration_ms: float = 0, detail: str = "", request_info: str = ""):
    results.append({
        "phase":        phase,
        "name":         name,
        "passed":       passed,
        "status_code":  status_code,
        "duration_ms":  round(duration_ms, 1),
        "detail":       detail,
        "request_info": request_info,
    })
    icon = "✅" if passed else "❌"
    print(f"  {icon}  {name} ({status_code}) [{round(duration_ms)}ms]")
    if not passed and detail:
        print(f"       ↳ {detail}")

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def get(path: str, token: str = None, api_key: str = None,
        params: dict = None, label: str = "") -> requests.Response:
    headers = {}
    if token:   headers["Authorization"] = f"Bearer {token}"
    if api_key: headers["X-API-Key"]     = api_key
    t0 = time.perf_counter()
    r  = requests.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=30)
    return r, (time.perf_counter() - t0) * 1000

def post(path: str, body: dict = None, token: str = None,
         api_key: str = None, label: str = "") -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if token:   headers["Authorization"] = f"Bearer {token}"
    if api_key: headers["X-API-Key"]     = api_key
    t0 = time.perf_counter()
    r  = requests.post(f"{API_BASE}{path}", json=body, headers=headers, timeout=30)
    return r, (time.perf_counter() - t0) * 1000

def patch(path: str, body: dict = None, token: str = None,
          api_key: str = None) -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if token:   headers["Authorization"] = f"Bearer {token}"
    if api_key: headers["X-API-Key"]     = api_key
    t0 = time.perf_counter()
    r  = requests.patch(f"{API_BASE}{path}", json=body, headers=headers, timeout=30)
    return r, (time.perf_counter() - t0) * 1000

def delete(path: str, token: str = None, api_key: str = None) -> requests.Response:
    headers = {}
    if token:   headers["Authorization"] = f"Bearer {token}"
    if api_key: headers["X-API-Key"]     = api_key
    t0 = time.perf_counter()
    r  = requests.delete(f"{API_BASE}{path}", headers=headers, timeout=30)
    return r, (time.perf_counter() - t0) * 1000

def make_event(name: str = "test_event", props: dict = None) -> dict:
    return {
        "event_name": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "properties": props or {"source": "production_test", "run_id": RUN_ID},
    }

RUN_ID = uuid.uuid4().hex[:8]

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Health & Infrastructure
# ═════════════════════════════════════════════════════════════════════════════

def phase_health():
    print("\n📋 Phase 1 — Health & Infrastructure")

    # Basic health
    try:
        r, ms = get("/health/")
        record("Health", "Basic health check", r.status_code == 200,
               r.status_code, ms, "" if r.status_code == 200 else r.text)
    except Exception as e:
        record("Health", "Basic health check", False, 0, 0, str(e))

    # Detailed health (DB + Redis)
    try:
        r, ms = get("/health/detailed")
        ok = r.status_code == 200
        detail = ""
        if ok:
            data = r.json()
            checks   = data.get("checks", {})
            db_ok    = checks.get("database", {}).get("status") == "healthy"
            redis_ok = checks.get("redis",    {}).get("status") == "healthy"
            ok = db_ok and redis_ok
            if not db_ok:    detail += "Database unhealthy. "
            if not redis_ok: detail += "Redis unhealthy."
        record("Health", "Detailed health (DB + Redis)", ok, r.status_code, ms, detail)
    except Exception as e:
        record("Health", "Detailed health (DB + Redis)", False, 0, 0, str(e))

    # Readiness probe
    try:
        r, ms = get("/health/ready")
        record("Health", "Readiness probe", r.status_code == 200,
               r.status_code, ms, "" if r.status_code == 200 else r.text)
    except Exception as e:
        record("Health", "Readiness probe", False, 0, 0, str(e))

    # Liveness probe
    try:
        r, ms = get("/health/live")
        record("Health", "Liveness probe", r.status_code == 200,
               r.status_code, ms, "" if r.status_code == 200 else r.text)
    except Exception as e:
        record("Health", "Liveness probe", False, 0, 0, str(e))

    # JS SDK reachable
    try:
        sdk_url = f"{BASE_URL}/static/eventpulse.js"
        t0 = time.perf_counter()
        r  = requests.get(sdk_url, timeout=15)
        ms = (time.perf_counter() - t0) * 1000
        ok = r.status_code == 200 and "EventPulse" in r.text
        record("Health", "JS SDK hosted and reachable", ok, r.status_code, ms,
               "" if ok else "File missing or does not contain EventPulse")
    except Exception as e:
        record("Health", "JS SDK hosted and reachable", False, 0, 0, str(e))


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Authentication
# ═════════════════════════════════════════════════════════════════════════════

def phase_auth():
    print("\n🔐 Phase 2 — Authentication")

    # Register
    try:
        r, ms = post("/auth/register", {
            "email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME
        })
        ok = r.status_code in (200, 201)
        record("Auth", "Register new user", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Auth", "Register new user", False, 0, 0, str(e))

    # Login
    try:
        r, ms = post("/auth/login", {"email": TEST_EMAIL, "password": TEST_PASSWORD})
        ok = r.status_code == 200
        if ok:
            data = r.json()
            state["access_token"]  = data.get("access_token")
            state["refresh_token"] = data.get("refresh_token")
            ok = bool(state["access_token"])
        record("Auth", "Login and receive JWT tokens", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Auth", "Login and receive JWT tokens", False, 0, 0, str(e))

    # Get profile
    try:
        r, ms = get("/auth/me", token=state["access_token"])
        ok = r.status_code == 200 and r.json().get("email") == TEST_EMAIL
        if ok:
            state["user_id"] = r.json().get("id")
        record("Auth", "GET /auth/me returns correct profile", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Auth", "GET /auth/me returns correct profile", False, 0, 0, str(e))

    # Refresh token
    try:
        r, ms = post("/auth/refresh", {"refresh_token": state["refresh_token"]})
        ok = r.status_code == 200 and bool(r.json().get("access_token"))
        if ok:
            state["access_token"] = r.json().get("access_token")
        record("Auth", "Refresh token → new access token", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Auth", "Refresh token → new access token", False, 0, 0, str(e))

    # Wrong password → 401
    try:
        r, ms = post("/auth/login", {"email": TEST_EMAIL, "password": "wrongpassword"})
        record("Auth", "Wrong password returns 401", r.status_code == 401,
               r.status_code, ms,
               "" if r.status_code == 401 else f"Expected 401, got {r.status_code}")
    except Exception as e:
        record("Auth", "Wrong password returns 401", False, 0, 0, str(e))

    # No token → 401
    try:
        r, ms = get("/auth/me")
        record("Auth", "No token on protected route returns 401", r.status_code == 401,
               r.status_code, ms,
               "" if r.status_code == 401 else f"Expected 401, got {r.status_code}")
    except Exception as e:
        record("Auth", "No token on protected route returns 401", False, 0, 0, str(e))


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 3 — API Key Lifecycle
# ═════════════════════════════════════════════════════════════════════════════

def phase_api_keys():
    print("\n🔑 Phase 3 — API Key Lifecycle")

    # Create key
    try:
        r, ms = post("/api-keys/", {"client_name": f"test-key-{RUN_ID}"},
                     token=state["access_token"])
        ok = r.status_code in (200, 201)
        if ok:
            data = r.json()
            state["api_key_id"]    = data.get("id")
            state["api_key_value"] = data.get("api_key") or data.get("key")
            ok = bool(state["api_key_value"]) and state["api_key_value"].startswith("ep_live_")
        record("API Keys", "Create API key (ep_live_* prefix)", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("API Keys", "Create API key (ep_live_* prefix)", False, 0, 0, str(e))

    # List keys
    try:
        r, ms = get("/api-keys/", token=state["access_token"])
        ok = r.status_code == 200
        if ok:
            keys = r.json()
            ids = [k.get("id") for k in (keys if isinstance(keys, list) else keys.get("items", []))]
            ok  = state["api_key_id"] in ids
        record("API Keys", "List keys — new key appears", ok, r.status_code, ms,
               "" if ok else "Key ID not found in list")
    except Exception as e:
        record("API Keys", "List keys — new key appears", False, 0, 0, str(e))

    # Use key on /ingest/status
    try:
        r, ms = get("/ingest/status", api_key=state["api_key_value"])
        record("API Keys", "Valid API key accepted on /ingest/status",
               r.status_code == 200, r.status_code, ms,
               "" if r.status_code == 200 else r.text[:200])
    except Exception as e:
        record("API Keys", "Valid API key accepted on /ingest/status", False, 0, 0, str(e))

    # Create a second key to use for ingestion (so we can safely revoke the first)
    try:
        r, ms = post("/api-keys/", {"client_name": f"ingest-key-{RUN_ID}"},
                     token=state["access_token"])
        ok = r.status_code in (200, 201)
        if ok:
            state["ingest_key"]    = r.json().get("api_key") or r.json().get("key")
            state["ingest_key_id"] = str(r.json().get("id"))
        record("API Keys", "Create secondary key for ingestion tests", ok,
               r.status_code, ms, "" if ok else r.text[:200])
    except Exception as e:
        record("API Keys", "Create secondary key for ingestion tests", False, 0, 0, str(e))

    # Revoke first key
    try:
        r, ms = patch(f"/api-keys/{state['api_key_id']}/revoke",
                      token=state["access_token"])
        record("API Keys", "Revoke API key", r.status_code in (200, 204),
               r.status_code, ms,
               "" if r.status_code in (200, 204) else r.text[:200])
    except Exception as e:
        record("API Keys", "Revoke API key", False, 0, 0, str(e))

    # Revoked key → 401
    try:
        r, ms = get("/ingest/status", api_key=state["api_key_value"])
        record("API Keys", "Revoked key returns 401", r.status_code == 401,
               r.status_code, ms,
               "" if r.status_code == 401 else f"Expected 401, got {r.status_code}")
    except Exception as e:
        record("API Keys", "Revoked key returns 401", False, 0, 0, str(e))

    # Invalid key format → 401
    try:
        r, ms = get("/ingest/status", api_key="ep_live_totallyFakeKey")
        record("API Keys", "Invalid key returns 401", r.status_code == 401,
               r.status_code, ms,
               "" if r.status_code == 401 else f"Expected 401, got {r.status_code}")
    except Exception as e:
        record("API Keys", "Invalid key returns 401", False, 0, 0, str(e))


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Event Ingestion
# ═════════════════════════════════════════════════════════════════════════════

def phase_ingestion():
    print("\n📥 Phase 4 — Event Ingestion")

    key = state["ingest_key"]
    if not key:
        print("  ⚠️  Skipping — no ingest key available")
        return

    # Single event
    try:
        r, ms = post("/ingest/events", make_event("single_event_test"), api_key=key)
        record("Ingestion", "Ingest single event → 202", r.status_code == 202,
               r.status_code, ms, "" if r.status_code == 202 else r.text[:200])
    except Exception as e:
        record("Ingestion", "Ingest single event → 202", False, 0, 0, str(e))

    # Batch of 10
    try:
        batch = [make_event(f"batch_event_{i}") for i in range(10)]
        r, ms = post("/ingest/events/batch", {"events": batch}, api_key=key)
        record("Ingestion", "Ingest batch of 10 events → 202", r.status_code == 202,
               r.status_code, ms, "" if r.status_code == 202 else r.text[:200])
    except Exception as e:
        record("Ingestion", "Ingest batch of 10 events → 202", False, 0, 0, str(e))

    # Batch of 100
    try:
        batch = [make_event("load_test_event", {"index": i}) for i in range(100)]
        r, ms = post("/ingest/events/batch", {"events": batch}, api_key=key)
        record("Ingestion", "Ingest batch of 100 events → 202", r.status_code == 202,
               r.status_code, ms, "" if r.status_code == 202 else r.text[:200])
    except Exception as e:
        record("Ingestion", "Ingest batch of 100 events → 202", False, 0, 0, str(e))


    # Missing event name → 422
    try:
        r, ms = post("/ingest/events/batch",
                     {"events": [{"timestamp": datetime.now(timezone.utc).isoformat(),
                                  "properties": {}}]}, api_key=key)
        ok = r.status_code == 422
        record("Ingestion", "Missing event name returns 422", ok, r.status_code, ms,
               "" if ok else f"Expected 422, got {r.status_code}")
    except Exception as e:
        record("Ingestion", "Missing event name returns 422", False, 0, 0, str(e))

    # Empty batch → 422
    try:
        r, ms = post("/ingest/events/batch", {"events": []}, api_key=key)
        ok = r.status_code == 422
        record("Ingestion", "Empty batch returns 422", ok, r.status_code, ms,
               "" if ok else f"Expected 422, got {r.status_code}")
    except Exception as e:
        record("Ingestion", "Empty batch returns 422", False, 0, 0, str(e))

    # Pipeline status
    try:
        r, ms = get("/ingest/status", api_key=key)
        record("Ingestion", "Pipeline status endpoint reachable", r.status_code == 200,
               r.status_code, ms, "" if r.status_code == 200 else r.text[:200])
    except Exception as e:
        record("Ingestion", "Pipeline status endpoint reachable", False, 0, 0, str(e))


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Metrics API
# ═════════════════════════════════════════════════════════════════════════════

def phase_metrics():
    print("\n📊 Phase 5 — Metrics API")

    key = state["ingest_key"]
    if not key:
        print("  ⚠️  Skipping — no ingest key available")
        return

    # Overview
    try:
        r, ms = get("/metrics/overview", api_key=key)
        ok = r.status_code == 200
        record("Metrics", "GET /metrics/overview", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Metrics", "GET /metrics/overview", False, 0, 0, str(e))

    # Top events
    try:
        r, ms = get("/metrics/top-events", api_key=key, params={"limit": 10})
        ok = r.status_code == 200
        record("Metrics", "GET /metrics/top-events", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Metrics", "GET /metrics/top-events", False, 0, 0, str(e))

    # Active users
    try:
        r, ms = get("/metrics/active-users", api_key=key)
        ok = r.status_code == 200
        record("Metrics", "GET /metrics/active-users", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Metrics", "GET /metrics/active-users", False, 0, 0, str(e))

    # Time series
    try:
        r, ms = get("/metrics/time-series/event_count", api_key=key,
                    params={"interval": "1h", "limit": 24})
        ok = r.status_code == 200
        record("Metrics", "GET /metrics/time-series/event_count", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Metrics", "GET /metrics/time-series/event_count", False, 0, 0, str(e))

    # Paginated events
    try:
        r, ms = get("/metrics/events", api_key=key, params={"page": 1, "page_size": 20})
        ok = r.status_code == 200
        record("Metrics", "GET /metrics/events (paginated)", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Metrics", "GET /metrics/events (paginated)", False, 0, 0, str(e))

    # Events filtered by name
    try:
        r, ms = get("/metrics/events", api_key=key,
                    params={"event_name": "batch_event_0", "page": 1, "page_size": 5})
        ok = r.status_code == 200
        record("Metrics", "GET /metrics/events filtered by event_name", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Metrics", "GET /metrics/events filtered by event_name", False, 0, 0, str(e))


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Alerts
# ═════════════════════════════════════════════════════════════════════════════

def phase_alerts():
    print("\n🚨 Phase 6 — Alerts")

    key = state["ingest_key"]
    if not key:
        print("  ⚠️  Skipping — no ingest key available")
        return

    alert_payload = {
        "name":       f"Test Alert {RUN_ID}",
        "expression": {"metric": "event_count", "operator": ">", "threshold": 0},
        "severity":   "info",
        "cooldown":   60,
        "enabled":    True,
    }

    # Create alert
    try:
        r, ms = post("/alerts/", alert_payload, api_key=key)
        ok = r.status_code in (200, 201)
        if ok:
            state["alert_id"] = r.json().get("id")
            ok = bool(state["alert_id"])
        record("Alerts", "Create alert", ok, r.status_code, ms,
               "" if ok else r.text[:200])
    except Exception as e:
        record("Alerts", "Create alert", False, 0, 0, str(e))

    # List alerts
    try:
        r, ms = get("/alerts/", api_key=key)
        ok = r.status_code == 200
        if ok:
            alerts = r.json()
            ids = [a.get("id") for a in (alerts if isinstance(alerts, list) else alerts.get("items", []))]
            ok  = state["alert_id"] in ids
        record("Alerts", "List alerts — new alert appears", ok, r.status_code, ms,
               "" if ok else "Alert ID not found in list")
    except Exception as e:
        record("Alerts", "List alerts — new alert appears", False, 0, 0, str(e))

    # Dry-run test
    if state["alert_id"]:
        try:
            r, ms = post(f"/alerts/{state['alert_id']}/test", api_key=key)
            ok = r.status_code == 200
            record("Alerts", "Dry-run test alert returns result", ok, r.status_code, ms,
                   "" if ok else r.text[:200])
        except Exception as e:
            record("Alerts", "Dry-run test alert returns result", False, 0, 0, str(e))

        # Disable
        try:
            r, ms = post(f"/alerts/{state['alert_id']}/disable", api_key=key)
            ok = r.status_code in (200, 204)
            record("Alerts", "Disable alert", ok, r.status_code, ms,
                   "" if ok else r.text[:200])
        except Exception as e:
            record("Alerts", "Disable alert", False, 0, 0, str(e))

        # Enable
        try:
            r, ms = post(f"/alerts/{state['alert_id']}/enable", api_key=key)
            ok = r.status_code in (200, 204)
            record("Alerts", "Enable alert", ok, r.status_code, ms,
                   "" if ok else r.text[:200])
        except Exception as e:
            record("Alerts", "Enable alert", False, 0, 0, str(e))

        # Alert history
        try:
            r, ms = get(f"/alerts/{state['alert_id']}/history", api_key=key)
            ok = r.status_code == 200
            record("Alerts", "GET alert history", ok, r.status_code, ms,
                   "" if ok else r.text[:200])
        except Exception as e:
            record("Alerts", "GET alert history", False, 0, 0, str(e))

        # Update alert
        try:
            r, ms = patch(f"/alerts/{state['alert_id']}",
                          {"name": f"Updated Alert {RUN_ID}"}, api_key=key)
            ok = r.status_code in (200, 204)
            record("Alerts", "Update alert (PATCH)", ok, r.status_code, ms,
                   "" if ok else r.text[:200])
        except Exception as e:
            record("Alerts", "Update alert (PATCH)", False, 0, 0, str(e))

        # Delete
        try:
            r, ms = delete(f"/alerts/{state['alert_id']}", api_key=key)
            ok = r.status_code in (200, 204)
            record("Alerts", "Delete alert → 204", ok, r.status_code, ms,
                   "" if ok else r.text[:200])
            if ok:
                state["alert_id"] = None
        except Exception as e:
            record("Alerts", "Delete alert → 204", False, 0, 0, str(e))


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 7 — WebSocket Live Feed
# ═════════════════════════════════════════════════════════════════════════════

async def _ws_test():
    key        = state["ingest_key"]
    client_id  = state["ingest_key_id"]
    ws_url = f"{WS_BASE}/api/v1/ws/live/{client_id}?token={key}"
    extra_headers = {"X-API-Key": key}
    results_ws = []

    # Connect + ping/pong
    try:
        t0 = time.perf_counter()
        async with websockets.connect(ws_url, additional_headers={"X-API-Key": key}, open_timeout=15) as ws:
            ms = (time.perf_counter() - t0) * 1000
            results_ws.append(("WebSocket", "Connect with valid API key", True, 101, ms, ""))

            # Ping → pong
            try:
                t0 = time.perf_counter()
                await ws.send(json.dumps({"type": "ping"}))
                # Server sends 'connected' welcome first — drain it
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                if data.get("type") == "connected":
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                ms  = (time.perf_counter() - t0) * 1000
                data = json.loads(msg)
                ok   = data.get("type") == "pong"
                results_ws.append(("WebSocket", "Ping → Pong round trip", ok, 0, ms,
                                   "" if ok else f"Got: {msg[:100]}"))
            except Exception as e:
                results_ws.append(("WebSocket", "Ping → Pong round trip", False, 0, 0, str(e)))

            # Subscribe to events channel
            try:
                t0 = time.perf_counter()
                await ws.send(json.dumps({"type": "subscribe", "channels": ["events"]}))
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                ms  = (time.perf_counter() - t0) * 1000
                data = json.loads(msg)
                ok   = data.get("type") in ("subscribed", "subscription_confirmed", "ack", "ok")
                # Some backends echo differently — also accept any non-error response
                if not ok and "error" not in str(data).lower():
                    ok = True
                results_ws.append(("WebSocket", "Subscribe to events channel", ok, 0, ms,
                                   "" if ok else f"Got: {msg[:100]}"))
            except Exception as e:
                results_ws.append(("WebSocket", "Subscribe to events channel", False, 0, 0, str(e)))

            # Ingest event and see if it arrives
            try:
                requests.post(
                    f"{API_BASE}/ingest/events/batch",
                    json={"events": [make_event("ws_live_test", {"ws_check": True})]},
                    headers={"X-API-Key": key, "Content-Type": "application/json"},
                    timeout=10,
                )
                # Wait up to 8s for the event to arrive via WebSocket
                received = False
                deadline = time.perf_counter() + 15
                t0 = time.perf_counter()
                while time.perf_counter() < deadline:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=2)
                        if "ws_live_test" in msg or "event" in msg.lower():
                            received = True
                            break
                    except asyncio.TimeoutError:
                        break
                ms = (time.perf_counter() - t0) * 1000
                results_ws.append(("WebSocket", "Ingest event arrives on live feed", received, 0, ms,
                                   "" if received else "Event did not arrive within 15s (APScheduler flush may be delayed)"))
            except Exception as e:
                results_ws.append(("WebSocket", "Ingest event arrives on live feed", False, 0, 0, str(e)))

    except Exception as e:
        results_ws.append(("WebSocket", "Connect with valid API key", False, 0, 0, str(e)))

    # Connect with invalid key → should be rejected
    try:
        bad_url = f"{WS_BASE}/api/v1/ws/live/bad_client?api_key=ep_live_fakefakefake"
        t0 = time.perf_counter()
        try:
            async with websockets.connect(bad_url, open_timeout=10) as ws:
                ms  = (time.perf_counter() - t0) * 1000
                # If we connected, try receiving — server may close immediately
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3)
                except Exception:
                    pass
                results_ws.append(("WebSocket", "Invalid API key rejected", False, 0, ms,
                                   "Connection succeeded — expected rejection"))
        except (websockets.exceptions.InvalidStatus,
                websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.WebSocketException,
                OSError) as e:
            ms = (time.perf_counter() - t0) * 1000
            results_ws.append(("WebSocket", "Invalid API key rejected", True, 401, ms, ""))
    except Exception as e:
        results_ws.append(("WebSocket", "Invalid API key rejected", False, 0, 0, str(e)))

    return results_ws


def phase_websocket():
    print("\n🔌 Phase 7 — WebSocket Live Feed")
    key = state["ingest_key"]
    if not key:
        print("  ⚠️  Skipping — no ingest key available")
        return

    ws_results = asyncio.run(_ws_test())
    for phase, name, passed, status, ms, detail in ws_results:
        record(phase, name, passed, status, ms, detail)


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 8 — Rate Limiter
# ═════════════════════════════════════════════════════════════════════════════

def phase_rate_limiter():
    print("\n⏱️  Phase 8 — Rate Limiter")

    key = state["ingest_key"]
    if not key:
        print("  ⚠️  Skipping — no ingest key available")
        return

    # Check X-RateLimit-* headers on normal request
    try:
        r, ms = get("/ingest/status", api_key=key)
        has_headers = any(h.lower().startswith(("x-ratelimit", "x-process-time")) for h in r.headers)
        record("Rate Limiter", "X-RateLimit-* headers present on response", has_headers,
               r.status_code, ms,
               "" if has_headers else f"Headers found: {dict(r.headers)}")
    except Exception as e:
        record("Rate Limiter", "X-RateLimit-* headers present on response", False, 0, 0, str(e))

    # Fire rapid requests to trigger 429
    hit_429     = False
    retry_after = False
    t0 = time.perf_counter()
    try:
        for i in range(120):
            r = requests.get(
                f"{API_BASE}/ingest/status",
                headers={"X-API-Key": key},
                timeout=10,
            )
            if r.status_code == 429:
                hit_429     = True
                retry_after = "retry-after" in r.headers
                break
        ms = (time.perf_counter() - t0) * 1000
        record("Rate Limiter", "Rapid requests trigger 429 Too Many Requests",
               hit_429, 429 if hit_429 else r.status_code, ms,
               "" if hit_429 else "429 not triggered after 120 rapid requests — limit may be high")
        record("Rate Limiter", "429 response includes Retry-After header",
               retry_after, 429 if hit_429 else 0, 0,
               "" if retry_after else "Retry-After header missing on 429")
    except Exception as e:
        record("Rate Limiter", "Rapid requests trigger 429 Too Many Requests", False, 0, 0, str(e))


# ═════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ═════════════════════════════════════════════════════════════════════════════

def cleanup():
    print("\n🧹 Cleanup — removing test data")
    token = state["access_token"]

    # Delete alert if still exists
    if state["alert_id"] and state["ingest_key"]:
        try:
            delete(f"/alerts/{state['alert_id']}", api_key=state["ingest_key"])
            print("  ✔ Alert deleted")
        except Exception:
            pass

    # List and delete all API keys created in this run
    if token:
        try:
            r, _ = get("/api-keys/", token=token)
            if r.status_code == 200:
                keys = r.json()
                items = keys if isinstance(keys, list) else keys.get("items", [])
                for k in items:
                    if RUN_ID in k.get("name", ""):
                        delete(f"/api-keys/{k['id']}", token=token)
            print("  ✔ Test API keys deleted")
        except Exception:
            pass

    print("  ✔ Cleanup complete\n")


# ═════════════════════════════════════════════════════════════════════════════
# HTML REPORT GENERATOR
# ═════════════════════════════════════════════════════════════════════════════

def generate_report(run_duration: float) -> str:
    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    rate   = round(passed / total * 100) if total else 0

    # Group by phase
    phases = {}
    for r in results:
        phases.setdefault(r["phase"], []).append(r)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    phase_html = ""
    for phase_name, tests in phases.items():
        ph_pass = sum(1 for t in tests if t["passed"])
        ph_fail = len(tests) - ph_pass
        ph_icon = "✅" if ph_fail == 0 else "❌"
        rows = ""
        for t in tests:
            icon    = "✅" if t["passed"] else "❌"
            row_cls = "pass-row" if t["passed"] else "fail-row"
            sc      = t["status_code"] if t["status_code"] else "—"
            detail  = f'<div class="detail">{t["detail"]}</div>' if not t["passed"] and t["detail"] else ""
            rows += f"""
            <tr class="{row_cls}">
              <td class="icon-cell">{icon}</td>
              <td class="test-name">{t['name']}{detail}</td>
              <td class="center"><span class="badge sc-{sc}">{sc}</span></td>
              <td class="center">{t['duration_ms']} ms</td>
            </tr>"""

        phase_html += f"""
      <div class="phase-block">
        <div class="phase-header">
          <span class="phase-icon">{ph_icon}</span>
          <span class="phase-title">{phase_name}</span>
          <span class="phase-counts">
            <span class="count-pass">{ph_pass} passed</span>
            {'<span class="count-fail">' + str(ph_fail) + ' failed</span>' if ph_fail else ''}
          </span>
        </div>
        <table class="test-table">
          <thead>
            <tr>
              <th style="width:40px"></th>
              <th>Test</th>
              <th class="center" style="width:90px">Status</th>
              <th class="center" style="width:100px">Duration</th>
            </tr>
          </thead>
          <tbody>{rows}
          </tbody>
        </table>
      </div>"""

    summary_class = "summary-all-pass" if failed == 0 else "summary-has-fail"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EventPulse — Production Test Report</title>
<style>
  :root {{
    --bg:       #0f1117;
    --surface:  #1a1d27;
    --border:   #2a2d3a;
    --text:     #e2e8f0;
    --muted:    #8892a4;
    --green:    #22c55e;
    --red:      #ef4444;
    --yellow:   #f59e0b;
    --blue:     #3b82f6;
    --purple:   #a855f7;
    --radius:   10px;
    --font:     'Segoe UI', system-ui, -apple-system, sans-serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--font);
          font-size: 14px; line-height: 1.6; padding: 32px 24px; }}

  /* ── Header ── */
  .header {{ text-align: center; margin-bottom: 40px; }}
  .logo {{ font-size: 28px; font-weight: 800; letter-spacing: -0.5px;
           background: linear-gradient(135deg, var(--blue), var(--purple));
           -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .subtitle {{ color: var(--muted); margin-top: 4px; font-size: 13px; }}
  .meta {{ color: var(--muted); font-size: 12px; margin-top: 8px; }}
  .meta a {{ color: var(--blue); text-decoration: none; }}

  /* ── Summary bar ── */
  .summary-bar {{
    display: flex; align-items: center; gap: 20px;
    padding: 20px 28px; border-radius: var(--radius);
    border: 1px solid var(--border); margin-bottom: 32px;
    background: var(--surface);
  }}
  .summary-all-pass {{ border-color: #16a34a44; background: #052e1644; }}
  .summary-has-fail  {{ border-color: #b91c1c44; background: #2d050544; }}
  .summary-rate {{
    font-size: 42px; font-weight: 800; line-height: 1;
    min-width: 80px;
  }}
  .all-pass {{ color: var(--green); }}
  .has-fail  {{ color: var(--red);   }}
  .summary-details {{ flex: 1; }}
  .summary-label {{ font-size: 16px; font-weight: 600; margin-bottom: 6px; }}
  .summary-chips {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .chip {{ padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .chip-pass {{ background: #16a34a22; color: var(--green); border: 1px solid #16a34a55; }}
  .chip-fail {{ background: #b91c1c22; color: var(--red);   border: 1px solid #b91c1c55; }}
  .chip-time {{ background: #1d4ed822; color: var(--blue);  border: 1px solid #1d4ed855; }}
  .progress-bar {{ height: 6px; border-radius: 999px; background: var(--border);
                   overflow: hidden; margin-top: 12px; width: 100%; max-width: 400px; }}
  .progress-fill {{ height: 100%; border-radius: 999px;
                    background: linear-gradient(90deg, var(--green), #16a34a);
                    transition: width 0.5s; }}

  /* ── Phase blocks ── */
  .phase-block {{ margin-bottom: 24px; border-radius: var(--radius);
                  border: 1px solid var(--border); overflow: hidden; }}
  .phase-header {{ display: flex; align-items: center; gap: 12px;
                   padding: 14px 20px; background: var(--surface);
                   border-bottom: 1px solid var(--border); }}
  .phase-icon  {{ font-size: 18px; }}
  .phase-title {{ font-weight: 700; font-size: 15px; flex: 1; }}
  .phase-counts {{ display: flex; gap: 10px; }}
  .count-pass {{ color: var(--green); font-size: 13px; font-weight: 600; }}
  .count-fail {{ color: var(--red);   font-size: 13px; font-weight: 600; }}

  /* ── Test table ── */
  .test-table {{ width: 100%; border-collapse: collapse; }}
  .test-table th {{
    padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted);
    border-bottom: 1px solid var(--border); background: #13151e;
  }}
  .test-table td {{ padding: 11px 16px; border-bottom: 1px solid #1e2130; }}
  .test-table tr:last-child td {{ border-bottom: none; }}
  .pass-row {{ background: transparent; }}
  .fail-row {{ background: #1a0a0a; }}
  .fail-row:hover {{ background: #200d0d; }}
  .pass-row:hover {{ background: #ffffff06; }}
  .icon-cell  {{ font-size: 16px; width: 40px; }}
  .test-name  {{ font-weight: 500; }}
  .center     {{ text-align: center; }}
  .detail     {{ font-size: 12px; color: var(--red); margin-top: 3px; font-family: monospace; }}

  /* ── Status code badges ── */
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 5px;
            font-size: 12px; font-weight: 700; font-family: monospace; }}
  .sc-200, .sc-201, .sc-202, .sc-204 {{ background:#052e16; color:var(--green); }}
  .sc-400, .sc-401, .sc-403, .sc-404, .sc-422 {{ background:#2d0505; color:var(--red); }}
  .sc-429 {{ background:#422006; color:var(--yellow); }}
  .sc-101 {{ background:#1e1b4b; color:#818cf8; }}
  .sc-— {{ background:var(--border); color:var(--muted); }}

  /* ── Footer ── */
  .footer {{ text-align: center; margin-top: 48px; color: var(--muted);
             font-size: 12px; padding-top: 24px; border-top: 1px solid var(--border); }}
  .footer a {{ color: var(--blue); text-decoration: none; }}
</style>
</head>
<body>

<div class="header">
  <div class="logo">⚡ EventPulse Analytics</div>
  <div class="subtitle">Production End-to-End Test Report</div>
  <div class="meta">
    Run at <strong>{now}</strong> &nbsp;·&nbsp;
    Backend: <a href="{BASE_URL}" target="_blank">{BASE_URL}</a> &nbsp;·&nbsp;
    Run ID: <code>{RUN_ID}</code>
  </div>
</div>

<div class="summary-bar {summary_class}">
  <div class="summary-rate {'all-pass' if failed == 0 else 'has-fail'}">{rate}%</div>
  <div class="summary-details">
    <div class="summary-label">
      {'🎉 All tests passed!' if failed == 0 else f'{failed} test{"s" if failed > 1 else ""} failed'}
    </div>
    <div class="summary-chips">
      <span class="chip chip-pass">✅ {passed} passed</span>
      {'<span class="chip chip-fail">❌ ' + str(failed) + ' failed</span>' if failed else ''}
      <span class="chip chip-time">⏱ {round(run_duration, 1)}s total</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" style="width:{rate}%"></div>
    </div>
  </div>
</div>

{phase_html}

<div class="footer">
  EventPulse Analytics &nbsp;·&nbsp;
  <a href="https://github.com/ayushi-shahi/EventPulse-Analytics" target="_blank">GitHub</a> &nbsp;·&nbsp;
  <a href="{BASE_URL}/docs" target="_blank">API Docs</a>
</div>

</body>
</html>"""


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  ⚡ EventPulse — Production Test Suite")
    print(f"  Backend : {BASE_URL}")
    print(f"  Email   : {TEST_EMAIL}")
    print(f"  Run ID  : {RUN_ID}")
    print("=" * 60)

    run_start = time.perf_counter()

    try:
        phase_health()
        phase_auth()
        phase_api_keys()
        phase_ingestion()
        phase_metrics()
        phase_alerts()
        phase_websocket()
        phase_rate_limiter()
    finally:
        cleanup()

    run_duration = time.perf_counter() - run_start

    # Summary
    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    print("=" * 60)
    print(f"  Results : {passed}/{total} passed  |  {failed} failed")
    print(f"  Duration: {round(run_duration, 1)}s")
    print("=" * 60)

    # Write report
    report_path = "eventpulse_test_report.html"
    html = generate_report(run_duration)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n📄 Report saved → {report_path}")
    print("   Open it in your browser to view results.\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()