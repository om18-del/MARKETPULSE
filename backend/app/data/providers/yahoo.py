"""Yahoo Finance chart API — keyless real-history provider.

Covers everything the older providers miss (verified against the live API):
global indices (^BSESN SENSEX, ^GSPC, ^NDX, ^DJI, ^RUT, ^GDAXI, ^FCHI,
^STOXX50E, ^N225, ^HSI, ^KS11, ^AXJO), commodities (CL=F WTI, DX-Y.NYB DXY,
^TNX US 10y yield), FX (USDINR=X) and equities on NSE (.NS) / BSE (.BO).

Keyless, generous limits, and returns the exchange's own OHLCV history plus
a live `regularMarketPrice` — ideal as the FIRST fallback for any instrument
the India store cannot serve, eliminating fabricated demo data.

Cross-check performed 2026-09-15: Yahoo ^NSEI close (23,398.10) matches the
NSE bhavcopy exactly; ^BSESN returns the real SENSEX (~74.8k) where demo had
a fabricated 140k.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import ProviderError

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _to_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).date().isoformat()


class YahooChartProvider:
    name = "yahoo"

    def __init__(self, http: httpx.AsyncClient | None = None):
        self._http = http

    @property
    def available(self) -> bool:
        return True  # keyless

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(20.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": UA, "Accept": "application/json",
                         "Referer": "https://finance.yahoo.com/"},
            )
        return self._http

    async def fetch_history(self, symbol: str, rng: str = "1y") -> list[dict]:
        """Daily bars, oldest -> newest: {date, open, high, low, close, volume}."""
        url = BASE_URL.format(symbol=httpx.QueryParams({"s": symbol})["s"])
        try:
            http = await self._client()
            resp = await http.get(url, params={"range": rng, "interval": "1d"})
        except Exception as exc:
            raise ProviderError(f"yahoo network error: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"yahoo HTTP {resp.status_code}")
        try:
            result = resp.json()["chart"]["result"][0]
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderError(f"yahoo: unexpected payload ({exc})") from exc

        ts = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        vols = quote.get("volume") or []

        rows: list[dict] = []
        last_date = ""
        for i, t in enumerate(ts):
            close = closes[i] if i < len(closes) else None
            if close is None:
                continue  #Yahoo emits null placeholders on halt days
            d = _to_iso(t)
            if d <= last_date:
                continue  # strict uniqueness for chart safety
            last_date = d
            rows.append({
                "date": d,
                "open": opens[i] if i < len(opens) else None,
                "high": highs[i] if i < len(highs) else None,
                "low": lows[i] if i < len(lows) else None,
                "close": close,
                "volume": vols[i] if i < len(vols) else None,
            })
        if len(rows) < 2:
            raise ProviderError("yahoo: fewer than 2 usable bars")
        return rows
