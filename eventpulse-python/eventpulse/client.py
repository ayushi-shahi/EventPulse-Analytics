"""
EventPulse Python SDK — core client.
Mirrors the JS EventPulseClient: batched, background-threaded, retry-on-failure.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import urllib.request
import urllib.error
import json

logger = logging.getLogger("eventpulse")

DEFAULT_ENDPOINT = "https://eventpulse-analytics-backend.onrender.com"
DEFAULT_BATCH_INTERVAL = 5.0   # seconds
DEFAULT_MAX_QUEUE = 1000
DEFAULT_MAX_RETRIES = 3


class EventPulseClient:
    """
    Thread-safe EventPulse analytics client.

    Usage::

        client = EventPulseClient(api_key="ep_live_...")
        client.track("signup", {"plan": "pro"})
        client.identify("user_123")
        client.shutdown()   # flush & stop background thread
    """

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        batch_interval: float = DEFAULT_BATCH_INTERVAL,
        max_queue_size: int = DEFAULT_MAX_QUEUE,
        max_retries: int = DEFAULT_MAX_RETRIES,
        async_mode: bool = True,
    ) -> None:
        if not api_key.startswith("ep_"):
            raise ValueError("api_key must start with 'ep_'")

        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._batch_interval = batch_interval
        self._max_queue_size = max_queue_size
        self._max_retries = max_retries
        self._async = async_mode

        self._queue: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._user_id: Optional[str] = None

        if self._async:
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._run, daemon=True, name="eventpulse-flusher")
            self._thread.start()

    # ------------------------------------------------------------------
    # Public API  (mirrors JS: track / identify / page / flush)
    # ------------------------------------------------------------------

    def track(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> "EventPulseClient":
        """Queue a custom event."""
        self._enqueue(event_name, properties)
        return self

    def identify(self, user_id: str, traits: Optional[Dict[str, Any]] = None) -> "EventPulseClient":
        """Associate subsequent events with a user."""
        self._user_id = user_id
        props = {"identified_user_id": user_id, **(traits or {})}
        self._enqueue("identify", props)
        return self

    def page(self, url: str, properties: Optional[Dict[str, Any]] = None) -> "EventPulseClient":
        """Track a page / route view (useful in server-side rendering)."""
        props = {"url": url, **(properties or {})}
        self._enqueue("page_view", props)
        return self

    def flush(self) -> "EventPulseClient":
        """Force-send all queued events immediately (blocking)."""
        self._flush()
        return self

    def shutdown(self, timeout: float = 10.0) -> None:
        """Flush remaining events and stop the background thread."""
        if self._async:
            self._stop_event.set()
            self._thread.join(timeout=timeout)
        self._flush()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _enqueue(self, event_name: str, properties: Optional[Dict[str, Any]]) -> None:
        payload = {
            "event_name": event_name,
            "user_id": self._user_id,
            "properties": properties or {},
            "client_time": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            if len(self._queue) >= self._max_queue_size:
                logger.warning("EventPulse queue full — dropping oldest event")
                self._queue.pop(0)
            self._queue.append(payload)

    def _flush(self) -> None:
        with self._lock:
            if not self._queue:
                return
            batch, self._queue = self._queue[:], []

        url = f"{self._endpoint}/api/v1/ingest/events/batch"
        body = json.dumps({"events": batch}).encode()

        for attempt in range(1, self._max_retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": self._api_key,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status < 300:
                        return
                    raise urllib.error.HTTPError(url, resp.status, "Server error", {}, None)

            except Exception as exc:
                logger.warning("EventPulse flush attempt %d/%d failed: %s", attempt, self._max_retries, exc)
                if attempt < self._max_retries:
                    time.sleep(2 ** (attempt - 1))   # exponential back-off: 1s, 2s

        # All retries exhausted — put events back (prepend so order is preserved)
        with self._lock:
            self._queue = batch + self._queue

    def _run(self) -> None:
        """Background flusher loop."""
        while not self._stop_event.wait(timeout=self._batch_interval):
            self._flush()
        self._flush()   # final flush on shutdown

    # context-manager support
    def __enter__(self) -> "EventPulseClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.shutdown()