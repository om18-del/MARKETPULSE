"""Single Gemini client (gemini-2.5-flash) shared by both AI roles.

Hardened for free-tier realities: short timeouts, bounded retries with
backoff, response caching (TTL) to respect ~10 RPM, and graceful
unavailability when no key is configured.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from ..core.cache import TTLCache
from ..core.config import get_settings
from . import prism

log = logging.getLogger("marketpulse.ai")

# Fallback ladder: each Gemini model has its OWN free-tier daily quota bucket.
# When the primary model's daily quota is exhausted, we transparently try the
# next model so AI features keep working instead of dropping to keyword mode.
MODEL_LADDER = ["gemini-flash-lite-latest", "gemini-3.6-flash"]


def _is_daily_quota_error(exc: Exception) -> bool:
    """True when the error is a per-model DAILY quota exhaustion (not per-minute)."""
    text = str(exc)
    return "PerDayPerProjectPerModel" in text or "GenerateRequestsPerDay" in text


class GeminiClient:
    def __init__(self) -> None:
        s = get_settings()
        self.model_name = s.gemini_model
        self.available = bool(s.gemini_api_key)
        self._cache = TTLCache()
        self._model = None
        self._model_dead: set[str] = set()  # models whose daily quota ran out
        if self.available:
            try:
                from google import genai

                self._client = genai.Client(api_key=s.gemini_api_key)
                self._model = self._client.models
            except Exception as exc:  # pragma: no cover
                log.warning("Gemini init failed: %s", exc)
                self.available = False

    async def generate(self, prompt: str, *, ttl: int = 300,
                       temperature: float = 0.4, max_tokens: int = 3000) -> str:
        """Cached, retried text generation. Raises RuntimeError if unavailable/exhausted.

        Note: thinking-style models (gemini-3.x-flash) spend part of max_tokens on
        internal reasoning, so budgets here are generous to avoid truncated output."""
        if not self.available:
            raise RuntimeError("gemini unavailable: no API key")
        cache_key = f"{self.model_name}:{temperature}:{hashlib_sha(prompt)}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        t0 = prism.now_ms()
        last_exc: Exception | None = None
        candidates = [self.model_name] + [m for m in MODEL_LADDER if m != self.model_name]
        for model in candidates:
            if model in self._model_dead:
                continue
            for attempt in range(2):
                try:
                    def _call() -> str:
                        resp = self._model.generate_content(
                            model=model,
                            contents=prompt,
                            config={
                                "temperature": temperature,
                                "max_output_tokens": max_tokens,
                            },
                        )
                        return (resp.text or "").strip()

                    text = await asyncio.to_thread(_call)
                    self._cache.set(cache_key, text, ttl)
                    # PRISM: forward the real call (fail-open, never blocks,
                    # never adds latency to the user's response)
                    prism.emit_llm_bg(
                        model=model, prompt=prompt, output=text,
                        latency_ms=(prism.now_ms() - t0),
                        metadata={"attempt": attempt + 1, "cached": False},
                    )
                    return text
                except Exception as exc:
                    last_exc = exc
                    if _is_daily_quota_error(exc):
                        self._model_dead.add(model)
                        log.warning("Gemini model %s daily quota exhausted — switching models", model)
                        break  # next model in the ladder
                    wait = 1.2 * (attempt + 1)
                    log.warning("Gemini %s attempt %d failed: %s — retrying in %.1fs",
                                model, attempt + 1, exc, wait)
                    await asyncio.sleep(wait)
        raise RuntimeError(f"gemini failed after retries: {last_exc}")

    async def generate_json(self, prompt: str, *, ttl: int = 300,
                            temperature: float = 0.2, max_tokens: int = 4096) -> dict:
        """Generation that must yield a JSON object; retries with a larger budget
        if the model's reasoning truncated the JSON."""
        import re

        text = await self.generate(prompt, ttl=ttl, temperature=temperature, max_tokens=max_tokens)
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        # Truncated (thinking ate the budget) or non-JSON: retry once, bigger.
        text = await self.generate(
            prompt + "\n\nIMPORTANT: output the complete JSON object only.",
            ttl=0, temperature=temperature, max_tokens=max_tokens * 2,
        )
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise RuntimeError("gemini returned non-JSON")
        return json.loads(m.group(0))

    async def generate_with_image(self, image_bytes: bytes, mime: str, prompt: str = "") -> str:
        """Vision: explain an uploaded chart/screenshot educationally."""
        if not self.available:
            raise RuntimeError("gemini unavailable: no API key")
        cache_key = f"img:{hashlib_sha(prompt + str(len(image_bytes)))}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        t0_img = prism.now_ms()

        def _call() -> str:
            from google.genai import types

            resp = self._model.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime),
                    prompt,
                ],
                config={"temperature": 0.3, "max_output_tokens": 900},
            )
            return (resp.text or "").strip()

        text = await asyncio.to_thread(_call)
        self._cache.set(cache_key, text, 600)
        prism.emit_llm_bg(
            model=self.model_name, prompt=prompt, output=text,
            latency_ms=(prism.now_ms() - t0_img), metadata={"vision": True},
        )
        return text


def hashlib_sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:24]


gemini_client = GeminiClient()


def get_gemini() -> GeminiClient:
    return gemini_client
