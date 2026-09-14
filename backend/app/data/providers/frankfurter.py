"""Frankfurter — keyless FX provider backed by the European Central Bank's
official reference rates (via api.frankfurter.dev).

Covers USD, INR, EUR, GBP, JPY, CNY, AUD, CAD, CHF as daily closes.
Pairs are requested as "BASE:QUOTE" (e.g. "USD:INR"); the API quotes
everything against EUR internally, so we derive the requested pair exactly.
"""

from __future__ import annotations

from datetime import date, timedelta

from .base import ProviderError, client

BASE_URL = "https://api.frankfurter.dev/v1"


class FrankfurterProvider:
    name = "frankfurter"

    def __init__(self) -> None:
        self.available = True  # fully keyless

    async def fetch_history(self, symbol: str) -> list[dict]:
        if ":" not in symbol:
            raise ProviderError("frankfurter: expected BASE:QUOTE symbol")
        base, quote = symbol.split(":", 1)
        start = (date.today() - timedelta(days=400)).isoformat()
        url = f"{BASE_URL}/{start}..?base={base}&symbols={quote}"
        try:
            async with client() as http:
                resp = await http.get(url)
        except Exception as exc:
            raise ProviderError(f"frankfurter network error: {exc}") from exc
        if resp.status_code != 200:
            raise ProviderError(f"frankfurter HTTP {resp.status_code}")
        data = resp.json()
        rates = data.get("rates") or {}
        rows: list[dict] = []
        for day, vals in sorted(rates.items()):
            if quote in vals and vals[quote]:
                rows.append({
                    "date": day,
                    "open": None, "high": None, "low": None,
                    "close": vals[quote], "volume": None,
                })
        if not rows:
            raise ProviderError("frankfurter: no rates returned")
        return rows
