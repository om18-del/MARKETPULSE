"""Finnhub — key-based fallback (quote endpoint; free tier is quote-only
for most instruments, so this provider contributes a quote-level fallback
rather than full history)."""

from __future__ import annotations

from ...core.config import get_settings
from .base import ProviderError, client

QUOTE_URL = "https://finnhub.io/api/v1/quote"


class FinnhubProvider:
    name = "finnhub"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_settings().finnhub_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def fetch_history(self, symbol: str) -> list[dict]:
        """Returns a single-row 'history' derived from the live quote."""
        if not self.api_key:
            raise ProviderError("finnhub: no api key configured")
        params = {"symbol": symbol, "token": self.api_key}
        try:
            async with client() as http:
                resp = await http.get(QUOTE_URL, params=params)
        except Exception as exc:
            raise ProviderError(f"finnhub network error: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"finnhub HTTP {resp.status_code}")
        q = resp.json()
        if not q or q.get("c") in (None, 0):
            raise ProviderError("finnhub: no quote for symbol")
        return [{
            "date": q.get("t"),  # epoch seconds; validation parses if possible
            "open": q.get("o"),
            "high": q.get("h"),
            "low": q.get("l"),
            "close": q.get("c"),
            "volume": None,
            "_prev_close": q.get("pc"),
        }]
