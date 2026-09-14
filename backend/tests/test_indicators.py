"""Tests for technical indicators on synthetic data."""

from app.engines import indicators as ind


def _mk_series(values: list[float], volume: float = 1_000_000) -> list[dict]:
    rows = []
    for i, v in enumerate(values):
        rows.append({"date": f"2025-01-{(i % 28) + 1:02d}", "open": v, "high": v * 1.01,
                     "low": v * 0.99, "close": v, "volume": volume})
    return rows


def test_sma_basic():
    assert ind.sma([1, 2, 3, 4, 5], 5) == 3.0
    assert ind.sma([1, 2], 5) is None


def test_rsi_bounds():
    # monotonic rising series -> RSI 100
    rising = _mk_series([100 + i for i in range(30)])
    r = ind.rsi(rising)
    assert r == 100.0
    # monotonic falling -> RSI 0
    falling = _mk_series([100 - i for i in range(30)])
    assert ind.rsi(falling) == 0.0


def test_rsi_midrange():
    import math
    vals = [100 + 5 * math.sin(i / 2) for i in range(40)]
    r = ind.rsi(_mk_series(vals))
    assert r is not None and 20 <= r <= 80


def test_macd_shape():
    vals = [100 + i * 0.5 for i in range(60)]
    m = ind.macd(_mk_series(vals))
    assert m is not None and "macd" in m and "histogram" in m


def test_bollinger_contains_price():
    import random
    random.seed(7)
    vals = [100 * (1 + random.uniform(-0.02, 0.02)) for _ in range(40)]
    b = ind.bollinger(_mk_series(vals))
    assert b["upper"] > b["middle"] > b["lower"]


def test_realized_vol_low_for_steady():
    vals = [100 * (1 + 0.0005 * i) for i in range(40)]
    rv = ind.realized_vol_pct(_mk_series(vals))
    assert rv is not None and rv < 10


def test_volume_vs_avg():
    rows = _mk_series([100] * 25, volume=1_000_000)
    rows[-1]["volume"] = 2_000_000
    va = ind.volume_vs_avg(rows)
    assert va is not None and va["ratio"] > 1.5
