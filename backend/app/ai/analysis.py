"""ANALYSIS ROLE — data-grounded market analysis (the "main" AI).

Voice: precise, structured, professional analyst. Strict rule: the model
only *translates* the deterministic feature payload it receives — every
number it may quote appears in the payload. It must never predict prices
or give advice, and must follow the structured thesis format.

Pulse Assistant (the other role) never uses this module.
"""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are the Analysis Engine of MarketPulse, an educational \
market-literacy platform. You translate pre-computed quantitative features into \
clear, structured explanations for beginners.

RULES:
- Use ONLY the numbers in the provided FEATURES JSON. Never invent or alter any number.
- Never give investment advice, recommendations, or price predictions. You describe \
the current environment, not the future.
- Structure every thesis exactly as: "Structural Read", "Cross-Asset Drivers", \
"Risk Conditions", "What Would Change This Read".
- Begin sections with the verdict sentence, then explain in plain English.
- End with the exact line: "Educational information — not investment advice."
- Maximum ~220 words. No markdown headings, use plain sentences with the four labels."""


def _features_text(features: dict[str, Any]) -> str:
    return json.dumps(features, indent=1, default=str)


async def build_thesis(gemini, features: dict[str, Any]) -> dict[str, Any]:
    """Structured thesis from deterministic features. Falls back to a
    deterministic template thesis when AI is unavailable."""
    payload = {
        "instrument": features.get("instrument_name", ""),
        "verdict": features.get("verdict"),
        "confidence": features.get("confidence"),
        "regime_equation": features.get("equation"),
        "factors": features.get("factors"),
        "deterministic_filters": features.get("filters"),
        "key_news": features.get("news_headlines", [])[:5],
    }
    prompt = (
        f"{SYSTEM_PROMPT}\n\nFEATURES JSON:\n{_features_text(payload)}\n\n"
        "Write the four-section thesis now."
    )
    fallback = _fallback_thesis(features)
    if gemini is None or not getattr(gemini, "available", False):
        return {"text": fallback, "generated_by": "deterministic-template"}
    try:
        text = await gemini.generate(prompt, ttl=300, temperature=0.35, max_tokens=700)
        if _mentions_forbidden(text):
            text = fallback + "\n\n(Redacted and replaced: the model attempted advice.)"
        return {"text": text, "generated_by": "gemini-analysis"}
    except Exception:
        return {"text": fallback, "generated_by": "deterministic-template"}


def _mentions_forbidden(text: str) -> bool:
    bad = ("you should buy", "you should sell", "i recommend buying", "i recommend selling",
           "buy now", "sell now", "target price", "price target", "will reach", "guaranteed")
    t = text.lower()
    return any(b in t for b in bad)


def _fallback_thesis(f: dict[str, Any]) -> str:
    verdict = f.get("verdict", "neutral").upper()
    conf = f.get("confidence", "-")
    filt = f.get("filters") or {}
    vwap = (filt.get("vwap") or {})
    vp = (filt.get("volume_pressure") or {})
    vix = (filt.get("vix_velocity") or {})
    parts = []
    parts.append(
        f"Structural Read: MarketPulse's math layer scores this environment {verdict} "
        f"with {conf}% confidence. {f.get('equation', '')}"
    )
    parts.append(
        f"Cross-Asset Drivers: "
        + "; ".join(f"{k}: {v.get('correlation', 'n/a')} correlation"
                    for k, v in ((f.get('cross_asset') or {}).get('drivers') or {}).items())
        + ". Volume flow reads as " + str(vp.get('proxy_label', 'balanced'))
        + ("; volatility is " + str(vix.get('regime', 'stable')) if vix else "")
        + "."
    )
    parts.append(
        "Risk Conditions: "
        + (f"price is {vwap.get('band', 'normal')} relative to its volume-weighted average "
           f"(z-score {vwap.get('zscore', 'n/a')}). " if vwap else "")
        + "High volatility would push this read toward Uncertain."
    )
    parts.append(
        "What Would Change This Read: " +
        "; ".join(f.get("what_would_change_this_read", [])[:3])
    )
    parts.append("Educational information — not investment advice.")
    return "\n".join(parts)


ANALYSIS_CHAT_PROMPT = """You are the Analysis chat of MarketPulse. Answer the user's question \
using ONLY the MARKET CONTEXT JSON provided. Explain like a patient teacher for beginners. \
Never give advice, predictions, or recommendations; if asked, explain how one *could think about* \
the situation instead. Cite the exact numbers you use. Max 180 words. \
End with: "Educational information — not investment advice."
"""


async def chat_answer(gemini, question: str, context: dict[str, Any]) -> dict[str, Any]:
    """Data-grounded Q&A about current market state."""
    if gemini is None or not getattr(gemini, "available", False):
        return {
            "answer": ("AI chat needs a Gemini API key on the backend. Everything else in "
                       "MarketPulse — data, math engine, evidence panels — still works. "
                       "Educational information — not investment advice."),
            "generated_by": "unavailable",
        }
    prompt = (
        f"{ANALYSIS_CHAT_PROMPT}\n\nMARKET CONTEXT JSON:\n{_features_text(context)}\n\n"
        f"USER QUESTION: {question}"
    )
    try:
        text = await gemini.generate(prompt, ttl=120, temperature=0.4, max_tokens=600)
        return {"answer": text, "generated_by": "gemini-analysis"}
    except Exception:
        return {
            "answer": ("The AI service is temporarily unavailable (likely free-tier quota). "
                       "The deterministic analysis and evidence panels remain fully available. "
                       "Educational information — not investment advice."),
            "generated_by": "fallback",
        }


RECAP_PROMPT = """You are the Analysis Engine of MarketPulse writing the "60-second market recap".
Using ONLY the DATA JSON: write 5 short bullet lines:
1) Global read (verdict + confidence + one reason)
2) Biggest mover and why (cite its number)
3) What volatility is doing (cite VIX or realized vol)
4) One macro/FX driver worth knowing (cite the number)
5) One thing beginners should watch next (educational, not advice)
Plain text lines starting with "• ". Max 130 words total. End with:
"Educational information — not investment advice."
"""


async def daily_recap(gemini, data: dict[str, Any]) -> dict[str, Any]:
    if gemini is None or not getattr(gemini, "available", False):
        return {"text": _fallback_recap(data), "generated_by": "deterministic-template"}
    prompt = f"{RECAP_PROMPT}\n\nDATA JSON:\n{_features_text(data)}"
    try:
        text = await gemini.generate(prompt, ttl=600, temperature=0.4, max_tokens=500)
        return {"text": text, "generated_by": "gemini-analysis"}
    except Exception:
        return {"text": _fallback_recap(data), "generated_by": "deterministic-template"}


def _fallback_recap(data: dict[str, Any]) -> str:
    g = data.get("global", {})
    movers = data.get("movers", {})
    lines = [
        f"• Global read: {str(g.get('verdict', 'n/a')).upper()} ({g.get('confidence', '-')}% confidence) — {g.get('equation', 'math blend of all assets')}.",
    ]
    top_g = (movers.get("gainers") or [{}])[0]
    top_l = (movers.get("losers") or [{}])[0]
    if top_g:
        lines.append(f"• Biggest gainer: {top_g.get('name')} {top_g.get('change_pct', 0):+.2f}% today.")
    if top_l:
        lines.append(f"• Biggest loser: {top_l.get('name')} {top_l.get('change_pct', 0):+.2f}% today.")
    vix = data.get("vix")
    if vix:
        lines.append(f"• Volatility: VIX at {vix.get('last_price')} ({vix.get('change_pct', 0):+.2f}% today).")
    lines.append("• Watch next: whether breadth (share of assets above their 50-day averages) improves or fades.")
    lines.append("Educational information — not investment advice.")
    return "\n".join(lines)


FX_PROMPT = """You are the Analysis Engine of MarketPulse. Explain in 3-4 beginner-friendly \
sentences what the DATA JSON says about this currency pair: the level, the recent move, and one \
plain-English implication (e.g. for import prices, travel, or export competitiveness). Use only \
given numbers. No advice. End with: "Educational information — not investment advice."
"""


async def fx_explainer(gemini, pair_name: str, data: dict[str, Any]) -> dict[str, Any]:
    if gemini is None or not getattr(gemini, "available", False):
        return {"text": (f"{pair_name} is at {data.get('rate')}. It has moved "
                         f"{data.get('d5_pct', 0):+.2f}% over 5 days. Educational information — "
                         "not investment advice."),
                "generated_by": "deterministic-template"}
    prompt = f"{FX_PROMPT}\n\nDATA JSON:\n{_features_text({'pair': pair_name, **data})}"
    try:
        text = await gemini.generate(prompt, ttl=600, temperature=0.4, max_tokens=300)
        return {"text": text, "generated_by": "gemini-analysis"}
    except Exception:
        return {"text": (f"{pair_name} is at {data.get('rate')}, {data.get('d5_pct', 0):+.2f}% "
                         "over 5 days. Educational information — not investment advice."),
                "generated_by": "deterministic-template"}
