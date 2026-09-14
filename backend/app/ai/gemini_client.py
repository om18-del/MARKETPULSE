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

log = logging.getLogger("marketpulse.ai")


class GeminiClient:
    def __init__(self) -> None:
        s = get_settings()
        self.model_name = s.gemini_model
        self.available = bool(s.gemini_api_key)
        self._cache = TTLCache()
        self._model = None
        if self.available:
            try:
                from google import genai

                self._client = genai.Client(api_key=s.gemini_api_key)
                self._model = self._client.models
            except Exception as exc:  # pragma: no cover
                log.warning("Gemini init failed: %s", exc)
                self.available = False

    async def generate(self, prompt: str, *, ttl: int = 300,
                       temperature: float = 0.4, max_tokens: int = 1200) -> str:
        """Cached, retried text generation. Raises RuntimeError if unavailable/exhausted."""
        if not self.available:
            raise RuntimeError("gemini unavailable: no API key")
        cache_key = f"{self.model_name}:{temperature}:{hashlib_sha(prompt)}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                def _call() -> str:
                    resp = self._model.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config={
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                        },
                    )
                    return (resp.text or "").strip()

                text = await asyncio.to_thread(_call)
                self._cache.set(cache_key, text, ttl)
                return text
            except Exception as exc:
                last_exc = exc
                wait = 1.5 * (attempt + 1)
                log.warning("Gemini attempt %d failed: %s — retrying in %.1fs",
                            attempt + 1, exc, wait)
                await asyncio.sleep(wait)
        raise RuntimeError(f"gemini failed after retries: {last_exc}")

    async def generate_json(self, prompt: str, *, ttl: int = 300,
                            temperature: float = 0.2, max_tokens: int = 900) -> dict:
        """Generation that must yield a JSON object; raises if it can't."""
        text = await self.generate(prompt, ttl=ttl, temperature=temperature, max_tokens=max_tokens)
        import re
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
        return text


def hashlib_sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:24]


gemini_client = GeminiClient()


def get_gemini() -> GeminiClient:
    return gemini_client
