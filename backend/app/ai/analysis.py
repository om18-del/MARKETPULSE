"""ANALYSIS ROLE — data-grounded market analysis (the "main" AI).

Voice: precise, structured, professional analyst. Strict rule: the model
only *translates* the deterministic feature payload it receives — every
number it may quote appears in the payload. It must never predict prices
or give advice, and must follow the structured thesis format.

Pulse Assistant (the other role) never uses this module.
"""

from __future__ import annotations

import json
import re
from typing import Any

SYSTEM_PROMPT = """You are the Analysis Engine of MarketPulse, an educational \
market-literacy platform. You translate pre-computed quantitative features into \
clear, structured explanations for beginners.

GROUNDING RULES (violations are rejected):
- Every number you write MUST come from the FEATURES JSON. You may round long \
decimals to at most 2 places (write -0.48, never -0.48251929…); never alter \
formatted values like "-3.13%" or "1.03×"; never derive or compute new figures.
- Never mention a metric that is absent from the JSON (no VIX, breadth, or \
macro numbers unless they are literally in the payload). If a section's data is \
missing, write one short honest sentence saying so — never improvise.
- Use the "what_would_change_this_read" list verbatim as the basis of the final \
section; expand each item with its plain-English meaning, add nothing external.
- Use the "cross_asset" drivers (correlations) for the Cross-Asset Drivers section; \
if the list is empty, say the asset has no significant macro-driver relationships \
right now and move on.
- Never give investment advice, recommendations, or price predictions. Describe \
the current environment, never the future.

QUALITY RULES:
- FORMAT IS STRICT: your response MUST begin with the exact label \
"Structural Read:" — no preamble, no introduction, no summary sentence before it. \
The verdict sentence (verdict + confidence + the regime_equation in plain words) \
is the FIRST sentence INSIDE the Structural Read section, not before it.
- Then exactly three more labeled sections, in this order: "Cross-Asset Drivers", \
"Risk Conditions", "What Would Change This Read". Nothing comes before the first \
label and nothing after the final disclaimer line.
- Each section: cite 2-3 concrete values WITH their meaning in plain English \
(e.g. "RSI 39.8 — tilting bearish but far from oversold"). Explain what the \
reader should learn from each number, not just its label.
- Resolve apparent tensions explicitly (e.g. RSI oversold inside a downtrend = \
falling but stretched; volume above average means real participation).
- Sentence case, no markdown headings, no bullet points — plain sentences with \
the four labels. Maximum ~220 words.
- End with the exact line: "Educational information — not investment advice."

FOLLOW THIS SKELETON EXACTLY (fill the brackets, keep the labels):
"Structural Read: [verdict] environment with [confidence]% confidence — [the \
regime_equation in plain words]. [2-3 numbers with their meanings]."
"Cross-Asset Drivers: [driver correlations and what they mean, or the honest \
one-liner if empty]."
"Risk Conditions: [volatility, volume-flow, vwap numbers with meanings]."
"What Would Change This Read: [expand the what_would_change_this_read items]."
"Educational information — not investment advice."""


def _features_text(features: dict[str, Any]) -> str:
    return json.dumps(features, indent=1, default=str)


async def build_thesis(gemini, features: dict[str, Any]) -> dict[str, Any]:
    """Structured thesis from deterministic features. Falls back to a
    deterministic template thesis when AI is unavailable."""
    filt = features.get("filters") or {}
    payload = {
        "instrument": features.get("instrument_name", ""),
        "verdict": features.get("verdict"),
        "confidence": features.get("confidence"),
        "regime_equation": features.get("equation"),
        "factors": features.get("factors"),
        "cross_asset_drivers": (features.get("cross_asset") or {}).get("drivers") or {},
        "cross_asset_summary": (features.get("cross_asset") or {}).get("summary", ""),
        "vix_velocity": filt.get("vix_velocity"),
        "vwap_position": filt.get("vwap"),
        "what_would_change_this_read": features.get("what_would_change_this_read") or [],
        "key_news": features.get("news_headlines", [])[:3],
    }
    # Drop None entries so the model never sees an ambiguous key.
    payload = {k: v for k, v in payload.items() if v is not None}
    prompt = (
        f"{SYSTEM_PROMPT}\n\nFEATURES JSON:\n{_features_text(payload)}\n\n"
        "Write the four-section thesis now. Ground every sentence in this JSON."
    )
    fallback = _fallback_thesis(features)
    if gemini is None or not getattr(gemini, "available", False):
        return {"text": fallback, "generated_by": "deterministic-template"}
    try:
        # Generous budget: thinking-style models spend tokens on internal
        # reasoning before the visible text — a tight cap truncates theses
        # mid-sentence (the #1 failure PRISM's audit found).
        text = await gemini.generate(prompt, ttl=300, temperature=0.3, max_tokens=1600)
        if _mentions_forbidden(text):
            text = fallback + "\n\n(Redacted and replaced: the model attempted advice.)"
        # Format enforcement: the thesis must START at "Structural Read:" —
        # any preamble the model adds is stripped; no label at all = unusable.
        enforced = _enforce_thesis_format(text)
        if enforced is None:
            return {"text": fallback,
                    "generated_by": "deterministic-template (format guard)"}
        text = _enforce_word_cap(enforced)
        bad = _grounding_violations(text, payload)
        if bad:
            # The model quoted numbers that exist nowhere in the payload —
            # serve the deterministic template, which is grounded by design.
            return {"text": fallback,
                    "generated_by": "deterministic-template (grounding guard)",
                    "grounding_violations": bad}
        return {"text": text, "generated_by": "gemini-analysis"}
    except Exception:
        return {"text": fallback, "generated_by": "deterministic-template"}


