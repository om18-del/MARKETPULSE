"""Regime engine: deterministic, explainable scoring.

Verdict = weighted blend of Trend / Momentum / Volatility / Volume factors,
optionally nudged by news sentiment. Every factor contributes a visible
row in the Evidence panel: value, rule, weight, contribution — and the
final equation is emitted so the UI can show exactly how the verdict
was reached. High volatility pushes toward *Uncertain* (never "crash").
"""

from __future__ import annotations

from typing import Any, Optional

from . import indicators as ind

# --- model constants (documented on the Methodology page) ---
W_TREND, W_MOM, W_VOLA, W_VOL = 0.35, 0.25, 0.25, 0.15
NEWS_MODIFIER_CAP = 0.10
UNCERTAINTY_VOL_THRESHOLD = 28.0   # annualized vol % above which confidence is dampened
OVERBOUGHT_RSI, OVERSOLD_RSI = 70, 30

VERDICTS = ("bullish", "bearish", "neutral", "uncertain")


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _trend_factor(rows: list[Row], close: float) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    score = 0.0
    for label, period in (("SMA20", 20), ("SMA50", 50), ("SMA200", 200)):
        v = ind.sma([r["close"] for r in rows], period)
        if v is None:
            continue
        pct_diff = (close / v - 1) * 100
        sub = _clamp(pct_diff / 5)  # ±5% from SMA saturates the sub-score
        parts.append({"name": f"price vs {label.lower()}", "value": f"{pct_diff:+.2f}%",
                      "rule": f"±5% from {label} saturates", "weight": 1 / 3,
                      "sub_score": sub,
                      "meaning": ("above" if pct_diff > 0 else "below") + f" {label}"})
        score += sub / 3
    m = ind.macd(rows)
    if m:
        hist = m["histogram"]
        sub = _clamp(hist / (close * 0.01))  # ±1% of price saturates
        parts.append({"name": "MACD histogram", "value": f"{hist:.2f}",
                      "rule": "±1% of price saturates", "weight": 1 / 3,
                      "sub_score": sub,
                      "meaning": "bullish cross" if hist > 0 else "bearish cross"})
        score += sub / 3
    return {"score": _clamp(score), "parts": parts}


def _momentum_factor(rows: list[Row]) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    score = 0.0
    r = ind.rsi(rows)
    if r is not None:
        if r >= OVERBOUGHT_RSI:
            sub, meaning = -0.5, "overbought — extended upside"
        elif r <= OVERSOLD_RSI:
            sub, meaning = 0.5, "oversold — stretched downside"
        else:
            sub = (r - 50) / 50
            meaning = "mid-range" if abs(r - 50) < 10 else ("tilting bullish" if r > 50 else "tilting bearish")
        parts.append({"name": "RSI(14)", "value": f"{r:.1f}",
                      "rule": f">= {OVERBOUGHT_RSI} overbought, <= {OVERSOLD_RSI} oversold",
                      "weight": 0.5, "sub_score": _clamp(sub), "meaning": meaning})
        score += _clamp(sub) * 0.5
    rets = ind.returns(rows)
    if rets and rets["d5"] is not None:
        sub = _clamp(rets["d5"] / 6)
        parts.append({"name": "5-day return", "value": f"{rets['d5']:+.2f}%",
                      "rule": "±6% in 5 days saturates", "weight": 0.3,
                      "sub_score": sub,
                      "meaning": "strong week" if abs(rets["d5"]) > 4 else "normal week"})
        score += sub * 0.3
    if rets and rets["d1m"] is not None:
        sub = _clamp(rets["d1m"] / 12)
        parts.append({"name": "1-month return", "value": f"{rets['d1m']:+.2f}%",
                      "rule": "±12% in a month saturates", "weight": 0.2,
                      "sub_score": sub,
                      "meaning": "monthly trend direction"})
        score += sub * 0.2
    return {"score": _clamp(score), "parts": parts}


