# Runbook — EventPulse & WorkScribe

What to check, in what order, when something breaks. Written to be followed
months from now with none of it fresh in your head.

Two projects, wired together: **WorkScribe** sends events to **EventPulse**.

---

## The estate

| Piece | Provider | Address / identifier |
|---|---|---|
| EventPulse API | Render (Docker, free) | `eventpulse-analytics-backend.onrender.com` |
| EventPulse dashboard | Vercel | `event-pulse-analytics-frontend.vercel.app` |
| EventPulse database | Neon (Postgres 17, Singapore) | project `eventpulse` |
| EventPulse cache/queue | Upstash Redis (Singapore) | `adapted-walleye-138456` |
| WorkScribe API | Render (Docker, free) | `workscribe-api.onrender.com` |
| WorkScribe frontend | Vercel | `work-scribe.vercel.app` |
| WorkScribe database | Neon (Postgres 17, Singapore) | project `Workscribe` |
| WorkScribe cache | Upstash Redis (Singapore, separate account) | `settling-dolphin-84181` |
| WorkScribe email | Brevo | account `ayushishahi14072004@gmail.com` |
| Demo traffic | GitHub Actions | `.github/workflows/demo-traffic.yml` |

Login for both apps: `ayushishahi14072004@gmail.com` / `String@12345`

---

# STEP 0 — Find out what is actually broken

Run these two. Everything below depends on the answer.

```bash
curl https://eventpulse-analytics-backend.onrender.com/api/v1/health/ready
curl https://workscribe-api.onrender.com/health/ready
```

Allow up to 60 seconds each — free instances sleep and must boot first.

| Response | Meaning | Section |
|---|---|---|
| `{"status":"ready"}` | API and its dependencies are fine — the problem is in the browser | **§A** |
| `database` not ok | Postgres unreachable | **§B** |
| `redis` not ok | Redis unreachable | **§C** |
| Nothing at all, even after 2 minutes | The service is not running | **§D** |

### A CORS error is almost never CORS

When an API returns a 500, the browser reports a missing CORS header instead of
the real error and hides the cause. Run Step 0 before touching any CORS
setting. If the API is healthy *and* you still get a CORS error, see §G.

---

# §A — API healthy, but something looks wrong in the browser

### A1. A page area shows "This page ran into a problem"

**Hard refresh: `Ctrl+Shift+R`.**

Pages are code-split, and each deploy renames the chunks. A tab holding the old
`index.html` asks for a file that no longer exists. This now self-heals (one
automatic reload) and missing chunks return a real 404, but a hard refresh is
the instant fix.

Still broken? Open DevTools → Console and read the `[ErrorBoundary]` line — the
real error is logged there and shown under "Technical details" on the page.

### A2. The dashboard is empty, or shows the wrong numbers

**Check which source is selected** in the top-left dropdown. Each API key is a
separate dataset. WorkScribe's traffic only appears under the **WorkScribe**
source; the seeded demo data lives under **Production Web App**. Your choice is
remembered per browser.

Then check the period buttons — "Last hour" is genuinely empty if nothing
arrived in the last hour.

### A3. Changed an environment variable and nothing happened

Vite bakes `VITE_*` values in **at build time**. Saving the variable in Vercel
changes nothing until you **redeploy**.

---

# §B — Database unreachable

Neon suspends compute when idle and **wakes by itself**, so retry once after
~30 seconds before doing anything.

If it stays down, the project was deleted:

1. Create a new project at **neon.com** — Postgres **17**, Singapore, **Neon
   Auth off**.
2. Copy the **Direct connection** string (no `-pooler` in the hostname).
3. Rewrite it — all three edits are required:
   - `postgresql://` → `postgresql+asyncpg://`
   - delete `?sslmode=require`
   - delete `&channel_binding=require`
   - append `?ssl=require`
4. Render → the service → Environment → set `DATABASE_URL` → save.
5. Apply the schema:
   ```bash
   cd backend
   DATABASE_URL="postgresql+asyncpg://...?ssl=require" alembic upgrade head
   ```
