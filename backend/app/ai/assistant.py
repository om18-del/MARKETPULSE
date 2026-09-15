"""PULSE ASSISTANT (PA) — the simple-words explainer + light general QA.

Voice: warm, patient teacher. Scope guard: PA explains; it does not
analyze. It receives the selected text + its surrounding context and
translates that specific thing into beginner language. It never produces
theses, verdicts, or advice, and it is strictly separated from the
Analysis role (different prompts, different routes).
"""

from __future__ import annotations

from typing import Any

FAQ: list[dict[str, str]] = [
    {"q": "what is a stock", "a": "A stock is a small ownership slice of a company. If a company has 1,000 shares and you own 1, you own 0.1% of it — and its future success (or struggle) is reflected in that share's price. Educational information — not investment advice."},
    {"q": "what is an index", "a": "An index is a basket that tracks many stocks at once — like the NIFTY 50 (India's 50 biggest) or the S&P 500 (500 large US companies). It shows the market's overall direction instead of one company's. Educational information — not investment advice."},
    {"q": "what is volatility", "a": "Volatility is how wildly a price swings. High volatility = bigger, faster moves in both directions. It's not good or bad — but it makes outcomes harder to anticipate, which is why MarketPulse maps high volatility to 'Uncertain'. Educational information — not investment advice."},
    {"q": "what is a bull market", "a": "A bull market is a sustained period of rising prices and optimism. A bear market is the opposite: falling prices and caution. The names come from how each animal attacks — bull horns swing up, bear paws swing down. Educational information — not investment advice."},
    {"q": "what is rsi", "a": "RSI (Relative Strength Index) scores recent gains vs losses on a 0-100 scale. Above 70 is often called 'overbought' (a big run-up already happened); below 30 'oversold'. It's a speedometer, not a signal to act. Educational information — not investment advice."},
    {"q": "what is a pe ratio", "a": "The price-to-earnings ratio compares a company's share price to its annual profit per share. High P/E can mean high growth expectations — or an expensive price. It's a context tool, not a verdict. Educational information — not investment advice."},
    {"q": "why do markets fall when the fed raises rates", "a": "Higher US interest rates make safe bonds pay more, so riskier assets like stocks look relatively less attractive; borrowing also costs companies more. That's why rate decisions move global markets. Educational information — not investment advice."},
    {"q": "what is volume", "a": "Volume is how many shares changed hands. Big price moves on high volume mean broad participation; the same move on thin volume is easier to reverse. Educational information — not investment advice."},
    {"q": "how do i start investing", "a": "The usual first steps people learn: build an emergency fund, then learn broad instruments (like index funds) before individual stocks, and only invest money you won't need soon. MarketPulse teaches how to *read* markets — decisions are always yours. Educational information — not investment advice."},
    {"q": "is this app giving me advice", "a": "No. MarketPulse is educational: it shows market signals, math, and news with full evidence, and explains what they mean. It never tells anyone to buy or sell. Educational information — not investment advice."},
]

EXPLAIN_PROMPT = """You are the Pulse Assistant of MarketPulse — a patient teacher for stock-market \
beginners. The user selected a piece of analysis text and wants it explained.

RULES:
- Explain ONLY what the selected text says, in even simpler words. Never introduce \
new numbers — reuse only figures present in the selection or context.
- Structure the answer in three labeled parts:
  "In simple words:" 1-2 sentences a 12-year-old would understand (use a everyday \
analogy where it genuinely helps).
  "Why it matters:" 1-2 sentences connecting it to what the reader can observe.
  "Remember:" one short takeaway line.
- If the selection contains jargon, decode each term inside the explanation.
- Do NOT add new market analysis or advice. Do NOT predict anything — never \
say a price is "due for" a move, a bounce, or a reversal; describe only what the \
numbers currently show.
- If the selection asks whether to buy/sell, explain that MarketPulse doesn't advise and
  what information *would* help them think about it.
- Max 130 words. End with: "Educational information — not investment advice."
"""

GENERAL_PROMPT = """You are the Pulse Assistant of MarketPulse — answer general beginner questions \
about stock markets, finance terms, and how markets work.

Structure: define the concept in one plain sentence first, then one concrete everyday \
analogy or example, then one "Remember:" takeaway line. Simple words, max 110 words, \
no advice, no predictions, no specific stock recommendations, no invented numbers or \
statistics. If a question needs current market data, say what kind of data would answer \
it rather than inventing numbers. End with: \
"Educational information — not investment advice."
"""


def _faq_match(question: str) -> str | None:
    import re

    stop = {"what", "is", "a", "an", "the", "of", "in", "for", "on", "and", "do",
            "does", "how", "to", "i", "my", "me", "can", "should", "when", "it", "this"}
    norm = question.lower().replace("p/e", "pe")
    q_words = set(re.findall(r"[a-z0-9]+", norm)) - stop
    best, best_score = None, 0
    for item in FAQ:
        kws = set(re.findall(r"[a-z0-9]+", item["q"])) - stop
        score = len(q_words & kws)
        if score > best_score:
            best, best_score = item, score
    return best["a"] if best and best_score >= 2 else None


async def explain_snippet(gemini, selected_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Explain a user-selected snippet of analysis text in simple terms."""
    if gemini is None or not getattr(gemini, "available", False):
        return {
            "answer": ("Pulse Assistant needs the Gemini API key on the backend to explain "
                       "selected text. Tip: the in-app Dictionary explains most jargon offline."),
            "generated_by": "unavailable",
        }
    ctx = context or {}
    prompt = (
        f"{EXPLAIN_PROMPT}\n\n"
        f"PAGE CONTEXT (for reference only, do not analyze): {json_dumps(ctx)}\n"
        f"SELECTED TEXT: \"\"\"{selected_text[:1200]}\"\"\"\n\n"
        "Explain the selection now."
    )
    try:
        text = await gemini.generate(prompt, ttl=120, temperature=0.3, max_tokens=400)
        return {"answer": text, "generated_by": "pulse-assistant"}
    except Exception:
        return {
            "answer": ("The Assistant is temporarily unavailable (free-tier quota). "
                       "Try again in a minute — or use the Dictionary for term lookups. "
                       "Educational information — not investment advice."),
            "generated_by": "fallback",
        }


async def general_qa(gemini, question: str) -> dict[str, Any]:
    """Light general Q&A. FAQ knowledge base covers key/quota outages."""
    faq = _faq_match(question)
    if gemini is None or not getattr(gemini, "available", False):
        if faq:
            return {"answer": faq, "generated_by": "faq-knowledge-base"}
        return {
            "answer": ("The Assistant needs the Gemini API key (or quota) for custom questions. "
                       "Meanwhile: the Dictionary explains ~50 common terms, and the Overview "
                       "page shows the full math behind every verdict. "
                       "Educational information — not investment advice."),
            "generated_by": "unavailable",
        }
    try:
        text = await gemini.generate(
            f"{GENERAL_PROMPT}\n\nQUESTION: {question}", ttl=180, temperature=0.35, max_tokens=350
        )
        return {"answer": text, "generated_by": "pulse-assistant"}
    except Exception:
        if faq:
            return {"answer": faq, "generated_by": "faq-knowledge-base"}
        return {
            "answer": ("The Assistant hit its free-tier quota. Please try again in a minute. "
                       "Educational information — not investment advice."),
            "generated_by": "fallback",
        }


def json_dumps(x: Any) -> str:
    import json
    return json.dumps(x, default=str)[:800]
