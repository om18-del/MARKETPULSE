"""Shared provider plumbing: HTTP client with timeout + ProviderError."""

from __future__ import annotations

import httpx

USER_AGENT = "MarketPulse/1.0 (educational market-literacy app)"
DEFAULT_TIMEOUT = 15.0


class ProviderError(Exception):
    """Raised when a provider fails (network, parse, quota)."""


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )
