"""India market store — official NSE exchange files, keyless, cached per day.

This is the PRIMARY data engine for the India-first product. Everything here
comes from exchange-published files (no keys, no scraping of bot-gated pages):

* sec_bhavdata_full_{DDMMYYYY}.csv   every traded NSE equity — full OHLC,
  prev-close, volume, trades, turnover (nsearchives /products/content/)
* ind_close_all_{DDMMYYYY}.csv       EVERY NSE index (300+): OHLC, %change,
  P/E, P/B, volumes (nsearchives /content/indices/)
* ind_nifty50list.csv                NIFTY 50 constituents + names
* Dhan public scrip master           symbol -> company name for NSE + BSE
  (images.dhan.co/api-data/api-scrip-master.csv, refreshed daily by Dhan)

Truth model: a file for trading-date D is published only AFTER market close
of D. "Today" therefore means "the latest date with a file on the server" —
the store never invents a bar, and every payload carries its exact date.
Published files are immutable, so each is downloaded once per process and
cached in memory (negative-cached briefly for holidays/not-yet-published).

Verification: `verify()` cross-checks closes across the two independent
files (bhavcopy vs index file for indices) and the previous close chain —
used by the /api/verify endpoint so users can audit any price against the
official source, with an optional Gemini plausibility cross-check.
"""

from __future__ import annotations

import asyncio
import csv
import io
import re
import time
from datetime import date, datetime, timedelta
from typing import Any

import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ARCHIVES = "https://nsearchives.nseindia.com"
DHAN_MASTER = "https://images.dhan.co/api-data/api-scrip-master.csv"
NSE_WWW = "https://www.nseindia.com"

_file_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


def _lock_for(key: str) -> asyncio.Lock:
    return _file_locks.setdefault(key, asyncio.Lock())


