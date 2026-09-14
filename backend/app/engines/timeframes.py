"""Multi-timeframe regime stats: Intraday · Daily · Monthly.

The user-facing promise: "show bullish and bearish stats" per timeframe.
For each timeframe we compute a transparent factor battery on that
timeframe's own bars, then map it to a label (BULLISH/BEARISH/NEUTRAL),
a score, confidence and plain-English drivers — zero black box, every
number reproducible from the shown bars.

Intraday = real 5-minute bars (Yahoo, keyless). Monthly = 10 years of
monthly bars. Where a Yahoo symbol is unavailable (e.g. NIFTY Midcap 150
intraday), the timeframe is reported as unavailable — never fabricated.
"""

from __future__ import annotations

from typing import Any

Row = dict[str, Any]


# ----------------------------------------------------------------- math --
def _closes(rows: list[Row]) -> list[float]:
    return [r["close"] for r in rows if r.get("close") is not None]


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0:
        return 100.0 if avg_g > 0 else 50.0
    rs = avg_g / avg_l
    return 100.0 - (100.0 / (1.0 + rs))


def _macd_hist(values: list[float]) -> float | None:
    if len(values) < 35:
        return None

    def ema(vals: list[float], period: int) -> list[float]:
        k = 2 / (period + 1)
        out = [vals[0]]
        for v in vals[1:]:
            out.append(v * k + out[-1] * (1 - k))
        return out

    e12 = ema(values, 12)
    e26 = ema(values, 26)
    macd_line = [a - b for a, b in zip(e12, e26)]
    signal = ema(macd_line, 9)
    return macd_line[-1] - signal[-1]


def _updown_volume(rows: list[Row], window: int = 20) -> float | None:
    """Up-volume / down-volume ratio over the last `window` bars."""
    pairs = [(r.get("close"), r.get("volume")) for r in rows[-window - 1:]]
    pairs = [(c, v) for c, v in pairs if c is not None and v is not None]
    if len(pairs) < 5:
        return None
    up = down = 0.0
    for i in range(1, len(pairs)):
        c, v = pairs[i]
        pc = pairs[i - 1][0]
        if v and pc:
            if c >= pc:
                up += v
            else:
                down += v
    if down == 0:
        return 3.0 if up > 0 else 1.0
    return round(up / down, 3)


# -------------------------------------------------------------- scoring --
_BULL, _BEAR = "BULLISH", "BEARISH"
_NEU = "NEUTRAL"


def timeframe_stats(rows: list[Row], kind: str) -> dict[str, Any]:
    """Bull/bear stats for one timeframe's bars (`kind`: intraday|daily|monthly)."""
    closes = _closes(rows)
    if len(closes) < 10:
        return {"kind": kind, "available": False,
                "reason": f"only {len(closes)} bars — not enough for stats"}

    last = closes[-1]
    first = closes[0]
    period_high = max(closes)
    period_low = min(closes)
    span = (period_high - period_low) or 1.0

    factors: list[dict[str, Any]] = []
    score = 0.0

    # 1. trend: last vs period SMA(20)
    sma20 = _sma(closes, 20)
    if sma20:
        diff_pct = (last / sma20 - 1) * 100
        pts = 1 if diff_pct > 0.15 else (-1 if diff_pct < -0.15 else 0)
        score += pts
        factors.append({
            "name": "price vs SMA20",
            "value": f"{diff_pct:+.2f}%",
            "side": _BULL if pts > 0 else _BEAR if pts < 0 else _NEU,
        })

    # 2. momentum: RSI(14)
    rsi_v = _rsi(closes)
    if rsi_v is not None:
        pts = 1 if rsi_v >= 55 else (-1 if rsi_v <= 45 else 0)
        score += pts
        factors.append({
            "name": "RSI(14)",
            "value": f"{rsi_v:.1f}",
            "side": _BULL if pts > 0 else _BEAR if pts < 0 else _NEU,
        })

    # 3. MACD histogram
    hist = _macd_hist(closes)
    if hist is not None:
        rel = abs(hist) / (last * 0.001 or 1.0)
        pts = 1 if hist > 0 and rel > 0.2 else (-1 if hist < 0 and rel > 0.2 else 0)
        score += pts
        factors.append({
            "name": "MACD histogram",
            "value": f"{hist:+.2f}",
            "side": _BULL if pts > 0 else _BEAR if pts < 0 else _NEU,
        })

    # 4. position in period range (0..1)
    pos = (last - period_low) / span
    pts = 1 if pos > 0.66 else (-1 if pos < 0.33 else 0)
    score += pts
    factors.append({
        "name": "range position",
        "value": f"{pos * 100:.0f}% of {kind} range",
        "side": _BULL if pts > 0 else _BEAR if pts < 0 else _NEU,
    })

    # 5. period return
    period_ret = (last / first - 1) * 100 if first else 0.0
    pts = 1 if period_ret > 0.3 else (-1 if period_ret < -0.3 else 0)
    score += pts
    factors.append({
        "name": f"{kind} return",
        "value": f"{period_ret:+.2f}%",
        "side": _BULL if pts > 0 else _BEAR if pts < 0 else _NEU,
    })

    # 6. volume pressure (skipped for monthly: Yahoo monthly volume unreliable)
    if kind != "monthly":
        ratio = _updown_volume(rows)
        if ratio is not None:
            pts = 1 if ratio > 1.15 else (-1 if ratio < 0.85 else 0)
            score += pts
            factors.append({
                "name": "up/down volume",
                "value": f"{ratio:.2f}",
                "side": _BULL if pts > 0 else _BEAR if pts < 0 else _NEU,
            })

    n = max(len(factors), 1)
    norm = score / n                       # -1..1
    confidence = round(min(95.0, 40.0 + abs(norm) * 55.0), 1)
    label = _BULL if norm > 0.2 else _BEAR if norm < -0.2 else _NEU

    bull = sum(1 for f in factors if f["side"] == _BULL)
    bear = sum(1 for f in factors if f["side"] == _BEAR)
    neu = len(factors) - bull - bear

    drivers = [f"{f['side']}: {f['name']} {f['value']}" for f in factors]
    summary = (
        f"{label.capitalize()} on the {kind} timeframe — {bull} bullish vs "
        f"{bear} bearish signals ({neu} neutral). Latest {kind} close "
        f"{last:,.2f}; {kind} range {period_low:,.2f} – {period_high:,.2f}."
    )

    return {
        "kind": kind,
        "available": True,
        "label": label,
        "score": round(norm, 3),           # -1..1
        "confidence": confidence,
        "bull_count": bull,
        "bear_count": bear,
        "neutral_count": neu,
        "last_close": last,
        "period_low": period_low,
        "period_high": period_high,
        "period_return_pct": round(period_ret, 2),
        "bars": len(rows),
        "factors": factors,
        "drivers": drivers,
        "summary": summary,
    }
