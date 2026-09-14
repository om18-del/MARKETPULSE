"""News sentiment analyzer.

Primary: Gemini with a strict JSON contract — returns a per-article verdict
(sentiment -1..1, one-phrase reason, key phrase quoted) plus an aggregate.
Fallback: deterministic keyword model so the app never shows an AI failure
to the user — it shows "keyword-based analysis" instead.
"""

from __future__ import annotations

import re
from typing import Any

POSITIVE = ["surge", "rally", "gain", "jump", "beat", "record high", "boost", "optimism",
            "upbeat", "strong", "growth", "recovery", "soar", "climb", "advance", "rise",
            "bullish", "inflow", "upgrade", "profit", "expansion", " stimulus"]
NEGATIVE = ["plunge", "slump", "fall", "drop", "crash", "fear", "selloff", "sell-off",
            "recession", "inflation", "rate hike", "warning", "weak", "loss", "decline",
            "bearish", "outflow", "downgrade", "tariff", "war", "sanction", "crisis",
            "layoff", "default", "sink", "tumble"]


def keyword_sentiment(title: str) -> tuple[float, str, str]:
    t = title.lower()
    pos = sum(1 for w in POSITIVE if w in t)
    neg = sum(1 for w in NEGATIVE if w in t)
    if pos > neg:
        score = min(1.0, 0.3 + 0.2 * (pos - neg))
        word = next((w for w in POSITIVE if w in t), "")
        return score, f'positive cue: "{word}"', word
    if neg > pos:
        score = -min(1.0, 0.3 + 0.2 * (neg - pos))
        word = next((w for w in NEGATIVE if w in t), "")
        return score, f'negative cue: "{word}"', word
    return 0.0, "no strong cue", ""


def keyword_analyze(articles: list[dict[str, Any]]) -> dict[str, Any]:
    tagged = []
    total = 0.0
    for a in articles:
        s, reason, phrase = keyword_sentiment(a.get("title", ""))
        total += s
        tagged.append({**a, "sentiment": round(s, 2), "reason": reason, "key_phrase": phrase,
                       "method": "keyword"})
    n = len(tagged) or 1
    return {
        "aggregate_score": round(total / n, 2),
        "method": "keyword",
        "articles": tagged,
        "summary": ("News tone leans positive" if total / n > 0.1 else
                    "News tone leans negative" if total / n < -0.1 else
                    "News tone is mixed/neutral"),
    }


def build_gemini_prompt(articles: list[dict[str, Any]]) -> str:
    lines = []
    for i, a in enumerate(articles):
        lines.append(f"{i}. [{a.get('publisher', '')}] {a.get('title', '')}")
    joined = "\n".join(lines)
    return (
        "You are a financial-literacy assistant. For each headline, output STRICT JSON only "
        '(no markdown fences) matching exactly:\n'
        '{"articles":[{"i":0,"sentiment":0.0,"reason":"max 12 words","key_phrase":"words from headline"}],'
        '"summary":"one sentence, plain English, max 25 words"}\n'
        "sentiment is between -1 (very negative for markets) and +1 (very positive). "
        "reason must cite the specific words in the headline that drove the score. "
        "Do not invent facts. Here are the headlines:\n" + joined
    )


def parse_gemini_json(text: str, articles: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Robustly parse the model's JSON (tolerates fences)."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        import json
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    per_article = {int(x.get("i", -1)): x for x in data.get("articles", []) if isinstance(x, dict)}
    tagged = []
    total = 0.0
    for i, a in enumerate(articles):
        x = per_article.get(i, {})
        s = max(-1.0, min(1.0, float(x.get("sentiment", 0))))
        total += s
        tagged.append({**a, "sentiment": round(s, 2),
                       "reason": str(x.get("reason", ""))[:120],
                       "key_phrase": str(x.get("key_phrase", ""))[:80],
                       "method": "gemini"})
    n = len(tagged) or 1
    return {
        "aggregate_score": round(total / n, 2),
        "method": "gemini",
        "articles": tagged,
        "summary": str(data.get("summary", ""))[:200],
    }


async def analyze(articles: list[dict[str, Any]], gemini=None) -> dict[str, Any]:
    """Gemini analysis with deterministic keyword fallback."""
    if not articles:
        return {"aggregate_score": 0.0, "method": "none", "articles": [],
                "summary": "No headlines available."}
    if gemini is not None:
        try:
            raw = await gemini.generate(build_gemini_prompt(articles))
            parsed = parse_gemini_json(raw, articles)
            if parsed:
                return parsed
        except Exception:
            pass
    return keyword_analyze(articles)