def _volatility_factor(rows: list[Row]) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    a = ind.atr(rows)
    closes = [r["close"] for r in rows]
    price = closes[-1]
    score = 0.0
    if a and price:
        atr_pct = a / price * 100
        sub = _clamp(atr_pct / 4)
        parts.append({"name": "ATR(14) %", "value": f"{atr_pct:.2f}%",
                      "rule": "≥4% daily range = very high", "weight": 0.5,
                      "sub_score": sub, "meaning": "daily swing size"})
        score += sub * 0.5
    rv = ind.realized_vol_pct(rows)
    if rv is not None:
        sub = _clamp((rv - 12) / 30)  # 12% baseline, 42%+ saturates
        parts.append({"name": "Realized vol (20d, ann.)", "value": f"{rv:.1f}%",
                      "rule": "12% calm baseline; 42%+ = stressed", "weight": 0.5,
                      "sub_score": sub, "meaning": "how wild the ride has been"})
        score += sub * 0.5
    return {"score": _clamp(score), "parts": parts, "realized_vol": rv}


def _volume_factor(rows: list[Row]) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    score = 0.0
    va = ind.volume_vs_avg(rows)
    if va:
        ratio = va["ratio"]
        # rising price + high volume = confirmation; falling price + high volume = pressure
        closes = [r["close"] for r in rows]
        day_dir = 1 if closes[-1] >= closes[-2] else -1
        sub = _clamp((ratio - 1) * 0.5) * day_dir
        parts.append({"name": "Volume vs 20d avg", "value": f"{ratio:.2f}×",
                      "rule": ">1× = above-average participation", "weight": 0.6,
                      "sub_score": sub,
                      "meaning": ("above-average participation — today's move is backed by real volume"
                                  if ratio > 1.2 else
                                  "above-average participation" if ratio > 1 else
                                  "below-average participation — thin trading today")})
        score += sub * 0.6
    ud = ind.updown_volume_ratio(rows)
    if ud is not None:
        sub = _clamp((ud - 1) / 1.5)
        parts.append({"name": "Up/down volume (10d)", "value": f"{ud:.2f}",
                      "rule": ">1.5 accumulation, <0.67 distribution", "weight": 0.4,
                      "sub_score": sub,
                      "meaning": "buyers" if ud > 1.2 else ("sellers" if ud < 0.83 else "balanced")})
        score += sub * 0.4
    return {"score": _clamp(score), "parts": parts}


def news_modifier(sentiment: Optional[dict]) -> dict[str, Any]:
    """News contribution: deterministic mapping, capped at ±10%."""
    if not sentiment or sentiment.get("score") is None:
        return {"score": 0.0, "applied": False,
                "meaning": "no news sentiment available"}
    s = _clamp(float(sentiment["score"]))
    applied = s * NEWS_MODIFIER_CAP
    return {"score": applied, "applied": True,
            "meaning": f"news sentiment {s:+.2f} shifts the score by {applied:+.2f}",
            "articles": sentiment.get("articles", [])}


