"""Technical indicators — pure functions over clean OHLCV rows.

Every function returns None when there isn't enough data. All outputs are
plain floats (or None), so the evidence layer can serialize them directly.
"""

from __future__ import annotations

from typing import Optional

Row = dict  # {date, open, high, low, close, volume}


def _closes(rows: list[Row]) -> list[float]:
    return [float(r["close"]) for r in rows]


def _volumes(rows: list[Row]) -> list[float]:
    return [float(r.get("volume") or 0) for r in rows]


def sma(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(rows: list[Row], period: int = 14) -> Optional[float]:
    """Wilder's RSI."""
    closes = _closes(rows)
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas[-period:]]
    losses = [max(-d, 0.0) for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(rows: list[Row], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[dict]:
    closes = _closes(rows)
    if len(closes) < slow + signal:
        return None
    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema_series(macd_line, signal)
    m = macd_line[-1]
    s = signal_line[-1]
    return {
        "macd": m,
        "signal": s,
        "histogram": m - s,
        "prev_histogram": macd_line[-2] - signal_line[-2] if len(macd_line) > 1 else None,
    }


def bollinger(rows: list[Row], period: int = 20, num_std: float = 2.0) -> Optional[dict]:
    closes = _closes(rows)
    if len(closes) < period:
        return None
    window = closes[-period:]
    mean = sum(window) / period
    var = sum((c - mean) ** 2 for c in window) / period
    sd = var ** 0.5
    return {"middle": mean, "upper": mean + num_std * sd, "lower": mean - num_std * sd,
            "bandwidth_pct": ((mean + num_std * sd) - (mean - num_std * sd)) / mean * 100}


def atr(rows: list[Row], period: int = 14) -> Optional[float]:
    if len(rows) < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, len(rows)):
        h, l = float(rows[i]["high"] or rows[i]["close"]), float(rows[i]["low"] or rows[i]["close"])
        pc = float(rows[i - 1]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    window = trs[-period:]
    return sum(window) / len(window)


def realized_vol_pct(rows: list[Row], window: int = 20) -> Optional[float]:
    """Annualized realized volatility (%) over the last `window` returns."""
    closes = _closes(rows)
    if len(closes) < window + 1:
        return None
    rets = []
    for i in range(len(closes) - window, len(closes)):
        prev, cur = closes[i - 1], closes[i]
        if prev:
            rets.append(cur / prev - 1)
    if not rets:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return (var ** 0.5) * (252 ** 0.5) * 100


def returns(rows: list[Row]) -> Optional[dict]:
    closes = _closes(rows)
    n = len(closes)
    if n < 8:
        return None

    def ret(days: int) -> Optional[float]:
        if n <= days:
            return None
        prev = closes[-1 - days]
        return (closes[-1] / prev - 1) * 100 if prev else None

    return {"d5": ret(5), "d1m": ret(21), "d3m": ret(63), "d6m": ret(126)}


def high_52w_position(rows: list[Row]) -> Optional[dict]:
    closes = _closes(rows)
    if len(closes) < 60:
        return None
    window = closes[-252:]
    hi, lo = max(window), min(window)
    cur = closes[-1]
    if hi <= lo:
        return None
    return {"high": hi, "low": lo, "position_pct": (cur - lo) / (hi - lo) * 100,
            "dist_from_high_pct": (cur / hi - 1) * 100}


def volume_vs_avg(rows: list[Row], period: int = 20) -> Optional[dict]:
    vols = _volumes(rows)
    if len(vols) < period + 1 or sum(vols) == 0:
        return None
    avg = sum(vols[-period - 1:-1]) / period
    if avg <= 0:
        return None
    cur = vols[-1]
    return {"current": cur, "avg20": avg, "ratio": cur / avg}


def obv_slope(rows: list[Row], window: int = 10) -> Optional[float]:
    """OBV slope (% of its own stdev per day) — volume-flow direction."""
    vols = _volumes(rows)
    closes = _closes(rows)
    if len(rows) < window + 2 or sum(vols) == 0:
        return None
    obv = [0.0]
    for i in range(1, len(rows)):
        delta = closes[i] - closes[i - 1]
        sign = 1 if delta > 0 else (-1 if delta < 0 else 0)
        obv.append(obv[-1] + sign * vols[i])
    window_vals = obv[-window:]
    x = list(range(window))
    mean_x, mean_y = sum(x) / window, sum(window_vals) / window
    num = sum((x[i] - mean_x) * (window_vals[i] - mean_y) for i in range(window))
    den = sum((x[i] - mean_x) ** 2 for i in range(window)) or 1
    slope = num / den
    spread = max(abs(v - mean_y) for v in window_vals) or 1
    return slope / spread  # normalized, roughly [-1, 1]


def updown_volume_ratio(rows: list[Row], window: int = 10) -> Optional[float]:
    """Sum(volume on up days) / Sum(volume on down days) over the window."""
    vols = _volumes(rows)
    closes = _closes(rows)
    if len(rows) < window + 1 or sum(vols) == 0:
        return None
    up = down = 0.0
    for i in range(len(rows) - window, len(rows)):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            up += vols[i]
        elif delta < 0:
            down += vols[i]
    if down == 0:
        return 2.5 if up > 0 else None
    return min(up / down, 3.0)


def session_vwap(rows: list[Row], window: int = 10) -> Optional[float]:
    """Rolling n-day VWAP (typical price weighted by volume)."""
    if len(rows) < window:
        return None
    num = den = 0.0
    for r in rows[-window:]:
        tp = (float(r["high"] or r["close"]) + float(r["low"] or r["close"]) + float(r["close"])) / 3
        v = float(r.get("volume") or 0)
        num += tp * v
        den += v
    return num / den if den else None
