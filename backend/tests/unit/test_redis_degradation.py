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
    """Reset the module's poll state and swap in a recording client."""
    from app.tasks import tasks_ingest

    monkeypatch.setattr(tasks_ingest, "_pending", False, raising=False)
    monkeypatch.setattr(tasks_ingest, "_last_poll", 0.0, raising=False)

    def _install(client, *, armed=True):
        monkeypatch.setattr(tasks_ingest, "_client", client, raising=False)
        monkeypatch.setattr(tasks_ingest, "_get_client", lambda: client)
        if armed:
            tasks_ingest.notify_pending()
        return tasks_ingest

    return _install


@pytest.mark.asyncio
async def test_signalled_poll_costs_one_command(poller):
    """Draining a signalled queue must cost one command, not `batch_size`."""
    redis = _Recorder()
    ti = poller(redis)

    await ti.process_event_batch(batch_size=100)

    assert redis.commands == ["rpop"]


@pytest.mark.asyncio
async def test_unsignalled_ticks_do_not_touch_redis(poller):
    """
    With nothing queued through this process, ticks must be free. This is the
    whole budget: polling an empty queue every 5s is what burned the quota.
    """
    redis = _Recorder()
    ti = poller(redis, armed=False)
    ti._last_poll = __import__("time").monotonic()  # safety net not yet due

    for _ in range(60):  # 5 minutes of ticks
        await ti.process_event_batch(batch_size=100)

    assert redis.commands == []


@pytest.mark.asyncio
async def test_idle_cost_stays_under_fifty_commands_per_hour(poller):
    """The safety-net poll alone must keep idle cost far below the free tier."""
    from app.tasks import tasks_ingest

    commands_per_hour = 3600 / tasks_ingest.IDLE_POLL_SECONDS
    assert commands_per_hour <= 50
    # ...and comfortably inside 500K/month.
    assert commands_per_hour * 24 * 31 < 100_000


@pytest.mark.asyncio
async def test_enqueue_wakes_the_poller(poller):
    """An event queued through this process is drained on the next tick."""
    redis = _Recorder()
    ti = poller(redis, armed=False)
    ti._last_poll = __import__("time").monotonic()

    await ti.process_event_batch(batch_size=100)
    assert redis.commands == []          # nothing signalled yet

    ti.notify_pending()                  # what the ingest endpoint calls
    await ti.process_event_batch(batch_size=100)
    assert redis.commands == ["rpop"]    # drained immediately


@pytest.mark.asyncio
async def test_enqueue_racing_a_poll_is_not_swallowed(poller):
    """
    An enqueue landing *while* a poll is in flight must not be lost: the flag is
    cleared before dequeuing, so the racing notify re-arms it.
    """
    from app.tasks import tasks_ingest

    class _Racing(_Recorder):
        async def rpop(self, key, count=None):
            tasks_ingest.notify_pending()   # enqueue lands mid-poll
            return await super().rpop(key, count)

    redis = _Racing()
    ti = poller(redis)

    await ti.process_event_batch(batch_size=100)
    assert ti._pending is True           # will drain again next tick


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
