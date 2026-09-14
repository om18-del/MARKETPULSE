"""Application service layer: orchestrates data + engines + news + AI.

Every public method returns JSON-ready dicts with:
* provenance (which provider, demo or live, freshness)
* evidence (factor tables, citations, equations)
* the persistent disclaimer line.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .ai import analysis as ai_analysis
from .ai import assistant as ai_assistant
from .ai.gemini_client import get_gemini
from .core.config import get_settings
from .data.aggregator import get_aggregator
from .data.registry import ALL, REGISTRY
from .data.registry import search as search_registry
from .demo.snapshots import demo_history
from .engines import fx as fx_engine
from .engines import indicators as ind
from .engines.breadth import compute_breadth
from .engines.filters import cross_asset_pressure, volume_pressure, vwap_zscore, vix_velocity
from .engines.regime import assess as regime_assess
from .engines.regime import global_blend
from .news.analyzer import analyze as analyze_news
from .news.rss import fetch_topic

DEMO_STATE = {"forced": False}

DISCLAIMER = "Educational information — not investment advice."

NEWS_TOPIC_BY_REGION = {
    "us": "us", "india": "india", "europe": "global",
    "apac": "global", "macro": "macro", "fx": "fx",
}

DRIVER_IDS = ["dxy", "us10y", "gold", "crude", "vix"]


async def _history_with_demo(instrument_id: str, force_refresh: bool = False) -> tuple[dict, bool]:
    """History with automatic Demo Mode fallback. Returns (payload, used_demo)."""
    agg = get_aggregator()
    if DEMO_STATE["forced"] or get_settings().force_demo_mode:
        demo = demo_history(instrument_id)
        demo["instrument"] = ALL[instrument_id].to_dict()
        return demo, True
    hist = await agg.get_history(instrument_id, force_refresh=force_refresh)
    if hist["available"]:
        return hist, False
    demo = demo_history(instrument_id)
    demo["instrument"] = ALL[instrument_id].to_dict()
    return demo, True


async def overview() -> dict[str, Any]:
    """The homepage payload: global verdict, grid, breadth, movers, heat."""
    results = await asyncio.gather(
        *[_history_with_demo(inst.id) for inst in REGISTRY.values()],
        return_exceptions=True,
    )
    demo_used = False
    asset_states: list[dict[str, Any]] = []
    assessments: list[dict[str, Any]] = []
    heatmap: list[dict[str, Any]] = []
    grid: dict[str, list[dict[str, Any]]] = {}

    for inst, res in zip(REGISTRY.values(), results):
        region_rows = grid.setdefault(inst.region, [])
        if isinstance(res, Exception):
            region_rows.append({"id": inst.id, "name": inst.name, "available": False})
            asset_states.append({"available": False, "category": inst.category})
            continue
        hist, used_demo = res
        demo_used = demo_used or used_demo
        rows = hist["rows"]
        if not rows:
            region_rows.append({"id": inst.id, "name": inst.name, "available": False})
            asset_states.append({"available": False, "category": inst.category})
            continue

        closes = [float(r["close"]) for r in rows]
        price = closes[-1]
        prev = closes[-2] if len(closes) > 1 else price
        change_pct = (price / prev - 1) * 100 if prev else 0.0
        sma50 = ind.sma(closes, 50)

        assessment = regime_assess(rows, news_sentiment=None, instrument_name=inst.name)
        assessment["instrument_id"] = inst.id
        assessment["instrument_weight"] = inst.weight
        assessments.append(assessment)

        asset_states.append({
            "available": True, "change_pct": change_pct, "above_sma50": bool(sma50 and price > sma50),
            "region": inst.region, "category": inst.category,
        })
        entry = {
            "id": inst.id, "name": inst.name, "category": inst.category,
            "region": inst.region, "currency": inst.currency,
            "price": price, "change_pct": round(change_pct, 2),
            "spark": closes[-30:],
            "verdict": assessment["verdict"],
            "score": assessment["score_0_100"],
            "above_sma50": bool(sma50 and price > sma50),
            "demo": used_demo,
        }
        region_rows.append(entry)
        heatmap.append({"id": inst.id, "name": inst.name, "region": inst.region,
                        "category": inst.category, "change_pct": entry["change_pct"]})

    ranked = sorted([e for rs in grid.values() for e in rs if e.get("change_pct") is not None],
                    key=lambda e: e["change_pct"])
    losers = ranked[:5]
    gainers = list(reversed(ranked[-5:]))

    global_read = global_blend(assessments)
    breadth = compute_breadth(asset_states)

    vix_summary = None
    for h, inst in zip(results, REGISTRY.values()):
        if inst.id != "vix" or isinstance(h, Exception):
            continue
        vrows = h[0]["rows"]
        if len(vrows) > 1:
            vix_summary = {"price": float(vrows[-1]["close"]),
                           "change_pct": round((float(vrows[-1]["close"]) / float(vrows[-2]["close"]) - 1) * 100, 2)}

    return {
        "global": global_read,
        "breadth": breadth,
        "grid": grid,
        "movers": {"gainers": gainers, "losers": losers},
        "heatmap": heatmap,
        "vix": vix_summary,
        "data_mode": "demo" if demo_used else "live",
        "disclaimer": DISCLAIMER,
    }


async def asset_detail(instrument_id: str) -> dict[str, Any]:
    inst = ALL.get(instrument_id)
    if inst is None:
        raise ValueError(f"unknown instrument: {instrument_id}")
    hist, used_demo = await _history_with_demo(inst.id)
    rows = hist["rows"]
    closes = [float(r["close"]) for r in rows]
    quote = None
    if closes:
        prev = closes[-2] if len(closes) > 1 else closes[-1]
        quote = {"price": closes[-1], "change_pct": round((closes[-1] / prev - 1) * 100, 2) if prev else 0.0,
                 "provider": hist["provenance"]["provider"], "demo": used_demo}
    return {
        "instrument": inst.to_dict(),
        "quote": quote,
        "rows": rows[-180:],
        "spark": closes[-30:],
        "data_mode": "demo" if used_demo else "live",
        "provenance": hist["provenance"],
        "disclaimer": DISCLAIMER,
    }


async def full_analysis(instrument_id: str) -> dict[str, Any]:
    """Everything for the detail page: regime + filters + cross-asset + news + thesis."""
    inst = ALL.get(instrument_id)
    if inst is None:
        raise ValueError(f"unknown instrument: {instrument_id}")

    hist, used_demo = await _history_with_demo(inst.id)
    rows = hist["rows"]
    if len(rows) < 30:
        return {"available": False, "reason": "insufficient history", "disclaimer": DISCLAIMER}

    gemini = get_gemini()

    # --- news sentiment (cached by TTLCache upstream in gemini/none; rss cached here) ---
    topic = NEWS_TOPIC_BY_REGION.get(inst.region, "global")
    news_payload = await _cached_news(topic)
    tagged = news_payload.get("articles", [])[:8]
    news_for_regime = {"score": news_payload.get("aggregate_score", 0.0), "articles": tagged[:5]}

    # --- deterministic filters ---
    vix_rows = None
    try:
        vix_hist, _ = await _history_with_demo("vix")
        vix_rows = vix_hist["rows"]
    except Exception:
        pass
    filters_bundle = {
        "vwap": vwap_zscore(rows),
        "volume_pressure": volume_pressure(rows),
        "vix_velocity": vix_velocity(vix_rows),
    }

    # --- cross-asset pressure matrix ---
    driver_rows: dict[str, list] = {}
    for did in DRIVER_IDS:
        if did == inst.id:
            continue
        try:
            dh, _ = await _history_with_demo(did)
            if dh["rows"]:
                driver_rows[did] = dh["rows"]
        except Exception:
            continue
    cross = cross_asset_pressure(rows, driver_rows)

    # --- regime ---
    assessment = regime_assess(rows, news_sentiment=news_for_regime, instrument_name=inst.name)

    features = {
        "instrument_name": inst.name,
        "verdict": assessment.get("verdict"),
        "confidence": assessment.get("confidence"),
        "equation": assessment.get("equation"),
        "factors": assessment.get("factors"),
        "filters": filters_bundle,
        "cross_asset": cross,
        "news_headlines": [{"title": a.get("title"), "publisher": a.get("publisher"),
                            "sentiment": a.get("sentiment"), "reason": a.get("reason")}
                           for a in tagged[:5]],
    }
    thesis = await ai_analysis.build_thesis(gemini, features)

    return {
        "available": True,
        "instrument": inst.to_dict(),
        "data_mode": "demo" if used_demo else "live",
        "provenance": hist["provenance"],
        "assessment": assessment,
        "filters": filters_bundle,
        "cross_asset": cross,
        "news": {"topic": topic, "aggregate_score": news_payload.get("aggregate_score"),
                 "method": news_payload.get("method"), "articles": tagged},
        "thesis": thesis,
        "disclaimer": DISCLAIMER,
    }


_NEWS_CACHE: dict[str, tuple[float, dict]] = {}


async def _cached_news(topic: str) -> dict[str, Any]:
    import time
    hit = _NEWS_CACHE.get(topic)
    if hit and time.monotonic() - hit[0] < 600:
        return hit[1]
    feed = await fetch_topic(topic)
    gemini = get_gemini()
    analyzed = await analyze_news(feed["articles"], gemini if gemini.available else None)
    payload = {**analyzed, "fetched_at": feed["fetched_at"], "errors": feed["errors"]}
    _NEWS_CACHE[topic] = (time.monotonic(), payload)
    return payload


async def news_feed(topic: str = "global") -> dict[str, Any]:
    payload = await _cached_news(topic)
    return {**payload, "disclaimer": DISCLAIMER}


async def fx_overview() -> dict[str, Any]:
    pair_ids = list(fx_engine.USD_PAIRS.values())
    results = await asyncio.gather(*[_history_with_demo(pid) for pid in pair_ids],
                                   return_exceptions=True)
    pair_quotes: dict[str, dict] = {}
    pair_meta: dict[str, dict] = {}
    demo_used = False
    for pid, res in zip(pair_ids, results):
        if isinstance(res, Exception):
            continue
        hist, used_demo = res
        demo_used = demo_used or used_demo
        rows = hist["rows"]
        if len(rows) < 6:
            continue
        closes = [float(r["close"]) for r in rows]
        pair_quotes[pid] = {"last_price": closes[-1]}
        pair_meta[pid] = {"name": fx_engine.PAIR_NAME.get(pid, pid),
                          "rate_usd": closes[-1],
                          "d1_pct": round((closes[-1] / closes[-2] - 1) * 100, 2),
                          "d5_pct": round((closes[-1] / closes[-6] - 1) * 100, 2),
                          "spark": closes[-30:],
                          "demo": used_demo}
    rates = fx_engine.usd_rates_from_pairs(pair_quotes)
    return {
        "currencies": fx_engine.CURRENCIES,
        "flags": fx_engine.FLAG,
        "usd_rates": rates,
        "pairs": pair_meta,
        "data_mode": "demo" if demo_used else "live",
        "disclaimer": DISCLAIMER,
    }


def fx_convert(amount: float, from_cur: str, to_cur: str, rates: dict) -> dict[str, Any]:
    result = fx_engine.convert(amount, from_cur.upper(), to_cur.upper(), rates)
    return {"amount": amount, "from": from_cur.upper(), "to": to_cur.upper(),
            "result": result, "disclaimer": DISCLAIMER}


async def recap() -> dict[str, Any]:
    ov = await overview()
    data = {"global": ov["global"], "movers": ov["movers"],
            "breadth": ov["breadth"], "vix": ov["vix"], "data_mode": ov["data_mode"]}
    text = await ai_analysis.daily_recap(get_gemini(), data)
    return {"text": text["text"], "generated_by": text["generated_by"],
            "data_mode": ov["data_mode"], "disclaimer": DISCLAIMER}


async def chat(question: str, instrument_id: str | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {}
    if instrument_id and instrument_id in ALL:
        detail = await full_analysis(instrument_id)
        context = {
            "instrument": detail["instrument"],
            "assessment": {"verdict": detail["assessment"].get("verdict"),
                           "score": detail["assessment"].get("score_0_100"),
                           "confidence": detail["assessment"].get("confidence"),
                           "equation": detail["assessment"].get("equation")},
            "filters": detail["filters"],
            "cross_asset": detail["cross_asset"].get("drivers"),
            "recent_news": [a.get("title") for a in detail["news"]["articles"][:5]],
            "data_mode": detail["data_mode"],
        }
    else:
        ov = await overview()
        context = {"global": ov["global"], "breadth": ov["breadth"],
                   "movers": ov["movers"], "data_mode": ov["data_mode"]}
    return await ai_analysis.chat_answer(get_gemini(), question, context)


async def assistant_explain(selected_text: str, context: dict | None) -> dict[str, Any]:
    return await ai_assistant.explain_snippet(get_gemini(), selected_text, context)


async def assistant_ask(question: str) -> dict[str, Any]:
    return await ai_assistant.general_qa(get_gemini(), question)


async def analyze_image(image_bytes: bytes, mime: str) -> dict[str, Any]:
    gemini = get_gemini()
    prompt = (
        "You are MarketPulse's educational image analyst. A user uploaded this image "
        "(likely a price chart, market screenshot, or a social-media market tip). "
        "Explain educationally in max 150 words: what the image shows, how to read it, "
        "and what a beginner should be skeptical about. NEVER give advice or predictions; "
        "if it looks like a buy/sell tip, explain why unverified tips are risky. "
        "End with: \"Educational information — not investment advice.\""
    )
    if not gemini.available:
        return {"text": "Image analysis needs the Gemini API key on the backend. "
                        "Educational information — not investment advice.",
                "generated_by": "unavailable"}
    try:
        text = await gemini.generate_with_image(image_bytes, mime, prompt)
        return {"text": text, "generated_by": "gemini-analysis", "disclaimer": DISCLAIMER}
    except Exception:
        return {"text": "Image analysis is temporarily unavailable (quota). Please try again shortly. "
                        "Educational information — not investment advice.",
                "generated_by": "fallback", "disclaimer": DISCLAIMER}


def toggle_demo(enabled: bool) -> dict[str, Any]:
    DEMO_STATE["forced"] = bool(enabled)
    get_aggregator().clear_caches()
    return {"demo_mode": DEMO_STATE["forced"]}


def search_all(q: str) -> dict[str, Any]:
    hits = search_registry(q, limit=10)
    return {"query": q,
            "results": [{**h.to_dict(), "category_label": h.category} for h in hits],
            "disclaimer": DISCLAIMER}
