"""Regression tests for the regime-engine correctness fixes.

Each test pins a bug that was live in the engine, so a future refactor cannot
silently reintroduce it.
"""

from app.engines.regime import assess, global_blend


def _mk(values: list[float]) -> list[dict]:
    return [{"date": f"d{i}", "open": v, "high": v * 1.01, "low": v * 0.99,
             "close": v, "volume": 1_000_000} for i, v in enumerate(values)]


def _asset(instrument_id: str, score: float, weight: float = 1.0) -> dict:
    return {"available": True, "instrument_id": instrument_id,
            "score_0_100": score, "instrument_weight": weight}


# --- fix: score must never exceed 0-100 -------------------------------------
def test_score_is_bounded_to_0_100():
    """News sentiment can push the raw blend past +-1; the score must clamp."""
    for trend in ([100 * (1.01 ** i) for i in range(260)],
                  [100 * (0.99 ** i) for i in range(260)]):
        a = assess(_mk(trend), news_sentiment={"score": 1.0})
        assert a["available"]
        assert 0.0 <= a["score_0_100"] <= 100.0, a["score_0_100"]


# --- fix: trend sub-factor weights must sum to 1.0 -------------------------
def test_trend_subfactor_weights_sum_to_one():
    """Four sub-factors were each weighted 1/3, summing to 1.33 in the UI."""
    a = assess(_mk([100 * (1.004 ** i) for i in range(260)]))
    parts = a["factors"]["trend"]["parts"]
    assert parts
    assert abs(sum(p["weight"] for p in parts) - 1.0) < 1e-9


def test_short_history_renormalises_missing_subfactors():
    """With <200 bars sma200 is absent; the rest must still carry full weight."""
    a = assess(_mk([100 * (1.004 ** i) for i in range(60)]))
    parts = a["factors"]["trend"]["parts"]
    names = {p["name"] for p in parts}
    assert "price vs sma200" not in names
    assert abs(sum(p["weight"] for p in parts) - 1.0) < 1e-9


def test_all_factor_weights_sum_to_one():
    a = assess(_mk([100 * (1.004 ** i) for i in range(260)]))
    for factor in ("trend", "momentum", "volatility", "volume"):
        parts = a["factors"][factor]["parts"]
        if parts:
            assert abs(sum(p["weight"] for p in parts) - 1.0) < 1e-9, factor


# --- fix: VIX is a fear gauge, not a directional asset ---------------------
def test_high_vix_drags_global_read_down():
    """A volatility spike must lower the global score, not raise it."""
    calm = global_blend([_asset("sp500", 50, 1.5), _asset("vix", 20, 1.2)])
    panic = global_blend([_asset("sp500", 50, 1.5), _asset("vix", 80, 1.2)])
    assert panic["score_0_100"] < calm["score_0_100"]


def test_vix_reported_score_is_not_sign_flipped():
    """The raw VIX reading is still surfaced to the UI unchanged."""
    g = global_blend([_asset("vix", 80, 1.2)])
    assert g["vix_score_0_100"] == 80