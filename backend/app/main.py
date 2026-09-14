"""MarketPulse — FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .routes.api import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("marketpulse")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("MarketPulse starting — AI: %s | model: %s",
             "enabled" if settings.has_ai else "DISABLED (no key)",
             settings.gemini_model)
    yield
    log.info("MarketPulse shutting down")


app = FastAPI(
    title="MarketPulse API",
    description="Educational market decision-support: deterministic math + explainable AI. "
                "Not investment advice.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root() -> dict:
    return {
        "app": "MarketPulse",
        "tagline": "See the market's pulse. Understand the why.",
        "docs": "/docs",
        "health": "/api/health",
        "disclaimer": "Educational information — not investment advice.",
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