6. Repopulate demo data — see §E.

> `sslmode` and `channel_binding` are libpq options. asyncpg rejects both, and
> leaving either in place crashes the app on boot. This is the single most
> common mistake when moving databases.

---

# §C — Redis unreachable

**EventPulse ingestion stops** without Redis: events are queued there before
being written. **WorkScribe keeps working** — it degrades to no rate limiting
and no server-side logout.

1. Create a database at **console.upstash.com** (Regional, Singapore).
2. Copy the **TCP** URL. It must start with **`rediss://`** — two s's. Upstash
   shows `redis-cli --tls -u redis://…`; that `--tls` flag only applies to
   `redis-cli`. Your app decides TLS from the scheme alone, so `redis://` is
   refused.
3. Render → Environment → set `REDIS_URL` → save.

> The free tier allows **one database per account**. The two projects use
> separate Upstash accounts on purpose — both apps use the key prefix
> `rate_limit:`, so sharing one instance would have them overwriting each
> other's counters.

### C1. "max requests limit exceeded" — the monthly command quota is gone

Upstash free tier allows **500,000 commands per month**. Past that, *every*
command is refused:

```
ResponseError: max requests limit exceeded. Limit: 500000, Usage: 500000.
```

**Confirm it:**

```bash
python -c "
import asyncio, redis.asyncio as r
c = r.from_url('<REDIS_URL>')
print(asyncio.run(c.ping()))"
```

**Get running again** — create a fresh Upstash database and point `REDIS_URL`
at it. The quota is per database, so a new one starts at zero; you do not have
to wait for the reset date. Then check the reset date in the Upstash console so
you know when the old one frees up.

**Then find what is burning commands.** A pipeline is billed **one command per
queued call**, not one for the pipeline. That is the trap — pipelining looks
like an optimisation and is invisible in the code. Both the queue producer and
consumer now use *variadic* commands, which really are one command:

| Operation | Cost |
|---|---|
| `RPOP key COUNT 100` | 1 command |
| 100 pipelined `RPOP`s | 100 commands |
| `RPUSH key v1 … v50` | 1 command |
| 50 pipelined `RPUSH`es | 50 commands |

**The poller mostly does not poll.** APScheduler runs inside the FastAPI
process, so the ingest endpoint tells it directly when there is work
(`notify_pending()` in `app/tasks/tasks_ingest.py`). A tick with no signal
issues no Redis command at all.

`IDLE_POLL_SECONDS` (default 300) is only a safety net, for events queued by
something other than this process. So:

| | Commands |
|---|---|
| Idle, per hour | **12** (safety net only) |
| One traffic burst | **2** (1 RPUSH + 1 RPOP, any batch size) |
| Projected total | **~10K/month — about 2% of the free tier** |

Locally ingested events are still picked up within one 5s tick, so this is both
cheaper *and* lower latency than polling unconditionally.

Budget check before changing `IDLE_POLL_SECONDS`:

```
idle commands/hour = 3600 / IDLE_POLL_SECONDS
```

Note what *not* to do: polling every 5s costs 518K/month on its own — over the
limit before a single event is ingested. Never make the poller unconditional.

### C2. Redis is down but the API must stay up

Redis is a **degradable** dependency, not a required one. Metrics, dashboards,
Explorer and Funnels are served entirely from Postgres. When Redis is
unavailable:

- the app still **starts** and serves every read endpoint;
- rate limiting **fails open** (requests are allowed, not rejected);
- live WebSocket updates stop, and reconnect on their own once Redis returns;
- **ingestion stops** — new events cannot be queued;
- `/api/v1/health/ready` returns **200** with `"redis": "degraded"`.

Readiness deliberately tracks **Postgres only**. If it failed on Redis, a cache
outage would pull the whole service out of rotation.

---

# §D — The API is not running at all

