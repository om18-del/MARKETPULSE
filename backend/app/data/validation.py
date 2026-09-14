"""Data validation: every byte from a provider is suspect until proven clean.

Responsibilities
----------------
* Parse messy provider payloads into a normalized OHLCV row format.
* Drop corrupt rows (non-numeric, high < low, zero/negative prices).
* Sort + dedupe by date; keep only the most recent `limit` rows.
* Detect staleness (last bar age) so the UI can flag old data honestly.
* Compute a simple derived quote (last close vs previous close) with
  provenance labeling (which provider, how fresh).
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Any, Iterable


def _f(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        s = str(value).strip().split("T")[0].split(" ")[0]
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def sanitize_ohlcv(rows: Iterable[dict[str, Any]], limit: int = 400) -> list[dict[str, Any]]:
    """Normalize raw provider rows into {date,o,h,l,c,v} sorted ascending.

    Accepts flexible key names (open/Open/1. open, etc.). Corrupt rows are
    dropped silently — but the caller can compare counts to detect abuse.
    """
    key_aliases = {
        "date": ("date", "datetime", "time", "timestamp", "Date"),
        "open": ("open", "o", "1. open", "Open"),
        "high": ("high", "h", "2. high", "High"),
        "low": ("low", "l", "3. low", "Low"),
        "close": ("close", "c", "4. close", "Close", "adjclose", "5. adjusted close"),
        "volume": ("volume", "v", "5. volume", "6. volume", "Volume"),
    }

    def pick(row: dict, field: str) -> Any:
        for alias in key_aliases[field]:
            if alias in row:
                return row[alias]
        # case-insensitive fallback
        lower = {str(k).lower(): v for k, v in row.items()}
        for alias in key_aliases[field]:
            if alias.lower() in lower:
                return lower[alias.lower()]
        return None

    clean: list[dict[str, Any]] = []
    seen: set[date] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        d = parse_date(pick(row, "date"))
        if d is None or d in seen:
            continue
        o = _f(pick(row, "open"))
        h = _f(pick(row, "high"))
        l = _f(pick(row, "low"))
        c = _f(pick(row, "close"))
        v = _f(pick(row, "volume"))
        # Close-only payloads (common for FX/indices) are acceptable:
        if c is None or c <= 0:
            continue
        if h is not None and l is not None and o is not None:
            if h < l or h <= 0 or l <= 0 or o <= 0:
                continue
            # sanity: close within day range (small tolerance)
            if not (l * 0.98 <= c <= h * 1.02):
                continue
        clean.append({"date": d.isoformat(), "open": o, "high": h, "low": l, "close": c, "volume": v})
        seen.add(d)

    clean.sort(key=lambda r: r["date"])
    return clean[-limit:]


def staleness_days(last_date_iso: str | None) -> int | None:
    if not last_date_iso:
        return None
    try:
        last = date.fromisoformat(last_date_iso)
    except ValueError:
        return None
    return (date.today() - last).days


def derive_quote(rows: list[dict[str, Any]], provider: str, fetched_at: datetime | None = None) -> dict[str, Any]:
    """Build a quote from the last two clean bars, with honest provenance."""
    if not rows:
        return {"available": False, "reason": "no valid data after validation", "provider": provider}
    last, prev = rows[-1], (rows[-2] if len(rows) >= 2 else None)
    c_last, c_prev = float(last["close"]), float(prev["close"]) if prev else None
    change = c_last - c_prev if c_prev is not None else None
    change_pct = (change / c_prev * 100) if (c_prev not in (None, 0)) else None
    return {
        "available": True,
        "provider": provider,
        "fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(),
        "last_price": c_last,
        "prev_close": c_prev,
        "change": round(change, 4) if change is not None else None,
        "change_pct": round(change_pct, 2) if change_pct is not None else None,
        "last_bar_date": last["date"],
        "staleness_days": staleness_days(last["date"]),
        "history_points": len(rows),
    }
