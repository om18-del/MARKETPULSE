"""Tests for news analyzer (keyword path) and assistant FAQ."""

from app.news.analyzer import analyze, keyword_analyze, parse_gemini_json
from app.ai.assistant import _faq_match


def test_keyword_positive():
    arts = [{"title": "Markets rally as Fed signals growth optimism", "publisher": "X"}]
    out = keyword_analyze(arts)
    assert out["aggregate_score"] > 0
    assert out["method"] == "keyword"


def test_keyword_negative():
    arts = [{"title": "Stocks plunge as recession fears escalate", "publisher": "Y"}]
    out = keyword_analyze(arts)
    assert out["aggregate_score"] < 0


def test_parse_gemini_json_tolerates_fences():
    raw = '```json{"articles":[{"i":0,"sentiment":0.7,"reason":"rally word","key_phrase":"rally"}],"summary":"up"}```'
    parsed = parse_gemini_json(raw, [{"title": "Markets rally", "publisher": "Z"}])
    assert parsed is not None
    assert parsed["articles"][0]["sentiment"] == 0.7


async def test_analyze_falls_back_without_gemini():
    out = await analyze([{"title": "Oil sinks on demand worries", "publisher": "W"}], gemini=None)
    assert out["method"] == "keyword"


def test_faq_match():
    assert _faq_match("what is a P/E ratio exactly?") is not None
    assert _faq_match("completely unrelated gibberish xyz") is None
