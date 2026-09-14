"""Multi-timeframe regime stats: Intraday · Daily · Monthly.

The user-facing promise: "show bullish and bearish stats" per timeframe —
in detail. For each timeframe we compute a transparent factor battery on
that timeframe's own bars, then map it to a label (BULLISH/BEARISH/NEUTRAL),
a score, confidence, a hard-numbers metrics grid, and a plain-English
explanation for every factor — zero black box, every number reproducible
from the shown bars.

Intraday = real 5-minute bars (Yahoo, keyless, IST session labels).
Monthly = 10 years of monthly bars. Daily = official NSE files for Indian
instruments (Yahoo fallback elsewhere). Where a Yahoo symbol is unavailable
(e.g. NIFTY Midcap 150 intraday), the timeframe is reported as unavailable —
never fabricated.
"""

from __future__ import annotations

from typing import Any

Row = dict[str, Any]

# Thresholds tuned per timeframe: a 0.3% move is noise intraday but a full
# month's trend can be 3%; a 10-year return is never "neutral" at ±0.3%.
_TH = {
    "intraday": {"trend": 0.10, "ret": 0.15, "ret_recent": 0.10},
    "daily": {"trend": 0.15, "ret": 0.30, "ret_recent": 0.25},
    "monthly": {"trend": 1.50, "ret": 2.00, "ret_recent": 1.50},
}
_RECENT_BARS = {"intraday": 6, "daily": 5, "monthly": 12}  # ≈30min / week / year


# ----------------------------------------------------------------- math --
def _closes(rows: list[Row]) -> list[float]:
    return [r["close"] for r in rows if r.get("close") is not None]


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    out = values[0]
    for v in values[1:]:
        out = v * k + out * (1 - k)
    return out


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

    def ema_series(vals: list[float], period: int) -> list[float]:
        k = 2 / (period + 1)
        out = [vals[0]]
        for v in vals[1:]:
            out.append(v * k + out[-1] * (1 - k))
        return out

    e12 = ema_series(values, 12)
    e26 = ema_series(values, 26)
    macd_line = [a - b for a, b in zip(e12, e26)]
    signal = ema_series(macd_line, 9)
    return macd_line[-1] - signal[-1]


def _bollinger_pos(values: list[float], period: int = 20) -> float | None:
    """Position inside the Bollinger band, 0=lower .. 1=upper (can exceed)."""
    if len(values) < period:
        return None
    win = values[-period:]
    mid = sum(win) / period
    var = sum((v - mid) ** 2 for v in win) / period
    sd = var ** 0.5
    if sd == 0:
        return 0.5
    return (values[-1] - (mid - 2 * sd)) / (4 * sd)


def _roc(values: list[float], bars: int) -> float | None:
    """Rate of change over the last `bars` bars, in %."""
    if len(values) <= bars:
        return None
    base = values[-bars - 1]
    return (values[-1] / base - 1) * 100 if base else None


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


def _volume_vs_avg(rows: list[Row], period: int = 20) -> float | None:
    vols = [r["volume"] for r in rows if r.get("volume")]
    if len(vols) < period + 1 or sum(vols[-period - 1:-1]) == 0:
        return None
    return vols[-1] / (sum(vols[-period - 1:-1]) / period)


def _realized_vol_ann(values: list[float], kind: str, window: int = 20) -> float | None:
    if len(values) < window + 1:
        return None
    rets = [values[i] / values[i - 1] - 1 for i in range(len(values) - window, len(values))]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    sd = var ** 0.5
    bars_per_year = {"intraday": 75 * 250, "daily": 252, "monthly": 12}[kind]
    return sd * (bars_per_year ** 0.5) * 100


# -------------------------------------------------------------- scoring --
_BULL, _BEAR = "BULLISH", "BEARISH"
_NEU = "NEUTRAL"


