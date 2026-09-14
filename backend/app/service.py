"""Application service layer: orchestrates data + engines + news + AI.

Every public method returns JSON-ready dicts with:
* provenance (which provider, demo or live, freshness)
* evidence (factor tables, citations, equations)
* the persistent disclaimer line.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from .ai import analysis as ai_analysis
from .ai import assistant as ai_assistant
from .ai import prism
from .ai.gemini_client import get_gemini
from .core.config import get_settings
from .data.aggregator import get_aggregator
from .data.india_store import get_store
from .data.registry import ALL, REGISTRY, Instrument
from .data.registry import parse_ticker_suffix
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
    inst = ALL.get(instrument_id)
    if inst is None:
        inst = await agg.dynamic_instrument(instrument_id)  # dynamic NSE-universe id

    def _inst_dict() -> dict[str, Any]:
        if inst is not None:
            return inst.to_dict()
        return {"id": instrument_id, "name": instrument_id.upper(),
                "category": "stock", "region": "india", "currency": "INR"}

    if DEMO_STATE["forced"] or get_settings().force_demo_mode:
        demo = demo_history(instrument_id)
        demo["instrument"] = _inst_dict()
        return demo, True
    hist = await agg.get_history(instrument_id, force_refresh=force_refresh)
    if hist["available"]:
        return hist, False
    demo = demo_history(instrument_id)
    demo["instrument"] = _inst_dict()
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
        inst = await get_aggregator().dynamic_instrument(instrument_id)
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
        inst = await get_aggregator().dynamic_instrument(instrument_id)
    if inst is None:
        raise ValueError(f"unknown instrument: {instrument_id}")

    # Full-analysis cache: deep analysis is expensive (history + drivers + news
    # + AI thesis). Cache for 5 minutes so repeat visits/refreshes are instant.
    _analysis_cache_key = f"analysis:{inst.id}"
    _hit = _ANALYSIS_CACHE.get(_analysis_cache_key)
    if _hit and time.monotonic() - _hit[0] < 300:
        return _hit[1]

    _progress_start(inst.id)
    # PRISM: one trajectory per analysis run, named for the asset
    prism.new_session(f"analysis-{inst.id}")

    hist, used_demo = await _history_with_demo(inst.id)
    rows = hist["rows"]
    if len(rows) < 30:
        return {"available": False, "reason": "insufficient history", "disclaimer": DISCLAIMER}

    gemini = get_gemini()

    _progress_stage(inst.id, "history")
    # --- fetch everything independent in parallel (was sequential: ~2min cold) ---
    topic = NEWS_TOPIC_BY_REGION.get(inst.region, "global")
    news_task = _cached_news(topic)
    vix_task = _history_with_demo("vix")
    driver_tasks = {
        did: _history_with_demo(did)
        for did in DRIVER_IDS
        if did != inst.id
    }
    news_payload, vix_bundle, driver_bundles = await asyncio.gather(
        news_task, vix_task, asyncio.gather(*driver_tasks.values(), return_exceptions=True)
    )
    tagged = news_payload.get("articles", [])[:8]
    news_for_regime = {"score": news_payload.get("aggregate_score", 0.0), "articles": tagged[:5]}

    _progress_stage(inst.id, "filters")

    # --- deterministic filters ---
    vix_rows = None
    if not isinstance(vix_bundle, Exception):
        vix_rows = vix_bundle[0]["rows"]
    filters_bundle = {
        "vwap": vwap_zscore(rows),
        "volume_pressure": volume_pressure(rows),
        "vix_velocity": vix_velocity(vix_rows),
    }

    # --- cross-asset pressure matrix ---
    driver_rows: dict[str, list] = {}
    for did, bundle in zip(driver_tasks.keys(), driver_bundles):
        if isinstance(bundle, Exception):
            continue
        dh, _ = bundle
        if dh["rows"]:
            driver_rows[did] = dh["rows"]
    cross = cross_asset_pressure(rows, driver_rows)

    _progress_stage(inst.id, "regime")
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
    _progress_stage(inst.id, "thesis")
    thesis = await ai_analysis.build_thesis(gemini, features)

    outlook = _build_outlook(assessment, filters_bundle, news_payload, cross, inst.name)

    result = {
        "available": True,
        "instrument": inst.to_dict(),
        "data_mode": "demo" if used_demo else "live",
        "provenance": hist["provenance"],
        "outlook": outlook,
        "assessment": assessment,
        "filters": filters_bundle,
        "cross_asset": cross,
        "news": {"topic": topic, "aggregate_score": news_payload.get("aggregate_score"),
                 "method": news_payload.get("method"), "articles": tagged},
        "thesis": thesis,
        "disclaimer": DISCLAIMER,
    }
    _progress_done(inst.id)
    _ANALYSIS_CACHE[_analysis_cache_key] = (time.monotonic(), result)
    return result


def _risk_level(realized_vol: float | None) -> str:
    if realized_vol is None:
        return "unknown"
    if realized_vol < 15:
        return "calm"
    if realized_vol < 25:
        return "moderate"
    if realized_vol < 35:
        return "elevated"
    return "extreme"


def _build_outlook(assessment: dict, filters_bundle: dict, news_payload: dict,
                   cross: dict, name: str) -> dict[str, Any]:
    """Deterministic plain-English outlook: the instant 'clear answer' card.

    Assembled entirely from computed numbers — no AI call, no black box.
    """
    verdict = assessment.get("verdict", "neutral")
    conf = assessment.get("confidence", 0)
    factors = assessment.get("factors") or {}

    # top 3 contributing factors across trend/momentum/volume
    parts: list[dict] = []
    for key in ("trend", "momentum", "volume"):
        for p in (factors.get(key) or {}).get("parts", []):
            parts.append({**p, "factor_group": key})
    top = sorted(parts, key=lambda p: abs(p.get("sub_score", 0) * p.get("weight", 1)), reverse=True)[:3]

    rv = (factors.get("volatility") or {}).get("realized_vol")
    risk = _risk_level(rv if isinstance(rv, (int, float)) else None)

    news_score = news_payload.get("aggregate_score", 0.0) or 0.0
    news_method = news_payload.get("method", "n/a")
    news_word = ("positive" if news_score > 0.1 else "negative" if news_score < -0.1 else "neutral")

    vwap = filters_bundle.get("vwap") or {}
    vp = filters_bundle.get("volume_pressure") or {}

    drivers_sentence = "; ".join(
        f"{p.get('name')} {p.get('value')} ({p.get('meaning', '')})" for p in top
    )
    plain = (
        f"{name} is in a {verdict.upper()} environment with {conf}% confidence. "
        f"Key drivers: {drivers_sentence}. "
        f"Risk level is {risk}"
        + (f" (realized volatility {rv:.1f}% annualized)" if isinstance(rv, (int, float)) else "")
        + f"; volume flow reads {vp.get('proxy_label', 'balanced')}"
        + (f" and price is {vwap.get('band', 'normal')} vs its volume-weighted average" if vwap else "")
        + f". News tone is {news_word} ({news_score:+.2f}, {news_method}-tagged)."
    )

    return {
        "headline": f"{verdict.upper()} · {conf}% confidence · risk: {risk}",
        "plain_summary": plain,
        "key_drivers": [
            {"name": p.get("name"), "value": p.get("value"),
             "direction": "up" if (p.get("sub_score", 0) >= 0) else "down",
             "meaning": p.get("meaning", "")}
            for p in top
        ],
        "risk_level": risk,
        "realized_vol": rv,
        "news_influence": {"tone": news_word, "score": round(news_score, 2), "method": news_method},
        "watch_next": (assessment.get("what_would_change_this_read") or [])[:2],
        "logic_note": "Assembled deterministically from the 20-indicator math layer — the same numbers shown in the Evidence panel. No black box.",
    }


# --------------------------- progress tracking ---------------------------
# Live progress for deep-analysis requests so the UI can show stage + time
# remaining instead of a blind spinner. In-process only, like every cache here.

_ANALYSIS_PROGRESS: dict[str, dict[str, Any]] = {}
_LAST_COLD_SECONDS: dict[str, float] = {}

_ANALYSIS_STAGES = [
    "queued", "starting", "history", "drivers+news", "filters",
    "cross-asset", "regime", "thesis", "ready",
]


def _progress_start(instrument_id: str) -> None:
    _ANALYSIS_PROGRESS[instrument_id] = {
        "started": time.monotonic(),
        "mark": time.monotonic(),
        "stage": "starting",
        "stages_done": [],
    }


def _progress_stage(instrument_id: str, stage: str) -> None:
    p = _ANALYSIS_PROGRESS.get(instrument_id)
    if p is None:
        return
    now = time.monotonic()
    p["stages_done"].append(
        {"stage": p["stage"], "seconds": round(now - p["mark"], 2)}
    )
    p["mark"] = now
    p["stage"] = stage


def _progress_done(instrument_id: str) -> None:
    p = _ANALYSIS_PROGRESS.get(instrument_id)
    if p is None:
        return
    total = time.monotonic() - p["started"]
    _LAST_COLD_SECONDS[instrument_id] = total
    p["stage"] = "ready"


def analysis_progress(instrument_id: str) -> dict[str, Any]:
    """Time-remaining feed for the deep-analysis endpoint (polled by the UI)."""
    if instrument_id not in ALL:
        raise ValueError(f"unknown instrument: {instrument_id}")
    if analysis_is_cached(instrument_id):
        return {
            "active": False, "done": True, "cached": True, "stage": "ready",
            "pct": 100, "elapsed_seconds": 0, "seconds_remaining": 0,
            "note": "Ready — served instantly from cache.",
        }
    p = _ANALYSIS_PROGRESS.get(instrument_id)
    if p is None or p.get("stage") == "ready":
        est = _LAST_COLD_SECONDS.get(instrument_id, 35.0)
        return {
            "active": False, "done": False, "cached": False, "stage": "queued",
            "pct": 0, "elapsed_seconds": 0, "seconds_remaining": round(est, 1),
            "estimated_total_seconds": round(est, 1),
            "note": "Queued — the first deep analysis fetches providers, news and the AI thesis.",
        }
    now = time.monotonic()
    elapsed = now - p["started"]
    est = _LAST_COLD_SECONDS.get(instrument_id, 35.0)
    stage_i = _ANALYSIS_STAGES.index(p["stage"]) if p["stage"] in _ANALYSIS_STAGES else 1
    pct = min(95.0, round(100.0 * stage_i / (len(_ANALYSIS_STAGES) - 1), 1))
    return {
        "active": True, "done": False, "cached": False,
        "stage": p["stage"], "stages_done": p["stages_done"], "pct": pct,
        "elapsed_seconds": round(elapsed, 1),
        "estimated_total_seconds": round(est, 1),
        "seconds_remaining": round(max(0.0, est - elapsed), 1),
        "disclaimer": DISCLAIMER,
    }


def analysis_is_cached(instrument_id: str) -> bool:
    inst = ALL.get(instrument_id)
    if not inst:
        return False
    hit = _ANALYSIS_CACHE.get(f"analysis:{inst.id}")
    return bool(hit and time.monotonic() - hit[0] < 300)


_ANALYSIS_CACHE: dict[str, tuple[float, dict]] = {}

_NEWS_CACHE: dict[str, tuple[float, dict]] = {}


async def _cached_news(topic: str) -> dict[str, Any]:
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


async def nse_movers() -> dict[str, Any]:
    """NIFTY 50 gainers/losers + whole-market breadth from the latest
    official NSE bhavcopy (keyless, honest data date)."""
    store = get_store()
    m = await store.movers()
    return {
        "available": True,
        "date": m["date"],
        "gainers": m["gainers"], "losers": m["losers"],
        "advances": m["advances"], "declines": m["declines"],
        "counted": m["counted"],
        "market_advances": m.get("market_advances"),
        "market_declines": m.get("market_declines"),
        "disclaimer": DISCLAIMER,
    }


async def nse_status() -> dict[str, Any]:
    """Honest health of the India data pipeline (for the UI footer)."""
    store = get_store()
    status = await store.market_status()
    return {
        "source": "official NSE EOD files (keyless)",
        "market_status": status,
        "store": store.health(),
        "disclaimer": DISCLAIMER,
    }


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
    prism.new_session("daily-recap")
    ov = await overview()
    data = {"global": ov["global"], "movers": ov["movers"],
            "breadth": ov["breadth"], "vix": ov["vix"], "data_mode": ov["data_mode"]}
    text = await ai_analysis.daily_recap(get_gemini(), data)
    return {"text": text["text"], "generated_by": text["generated_by"],
            "data_mode": ov["data_mode"], "disclaimer": DISCLAIMER}


async def chat(question: str, instrument_id: str | None = None) -> dict[str, Any]:
    # PRISM: each chat exchange is one run -> its own trajectory
    prism.new_session("chat")
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
    prism.new_session("assistant-explain")
    return await ai_assistant.explain_snippet(get_gemini(), selected_text, context)


async def assistant_ask(question: str) -> dict[str, Any]:
    prism.new_session("assistant-qa")
    return await ai_assistant.general_qa(get_gemini(), question)


async def analyze_image(image_bytes: bytes, mime: str) -> dict[str, Any]:
    prism.new_session("image-analysis")
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


async def search_all(q: str) -> dict[str, Any]:
    """Search the static registry PLUS the full NSE + BSE listed universes.

    Users can paste tickers in the Yahoo convention — RELIANCE.NS or
    SBIN.BO — and get the exact instrument (suffix chooses the exchange:
    .NS/.NSE -> official NSE files, .BO/.BSE -> Alpha Vantage BSE history).
    Fuzzy search then covers company names across both universes.
    """
    agg = get_aggregator()
    extra: dict[str, Any] = {}
    universe_ok = False
    nse_error: str | None = None
    try:
        names = await agg.india.names()
        for sym, name in names.get("nse", {}).items():
            uid = f"nse-{sym.lower()}"
            extra[uid] = Instrument(
                id=uid, name=name, category="stock", region="india",
                currency="INR", stooq=None, twelvedata=None, finnhub=None,
                alphavantage=None, nse=sym, weight=0.6, keywords=(sym.lower(),),
            )
        for sym, name in names.get("bse", {}).items():
            uid = f"bse-{sym.lower()}"
            extra[uid] = Instrument(
                id=uid, name=name, category="stock", region="india",
                currency="INR", stooq=None, twelvedata=None, finnhub=None,
                alphavantage=f"{sym}.BO", nse=None, weight=0.5,
                keywords=(sym.lower(),),
            )
        universe_ok = bool(extra)
    except Exception as exc:
        nse_error = str(exc)

    # Exact pasted-ticker resolution (RELIANCE.NS / SBIN.BO / TCS) wins first.
    bare, exch = parse_ticker_suffix(q)
    exact: Instrument | None = None
    if exch == "nse" and bare in (await agg.india.names()).get("nse", {}):
        exact = await agg.dynamic_instrument(f"nse-{bare.lower()}")
    elif exch == "bse" and bare in (await agg.india.names()).get("bse", {}):
        exact = await agg.dynamic_instrument(f"bse-{bare.lower()}")
    elif exch is None and bare in (await agg.india.names()).get("nse", {}):
        exact = await agg.dynamic_instrument(f"nse-{bare.lower()}")

    hits = search_registry(q, limit=10, extra=extra)
    results: list[dict[str, Any]] = []
    if exact is not None:
        results.append({**exact.to_dict(), "category_label": "stock"})
    results.extend({**h.to_dict(), "category_label": h.category}
                   for h in hits if h.id != (exact.id if exact else None))
    return {"query": q,
            "results": results[:10],
            "nse_universe": universe_ok,
            "nse_error": nse_error,
            "disclaimer": DISCLAIMER}
