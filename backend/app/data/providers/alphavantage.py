"""Alpha Vantage — key-based last-resort fallback (TIME_SERIES_DAILY)."""

from __future__ import annotations

from ...core.config import get_settings
from .base import ProviderError, client

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageProvider:
    name = "alphavantage"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_settings().alphavantage_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def fetch_history(self, symbol: str) -> list[dict]:
        if not self.api_key:
            raise ProviderError("alphavantage: no api key configured")
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",
            "apikey": self.api_key,
        }
        try:
            async with client() as http:
                resp = await http.get(BASE_URL, params=params)
        except Exception as exc:
            raise ProviderError(f"alphavantage network error: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"alphavantage HTTP {resp.status_code}")
        data = resp.json()
        if "Note" in data or "Information" in data:
            raise ProviderError("alphavantage: rate limit reached")
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
        if not self.api_key:
            raise ProviderError("alphavantage: no api key configured")
        params = {
            "function": "TIME_SERIES_MONTHLY",
            "symbol": symbol,
            "apikey": self.api_key,
        }
        try:
            async with client() as http:
                resp = await http.get(BASE_URL, params=params)
        except Exception as exc:
            raise ProviderError(f"alphavantage network error: {exc}") from exc
        if resp.status_code != 200:
            raise ProviderError(f"alphavantage HTTP {resp.status_code}")
        data = resp.json()
        if "Note" in data or "Information" in data:
            raise ProviderError("alphavantage: rate limit reached")
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
