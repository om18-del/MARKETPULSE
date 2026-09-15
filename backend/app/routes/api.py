"""All MarketPulse API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .. import service
from ..dictionary.service import categories as dict_categories
from ..dictionary.service import search as dict_search
from ..demo.snapshots import PROFILE as DEMO_PROFILE

router = APIRouter(prefix="/api")


# ------------------------------- schemas -------------------------------
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    instrument_id: str | None = None


class AssistantRequest(BaseModel):
    mode: str = Field("qa", pattern="^(qa|explain)$")
    text: str = Field(..., min_length=1, max_length=4000)
    context: dict[str, Any] | None = None


class ImageRequest(BaseModel):
    image_b64: str = Field(..., min_length=32)
    mime: str = Field("image/png", pattern="^(image/(png|jpeg|jpg|webp))$")


class ConvertRequest(BaseModel):
    amount: float = Field(..., gt=0)
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)


class DemoToggleRequest(BaseModel):
    enabled: bool


class WatchlistRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=100)


# ------------------------------- basics --------------------------------
@router.get("/health")
async def health() -> dict:
    from ..ai.gemini_client import get_gemini

    agg = service.get_aggregator()
    gemini = get_gemini()
    return {
        "status": "ok",
        "app": "MarketPulse",
        "version": "1.0.0",
        "data_mode": "demo" if service.DEMO_STATE["forced"] else "auto",
        "ai_available": gemini.available,
        "providers": agg.health()["providers"],
        "disclaimer": service.DISCLAIMER,
    }


@router.get("/overview")
async def overview() -> dict:
    try:
        return await service.overview()
    except Exception as exc:  # last-resort guard: never kill the homepage
        raise HTTPException(status_code=503, detail=f"overview unavailable: {exc}") from exc


@router.get("/search")
async def search(q: str = Query(..., min_length=1, max_length=50)) -> dict:
    return await service.search_all(q)


@router.get("/asset/{instrument_id}")
async def asset(instrument_id: str) -> dict:
    try:
        return await service.asset_detail(instrument_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analysis/{instrument_id}")
async def analysis(instrument_id: str) -> dict:
    try:
        return await service.full_analysis(instrument_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"analysis unavailable: {exc}") from exc


@router.get("/analysis/{instrument_id}/progress")
async def analysis_progress(instrument_id: str) -> dict:
    """Stage + time-remaining feed for the deep-analysis request."""
    try:
        return service.analysis_progress(instrument_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/chart/{instrument_id}")
async def chart_bars(instrument_id: str, tf: str = Query("daily", pattern="^(intraday|daily|monthly)$")) -> dict:
    """Bars for the main price chart — daily (official files), intraday (5m) or monthly."""
    try:
        return await service.chart_bars(instrument_id, tf)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"chart bars unavailable: {exc}") from exc


@router.get("/timeframes/{instrument_id}")
async def timeframes(instrument_id: str, force: bool = Query(False)) -> dict:
    """Bullish/bearish stats per timeframe: intraday (5m) · daily · monthly."""
    try:
        return await service.timeframe_analysis(instrument_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/scanner/intraday-conflicts")
async def intraday_conflicts() -> dict:
    """NIFTY 50 stocks whose intraday direction opposes their daily trend."""
    return await service.intraday_scanner()


@router.get("/integrity")
async def integrity() -> dict:
    """Data self-audit: duplicate dates, ordering, flat lines, demo fallbacks."""
    return await service.integrity_audit()


@router.post("/watchlist/quotes")
async def watchlist_quotes(req: WatchlistRequest) -> dict:
    """EOD quotes for the user's saved watchlist (one round-trip, fully cached)."""
    return await service.watchlist_quotes(req.ids)


# --------------------------------- news --------------------------------
@router.get("/news")
async def news(topic: str = Query("india")) -> dict:
    """News feed — India is the default topic (India-first product)."""
    return await service.news_feed(topic)


# --------------------------------- chat --------------------------------
@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    try:
        return await service.chat(req.question, req.instrument_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"chat unavailable: {exc}") from exc


# ------------------------------ assistant ------------------------------
@router.post("/assistant")
async def assistant(req: AssistantRequest) -> dict:
    if req.mode == "explain":
        return await service.assistant_explain(req.text, req.context)
    return await service.assistant_ask(req.text)


# ------------------------------- image ---------------------------------
@router.post("/analyze-image")
async def analyze_image(req: ImageRequest) -> dict:
    import base64

    try:
        raw = base64.b64decode(req.image_b64, validate=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid base64 image") from exc
    if len(raw) > 6_000_000:
        raise HTTPException(status_code=413, detail="image too large (max ~6MB)")
    return await service.analyze_image(raw, req.mime)


# --------------------------------- fx ----------------------------------
@router.get("/fx")
async def fx(base: str = Query("INR", min_length=3, max_length=3)) -> dict:
    """FX panel — INR is the default base (India-first product)."""
    payload = await service.fx_overview()
    return {**payload, "selected_base": base.upper()}


@router.post("/fx/convert")
async def fx_convert(req: ConvertRequest) -> dict:
    payload = await service.fx_overview()
    return service.fx_convert(req.amount, req.from_currency, req.to_currency, payload["usd_rates"])


# ------------------------------- recap ---------------------------------
@router.get("/recap")
async def recap() -> dict:
    return await service.recap()


# ----------------------------- dictionary ------------------------------
@router.get("/dictionary")
async def dictionary(q: str = Query(""), category: str = Query("")) -> dict:
    return dict_search(q, category)


@router.get("/dictionary/categories")
async def dictionary_cats() -> dict:
    return {"categories": dict_categories()}


# --------------------------------- nse ----------------------------------
@router.get("/nse/movers")
async def nse_movers() -> dict:
    """NIFTY 50 gainers/losers/advances direct from nseindia.com."""
    try:
        return await service.nse_movers()
    except Exception as exc:
        return {"available": False, "reason": f"NSE unreachable: {exc}",
                "disclaimer": service.DISCLAIMER}


@router.get("/nse/status")
async def nse_status() -> dict:
    return await service.nse_status()


# ----------------------------- methodology -----------------------------
@router.get("/methodology")
async def methodology() -> dict:
    import json
    from pathlib import Path

    path = Path(__file__).parent.parent / "methodology.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# -------------------------------- demo ---------------------------------
@router.post("/demo/toggle")
async def demo_toggle(req: DemoToggleRequest) -> dict:
    return service.toggle_demo(req.enabled)


@router.get("/demo/snapshot-info")
async def demo_info() -> dict:
    return {"instruments": len(DEMO_PROFILE), "note": "deterministic synthetic daily histories"}