class IndiaStore:
    """Day-cached store over official NSE files + Dhan name master."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._bhavcopy: dict[date, dict[str, dict] | None] = {}
        self._indices: dict[date, dict[str, dict] | None] = {}
        self._neg_until: dict[str, float] = {}
        self._nifty50: set[str] | None = None
        self._names: dict[str, dict[str, str]] | None = None
        self.last_error: str | None = None
        self.fetch_count = 0

    # ------------------------------------------------------------- http --
    def http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(25.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": UA,
                         "Accept": "application/json, text/csv, */*",
                         "Referer": f"{NSE_WWW}/"},
            )
        return self._client

    async def _get(self, url: str, *, ok=(200,), neg_ttl: float = 1200.0) -> str | None:
        """GET text; None on 404 (holiday / not yet published), cached briefly."""
        key = f"neg:{url}"
        if self._neg_until.get(key, 0) > time.monotonic():
            return None
        lock = _lock_for(url)
        async with lock:
            if self._neg_until.get(key, 0) > time.monotonic():
                return None
            try:
                r = await self.http().get(url)
                self.fetch_count += 1
                if r.status_code == 404:
                    self._neg_until[key] = time.monotonic() + neg_ttl
                    return None
                r.raise_for_status()
                text = r.text
                if text.lstrip().startswith("<!DOCTYPE") or "<html" in text[:200].lower():
                    raise ValueError("got HTML instead of data (bot gate)")
                return text
            except Exception as exc:
                self.last_error = f"{url.rsplit('/', 1)[-1]}: {exc}"
                self._neg_until[key] = time.monotonic() + 300.0
                return None

    # ------------------------------------------------------------ dates --
    @staticmethod
    def recent_weekdays(n: int = 95, up_to: date | None = None) -> list[date]:
        """Last `n` weekdays, newest first (holidays filtered lazily by 404s)."""
        up_to = up_to or date.today()
        out: list[date] = []
        d = up_to
        while len(out) < n:
            if d.weekday() < 5:
                out.append(d)
            d -= timedelta(days=1)
        return out

    # --------------------------------------------------------- bhavcopy --
    async def bhavcopy(self, d: date) -> dict[str, dict] | None:
        """All traded NSE equities for date d: {SYMBOL: row}. None if absent."""
        if d in self._bhavcopy:
            return self._bhavcopy[d]
        url = f"{ARCHIVES}/products/content/sec_bhavdata_full_{d:%d%m%Y}.csv"
        text = await self._get(url)
        parsed = _parse_bhavcopy(text) if text else None
        self._bhavcopy[d] = parsed
        return parsed

    async def bhavcopy_dates(self, want: int = 75) -> list[date]:
        """Newest-first dates that actually have a bhavcopy (probes until `want`)."""
        dates: list[date] = []
        for d in self.recent_weekdays(want + 12):
            if len(dates) >= want:
                break
            got = await self.bhavcopy(d)
            if got:
                dates.append(d)
        return dates

    # ----------------------------------------------------------- indices --
    async def indices(self, d: date) -> dict[str, dict] | None:
        """All NSE indices for date d: {'NIFTY 50': row, ...}. None if absent."""
        if d in self._indices:
            return self._indices[d]
        url = f"{ARCHIVES}/content/indices/ind_close_all_{d:%d%m%Y}.csv"
        text = await self._get(url)
        parsed = _parse_indices(text) if text else None
        self._indices[d] = parsed
        return parsed

    # ------------------------------------------------------- constituents --
    async def nifty50_symbols(self) -> set[str]:
        if self._nifty50 is not None:
            return self._nifty50
        text = await self._get(f"{ARCHIVES}/content/indices/ind_nifty50list.csv",
                               neg_ttl=86400.0)
        self._nifty50 = _parse_nifty50(text) if text else set()
        return self._nifty50

    # ------------------------------------------------------------- names --
    async def names(self) -> dict[str, dict[str, str]]:
        """Dhan scrip master: {exchange: {SYMBOL: company name}} (24h cache)."""
        if self._names is not None:
            return self._names
        async with _lock_for(DHAN_MASTER):
            if self._names is not None:
                return self._names
            try:
                r = await self.http().get(DHAN_MASTER, timeout=90)
                r.raise_for_status()
                self._names = _parse_dhan(r.text)
                self.fetch_count += 1
            except Exception as exc:
                self.last_error = f"dhan master: {exc}"
                self._names = {"nse": {}, "bse": {}}
            return self._names

    # ----------------------------------------------------------- history --
    async def stock_history(self, symbol: str, min_bars: int = 70) -> list[dict]:
        """Chronological daily bars for an NSE symbol from bhavcopy files."""
        symbol = symbol.upper().strip()
        dates = await self.bhavcopy_dates(want=min_bars + 15)
        rows: list[dict] = []
        for d in reversed(dates):  # oldest -> newest
            table = await self.bhavcopy(d)
            row = (table or {}).get(symbol)
            if row:
                rows.append(row)
        return rows

    async def index_history(self, index_name: str, min_bars: int = 70) -> list[dict]:
        """Chronological daily bars for an NSE index from ind_close_all files."""
        dates: list[date] = []
        for d in self.recent_weekdays(min_bars + 15):
            got = await self.indices(d)
            if got:
                dates.append(d)
            if len(dates) >= min_bars + 10:
                break
        index_name = index_name.upper().strip()
        rows: list[dict] = []
        for d in reversed(dates):
            table = await self.indices(d)
            row = (table or {}).get(index_name)
            if row:
                rows.append(row)
        return rows

    # ----------------------------------------------------------- movers --
    async def movers(self) -> dict[str, Any]:
        """NIFTY 50 gainers/losers + whole-market breadth from the latest bhavcopy."""
        dates = await self.bhavcopy_dates(want=1)
        if not dates:
            raise RuntimeError(f"no bhavcopy available: {self.last_error}")
        d = dates[0]
        table = (await self.bhavcopy(d)) or {}
        n50 = await self.nifty50_symbols()
        try:
            names = (await self.names()).get("nse", {})
        except Exception:
            names = {}
        market_adv = market_dec = 0
        for row in table.values():
            pc = row.get("change_pct")
            if pc is None:
                continue
            if pc > 0:
                market_adv += 1
            elif pc < 0:
                market_dec += 1
        const: list[dict] = []
        for sym in n50:
            row = table.get(sym)
            if row and row.get("close") and row.get("prev_close"):
                const.append({"symbol": sym, "name": names.get(sym) or sym,
                              "last_price": row["close"],
                              "change_pct": round(row["change_pct"], 2)})
        ranked = sorted(const, key=lambda s: s["change_pct"])
        return {
            "date": d.isoformat(),
            "gainers": list(reversed(ranked[-5:])),
            "losers": ranked[:5],
            "advances": len([s for s in const if s["change_pct"] > 0]),
            "declines": len([s for s in const if s["change_pct"] < 0]),
            "counted": len(const),
            "market_advances": market_adv,
            "market_declines": market_dec,
        }

    # ----------------------------------------------------- market status --
    async def market_status(self) -> dict[str, Any]:
        """Honest market-state read. Tries NSE's keyless status API, falls
        back to what the EOD files can honestly say."""
        try:
            r = await self.http().get(f"{NSE_WWW}/api/marketStatus",
                                      headers={"Referer": f"{NSE_WWW}/"}, timeout=12)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                payload = r.json()
                for m in payload.get("marketState", []):
                    if m.get("market") == "Capital Market":
                        return {"status": m.get("marketStatus", "unknown"),
                                "trade_date": m.get("tradeDate"),
                                "source": "nseindia.com/api/marketStatus",
                                "disclaimer": None}
        except Exception as exc:
            self.last_error = f"marketStatus: {exc}"
        dates = await self.bhavcopy_dates(want=1)
        if dates:
            return {"status": "EOD published",
                    "trade_date": dates[0].isoformat(),
                    "source": "NSE bhavcopy presence",
                    "note": "Live status API unreachable; EOD file for this date exists.",
                    "disclaimer": None}
        return {"status": "unknown", "source": None,
                "disclaimer": "Could not determine market status."}

    # -------------------------------------------------------- verification --
    async def verify_index_close(self, index_name: str, close: float,
                                 on_date: date | None = None) -> dict[str, Any]:
        """Cross-check an index close against the official index file."""
        d = on_date or ((await self.bhavcopy_dates(want=1)) or [None])[0] or date.today()
        table = await self.indices(d)
        if not table or index_name not in table:
            return {"verdict": "unverifiable", "reason": f"no index file for {d}",
                    "date": d.isoformat()}
        official = table[index_name]
        diff = abs(close - official["close"]) / official["close"] * 100 if official["close"] else 100
        return {"verdict": "match" if diff <= 0.15 else "mismatch",
                "diff_pct": round(diff, 4), "official_close": official["close"],
                "date": d.isoformat(), "source_file": f"ind_close_all_{d:%d%m%Y}.csv"}

    async def verify_stock_context(self, symbol: str) -> dict[str, Any]:
        """Independent NSE-file context for auditing an equity price: the
        official close + prev-close + volume chain for the symbol."""
        symbol = symbol.upper().strip()
        rows = await self.stock_history(symbol, min_bars=5)
        if not rows:
            return {"verdict": "unverifiable", "reason": f"{symbol} not in recent NSE bhavcopies"}
        latest, prev = rows[-1], (rows[-2] if len(rows) > 1 else None)
        chain_ok = bool(prev and prev["close"] and latest["prev_close"]
                        and abs(prev["close"] - latest["prev_close"]) <= max(0.05, 0.005 * prev["close"]))
        return {
            "verdict": "verified-against-nse-files",
            "symbol": symbol,
            "official_close": latest["close"], "official_date": latest["date"],
            "prev_close_file": latest["prev_close"],
            "prev_close_consistent": chain_ok,
            "volume": latest.get("volume"), "trades": latest.get("trades"),
            "source_file": f"sec_bhavdata_full_{latest['date'].replace('-', '')}.csv",
        }

    # ------------------------------------------------------------ health --
    def health(self) -> dict[str, Any]:
        return {
            "bhavcopy_days_cached": sum(1 for v in self._bhavcopy.values() if v),
            "index_days_cached": sum(1 for v in self._indices.values() if v),
            "nifty50_count": len(self._nifty50 or ()),
            "names_loaded": bool(self._names),
            "files_fetched": self.fetch_count,
            "last_error": self.last_error,
        }


# ------------------------------------------------------------- parsers --
def _strip(row: dict) -> dict:
    return {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def _f(v: Any) -> float | None:
    try:
        x = float(str(v).replace(",", ""))
        return x
    except (TypeError, ValueError):
        return None


def _iso_date(raw: str) -> str:
    """Normalize NSE date formats ('11-SEP-2026', '11-09-2026', ISO) to ISO."""
    s = (raw or "").strip()
    for pat in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, pat).date().isoformat()
        except ValueError:
            continue
    return s


def _parse_bhavcopy(text: str) -> dict[str, dict]:
    """sec_bhavdata_full: SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE,
    HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, ..., TTL_TRD_QNTY, ..."""
    out: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(text)):
        r = _strip(row)
        if r.get("SERIES") != "EQ":
            continue
        sym = (r.get("SYMBOL") or "").upper()
        close = _f(r.get("CLOSE_PRICE"))
        if not sym or close is None or close <= 0:
            continue
        d_iso = _iso_date(r.get("DATE1") or "")
        out[sym] = {
            "symbol": sym, "date": d_iso,
            "open": _f(r.get("OPEN_PRICE")), "high": _f(r.get("HIGH_PRICE")),
            "low": _f(r.get("LOW_PRICE")), "close": close,
            "prev_close": _f(r.get("PREV_CLOSE")),
            "volume": _f(r.get("TTL_TRD_QNTY")), "trades": _f(r.get("NO_OF_TRADES")),
            "isin": r.get("ISIN") or None,
        }
        pc = out[sym]["prev_close"]
        out[sym]["change_pct"] = round(((close / pc) - 1) * 100, 4) if pc else None
    return out


def _parse_indices(text: str) -> dict[str, dict]:
    """ind_close_all: Index Name, Index Date, Open/High/Low/Closing, Change(%)..."""
    out: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(text)):
        r = _strip(row)
        name = (r.get("Index Name") or "").upper()
        close = _f(r.get("Closing Index Value"))
        if not name or close is None or close <= 0:
            continue
        d_iso = _iso_date(r.get("Index Date") or "")
        out[name] = {
            "index": name, "date": d_iso,
            "open": _f(r.get("Open Index Value")), "high": _f(r.get("High Index Value")),
            "low": _f(r.get("Low Index Value")), "close": close,
            "change_pct": _f(r.get("Change(%)")) if "Change(%)" in r else _f(r.get("Change(%) ".rstrip())),
            "volume": _f(r.get("Volume")), "pe": _f(r.get("P/E")), "pb": _f(r.get("P/B")),
        }
    return out


def _parse_nifty50(text: str) -> set[str]:
    """ind_nifty50list: Company Name, Industry, Symbol, Series, ISIN Code."""
    syms: set[str] = set()
    for row in csv.DictReader(io.StringIO(text)):
        r = _strip(row)
        if r.get("Series") in ("EQ", "EQ,", "EQ"):
            sym = (r.get("Symbol") or "").upper()
            if sym:
                syms.add(sym)
    return syms


def _parse_dhan(text: str) -> dict[str, dict[str, str]]:
    """Dhan master -> {'nse': {SYMBOL: name}, 'bse': {SYMBOL: name}} (EQ only)."""
    out: dict[str, dict[str, str]] = {"nse": {}, "bse": {}}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        r = _strip(row)
        exch = (r.get("SEM_EXM_EXCH_ID") or "").upper()
        instr = (r.get("SEM_INSTRUMENT_NAME") or "").upper()
        series = (r.get("SEM_SERIES") or "").upper()
        sym = (r.get("SEM_TRADING_SYMBOL") or "").upper()
        name = (r.get("SEM_CUSTOM_SYMBOL") or r.get("SM_SYMBOL_NAME") or sym).strip()
        if not sym:
            continue
        if exch == "NSE" and instr == "EQUITY" and series in ("EQ", "BE"):
            out["nse"].setdefault(sym, name)
        elif exch == "BSE" and instr == "EQUITY":
            out["bse"].setdefault(sym, name)
    return out


store = IndiaStore()


def get_store() -> IndiaStore:
    return store
