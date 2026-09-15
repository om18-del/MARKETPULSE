"""Single Gemini client shared by both AI roles.

Hardened for free-tier realities:
* Short timeouts, bounded retries with backoff, response caching (TTL).
* MULTI-KEY ROTATION: GEMINI_API_KEY accepts comma-separated keys. Free-tier
  quota is per key per model, so N keys multiply the daily budget. Keys whose
  quota is exhausted are skipped automatically for the rest of the day.
* MODEL LADDER: each Gemini model has its OWN daily bucket per key. When a
  (key, model) combo is exhausted, we transparently try the next model on the
  next live key — AI features keep working instead of dropping to templates.
* 429 rate-limit responses rotate to the next key immediately (per-minute
  limits, not daily ones) with a small backoff.
"""

from __future__ import annotations

import asyncio
import itertools
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


class TruncatedOutputError(RuntimeError):
    """Model hit max_output_tokens mid-synthesis (finish_reason=MAX_TOKENS)."""


def _is_daily_quota_error(exc: Exception) -> bool:
    """True when the error is a per-model DAILY quota exhaustion (not per-minute)."""
    text = str(exc)
    return "PerDayPerProjectPerModel" in text or "GenerateRequestsPerDay" in text


def _is_rate_limit_error(exc: Exception) -> bool:
    """Per-minute 429 exhaustion — rotate keys/models right away."""
    text = str(exc).lower()
    return "429" in text or "resource_exhausted" in text or "rate" in text


