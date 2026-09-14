"""Tests for FX engine + deterministic filters."""

from app.engines.filters import cross_asset_pressure, volume_pressure, vwap_zscore
from app.engines.fx import convert, rate_grid, usd_rates_from_pairs


def _mk(closes: list[float], with_volume: bool = True) -> list[dict]:
    return [{"date": f"d{i}", "open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
             "volume": 1_000_000 if with_volume else None} for i, c in enumerate(closes)]


def test_usd_rates_inversions():
    quotes = {"usdinr": {"last_price": 86.0}, "eurusd": {"last_price": 1.10}}
    rates = usd_rates_from_pairs(quotes)
    assert rates["INR"] == 86.0
    assert abs(rates["EUR"] - 1 / 1.10) < 1e-9


def test_grid_diagonal_is_one():
    rates = {"USD": 1.0, "INR": 86.0, "EUR": 0.9}
    grid = rate_grid(rates)
    for row in grid:
        if row["base"] in rates:  # unknown currencies are honestly None
            assert row["rates"][row["base"]] == 1.0
        else:
            assert row["rates"][row["base"]] is None


def test_convert_roundtrip():
    rates = {"USD": 1.0, "INR": 86.0}
    inr = convert(100, "USD", "INR", rates)
    assert inr == 8600.0
    back = convert(inr, "INR", "USD", rates)
    assert abs(back - 100) < 0.01


def test_vwap_zscore_bands():
    import random
    random.seed(11)
    closes = [100]
    for i in range(80):
        closes.append(closes[-1] * (1 + random.uniform(-0.01, 0.01)))
    rows = _mk(closes)
    z = vwap_zscore(rows)
    assert z is not None and z["band"] in ("normal", "stretched", "extended")


def test_volume_pressure_labels():
    # steady series with a final volume spike -> some label, z present
    rows = _mk([100 + (i % 3) for i in range(60)])
    rows[-1]["volume"] = 5_000_000
    vp = volume_pressure(rows)
    assert vp is not None and vp["proxy_label"] in ("balanced", "accumulation", "distribution")


def test_cross_asset_summary():
    base = [100 + i * 0.1 for i in range(80)]
    out = cross_asset_pressure(_mk(base), {"dxy": _mk([100 - i * 0.05 for i in range(80)])})
    assert "dxy" in out["drivers"]
    assert -1.0 <= out["drivers"]["dxy"]["correlation"] <= 1.0
