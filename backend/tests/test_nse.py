"""India data pipeline tests: NSE archive file parsing, history assembly,
movers, dynamic nse-* instruments, and India-first product defaults."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.india_store import (
    IndiaStore,
    _parse_bhavcopy,
    _parse_dhan,
    _parse_indices,
    _parse_nifty50,
)
from app.data.registry import ALL, get, search
from app.demo.snapshots import demo_history


# --------------------------------------------------------------- parsing ---
BHAV = """SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, D
RELIANCE, EQ, 11-09-2026, 2930.10, 2940.00, 2965.80, 2935.00, 2950.50, 2950.50, 2948.20, 5100000, 150321.44, 512000, .
TCS, EQ, 11-09-2026, 4120.00, 4105.00, 4130.00, 4090.10, 4100.00, 4100.00, 4110.00, 1200000, 49320.00, 198000, .
BADROW, EQ, 11-09-2026, 100.00, 0, 0, 0, 0, 0, 0, 0, 0, 0, .
PREF, PR, 11-09-2026, 50.00, 51.00, 52.00, 50.00, 51.50, 51.50, 51.00, 10000, 51.5, 100, .
"""


def test_parse_bhavcopy():
    table = _parse_bhavcopy(BHAV)
    assert set(table) == {"RELIANCE", "TCS"}  # zero-close + non-EQ excluded
    r = table["RELIANCE"]
    assert r["close"] == 2950.5 and r["prev_close"] == 2930.10
    assert r["date"] == "2026-09-11"
    assert r["change_pct"] == round((2950.5 / 2930.10 - 1) * 100, 4)
    assert r["volume"] == 5100000


IDX = """Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield
NIFTY 50,11-Sep-2026,24050.10,24210.55,24010.20,24180.35,120.25,0.50,312345678,10234.5,23.1,3.9,1.2
NIFTY BANK,11-Sep-2026,51900.00,52200.00,51800.00,52100.10,-40.00,-0.08,102345678,5012.2,20.1,2.8,1.1
NIFTY NEXT 50,11-Sep-2026,67900.00,68100.00,67800.00,68000.00,100.00,0.15,5023456,2012.2,25.0,4.1,1.0
"""


def test_parse_indices():
    table = _parse_indices(IDX)
    assert "NIFTY 50" in table and "NIFTY BANK" in table
    n = table["NIFTY 50"]
    assert n["close"] == 24180.35 and n["change_pct"] == 0.50
    assert n["date"] == "2026-09-11" and n["pe"] == 23.1


N50 = """Company Name,Industry,Symbol,Series,ISIN Code
Adani Enterprises Ltd.,Metals & Mining,ADANIENT,EQ,INE423A01024
Reliance Industries Limited,Energy,RELIANCE,EQ,INE002A01018
Some Preference,Finance,PREFXX,PR,INE123X01019
"""


def test_parse_nifty50():
    syms = _parse_nifty50(N50)
    assert syms == {"ADANIENT", "RELIANCE"}


DHAN = """SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,SEM_EXPIRY_CODE,SEM_TRADING_SYMBOL,SEM_LOT_UNITS,SEM_CUSTOM_SYMBOL,SEM_EXPIRY_DATE,SEM_STRIKE_PRICE,SEM_OPTION_TYPE,SEM_TICK_SIZE,SEM_EXPIRY_FLAG,SEM_EXCH_INSTRUMENT_TYPE,SEM_SERIES,SM_SYMBOL_NAME
NSE,C,281,EQUITY,0,RELIANCE,1,Reliance Industries,,,,0.05,M,,EQ,RELIANCE INDUSTRIES LIMITED
NSE,C,999,EQUITY,0,PREFXX,1,Pref Corp,,,,0.05,M,,PR,PREFERENCE CORP
BSE,C,500325,EQUITY,0,RELIANCE,1,Reliance Industries,,,,0.05,M,,A,RELIANCE INDUSTRIES LIMITED
"""


def test_parse_dhan():
    names = _parse_dhan(DHAN)
    assert names["nse"].get("RELIANCE") == "Reliance Industries"
    assert "PREFXX" not in names["nse"]
    assert names["bse"].get("RELIANCE") == "Reliance Industries"


# ------------------------------------------------------- history assembly --
def test_stock_history_from_files():
    """Two bhavcopy days -> chronological bars with honest dates."""
    import csv
    import io

    d1, d2 = date(2026, 9, 10), date(2026, 9, 11)
    store = IndiaStore()

    def bhav_row(d: date, close: float, prev: float) -> str:
        return (f"RELIANCE, EQ, {d:%d-%m-%Y}, {prev}, {close - 5}, {close + 5}, "
                f"{close - 8}, {close}, {close}, 100.0, 500000, 15000.0, 50000, .")

    t1 = "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, D\n" + bhav_row(d1, 2940.0, 2930.0)
    t2 = "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, D\n" + bhav_row(d2, 2950.5, 2940.0)

    store._bhavcopy[d1] = _parse_bhavcopy(t1)
    store._bhavcopy[d2] = _parse_bhavcopy(t2)
    store.bhavcopy_dates = _fake_dates_wrapper(store)  # type: ignore[method-assign]

    rows = asyncio.run(store.stock_history("RELIANCE", min_bars=2))
    assert [r["date"] for r in rows] == [d1.isoformat(), d2.isoformat()]
    assert rows[-1]["close"] == 2950.5


def _fake_dates_wrapper(store: IndiaStore):
    d1, d2 = date(2026, 9, 10), date(2026, 9, 11)

    async def wrapper(want=75):
        return [d2, d1][:want]
    return wrapper


def test_index_history_from_files():
    store = IndiaStore()
    d1, d2 = date(2026, 9, 10), date(2026, 9, 11)

    def idx_row(d: date, close: float) -> str:
        return (f"NIFTY 50,{d:%d-%b-%Y},{close - 50},{close + 50},{close - 70},"
                f"{close},10.0,0.04,1000,50,23.0,3.8,1.2")

    head = ("Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,"
            "Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n")
    store._indices[d1] = _parse_indices(head + idx_row(d1, 24130.10))
    store._indices[d2] = _parse_indices(head + idx_row(d2, 24180.35))
    # All dates with files are already cached, so probing works offline:
    store.recent_weekdays = staticmethod(lambda n=95, up_to=None: [d2, d1])  # type: ignore[assignment]
    rows = asyncio.run(store.index_history("NIFTY 50", min_bars=2))
    assert [r["date"] for r in rows] == [d1.isoformat(), d2.isoformat()]
    assert rows[-1]["close"] == 24180.35


def test_movers_from_bhavcopy():
    store = IndiaStore()
    d = date(2026, 9, 11)
    rows = ["SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, D"]
    stocks = {"AAA": (100, 110), "BBB": (100, 105), "CCC": (100, 95), "DDD": (100, 90),
              "EEE": (100, 104), "FFF": (100, 96), "GGG": (100, 103), "HHH": (100, 97),
              "III": (100, 102), "JJJ": (100, 98), "RELIANCE": (2930.10, 2950.50),
              "TCS": (4120.00, 4100.00)}
    for sym, (pc, c) in stocks.items():
        rows.append(f"{sym}, EQ, {d:%d-%m-%Y}, {pc}, {c}, {c + 1}, {c - 1}, {c}, {c}, {c}, 100000, 1000, 5000, .")
    table = _parse_bhavcopy("\n".join(rows))
    store._bhavcopy[d] = table
    store.bhavcopy_dates = _fake_dates_wrapper(store)  # type: ignore[method-assign]
    store._nifty50 = {"AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ",
                      "RELIANCE", "TCS"}
    m = asyncio.run(store.movers())
    assert m["date"] == d.isoformat()
    assert m["gainers"][0]["symbol"] == "AAA"
    assert m["losers"][0]["symbol"] == "DDD"
    # 5 up + RELIANCE = 6 advances; 5 down + TCS = 6 declines
    assert m["advances"] == 6 and m["declines"] == 6


# -------------------------------------------------- dynamic instruments ----
def test_dynamic_instrument_nse_prefix():
    from app.data.aggregator import Aggregator

    async def main():
        agg = Aggregator()
        agg.india._names = {"nse": {"TATAMOTORS": "Tata Motors Limited"}, "bse": {}}
        return await agg.dynamic_instrument("nse-tatamotors")

    inst = asyncio.run(main())
    assert inst is not None
    assert inst.currency == "INR" and inst.region == "india"
    assert inst.nse == "TATAMOTORS"
    assert inst.name == "Tata Motors Limited"


def test_registry_india_shape():
    n50 = get("nifty50")
    assert n50 is not None and n50.nse_index == "NIFTY 50" and n50.currency == "INR"
    for new_id in ("niftyit", "niftynext50", "niftymidcap150", "niftysmallcap250", "niftyfin"):
        assert get(new_id) is not None, f"missing index {new_id}"
    assert ALL["reliance"].nse == "RELIANCE"
    # SENSEX has no NSE-side mapping (honest): global chain only.
    assert get("sensex").nse_index is None


def test_search_covers_dynamic_universe():
    from app.data.registry import Instrument
    extra = {"nse-tatamotors": Instrument(
        id="nse-tatamotors", name="Tata Motors Limited", category="stock",
        region="india", currency="INR", stooq=None, twelvedata=None,
        finnhub=None, alphavantage=None, nse="TATAMOTORS",
        weight=0.6, keywords=("tatamotors",))}
    hits = search("tata", limit=5, extra=extra)
    ids = [h.id for h in hits]
    assert "nse-tatamotors" in ids and "tcs" in ids


def test_demo_history_no_future_dates():
    rows = demo_history("nse-unknowncompany")["rows"]
    assert len(rows) > 100
    assert all(r["date"] <= date.today().isoformat() for r in rows[-5:])


# ---------------------------------------------------------- INR default ---
def test_fx_route_default_base_is_inr():
    import inspect
    from app.routes.api import fx
    d = inspect.signature(fx).parameters["base"].default
    assert getattr(d, "default", d) == "INR"


def test_news_route_default_topic_is_india():
    import inspect
    from app.routes.api import news
    d = inspect.signature(news).parameters["topic"].default
    assert getattr(d, "default", d) == "india"


# ------------------------------------------------- circuit-breaker probe --
def test_breaker_half_open_probe():
    import time as _time
    from app.core.cache import CircuitBreaker
    br = CircuitBreaker(threshold=2, cooldown=60.0)
    br.record_failure("a"); br.record_failure("b")
    assert br.is_open is True           # open
    br.opened_at -= 61.0                # cooldown elapsed -> half-open
    assert br.is_open is False          # one probe allowed
    br.record_failure("probe failed")
    assert br.is_open is True           # failed probe -> re-opened
    br.opened_at -= 61.0
    br.record_success()
    assert br.is_open is False and br.failures == 0