1. Render dashboard → the service. Is it suspended, failed, or mid-deploy?
2. Read the deploy logs. Startup states plainly what is wrong:
   ```
   Database connection OK
   Redis UNREACHABLE at startup: ...
   ```
3. **A crash loop with no response at all** usually means the container exited
   during startup. EventPulse runs `alembic upgrade head` before uvicorn, so a
   dead database prevents the server from ever starting — that is why it times
   out instead of returning 503. Fix the database first (§B).
   *Redis can no longer cause this.* It once could: startup awaited
   `rate_limiter.initialize()`, which re-raised, so an exhausted Redis quota
   stopped the app from booting and took down every endpoint — including the
   ones that never touch Redis. Startup now degrades instead of raising
   (§C2), covered by `tests/unit/test_redis_degradation.py`.
4. Free instances sleep after ~15 minutes idle; the first request then takes
   30–60 seconds. That is not an outage.

---

# §E — Demo data and rolling traffic

### Rebuild the historical dataset (30 days, ~45k events)

```bash
cd "Analytics Platform"
DATABASE_URL="postgresql+asyncpg://...?ssl=require" python seeds/seed_demo_data.py
```

Safe to re-run: it wipes and rebuilds only the demo sources. Run it before a
demo — the seeded window ages, so "Last hour" empties over time.

### Hourly traffic (keeps the dashboard alive on its own)

GitHub Actions runs `seeds/generate_live_events.py` every hour at :30.

* **Check it:** repo → **Actions** → **Demo traffic**
* **Run it now:** Actions → Demo traffic → *Run workflow*
* **Needs:** repo secret `EVENTPULSE_DEMO_API_KEY` (Settings → Secrets and
  variables → Actions). Without it the job skips instead of failing.

> **GitHub disables scheduled workflows after 60 days of repo inactivity.** If
> the dashboard looks stale months from now, check Actions first — there will
> be a banner offering to re-enable it.

### Storage

Events older than **90 days** are deleted automatically once a day. Aggregates
are pruned at 30 days but outlive the raw rows, so old charts survive.

---

# §F — WorkScribe events are not appearing in EventPulse

Work down this list; the first two cause almost every case.

1. **Wrong source selected.** WorkScribe's events only show under the
   **WorkScribe** source. The dashboard defaults to the oldest key
   ("Production Web App"). Switch it in the top-left dropdown.
2. **Period too narrow.** Try "Last 24 hours" before concluding nothing arrived.
3. **Vercel not redeployed.** `VITE_*` values are baked at build time. Confirm
   the live bundle actually carries the key:
   ```bash
   curl -s https://work-scribe.vercel.app/ | grep -o 'assets/index-[^"]*\.js'
   # then fetch that file and search it
   curl -s https://work-scribe.vercel.app/assets/index-XXXX.js | grep -o 'ep_live_[a-f0-9]\{8\}'
   ```
4. **Wrong endpoint format.** `VITE_EVENTPULSE_ENDPOINT` must have **no**
   `/api/v1` — the SDK appends it. With it you get `/api/v1/api/v1/…`, which
   silently fails.
5. **Key belongs to a deleted database.** If EventPulse's database was
   recreated, every old key is gone. Create a new one in EventPulse → API Keys,
   update Vercel, redeploy.
6. **Delay is normal.** The SDK batches every 5 seconds, then a background
   worker moves events from Redis into Postgres. Allow up to a minute.

Check what actually arrived:

```sql
SELECT event_name, count(*), max(event_time)
FROM events
WHERE client_id = (SELECT id FROM api_keys WHERE client_name = 'WorkScribe')
GROUP BY 1 ORDER BY 2 DESC;
```

---

# §G — Genuine CORS errors

Only after Step 0 shows the API healthy.

* **WorkScribe** allows specific origins. `CORS_ORIGINS` must match the browser
  origin exactly, **no trailing slash**. It accepts one origin, a
  comma-separated list, or a JSON array.
* **EventPulse** allows `*`, so ingestion works from anywhere. If a CORS error
  appears here, it is a 500 in disguise.
