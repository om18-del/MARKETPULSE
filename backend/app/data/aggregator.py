"""Aggregator: the fallback brain.

India-first routing:
* Indian instruments -> IndiaStore (official NSE EOD files: the daily
  bhavcopy + ind_close_all index file, keyless, honest data dates).
* Global instruments -> Yahoo chart API (keyless, real exchange data for
  every global index/commodity/rate) -> Stooq -> Frankfurter(FX)
  -> Twelve Data -> Finnhub -> Alpha Vantage (each behind a circuit
  breaker; keyless first).

Every result carries provenance (provider, data date, cache age) so the UI
can show honest labels. If every provider fails for an instrument, callers
fall back to Demo Mode.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..core.cache import CircuitBreaker, TTLCache
from ..core.config import get_settings
from .india_store import get_store
from .providers import (
    AlphaVantageProvider,
    FinnhubProvider,
    FrankfurterProvider,
    ProviderError,
    StooqProvider,
    TwelveDataProvider,
    YahooChartProvider,
)
from .registry import ALL, Instrument, symbol_for
from .validation import derive_quote, sanitize_ohlcv


class Aggregator:
    def __init__(self) -> None:
        s = get_settings()
        self.settings = s
        self.india = get_store()
        self.providers = [
            YahooChartProvider(),   # keyless real data for every global instrument
            StooqProvider(),
            FrankfurterProvider(),  # keyless ECB FX — keeps FX alive without any keys
            TwelveDataProvider(),
            FinnhubProvider(),
            AlphaVantageProvider(),
        ]
        self.breakers: dict[str, CircuitBreaker] = {
            p.name: CircuitBreaker() for p in self.providers
        }
        self.quote_cache = TTLCache()
        self.history_cache = TTLCache()

    # ------------------------------------------------------------------
    async def get_history(self, instrument_id: str, force_refresh: bool = False) -> dict[str, Any]:
        """Clean daily history for an instrument with India-first fallback chain.

        Raises ValueError for unknown instruments; returns dict with
        {'available': bool, 'instrument': ..., 'rows': [...], 'provenance': ...}.
        """
        inst = ALL.get(instrument_id)
        if inst is None:
            inst = await self.dynamic_instrument(instrument_id)
        if inst is None:
            raise ValueError(f"unknown instrument: {instrument_id}")

        cache_key = f"hist:{inst.id}"
        if not force_refresh:
            cached = self.history_cache.get(cache_key)
            if cached is not None:
                return cached

        attempts: list[dict[str, Any]] = []

        # ------------- India-first: official NSE EOD files -------------
        if inst.region == "india":
            try:
                rows = await self._india_history_rows(inst)
                if len(rows) < 2:
                    raise ProviderError("NSE files had no usable rows")
                result = {
                    "available": True,
                    "instrument": inst.to_dict(),
                    "rows": rows,
                    "provenance": {
                        "provider": "nse-archives (official EOD files)",
                        "data_date": rows[-1]["date"],
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "attempts": [{"provider": "nse-archives", "ok": True}],
                    },
                }
                self.history_cache.set(cache_key, result, self.settings.daily_ttl_seconds)
                return result
            except ProviderError as exc:
                attempts.append({"provider": "nse-archives", "error": str(exc)})

        # ------------------- global provider chain --------------------
        for provider in self.providers:
            symbol = symbol_for(inst, provider.name)
            if not symbol:
                attempts.append({"provider": provider.name, "skipped": "no symbol mapping"})
                continue
            if not getattr(provider, "available", True):
                attempts.append({"provider": provider.name, "skipped": "no api key"})
                continue
            breaker = self.breakers[provider.name]
            if breaker.is_open:
                attempts.append({"provider": provider.name, "skipped": "circuit open"})
                continue
            try:
                raw = await provider.fetch_history(symbol)
                rows = sanitize_ohlcv(raw)
                if len(rows) < 2:
                    raise ProviderError("insufficient valid rows after validation")
                breaker.record_success()
                result = {
                    "available": True,
                    "instrument": inst.to_dict(),
                    "rows": rows,
                    "provenance": {
                        "provider": provider.name,
                        "data_date": rows[-1]["date"],
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "attempts": attempts + [{"provider": provider.name, "ok": True}],
                    },
                }
                self.history_cache.set(cache_key, result, self.settings.daily_ttl_seconds)
                return result
            except ProviderError as exc:
                breaker.record_failure(str(exc))
                attempts.append({"provider": provider.name, "error": str(exc)})
                continue

        return {
            "available": False,
            "instrument": inst.to_dict(),
            "rows": [],
            "provenance": {"attempts": attempts, "fetched_at": datetime.now(timezone.utc).isoformat()},
        }

    # ------------------------------------------------------------------
    async def _india_history_rows(self, inst: Instrument) -> list[dict]:
        """Daily bars from official NSE files for stocks and indices."""
        if inst.category == "index" and inst.nse_index:
            rows = await self.india.index_history(inst.nse_index, min_bars=70)
        else:
            sym = inst.nse or inst.id.upper()
            rows = await self.india.stock_history(sym, min_bars=70)
        return rows

    async def get_quote(self, instrument_id: str) -> dict[str, Any]:
        """Freshness-optimized quote: quote cache (60s) -> history chain."""
        inst = ALL.get(instrument_id)
        if inst is None:
            inst = await self.dynamic_instrument(instrument_id)
        if inst is None:
            raise ValueError(f"unknown instrument: {instrument_id}")

        cache_key = f"quote:{inst.id}"
        cached = self.quote_cache.get(cache_key)
        if cached is not None:
            return cached

        hist = await self.get_history(inst.id)
        if not hist["available"]:
            out = {"available": False, "instrument": inst.to_dict(), "reason": "all providers failed"}
            self.quote_cache.set(cache_key, out, 30)  # brief negative cache
            return out

        quote = derive_quote(hist["rows"], hist["provenance"]["provider"])
        out = {"available": True, "instrument": inst.to_dict(), "quote": quote}
        self.quote_cache.set(cache_key, out, self.settings.quote_ttl_seconds)
        return out

    # ------------------------------------------------------------------
    def health(self) -> dict[str, Any]:
        return {
            "india_store": self.india.health(),
            "providers": {
                name: {"available": getattr(p, "available", True), **br.status()}
                for (name, br), p in zip(
                    [(p.name, self.breakers[p.name]) for p in self.providers], self.providers
                )
            },
            "quote_cache_hits": self.quote_cache.hits,
            "quote_cache_misses": self.quote_cache.misses,
        }

    def clear_caches(self) -> None:
        self.quote_cache.clear()
        self.history_cache.clear()

    # ------------------------------------------------------------------
    async def dynamic_instrument(self, instrument_id: str) -> Instrument | None:
        """Resolve dynamic ids against the Dhan name master.

        The full NSE + BSE listed universe (~2000 + ~4500 equities) becomes
        searchable/trackable without hardcoding anything:
        * `nse-<symbol>` — NSE path: official NSE bhavcopy history.
        * `bse-<symbol>` — BSE path: Yahoo (.BO, keyless) daily history
          with Alpha Vantage as a last-resort fallback (its 25 req/day
          free quota made it the primary — that cliff is gone).
        """
        if instrument_id.startswith("nse-"):
            sym = instrument_id[4:].upper().replace("%20", " ")
            names = await self.india.names()
            name = names["nse"].get(sym) or sym
            return Instrument(
                id=f"nse-{sym.lower()}", name=name, category="stock",
                region="india", currency="INR", stooq=None, twelvedata=None,
                finnhub=None, alphavantage=None, nse=sym,
                weight=0.6, keywords=(sym.lower(),),
            )
        if instrument_id.startswith("bse-"):
            sym = instrument_id[4:].upper().replace("%20", " ")
            names = await self.india.names()
            name = names["bse"].get(sym) or names["nse"].get(sym) or sym
            return Instrument(
                id=f"bse-{sym.lower()}", name=name, category="stock",
                region="india", currency="INR", stooq=None, twelvedata=None,
                finnhub=None, alphavantage=f"{sym}.BO", nse=None,
                yahoo=f"{sym}.BO",
                weight=0.6, keywords=(sym.lower(),),
            )
        return None


aggregator = Aggregator()


def get_aggregator() -> Aggregator:
    return aggregator


def find_instrument(instrument_id: str) -> Instrument | None:
    return ALL.get(instrument_id)
