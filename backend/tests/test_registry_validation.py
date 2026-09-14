"""Tests for registry search + data validation."""

from app.data.registry import ALL, get, search, symbol_for
from app.data.validation import derive_quote, sanitize_ohlcv, staleness_days


def test_registry_size():
    # 20 market instruments + 10 searchable stocks
    assert len(ALL) >= 30


def test_fx_pairs_present():
    assert get("usdinr") is not None and get("usdinr").fx_pair
    assert get("eurusd") is not None


def test_search_by_name_and_keyword():
    hits = search("nifty")
    assert any(h.id == "nifty50" for h in hits)
    hits = search("apple")
    assert any(h.id == "aapl" for h in hits)
    hits = search("zzzznotexist")
    assert hits == []


def test_symbol_mappings():
    sp = get("sp500")
    assert symbol_for(sp, "stooq")
    assert symbol_for(sp, "stooq").startswith("^")


def test_sanitize_drops_corrupt_rows():
    raw = [
        {"date": "2025-01-02", "open": "10", "high": "11", "low": "9", "close": "10.5", "volume": "100"},
        {"date": "2025-01-03", "open": "10", "high": "5", "low": "12", "close": "11", "volume": "100"},  # high<low
        {"date": "2025-01-03", "open": "10", "high": "12", "low": "9", "close": "10.8", "volume": "100"},  # dup date
        {"date": "2025-01-04", "open": "11", "high": "13", "low": "10", "close": "-3", "volume": "100"},  # bad close
        {"date": "2025-01-06", "open": "11", "high": "12", "low": "10.5", "close": "11.2", "volume": "100"},
    ]
    rows = sanitize_ohlcv(raw)
    assert [r["date"] for r in rows] == ["2025-01-02", "2025-01-03", "2025-01-06"]


def test_sanitize_close_only_ok():
    rows = sanitize_ohlcv([{"date": "2025-01-02", "close": "86.2"}, {"date": "2025-01-03", "close": "86.5"}])
    assert len(rows) == 2 and rows[-1]["close"] == 86.5


def test_staleness():
    from datetime import date, timedelta
    today = date.today().isoformat()
    assert staleness_days(today) == 0
    assert staleness_days((date.today() - timedelta(days=9)).isoformat()) == 9
    assert staleness_days(None) is None


def test_derive_quote():
    rows = sanitize_ohlcv([
        {"date": "2025-01-02", "close": "100"},
        {"date": "2025-01-03", "close": "102"},
    ])
    q = derive_quote(rows, "stooq")
    assert q["available"] and q["last_price"] == 102
    assert q["change_pct"] == 2.0
    assert q["provider"] == "stooq"