* Moved to a custom domain? Update `CORS_ORIGINS` **and** Google's authorised
  JavaScript origins.

---

# §H — Email not arriving (WorkScribe)

Password reset always reports success to avoid revealing whether an account
exists, so failures are invisible in the UI. **Read the Render logs** — a
failed send logs `EMAIL NOT SENT` with Brevo's own response.

Three things must all be true:

1. **IP allowlist off.** app.brevo.com/security/authorised_ips → the `API keys`
   row must read **Deactivated**. If it is Activated, Brevo blocks Render's IP
   and reports `unrecognised IP address`. Most common cause.
2. **Key valid.** app.brevo.com/settings/keys/api → regenerate, update
   `BREVO_API_KEY` in Render.
3. **Sender verified.** app.brevo.com/senders/list must contain the address in
   `EMAIL_FROM`. Brevo rejects unverified senders even with a perfect key.

Free tier: 300 emails/day.

---

# §I — Google sign-in fails (WorkScribe)

console.cloud.google.com → project `inbound-hawk-439105-p1` → APIs & Services →
Credentials → OAuth client **WorkScribe** → **Authorised JavaScript origins**
must contain:

```
https://work-scribe.vercel.app
http://localhost:5173
```

Scheme and host only — no trailing slash, no path. The "Authorised redirect
URIs" section is irrelevant: this app uses the ID-token flow. Email/password
login is unaffected either way.

---

# §J — Cold starts

Free Render services sleep after ~15 minutes idle; the next request waits
30–60 seconds for the container to boot. Frontend timeouts are set to 60s
specifically to survive this.

EventPulse is kept warm by the hourly traffic job. For WorkScribe, point an
uptime monitor (UptimeRobot, Better Stack, cron-job.org) at:

```
https://workscribe-api.onrender.com/health
```

every 10 minutes. Use `/health`, **not** `/health/ready` — otherwise a Redis
blip pages you at 3am.

---

# Environment variables

**EventPulse (Render)**

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…?ssl=require` |
| `REDIS_URL` | `rediss://` — TLS scheme required |
| `SECRET_KEY` | JWT signing. Changing it signs everyone out |
| `APP_ENV` / `DEBUG` | `production` / `false` |

`CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are **not needed** — Celery is
not installed; the config falls back to `REDIS_URL`.

**EventPulse dashboard (Vercel)**

| Variable | Notes |
|---|---|
| `VITE_API_URL` | must include `/api/v1` |
| `VITE_WS_URL` | `wss://…/api/v1` |

**WorkScribe (Render)** — see `WorkScribe/backend/docs/DEPLOYMENT.md` for the
full list.

**WorkScribe frontend (Vercel)**

| Variable | Notes |
|---|---|
| `VITE_API_URL` | `https://workscribe-api.onrender.com/api/v1` |
| `VITE_EVENTPULSE_API_KEY` | the EventPulse key to attribute events to |
| `VITE_EVENTPULSE_ENDPOINT` | **no** `/api/v1` — the SDK appends it |

---

# Local development

**EventPulse**

```bash
cd backend
docker compose up -d
alembic upgrade head
uvicorn app.main:app --reload --port 8002

cd ../frontend && npm install && npm run dev     # :3000
```

**WorkScribe**

```bash
cd backend
docker compose up -d                              # API :8001, PG :5433, Redis :6380
docker compose exec api alembic upgrade head

cd ../frontend && npm install && npm run dev      # :5173
```

---

# Maintenance

Free tiers rot. Once or twice a year:

* Sign in to Neon, Upstash (**both accounts**), Render, Vercel, Brevo and
  GitHub so nothing is reaped for inactivity.
* Confirm both `/health/ready` endpoints return `ready`.
* Check **Actions → Demo traffic** is still enabled.
* Rotate `SECRET_KEY`, `JWT_SECRET_KEY`, database passwords, Redis tokens, the
  Brevo key and the EventPulse ingestion keys.

> Anything pasted into a chat, screenshot or commit should be treated as
> public and rotated.
