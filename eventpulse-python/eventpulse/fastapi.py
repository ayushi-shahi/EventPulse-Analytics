"""
EventPulse FastAPI / Starlette middleware — auto-tracks page_view.

Setup::

    from eventpulse.fastapi import EventPulseMiddleware

    app.add_middleware(
        EventPulseMiddleware,
        api_key="ep_live_...",
    )
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from eventpulse.client import EventPulseClient, DEFAULT_ENDPOINT


class EventPulseMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str, endpoint: str = DEFAULT_ENDPOINT, **kwargs) -> None:
        super().__init__(app, **kwargs)
        self.client = EventPulseClient(api_key=api_key, endpoint=endpoint)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        self.client.track("page_view", {
            "url": str(request.url),
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "referrer": request.headers.get("referer"),
            "user_agent": request.headers.get("user-agent"),
        })

        return response