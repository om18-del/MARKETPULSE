"""Application configuration loaded from environment variables (.env supported)."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration; every value can be overridden via env/.env."""

    app_name: str = "MarketPulse"
    version: str = "1.0.0"

    # --- AI ---
    # Comma-separated keys multiply the free daily quota (rotation built in).
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    # --- Providers ---
    # Comma-separated keys rotate automatically (each free key = own quota).
    twelvedata_api_key: str = ""
    finnhub_api_key: str = ""
    alphavantage_api_key: str = ""

    # --- PRISM tracing (optional; tracing is fail-open) ---
    prismtrace_api_key: str = ""
    prismtrace_project_id: str = ""
    prismtrace_host: str = "https://prism-api-prod.up.railway.app"

    # --- Server ---
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Behavior ---
    force_demo_mode: bool = False
    quote_ttl_seconds: int = 60
    daily_ttl_seconds: int = 6 * 3600
    news_ttl_seconds: int = 600
    ai_ttl_seconds: int = 300

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_ai(self) -> bool:
        return bool(self.gemini_api_key)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
