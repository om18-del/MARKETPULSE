"""Twelve Data — key-based fallback (time_series daily endpoint)."""

from __future__ import annotations

from ...core.config import get_settings
from .base import ProviderError, client

BASE_URL = "https://api.twelvedata.com/time_series"


class TwelveDataProvider:
    name = "twelvedata"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_settings().twelvedata_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def fetch_history(self, symbol: str) -> list[dict]:
        if not self.api_key:
            raise ProviderError("twelvedata: no api key configured")
        params = {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": 300,
            "apikey": self.api_key,
        }
        try:
            async with client() as http:
                resp = await http.get(BASE_URL, params=params)
        except Exception as exc:
            raise ProviderError(f"twelvedata network error: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"twelvedata HTTP {resp.status_code}")
        data = resp.json()
        if data.get("status") == "error" or "values" not in data:
            raise ProviderError(f"twelvedata: {data.get('message', 'unknown error')}")
        # values are newest-first; validation layer re-sorts
        return [
            {
                "date": v.get("datetime"),
                "open": v.get("open"),
                "high": v.get("high"),
                "low": v.get("low"),
                "close": v.get("close"),
                "volume": v.get("volume"),
            }
            for v in data["values"]
        ]