class GeminiClient:
    def __init__(self) -> None:
        s = get_settings()
        # Comma-separated keys: each free-tier key is its own daily bucket.
        self._keys = [k.strip() for k in (s.gemini_api_key or "").split(",") if k.strip()]
        self._key_cycle = itertools.cycle(range(len(self._keys))) if self._keys else None
        self._exhausted: set[tuple[str, str]] = set()  # (key, model) daily-dead
        self.available = bool(self._keys)
        self.model_name = s.gemini_model
        self._cache = TTLCache()
        self._model_dead: set[str] = set()  # models dead on EVERY key
        self._clients_by_key: dict[str, Any] = {}  # keep full clients alive (closing = dead HTTP pool)
        if self.available:
            try:
                from google import genai

                for key in self._keys:
                    try:
                        self._clients_by_key[key] = genai.Client(api_key=key)
                    except Exception as exc:  # invalid key — drop it, keep the rest
                        log.warning("Gemini key …%s rejected at init: %s", key[-6:], exc)
                self.available = bool(self._clients_by_key)
            except Exception as exc:  # pragma: no cover
                log.warning("Gemini init failed: %s", exc)
                self.available = False

    # ------------------------------------------------------------------
    def _live_combos(self, candidates: list[str]) -> list[tuple[str, str, Any]]:
        """All (model, key, models-api) combos still believed to have quota,
        rotated so consecutive calls spread the load across keys."""
        out: list[tuple[str, str, Any]] = []
        for model in candidates:
            for key in self._keys:
                if (key, model) in self._exhausted:
                    continue
                cl = self._clients_by_key.get(key)
                if cl is not None:
                    out.append((model, key, cl.models))
        # start the sweep at a different key each call (round-robin)
        if out and self._key_cycle is not None:
            offset = next(self._key_cycle) % len(out)
            out = out[offset:] + out[:offset]
        return out

    async def generate(self, prompt: str, *, ttl: int = 300,
                       temperature: float = 0.4, max_tokens: int = 3000) -> str:
        """Cached, retried, key-rotating text generation.

        Raises RuntimeError if unavailable/exhausted on every key.

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
        combos = self._live_combos(candidates)
        if not combos:
            raise RuntimeError("gemini exhausted: all keys/models out of daily quota")

        tried: set[tuple[str, str]] = set()
        for round_no in range(2):  # two sweeps: immediate rotation, then one retry sweep
            for model, key, models in combos:
                if (key, model) in tried or (key, model) in self._exhausted:
                    continue
                tried.add((key, model))
                # Sweep 2 doubles the budget: thinking-style models vary in
                # reasoning spend, so a truncation retry with 2x tokens usually
                # completes (the audit's top failure was MAX_TOKENS truncation).
                budget = max_tokens * (round_no + 1)
                try:
                    def _call() -> tuple[str, str]:
                        resp = models.generate_content(
                            model=model,
                            contents=prompt,
                            config={
                                "temperature": temperature,
                                "max_output_tokens": budget,
                            },
                        )
                        # finish_reason: MAX_TOKENS = output truncated mid-synthesis
                        # (the audit's top failure theme). Surface it so callers
                        # can retry instead of serving a cut-off thesis.
                        reason = str(getattr(resp, "finish_reason", "") or "")
                        return (resp.text or "").strip(), reason

                    text, finish = await asyncio.to_thread(_call)
                    if "MAX_TOKENS" in finish.upper():
                        raise TruncatedOutputError(
                            f"output truncated (finish_reason=MAX_TOKENS, {len(text)} chars)")
                    self._cache.set(cache_key, text, ttl)
                    # PRISM: forward the real call (fail-open, never blocks)
                    prism.emit_llm_bg(
                        model=model, prompt=prompt, output=text,
                        latency_ms=(prism.now_ms() - t0),
                        metadata={"attempt": round_no + 1, "cached": False,
                                  "key_tail": key[-6:] if len(self._keys) > 1 else "single"},
                    )
                    return text
                except Exception as exc:
                    last_exc = exc
                    if _is_daily_quota_error(exc):
                        self._exhausted.add((key, model))
                        log.warning(
                            "Gemini daily quota gone for key …%s on %s — %d combo(s) left",
                            key[-6:], model, len(candidates) * len(self._keys) - len(self._exhausted),
                        )
                        # If this model is dead on every key, mark it and let the
                        # ladder fall through to the next model on the next call.
                        if all((k, model) in self._exhausted for k in self._keys):
                            self._model_dead.add(model)
                        continue
                    if _is_rate_limit_error(exc):
                        # Per-minute limit: immediately try the next key/model,
                        # tiny pause to let the RPM window breathe.
                        await asyncio.sleep(0.8)
                        continue
                    if isinstance(exc, TruncatedOutputError):
                        log.warning("Gemini output truncated on %s/%s — next attempt gets 2x budget",
                                    model, key[-6:] if len(self._keys) > 1 else "single")
                        continue
                    await asyncio.sleep(1.2 * (round_no + 1))
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
        combos = self._live_combos([self.model_name])
        if not combos:
            raise RuntimeError("gemini exhausted: no live key for vision")

        def _call(models: Any) -> str:
            from google.genai import types

            resp = models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime),
                    prompt,
                ],
                config={"temperature": 0.3, "max_output_tokens": 900},
            )
            return (resp.text or "").strip()

        last_exc: Exception | None = None
        for model, key, models in combos:
            try:
                text = await asyncio.to_thread(_call, models)
                self._cache.set(cache_key, text, 600)
                prism.emit_llm_bg(
                    model=model, prompt=prompt, output=text,
                    latency_ms=(prism.now_ms() - t0_img), metadata={"vision": True},
                )
                return text
            except Exception as exc:
                last_exc = exc
                if _is_daily_quota_error(exc):
                    self._exhausted.add((key, model))
        raise RuntimeError(f"gemini vision failed: {last_exc}")

    def health(self) -> dict[str, Any]:
        """Key-rotation state for the health endpoint / About page."""
        live_keys = [k for k in self._keys if any((k, m) not in self._exhausted
                                                   for m in [self.model_name, *MODEL_LADDER])]
        return {
            "available": self.available,
            "keys_configured": len(self._keys),
            "keys_alive": len(live_keys),
            "model": self.model_name,
            "model_ladder": MODEL_LADDER,
            "exhausted_combos": len(self._exhausted),
        }


def hashlib_sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:24]


gemini_client = GeminiClient()


def get_gemini() -> GeminiClient:
    return gemini_client
