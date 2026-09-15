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

from datetime import datetime, timedelta, timezone

import httpx

from .base import ProviderError

HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")  # dual-host retry
BASE_URL = "https://{host}/v8/finance/chart/{symbol}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _to_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).date().isoformat()


def _to_key(epoch: float, interval: str) -> str:
    """Chart key: date for 1d/1mo, date+HH:MM (IST) for intraday intervals."""
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    if interval in ("1d", "1mo"):
        return dt.date().isoformat()
    # NSE/BSE trade in IST; Yahoo's epoch needs +5:30 for correct session labels
    ist = timezone(timedelta(hours=5, minutes=30))
    local = datetime.fromtimestamp(epoch, tz=ist)
    return f"{local.date().isoformat()} {local:%H:%M}"


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
        return await self.fetch_bars(symbol, rng=rng, interval="1d")

    async def fetch_bars(self, symbol: str, *, rng: str, interval: str) -> list[dict]:
        """Bars at any Yahoo interval (5m intraday, 1d, 1mo monthly).

        Rows: {time, open, high, low, close, volume} oldest -> newest with
        strictly unique ascending `time` keys ("YYYY-MM-DD" for daily/monthly,
        "YYYY-MM-DD HH:MM" for intraday) so the UI chart can consume them
        directly without crashing on duplicates.
        """
        sym = httpx.QueryParams({"s": symbol})["s"]
        try:
            http = await self._client()
        except Exception as exc:
            raise ProviderError(f"yahoo network error: {exc}") from exc
        resp = None
        last_err: Exception | None = None
        for host in HOSTS:  # rotate hosts before giving up (rate-limit resilience)
            url = BASE_URL.format(host=host, symbol=sym)
            try:
                resp = await http.get(url, params={"range": rng, "interval": interval})
                if resp.status_code == 429:
                    last_err = ProviderError(f"yahoo {host}: HTTP 429 (rate limited)")
                    continue
                break
            except Exception as exc:
                last_err = exc
                continue
        if resp is None:
            raise ProviderError(f"yahoo network error: {last_err}") from last_err

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
        last_key = ""
        for i, t in enumerate(ts):
            close = closes[i] if i < len(closes) else None
            if close is None:
                continue  # Yahoo emits null placeholders on halt days
            key = _to_key(t, interval)
            if key <= last_key:
                continue  # strict uniqueness for chart safety
            last_key = key
            rows.append({
                "time": key,
                "date": key.split(" ")[0],
                "open": opens[i] if i < len(opens) else None,
                "high": highs[i] if i < len(highs) else None,
                "low": lows[i] if i < len(lows) else None,
                "close": close,
                "volume": vols[i] if i < len(vols) else None,
            })
        if len(rows) < 2:
            raise ProviderError("yahoo: fewer than 2 usable bars")
        return rows
