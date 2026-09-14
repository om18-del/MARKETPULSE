"""Tests for the explainable regime engine."""

from app.engines.regime import assess, global_blend


def _mk(values: list[float]) -> list[dict]:
    return [{"date": f"d{i}", "open": v, "high": v * 1.01, "low": v * 0.99,
             "close": v, "volume": 1_000_000} for i, v in enumerate(values)]


def test_bullish_uptrend():
    rows = _mk([100 * (1.004 ** i) for i in range(120)])
    a = assess(rows)
    assert a["available"]
    assert a["verdict"] == "bullish"
    assert a["score_0_100"] > 55
    assert len(a["factors"]["trend"]["parts"]) >= 2
    assert "not investment advice" in a["disclaimer"]


def test_bearish_downtrend():
    rows = _mk([100 * (0.996 ** i) for i in range(120)])
    a = assess(rows)
    assert a["verdict"] == "bearish"
    assert a["score_0_100"] < 45


def test_insufficient_history():
    a = assess(_mk([100, 101, 102]))
    assert not a["available"]


def test_high_volatility_pushes_uncertain():
    import math, random
    random.seed(3)
    vals = []
    v = 100.0
    for i in range(120):
        v *= (1 + random.uniform(-0.05, 0.05))
        vals.append(v)
    a = assess(_mk(vals))
    assert a["available"]
    assert a["verdict"] in ("uncertain", "neutral") or a["confidence"] < 70


def test_news_modifier_capped():
    rows = _mk([100 * (1.003 ** i) for i in range(120)])
    a = assess(rows, news_sentiment={"score": 1.0, "articles": []})
    assert a["factors"]["news"]["score"] <= 0.10 + 1e-9
    b = assess(rows, news_sentiment={"score": -1.0, "articles": []})
    assert b["factors"]["news"]["score"] >= -0.10 - 1e-9


def test_equation_present():
    rows = _mk([100 * (1.002 ** i) for i in range(120)])
    a = assess(rows)
    assert "Trend" in a["equation"] and "/100" in a["equation"]


def test_global_blend_bullish():
    def mk_assessment(score):
        return {"available": True, "score_0_100": score, "instrument_weight": 1.0}
    g = global_blend([mk_assessment(80), mk_assessment(75), mk_assessment(70)])
    assert g["verdict"] == "bullish"
    assert g["assets_used"] == 3


def test_global_blend_empty():
    g = global_blend([])
    assert not g["available"]
