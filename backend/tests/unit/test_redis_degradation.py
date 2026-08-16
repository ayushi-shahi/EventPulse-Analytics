"""
Regression tests for the Redis outage of 2026-08-16.

Two independent faults took the whole API down when the managed Redis plan ran
out of monthly commands:

  1. The ingest poller pipelined `batch_size` RPOPs every 5 seconds. A pipeline
     is billed one command per queued call, so an *idle* queue still cost 100
     commands per tick and burned a 500K/month quota in about a day.
  2. `rate_limiter.initialize()` re-raised on failure and was awaited directly
     from the lifespan, so a Redis error meant the app never finished starting
     — every endpoint went down, including the ones that only need Postgres.

These tests need neither a live Redis nor a database.
"""
import pytest

from app.core.rate_limiter import RateLimiter


class _Recorder:
    """Stand-in Redis that records commands and can be told to fail."""

    def __init__(self, queue=None, fail=False):
        self.queue = list(queue or [])
        self.fail = fail
        self.commands = []

    def _record(self, name):
        self.commands.append(name)
        if self.fail:
            raise ConnectionError("max requests limit exceeded")

    async def rpop(self, key, count=None):
        self._record("rpop")
        if count is None:
            return self.queue.pop() if self.queue else None
        popped = [self.queue.pop() for _ in range(min(count, len(self.queue)))]
        return popped or None

    async def rpush(self, key, *values):
        self._record("rpush")
        self.queue.extend(values)
        return len(self.queue)

    async def lpush(self, key, *values):
        self._record("lpush")
        for v in values:
            self.queue.insert(0, v)
        return len(self.queue)

    async def script_load(self, script):
        self._record("script_load")
        return "sha"

    async def aclose(self):
        pass


# ---------------------------------------------------------------------------
# 1. Ingest poller — command cost
# ---------------------------------------------------------------------------

@pytest.fixture
def poller(monkeypatch):
    """Reset the module's backoff state and swap in a recording client."""
    from app.tasks import tasks_ingest

    monkeypatch.setattr(tasks_ingest, "_idle_streak", 0, raising=False)
    monkeypatch.setattr(tasks_ingest, "_ticks_to_skip", 0, raising=False)

    def _install(client):
        monkeypatch.setattr(tasks_ingest, "_client", client, raising=False)
        monkeypatch.setattr(tasks_ingest, "_get_client", lambda: client)
        return tasks_ingest

    return _install


@pytest.mark.asyncio
async def test_empty_poll_costs_one_command(poller):
    """An idle queue must cost exactly one command, not `batch_size`."""
    redis = _Recorder()
    ti = poller(redis)

    await ti.process_event_batch(batch_size=100)

    assert redis.commands == ["rpop"]


@pytest.mark.asyncio
async def test_idle_polling_backs_off(poller):
    """Sustained idleness must stop burning quota on every 5s tick."""
    redis = _Recorder()
    ti = poller(redis)

    for _ in range(30):  # ramp down into steady state
        await ti.process_event_batch(batch_size=100)

    redis.commands.clear()
    for _ in range(60):  # 60 ticks x 5s = 5 more minutes, fully backed off
        await ti.process_event_batch(batch_size=100)

    # Old behaviour: 60 * 100 = 6,000 commands for the same five minutes.
    # New: one poll per 30s, i.e. one per six 5s ticks.
    assert len(redis.commands) == 10


@pytest.mark.asyncio
async def test_batch_is_popped_in_a_single_command(poller, monkeypatch):
    """250 queued events must drain in 3 RPOPs, not 300 commands."""
    from app.tasks import tasks_ingest

    redis = _Recorder(queue=[f"e{i}" for i in range(250)])
    ti = poller(redis)

    processed = []

    class _Processor:
        async def process_events_batch(self, events, broadcast=True):
            processed.extend(events)
            return {"processed": len(events)}

        async def close(self):
            pass

    monkeypatch.setattr(tasks_ingest, "EventProcessor", _Processor)

    for _ in range(3):
        await ti.process_event_batch(batch_size=100)

    assert len(processed) == 250
    assert redis.commands.count("rpop") == 3


@pytest.mark.asyncio
async def test_poller_survives_redis_failure(poller):
    """A Redis error must be swallowed — an APScheduler job must not explode."""
    redis = _Recorder(fail=True)
    ti = poller(redis)

    await ti.process_event_batch(batch_size=100)  # must not raise


# ---------------------------------------------------------------------------
# 2. Rate limiter — must degrade, never take the app down
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initialize_never_raises(monkeypatch):
    """
    The lifespan awaits initialize(). If it raises, the app never starts and
    every endpoint dies with it — which is exactly what happened.
    """
    import app.core.rate_limiter as rl

    def _boom(*a, **k):
        raise ConnectionError("max requests limit exceeded")

    monkeypatch.setattr(rl.redis, "from_url", _boom)

    limiter = RateLimiter()
    assert await limiter.initialize() is False


@pytest.mark.asyncio
async def test_rate_limiter_fails_open_when_redis_is_down(monkeypatch):
    """With Redis unavailable, requests are allowed rather than rejected."""
    import app.core.rate_limiter as rl

    monkeypatch.setattr(
        rl.redis, "from_url",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down")),
    )

    limiter = RateLimiter()
    allowed, info = await limiter.is_allowed("some-key", limit=100, window_seconds=60)

    assert allowed is True
    assert info["degraded"] is True


@pytest.mark.asyncio
async def test_failed_init_is_not_retried_on_every_call(monkeypatch):
    """
    Without a cooldown, every request would open a fresh connection and pay the
    full connect timeout, turning a Redis outage into an app-wide stall.
    """
    import app.core.rate_limiter as rl

    attempts = {"n": 0}

    def _boom(*a, **k):
        attempts["n"] += 1
        raise ConnectionError("down")

    monkeypatch.setattr(rl.redis, "from_url", _boom)

    limiter = RateLimiter()
    for _ in range(50):
        await limiter.is_allowed("some-key", limit=100, window_seconds=60)

    assert attempts["n"] == 1


@pytest.mark.asyncio
async def test_rate_limiter_works_normally_when_redis_is_healthy(monkeypatch):
    """The degradation path must not weaken limiting when Redis is fine."""
    import app.core.rate_limiter as rl

    class _Healthy(_Recorder):
        async def evalsha(self, sha, numkeys, key, ts, window, limit):
            self._record("evalsha")
            return [0, limit + 1, limit]  # over the limit

    client = _Healthy()
    monkeypatch.setattr(rl.redis, "from_url", lambda *a, **k: client)

    limiter = RateLimiter()
    allowed, info = await limiter.is_allowed("some-key", limit=10, window_seconds=60)

    assert allowed is False           # still rejects when over the limit
    assert "degraded" not in info
