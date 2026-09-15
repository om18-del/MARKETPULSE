"""Alpha Vantage — key-based last-resort fallback with MULTI-KEY ROTATION.

Free tier: 25 requests/day PER KEY. ALPHAVANTAGE_API_KEY accepts
comma-separated keys; each call picks the next live key, and a key that hits
its daily cap (AV answers with a "Note"/"Information" body) is parked until
the process restarts — calls rotate to the remaining keys instead of failing.
"""

from __future__ import annotations

import itertools

from ...core.config import get_settings
from .base import ProviderError, client

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageProvider:
    name = "alphavantage"

    def __init__(self, api_key: str | None = None):
        raw = api_key or get_settings().alphavantage_api_key
        self._keys = [k.strip() for k in (raw or "").split(",") if k.strip()]
        self._cycle = itertools.cycle(range(len(self._keys))) if self._keys else None
        self._dead: set[str] = set()  # keys that hit their daily cap

    @property
    def api_key(self) -> str | None:
        """Next live key (round-robin), or None when exhausted/unconfigured."""
        live = [k for k in self._keys if k not in self._dead]
        if not live:
            return None
        return live[next(self._cycle) % len(live)] if self._cycle else live[0]

    @property
    def available(self) -> bool:
        return bool(self._keys)

    def _park(self, key: str | None) -> None:
        if key and len(self._keys) > 1:
            self._dead.add(key)

    async def _fetch(self, function: str, symbol: str) -> dict:
        if not self._keys:
            raise ProviderError("alphavantage: no api key configured")
        tried: set[str] = set()
        last_body: dict = {}
        for _ in range(len(self._keys)):
            key = self.api_key
            if not key or key in tried:
                break
            tried.add(key)
            params = {"function": function, "symbol": symbol, "apikey": key}
            try:
                async with client() as http:
                    resp = await http.get(BASE_URL, params=params)
            except Exception as exc:
                raise ProviderError(f"alphavantage network error: {exc}") from exc
            if resp.status_code != 200:
                raise ProviderError(f"alphavantage HTTP {resp.status_code}")
            data = resp.json()
            if "Note" in data or "Information" in data:
                last_body = data
                self._park(key)  # this key's daily cap — rotate to the next
                continue
            return data
        raise ProviderError(f"alphavantage: all keys rate-limited ({len(tried)} tried)")

    async def fetch_history(self, symbol: str) -> list[dict]:
        data = await self._fetch("TIME_SERIES_DAILY", symbol)
        series = data.get("Time Series (Daily)")
        if not series:
            raise ProviderError("alphavantage: unexpected payload")
        return [
            {
                "date": day,
                "open": vals.get("1. open"),
                "high": vals.get("2. high"),
                "low": vals.get("3. low"),
                "close": vals.get("4. close"),
                "volume": vals.get("5. volume"),
            }
            for day, vals in series.items()
        ]

    async def fetch_monthly(self, symbol: str) -> list[dict]:
        """TIME_SERIES_MONTHLY — secondary source for the monthly timeframe
        (verified for BSE .BSE and US symbols on the free tier). Rows are
        newest-first from AV; caller sorts."""
        data = await self._fetch("TIME_SERIES_MONTHLY", symbol)
        series = data.get("Monthly Time Series")
        if not series:
            raise ProviderError("alphavantage: unexpected monthly payload")
        return [
            {
                "date": day,
                "time": day,
                "open": vals.get("1. open"),
                "high": vals.get("2. high"),
                "low": vals.get("3. low"),
                "close": vals.get("4. close"),
                "volume": vals.get("5. volume"),
            }
            for day, vals in sorted(series.items())
        ]