def assess(rows: list[Row],
           news_sentiment: Optional[dict] = None,
           instrument_name: str = "") -> dict[str, Any]:
    """Full explainable assessment for one instrument."""
    if len(rows) < 30:
        return {"available": False, "reason": "insufficient history (need ≥30 bars)"}

    close = float(rows[-1]["close"])
    trend = _trend_factor(rows, close)
    momentum = _momentum_factor(rows)
    volatility = _volatility_factor(rows)
    volume = _volume_factor(rows)
    news = news_modifier(news_sentiment)

    raw = (trend["score"] * W_TREND + momentum["score"] * W_MOM +
           volatility["score"] * W_VOLA + volume["score"] * W_VOL +
           news["score"])

    # Volatility dampens directional confidence instead of reversing it
    rv = volatility.get("realized_vol")
    uncertainty_damp = 0.0
    if rv is not None and rv > UNCERTAINTY_VOL_THRESHOLD:
        uncertainty_damp = min((rv - UNCERTAINTY_VOL_THRESHOLD) / 40, 0.5)

    score100 = round((raw + 1) / 2 * 100, 1)  # [-1,1] -> [0,100]
    direction_confidence = round(100 * (1 - uncertainty_damp), 1)

    if abs(raw) < 0.12 and uncertainty_damp < 0.2:
        verdict = "neutral"
    elif uncertainty_damp > 0.45:
        verdict = "uncertain"
    elif raw > 0:
        verdict = "bullish"
    else:
        verdict = "bearish"

    confidence = round(min(95, max(35, direction_confidence * min(1.0, abs(raw) + 0.35))), 1)
    if verdict == "neutral":
        confidence = round(min(confidence, 60), 1)
    if verdict == "uncertain":
        confidence = round(min(confidence, 55), 1)

    equation = (
        f"Trend {trend['score']:+.2f}×{W_TREND} + Momentum {momentum['score']:+.2f}×{W_MOM} "
        f"+ Volatility {volatility['score']:+.2f}×{W_VOLA} + Volume {volume['score']:+.2f}×{W_VOL} "
        f"+ News {news['score']:+.2f} → raw {raw:+.3f} → {score100}/100"
    )
    if uncertainty_damp:
        equation += f" (vol dampens directional confidence ×{1 - uncertainty_damp:.2f})"

    # Plain-English version of the same math — for beginners and AI output.
    # (Audit feedback: raw formula syntax risks misinterpretation by
    # non-technical users in a regulated education context.)
    equation_plain = (
        f"each factor score is multiplied by its weight and the results are added: "
        f"trend {trend['score']:+.2f} × {W_TREND:.0%}, momentum {momentum['score']:+.2f} × {W_MOM:.0%}, "
        f"volatility {volatility['score']:+.2f} × {W_VOLA:.0%}, volume {volume['score']:+.2f} × {W_VOL:.0%}, "
        f"plus news {news['score']:+.2f} — giving {raw:+.2f}, which maps to {score100}/100 on the 0–100 score"
    )
    if uncertainty_damp:
        equation_plain += f" (high volatility dampens the directional confidence)"

    what_would_change: list[str] = []
    if verdict in ("bullish", "bearish"):
        what_would_change = [
            "A close on the other side of the 50-day average",
            f"RSI crossing {'down through 70' if verdict == 'bullish' else 'up through 30'}",
            f"Realized volatility rising above {UNCERTAINTY_VOL_THRESHOLD:.0f}% (pushes toward Uncertain)",
        ]
    else:
        what_would_change = [
            "A decisive break of the 20/50-day averages with above-average volume",
            "A volatility spike or collapse changing the risk backdrop",
            "Sustained 5-day moves exceeding ±6%",
        ]

    # Confidence interpretation — prevents readers from over-weighting a
    # verdict (audit recommendation: 53.7% is near 50-50 odds, not conviction).
    if confidence >= 70:
        confidence_note = "a strong lean — most signals agree"
    elif confidence >= 55:
        confidence_note = "a moderate lean — signals mostly agree"
    else:
        confidence_note = "near even odds — a mild lean, not a strong signal"

    return {
        "available": True,
        "instrument_name": instrument_name,
        "verdict": verdict,
        "score_0_100": score100,
        "confidence": confidence,
        "confidence_note": confidence_note,
        "equation": equation,
        "equation_plain": equation_plain,
        "factors": {
            "trend": trend, "momentum": momentum,
            "volatility": volatility, "volume": volume, "news": news,
        },
        "weights": {"trend": W_TREND, "momentum": W_MOM,
                    "volatility": W_VOLA, "volume": W_VOL,
                    "news_cap": NEWS_MODIFIER_CAP},
        "what_would_change_this_read": what_would_change,
        "disclaimer": "Educational information — not investment advice.",
    }


def global_blend(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    """Blend per-asset verdicts into one global market read."""
    total_w = contributions = 0.0
    used = []
    for a in assessments:
        if not a.get("available"):
            continue
        w = a.get("instrument_weight", 1.0)
        s = (a["score_0_100"] - 50) / 50  # back to [-1, 1]
        contributions += s * w
        total_w += w
        used.append(a)
    if not total_w:
        return {"available": False, "reason": "no asset assessments available"}
    raw = contributions / total_w
    score100 = round((raw + 1) / 2 * 100, 1)
    if abs(raw) < 0.1:
        verdict = "neutral"
    elif abs(raw) < 0.2:
        verdict = "uncertain"
    elif raw > 0:
        verdict = "bullish"
    else:
        verdict = "bearish"
    vix_score = next((a["score_0_100"] for a in used if a.get("instrument_id") == "vix"), None)
    confidence = round(min(90, max(35, 50 + abs(raw) * 80)), 1)
    return {
        "available": True,
        "verdict": verdict,
        "score_0_100": score100,
        "confidence": confidence,
        "assets_used": len(used),
        "vix_score_0_100": vix_score,
        "equation": f"Σ(asset score × weight) / Σ(weight) → raw {raw:+.3f} → {score100}/100",
        "disclaimer": "Educational information — not investment advice.",
    }