def timeframe_stats(rows: list[Row], kind: str) -> dict[str, Any]:
    """Detailed bull/bear stats for one timeframe's bars.

    Returns label/score/counts + a `metrics` grid of hard numbers + per-factor
    plain-English explanations, all computed only from the given bars.
    """
    th = _TH.get(kind, _TH["daily"])
    recent_bars = _RECENT_BARS.get(kind, 5)
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

    def add(name: str, value: str, pts: int, explain: str) -> None:
        nonlocal score
        score += pts
        factors.append({
            "name": name,
            "value": value,
            "side": _BULL if pts > 0 else _BEAR if pts < 0 else _NEU,
            "explain": explain,
        })

    # 1. trend: price vs SMA(20)
    sma20 = _sma(closes, 20)
    if sma20:
        diff_pct = (last / sma20 - 1) * 100
        pts = 1 if diff_pct > th["trend"] else (-1 if diff_pct < -th["trend"] else 0)
        add("price vs SMA20", f"{diff_pct:+.2f}%", pts,
            f"Compares the latest price with the average of the last 20 {kind} bars. "
            f"Above the average (±{th['trend']}% dead-zone) = buyers in control of the {kind} trend.")

    # 2. EMA(9) vs EMA(21) cross — faster trend read
    e9, e21 = _ema(closes, 9), _ema(closes, 21)
    if e9 and e21:
        cross_pct = (e9 / e21 - 1) * 100
        pts = 1 if cross_pct > 0 else (-1 if cross_pct < 0 else 0)
        add("EMA 9/21 cross", f"{cross_pct:+.2f}%", pts,
            "Fast average (9) vs slow average (21). Fast above slow = a fresh up-swing; "
            "below = down-swing. Reacts earlier than the SMA20 check.")

    # 3. RSI(14)
    rsi_v = _rsi(closes)
    if rsi_v is not None:
        pts = 1 if rsi_v >= 55 else (-1 if rsi_v <= 45 else 0)
        add("RSI(14)", f"{rsi_v:.1f}", pts,
            "Momentum gauge from 0–100. Above 55 = momentum favouring buyers, "
            "below 45 = sellers. Near 70+ can mean overbought, near 30 oversold.")

    # 4. MACD histogram
    hist = _macd_hist(closes)
    if hist is not None:
        rel = abs(hist) / (last * 0.001 or 1.0)
        pts = 1 if hist > 0 and rel > 0.2 else (-1 if hist < 0 and rel > 0.2 else 0)
        side_word = "above" if hist > 0 else "below"
        add("MACD histogram", f"{hist:+.2f}", pts,
            f"MACD line {side_word} its signal line = trend momentum is building "
            f"{'up' if hist > 0 else 'down'}. Flipping sign often marks turning points.")

    # 5. Bollinger position (0 = lower band, 1 = upper band)
    bb = _bollinger_pos(closes)
    if bb is not None:
        pts = 1 if bb > 0.66 else (-1 if bb < 0.33 else 0)
        add("Bollinger position", f"{bb * 100:.0f}%", pts,
            "Where price sits inside its 20-bar volatility band: near the top (66%+) = "
            "strong demand pressing the band; near the bottom (33%-) = heavy supply.")

    # 6. position in period range
    pos = (last - period_low) / span
    pts = 1 if pos > 0.66 else (-1 if pos < 0.33 else 0)
    add("range position", f"{pos * 100:.0f}% of {kind} range", pts,
        f"Where the price sits between the {kind} low ({period_low:,.2f}) and high "
        f"({period_high:,.2f}). Near the top of the range = buyers defending gains.")

    # 7. full-period return
    period_ret = (last / first - 1) * 100 if first else 0.0
    pts = 1 if period_ret > th["ret"] else (-1 if period_ret < -th["ret"] else 0)
    add(f"{kind} return", f"{period_ret:+.2f}%", pts,
        f"Total change across the whole {kind} window shown "
        f"({len(closes)} bars). The primary direction of this timeframe.")

    # 8. recent momentum (last N bars)
    roc = _roc(closes, recent_bars)
    if roc is not None:
        pts = 1 if roc > th["ret_recent"] else (-1 if roc < -th["ret_recent"] else 0)
        human = {"intraday": "last 30 minutes", "daily": "last week", "monthly": "last 12 months"}[kind]
        add("recent momentum", f"{roc:+.2f}% ({human})", pts,
            f"Return over just the last {recent_bars} bars ({human}). Captures what is "
            "happening right now, which the full-period return can hide.")

    # 9. volume pressure (skipped for monthly: Yahoo monthly volume unreliable)
    if kind != "monthly":
        ratio = _updown_volume(rows)
        if ratio is not None:
            pts = 1 if ratio > 1.15 else (-1 if ratio < 0.85 else 0)
            add("up/down volume", f"{ratio:.2f}", pts,
                "Volume traded on rising bars vs falling bars. Above 1.15 = money flows "
                "in on up-moves (accumulation); below 0.85 = distribution.")

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

    # ---- hard-numbers metrics grid (chart-agnostic, reproducible) ----
    vol_ann = _realized_vol_ann(closes, kind)
    vol_ratio = _volume_vs_avg(rows) if kind != "monthly" else None
    metrics: dict[str, Any] = {
        "last_close": last,
        "period_open": first,
        "period_low": period_low,
        "period_high": period_high,
        "period_return_pct": round(period_ret, 2),
        "recent_return_pct": round(roc, 2) if roc is not None else None,
        "rsi14": round(rsi_v, 1) if rsi_v is not None else None,
        "sma20": round(sma20, 2) if sma20 else None,
        "ema9": round(e9, 2) if e9 else None,
        "ema21": round(e21, 2) if e21 else None,
        "macd_hist": round(hist, 3) if hist is not None else None,
        "bollinger_pos_pct": round(bb * 100) if bb is not None else None,
        "range_pos_pct": round(pos * 100),
        "volatility_ann_pct": round(vol_ann, 1) if vol_ann is not None else None,
        "updown_volume": ratio if kind != "monthly" else None,
        "last_volume_vs_avg": vol_ratio,
        "bars": len(rows),
        "window": f"{rows[0].get('date', rows[0].get('time', ''))} → {rows[-1].get('date', rows[-1].get('time', ''))}"
                  if rows else None,
    }

    return {
        "kind": kind,
        "available": True,
        "label": label,
        "score": round(norm, 3),           # -1..1
        "confidence": confidence,
        "bull_count": bull,
        "bear_count": bear,
        "neutral_count": neu,
        "factors": factors,
        "metrics": metrics,
        "drivers": drivers,
        "summary": summary,
    }
