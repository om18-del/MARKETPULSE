"""Deterministic synthetic daily histories for Demo Mode.

Why generated instead of static files: history stays "current" forever —
the generator always ends at today's date, so the demo never shows stale
bars. Seeded by instrument id => same shape every run (no randomness
between page loads), and every series is labeled DEMO in the API.
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta, timezone

# Seed parameters per instrument: (drift per day %, daily vol %, base price)
PROFILE: dict[str, tuple[float, float, float]] = {
    "sp500": (0.04, 0.8, 6100), "nasdaq": (0.06, 1.1, 22100), "dowjones": (0.03, 0.7, 44200),
    "russell2000": (0.02, 1.2, 2280), "vix": (-0.05, 4.0, 14.5),
    "nifty50": (0.05, 0.8, 24100), "sensex": (0.05, 0.8, 79000), "niftybank": (0.06, 1.0, 52000),
    "niftyit": (0.07, 1.1, 38500), "niftynext50": (0.06, 0.9, 68000),
    "niftymidcap150": (0.07, 1.0, 17500), "niftysmallcap250": (0.08, 1.2, 16500),
    "niftyfin": (0.05, 0.9, 24500),
    "ftse100": (0.02, 0.7, 8300), "dax": (0.04, 0.9, 20200), "cac40": (0.03, 0.9, 7600),
    "eurostoxx50": (0.03, 0.9, 4900), "nikkei225": (0.05, 1.1, 39000),
    "hangseng": (-0.02, 1.3, 20100), "kospi": (0.02, 1.1, 2650), "asx200": (0.02, 0.8, 8200),
    "gold": (0.05, 0.8, 2900), "crude": (-0.03, 1.8, 71), "dxy": (-0.01, 0.4, 104),
    "us10y": (0.0, 1.5, 4.25),
    "usdinr": (0.01, 0.25, 86.2), "eurusd": (-0.02, 0.4, 1.08), "gbpusd": (-0.01, 0.45, 1.27),
    "usdjpy": (0.03, 0.5, 149), "usdcny": (0.00, 0.15, 7.25), "audusd": (-0.02, 0.5, 0.65),
    "usdcad": (0.01, 0.35, 1.36), "usdchf": (0.00, 0.4, 0.88),
    "reliance": (0.05, 1.3, 2950), "tcs": (0.04, 1.2, 4100), "hdfcbank": (0.04, 1.2, 1750),
    "infy": (0.04, 1.3, 1850), "icicibank": (0.06, 1.2, 1280), "sbin": (0.05, 1.4, 810),
    "bhartiartl": (0.08, 1.2, 1620), "lt": (0.06, 1.1, 3550), "itc": (0.03, 0.9, 445),
    "axisbank": (0.04, 1.3, 1150),
    "aapl": (0.06, 1.4, 232), "msft": (0.06, 1.3, 428),
    "googl": (0.05, 1.5, 178), "tsla": (0.02, 2.8, 330), "amzn": (0.05, 1.6, 205),
    "nvda": (0.12, 2.5, 128),
}


def _seeded_wave(seed: str, i: int) -> float:
    """Deterministic pseudo-random value in roughly [-1, 1] from a stable hash."""
    h = hashlib.sha256(f"{seed}:{i}".encode()).digest()
    a, b, c = h[0], h[1], h[2]
    return (a - 127.5) / 127.5 * 0.6 + (b - 127.5) / 127.5 * 0.3 + math.sin(i * (c % 7 + 1) / 4.0) * 0.1


def _volume_for(instrument_id: str, i: int) -> int:
    h = int(hashlib.sha256(f"{instrument_id}{i}".encode()).hexdigest(), 16)
    return 1_000_000 + h % 900_000


def generate_history(instrument_id: str, days: int = 400) -> list[dict]:
    """`days` = calendar window ending TODAY (never future dates)."""
    profile = PROFILE.get(instrument_id, (0.03, 1.0, 100.0))
    drift, vol, base = profile
    end = date.today()
    start = end - timedelta(days=days)
    trading_days = sum(
        1 for i in range(days + 1) if (start + timedelta(days=i)).weekday() < 5
    )
    rows: list[dict] = []
    price = base / (1 + drift / 100) ** max(trading_days, 1)  # walk back from today's base
    trading = 0
    cal = start
    while cal <= end:
        if cal.weekday() < 5:  # skip weekends
            trading += 1
            w = _seeded_wave(instrument_id, trading)
            shock = w * vol / 100
            # occasional regime shift for realism
            if trading % 47 == 0:
                drift_step = 0.15 if _seeded_wave(instrument_id, trading + 999) > 0 else -0.15
            else:
                drift_step = 0.0
            price = price * (1 + drift / 100 + drift_step + shock)
            price = max(price, base * 0.3)
            hi = price * (1 + abs(w) * vol / 250)
            lo = price * (1 - abs(w) * vol / 250)
            rows.append({
                "date": cal.isoformat(),
                "open": round(lo * 1.0005, 4), "high": round(hi, 4),
                "low": round(lo, 4), "close": round(price, 4),
                "volume": _volume_for(instrument_id, trading),
            })
        cal += timedelta(days=1)
    return rows


def demo_history(instrument_id: str) -> dict:
    """Demo history payload shaped exactly like an aggregator result."""
    rows = generate_history(instrument_id)
    return {
        "available": True,
        "instrument": None,  # filled by caller
        "rows": rows,
        "provenance": {
            "provider": "demo",
            "demo": True,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
    }
