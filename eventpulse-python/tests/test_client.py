"""Basic tests for EventPulseClient."""
import json
import threading
import time
from unittest.mock import patch, MagicMock

import pytest
from eventpulse import EventPulseClient


API_KEY = "ep_live_" + "a" * 64


def make_client(**kwargs):
    return EventPulseClient(API_KEY, async_mode=False, **kwargs)


# --- init ---

def test_invalid_key():
    with pytest.raises(ValueError):
        EventPulseClient("bad_key")


def test_valid_key():
    c = make_client()
    assert c._api_key == API_KEY


# --- track / identify / page ---

def test_track_enqueues():
    c = make_client()
    c.track("signup", {"plan": "pro"})
    assert len(c._queue) == 1
    assert c._queue[0]["event_name"] == "signup"
    assert c._queue[0]["properties"]["plan"] == "pro"


def test_identify_sets_user():
    c = make_client()
    c.identify("user_42")
    assert c._user_id == "user_42"
    assert c._queue[-1]["event_name"] == "identify"


def test_page_tracks_page_view():
    c = make_client()
    c.page("https://example.com/pricing")
    assert c._queue[0]["event_name"] == "page_view"
    assert c._queue[0]["properties"]["url"] == "https://example.com/pricing"


def test_chaining():
    c = make_client()
    result = c.track("a").track("b").track("c")
    assert result is c
    assert len(c._queue) == 3


# --- flush ---

def test_flush_sends_batch(monkeypatch):
    responses = []

    class FakeResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self): return b""

    def fake_urlopen(req, timeout=None):
        body = json.loads(req.data)
        responses.append(body)
        return FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    c = make_client()
    c.track("evt1")
    c.track("evt2")
    c.flush()

    assert len(responses) == 1
    assert len(responses[0]["events"]) == 2
    assert c._queue == []   # cleared after flush


def test_flush_retries_on_failure(monkeypatch):
    calls = []

    def fail_then_succeed(req, timeout=None):
        calls.append(1)
        if len(calls) < 2:
            raise Exception("network error")
        class R:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass
        return R()

    monkeypatch.setattr("urllib.request.urlopen", fail_then_succeed)
    monkeypatch.setattr("time.sleep", lambda _: None)   # skip back-off delay

    c = make_client(max_retries=3)
    c.track("test")
    c.flush()
    assert len(calls) == 2


def test_flush_requeues_on_all_failures(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr("time.sleep", lambda _: None)

    c = make_client(max_retries=2)
    c.track("evt")
    c.flush()
    assert len(c._queue) == 1   # event returned to queue


# --- async mode ---

def test_async_background_flush(monkeypatch):
    sent = []

    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: (sent.append(1), R())[1])

    c = EventPulseClient(API_KEY, async_mode=True, batch_interval=0.1)
    c.track("bg_event")
    time.sleep(0.35)
    c.shutdown()
    assert len(sent) >= 1


# --- context manager ---

def test_context_manager(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: (_ for _ in ()).throw(Exception()))
    monkeypatch.setattr("time.sleep", lambda _: None)
    with EventPulseClient(API_KEY, async_mode=False) as c:
        c.track("x")
    # no crash = pass