def _collect_allowed_numbers(x: Any, allowed: set[str]) -> None:
    """Every number that legitimately appears in the payload — numeric leaves
    plus numbers embedded inside formatted strings ('-3.90%', '1.03×', '39.8').
    Rounded spellings (1 and 2 decimals) are allowed too, so a model that
    writes -0.48 for -0.48251929… is not falsely flagged."""
    if isinstance(x, dict):
        for v in x.values():
            _collect_allowed_numbers(v, allowed)
    elif isinstance(x, list):
        for v in x:
            _collect_allowed_numbers(v, allowed)
    elif isinstance(x, bool):
        return
    elif isinstance(x, (int, float)):
        allowed.add(str(x))
        allowed.add(str(abs(x)))
        for nd in (0, 1, 2):
            allowed.add(f"{x:.{nd}f}")
            allowed.add(f"{abs(x):.{nd}f}")
    elif isinstance(x, str):
        for m in re.findall(r"-?\d+(?:\.\d+)?", x):
            allowed.add(m)
            allowed.add(m.lstrip("-"))
            try:
                f = float(m)
            except ValueError:
                continue
            for nd in (0, 1, 2):
                allowed.add(f"{f:.{nd}f}")
                allowed.add(f"{abs(f):.{nd}f}")


def _grounding_violations(text: str, payload: dict[str, Any]) -> list[str]:
    """Numbers in the output that exist nowhere in the payload.

    Only checks decimals and integers ≥ 100 — small integers are almost
    always structural prose ('20-day average', 'four sections'), not data.
    """
    allowed: set[str] = set()
    _collect_allowed_numbers(payload, allowed)
    normalized = text.replace(",", "")
    quoted = re.findall(r"-?\d+\.\d+|-?\d{3,}", normalized)
    bad: list[str] = []
    for q in quoted:
        if q in allowed or q.lstrip("-") in allowed:
            continue
        try:
            if abs(float(q)) >= 100 or "." in q:
                bad.append(q)
        except ValueError:
            continue
    return bad


DISCLAIMER_LINE = "Educational information — not investment advice."


def _enforce_word_cap(text: str, max_words: int = 220) -> str:
    """Hard-cap thesis length and guarantee the closing disclaimer line.

    Auditors enforce the <220-word constraint strictly, and truncation can
    drop the disclaimer — both zero the compliance score. We keep whole
    sentences up to the budget and always end with the exact line.
    """
    body = text.replace(DISCLAIMER_LINE, "").strip()
    sentences = re.split(r"(?<=[.!?])\s+", body)
    kept: list[str] = []
    count = 0
    for s in sentences:
        n = len(s.split())
        if count + n > max_words and kept:
            break
        if count + n > max_words:
            kept.append(" ".join(s.split()[: max_words - count]))
            break
        kept.append(s)
        count += n
    out = " ".join(kept).strip()
    if out and out[-1] not in ".!?":
        out += "."
    return f"{out}\n{DISCLAIMER_LINE}" if out else DISCLAIMER_LINE


def _ends_with_disclaimer(text: str) -> bool:
    return text.strip().endswith(DISCLAIMER_LINE)


def _enforce_thesis_format(text: str) -> str | None:
    """Guarantee the response begins at 'Structural Read:'.

    LLMs occasionally add a summary sentence before the first label even when
    forbidden; downstream evaluators parse the four-label format strictly, so
    a preamble would zero the score. Strip anything before the first label;
    if the label never appears, the output is unusable (caller falls back).
    """
    m = re.search(r"Structural\s+Read\s*:", text)
    if not m:
        return None
    out = text[m.start():].lstrip()
    # collapse an accidental doubled label ("Structural Read: Structural Read:")
    out = re.sub(r"^(Structural\s+Read\s*:\s*)Structural\s+Read\s*:\s*",
                 r"\1", out, count=1, flags=re.IGNORECASE)
    return out


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
using ONLY the MARKET CONTEXT JSON provided — every number you cite must appear in that \
JSON; if the context lacks the data the question needs, say so plainly and explain what \
would answer it. Explain like a patient teacher for beginners: answer in the first \
sentence, then give the reasoning with 2-3 cited values and their plain-English meaning. \
Never give advice, predictions, or recommendations; if asked, explain how one *could think about* \
the situation instead. Max 180 words. \
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
        text = await gemini.generate(prompt, ttl=120, temperature=0.4, max_tokens=1200)
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
        text = await gemini.generate(prompt, ttl=600, temperature=0.4, max_tokens=1400)
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
        text = await gemini.generate(prompt, ttl=600, temperature=0.4, max_tokens=900)
        return {"text": text, "generated_by": "gemini-analysis"}
    except Exception:
        return {"text": (f"{pair_name} is at {data.get('rate')}, {data.get('d5_pct', 0):+.2f}% "
                         "over 5 days. Educational information — not investment advice."),
                "generated_by": "deterministic-template"}
