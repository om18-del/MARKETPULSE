"""Regression tests for quote consistency and search-universe hygiene.

The detail page reported 0.00% while the overview card reported the real move,
because each surface measured the day's change against a different baseline.
These pin the baseline and the junk-symbol filter.
"""

import asyncio

from app.data.india_store import _is_placeholder_symbol, _parse_dhan


# --- the change% baseline --------------------------------------------------

def test_parse_dhan_drops_exchange_test_symbols():
    header = (
        "SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,"
        "SEM_EXPIRY_CODE,SEM_TRADING_SYMBOL,SEM_LOT_UNITS,SEM_CUSTOM_SYMBOL,"
        "SEM_EXPIRY_DATE,SEM_STRIKE_PRICE,SEM_OPTION_TYPE,SEM_TICK_SIZE,"
        "SEM_EXPIRY_FLAG,SEM_EXCH_INSTRUMENT_TYPE,SEM_SERIES,SM_SYMBOL_NAME"
    )
    rows = [
        "NSE,CM,1,EQUITY,,RELIANCE,1,Reliance Industries,,,,,,EQUITY,EQ,RELIANCE",
        "NSE,CM,2,EQUITY,,011NSETEST,1,,,,,,EQUITY,EQ,01INSTEST",
        "NSE,CM,3,EQUITY,,181NSETEST,1,,,,,,EQUITY,EQ,18INSTEST",
        "NSE,CM,4,EQUITY,,G1NSETEST,1,,,,,,EQUITY,EQ,G1INSTEST",
        "NSE,CM,5,EQUITY,,V1NSETEST,1,,,,,,EQUITY,EQ,V1INSTEST",
    ]
    parsed = _parse_dhan(header + "\n" + "\n".join(rows))
    assert "RELIANCE" in parsed["nse"], "real symbols must survive"
    for junk in ("011NSETEST", "181NSETEST", "G1NSETEST", "V1NSETEST"):
        assert junk not in parsed["nse"], f"{junk} must never be searchable"


def test_placeholder_symbol_filter_is_narrow():
    """Must not swallow legitimate tickers that merely contain 'TEST'-ish text."""
    for real in ("RELIANCE", "TCS", "INFY", "SBIN", "HDFCBANK", "TESTA", "PROTEST",
                 "LATEST", "CONTEST", "ZTEST", "MOTORTEST"):
        assert not _is_placeholder_symbol(real), real
    for junk in ("011NSETEST", "11NSETEST", "G1NSETEST", "TEST", "DUMMY", "SAMPLE"):
        assert _is_placeholder_symbol(junk), junk


# --- the API contract the frontend depends on -------------------------------

def test_asset_detail_quote_exposes_prev_close():
    """The detail page needs an explicit prev_close to agree with the card."""
    rows = [
        {"date": f"2026-01-{i:02d}", "open": v, "high": v * 1.01, "low": v * 0.99,
         "close": v, "volume": 1_000_000}
        for i, v in enumerate([100.0] * 29 + [110.0], start=1)
    ]

    async def fake_history(_id):
        return {"rows": rows,
                "provenance": {"provider": "test"}}, False

    import app.service as svc
    original = svc._history_with_demo
    svc._history_with_demo = fake_history
    try:
        out = asyncio.run(svc.asset_detail("nifty50"))
    finally:
        svc._history_with_demo = original

    q = out["quote"]
    assert q is not None
    assert q["price"] == 110.0
    assert q["prev_close"] == 100.0, "prev_close must be the prior session"
    assert q["change_pct"] == 10.0
    # the published change must be reproducible from the published prices
    assert round((q["price"] / q["prev_close"] - 1) * 100, 2) == q["change_pct"]