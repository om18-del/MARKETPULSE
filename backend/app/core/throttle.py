"""Per-IP throttle for AI-costing endpoints.

A tiny sliding-window counter in process memory — no dependencies. Fails
OPEN (if the limiter itself errors, requests pass) because the throttle
exists to protect quota, never to become a single point of failure.

Applied only to routes that spend Gemini tokens (chat / assistant /
image-analysis / recap): a request flood burns the free AI quota, which
would degrade the product for everyone. Market-data routes stay open.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# (requests per window per IP, window seconds) per protected path prefix
_RULES: dict[str, tuple[int, float]] = {
    "/api/chat": (10, 60.0),
    "/api/assistant": (20, 60.0),
    "/api/analyze-image": (6, 60.0),
    "/api/recap": (4, 60.0),
}

_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = threading.Lock()

# tests can freeze time
_clock = time.monotonic


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


class AIThrottleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            path = request.url.path
            rule = next((r for prefix, r in _RULES.items() if path.startswith(prefix)), None)
            if rule is None:
                return await call_next(request)

            limit, window = rule
            key = (path.split("/")[2] if path.count("/") > 2 else path, _client_ip(request))
            now = _clock()
            with _lock:
                q = _buckets[key]
                while q and q[0] <= now - window:
                    q.popleft()
                if len(q) >= limit:
                    retry_after = int(q[0] + window - now) + 1
                    return JSONResponse(
                        {"detail": f"Too many requests — try again in {retry_after}s."},
                        status_code=429,
                        headers={"Retry-After": str(retry_after)},
                    )
                q.append(now)
            return await call_next(request)
        except Exception:
            return await call_next(request)  # fail open, always
