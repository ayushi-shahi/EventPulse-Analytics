# /app/healthcheck.py
# Used by Docker healthcheck for celery_worker and celery_beat containers.
# Pure Python — no redis-cli or other external tools needed.
# Exits 0 (healthy) if Redis is reachable, 1 (unhealthy) otherwise.
import sys
import os
import socket

redis_url = os.getenv("REDIS_URL", "redis://eventpulse_redis:6379/0")

# Parse host and port from the URL
# Expected format: redis://host:port/db
try:
    without_scheme = redis_url.replace("redis://", "")
    host_port = without_scheme.split("/")[0]
    host, port = host_port.split(":")
    port = int(port)
except Exception:
    host, port = "eventpulse_redis", 6379

# Try to open a TCP connection — if Redis is up, this succeeds in <1s
try:
    sock = socket.create_connection((host, port), timeout=3)
    sock.close()
    sys.exit(0)   # healthy
except OSError:
    sys.exit(1)   # unhealthy