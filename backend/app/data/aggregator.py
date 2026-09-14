"""Aggregator: the fallback brain.

Order: Stooq (keyless) -> Twelve Data -> Finnhub -> Alpha Vantage.
Per-provider circuit breakers + TTL caches. Every result carries
provenance (which provider, cache age) so the UI can show honest labels.
If every provider fails for an instrument, callers fall back to Demo Mode.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..core.cache import CircuitBreaker, TTLCache
from ..core.config import get_settings
from .providers import (
    AlphaVantageProvider,
    FinnhubProvider,
    FrankfurterProvider,
    ProviderError,
    StooqProvider,
    TwelveDataProvider,
)
from .registry import ALL, Instrument, symbol_for
from .validation import derive_quote, sanitize_ohlcv


class Aggregator:
    def __init__(self) -> None:
        s = get_settings()
        self.settings = s
        self.providers = [
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
        """Clean daily history for an instrument with full fallback chain.

        Raises ValueError for unknown instruments; returns dict with
        {'available': bool, 'instrument': ..., 'rows': [...], 'provenance': ...}.
        """
        inst = ALL.get(instrument_id)
        if inst is None:
            raise ValueError(f"unknown instrument: {instrument_id}")

        cache_key = f"hist:{inst.id}"
        if not force_refresh:
            cached = self.history_cache.get(cache_key)
            if cached is not None:
                return cached

        attempts: list[dict[str, Any]] = []
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

    async def get_quote(self, instrument_id: str) -> dict[str, Any]:
        """Freshness-optimized quote: quote cache (60s) -> history chain."""
        inst = ALL.get(instrument_id)
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

        quote = derive_quote(
            hist["rows"], hist["provenance"]["provider"]
        )
        out = {"available": True, "instrument": inst.to_dict(), "quote": quote}
        self.quote_cache.set(cache_key, out, self.settings.quote_ttl_seconds)
        return out

    # ------------------------------------------------------------------
    def health(self) -> dict[str, Any]:
        return {
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


aggregator = Aggregator()


def get_aggregator() -> Aggregator:
    return aggregator


def find_instrument(instrument_id: str) -> Instrument | None:
    return ALL.get(instrument_id)
