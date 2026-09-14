"""PRISM live tracing (optional, fail-open).

Forwards every real Gemini call to the PRISM dashboard: model, latency,
input/output sizes, and a session id so calls group into trajectories.

Design rules:
* Never raises, never blocks longer than its HTTP timeout — observability
  must not add failure modes or latency to MarketPulse itself.
* Disabled cleanly when PRISMTRACE_API_KEY / PRISMTRACE_PROJECT_ID are unset.
* The real api key lives only in backend/.env (gitignored) or the secret
  manager; `.env.example` carries the names only.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

log = logging.getLogger("marketpulse.prism")

_client: Any | None = None
_client_checked = False
_session = "marketpulse-api"


def _get() -> Any | None:
    """Lazy PRISMtrace client; None when not configured."""
    global _client, _client_checked
    if not _client_checked:
        _client_checked = True
        from ..core.config import get_settings

        s = get_settings()
        if s.prismtrace_api_key and s.prismtrace_project_id:
            try:
                from prismtrace import PRISMtrace

                _client = PRISMtrace(
                    api_key=s.prismtrace_api_key,
                    host=s.prismtrace_host,
                    project_id=s.prismtrace_project_id,
                    timeout=5,
                )
                log.info("PRISM tracing enabled (%s)", s.prismtrace_host)
            except Exception as exc:
                log.warning("PRISM init failed — tracing disabled: %s", exc)
    return _client


def set_session(session_id: str) -> None:
    """Group subsequent LLM traces under one trajectory id."""
    global _session
    if session_id:
        _session = session_id


def current_session() -> str:
    return _session


async def emit_llm(*, model: str, prompt: str, output: str, latency_ms: float,
                   session: str | None = None, metadata: dict | None = None) -> None:
    """Send one LLM-call trace. Fire-and-forget: errors are logged, never raised."""
    pt = _get()
    if pt is None:
        return

    def _post() -> None:
        pt.trace_llm(
            model=model,
            input_messages=[{"role": "user", "content": str(prompt)[:4000]}],
            output=str(output)[:8000],
            latency_ms=int(latency_ms),
            agent_name="marketpulse",
            session_id=session or _session,
            metadata=metadata or {},
        )
        pt.flush(timeout=2.0)

    try:
        await asyncio.to_thread(_post)
    except Exception as exc:
        log.debug("PRISM trace dropped: %s", exc)


def now_ms() -> float:
    return time.perf_counter() * 1000.0
