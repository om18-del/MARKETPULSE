"""Instrument registry: every asset MarketPulse tracks, mapped to each
provider's symbol scheme.

Design notes
------------
* Stooq (keyless) is the primary provider; its symbols are lowercase,
  with ``^`` prefixes for indices (and occasional renames, e.g. ``^spx``).
* Twelve Data / Finnhub / Alpha Vantage are fallbacks; several instruments
  have no mapping there (``None``) and are simply skipped for that provider.
* ``weight`` is the instrument's influence on the global regime blend
  (US + India weighted higher per the product brief).
* FX pairs are first-class assets: they appear in search, detail pages and
  feed the cross-asset pressure matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Instrument:
    """A tradable/trackable instrument with per-provider symbol mappings."""

    id: str                 # stable internal id, e.g. "sp500", "usdinr"
    name: str               # display name, e.g. "S&P 500"
    category: str           # "index" | "volatility" | "commodity" | "rate" | "fx"
    region: str             # "us" | "india" | "europe" | "apac" | "macro" | "fx"
    currency: str           # quote currency for display
    stooq: Optional[str]    # stooq symbol (lowercase)
    twelvedata: Optional[str]
    finnhub: Optional[str]
    alphavantage: Optional[str]
    frankfurter: Optional[str] = None  # ECB keyless FX provider (pairs like "USD:INR")
    nse: Optional[str] = None            # NSE equity symbol (e.g. "RELIANCE")
    nse_index: Optional[str] = None      # NSE index name (e.g. "NIFTY 50")
    weight: float = 1.0     # influence on global regime blend
    fx_pair: bool = False
    keywords: tuple[str, ...] = field(default_factory=tuple)  # search hints

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "region": self.region,
            "currency": self.currency,
            "weight": self.weight,
            "fx_pair": self.fx_pair,
        }


REGISTRY: dict[str, Instrument] = {i.id: i for i in [
    # ---------------------------- US indices ----------------------------
    Instrument("sp500", "S&P 500", "index", "us", "USD",
               stooq="^usl20", twelvedata="SPX", finnhub=None, alphavantage="SPX",
               weight=1.5, keywords=("spx", "s&p", "standard and poors", "us market")),
    Instrument("nasdaq", "Nasdaq 100", "index", "us", "USD",
               stooq="^ndx", twelvedata="NDX", finnhub=None, alphavantage="NDX",
               weight=1.4, keywords=("nasdaq", "ndx", "tech stocks")),
    Instrument("dowjones", "Dow Jones Industrial", "index", "us", "USD",
               stooq="^dji", twelvedata="DJI", finnhub=None, alphavantage="DJI",
               weight=1.3, keywords=("dow", "dji", "industrial average")),
    Instrument("russell2000", "Russell 2000", "index", "us", "USD",
               stooq="^rut", twelvedata=None, finnhub=None, alphavantage="RUT",
               weight=1.0, keywords=("russell", "small cap")),
    Instrument("vix", "VIX (Volatility Index)", "volatility", "us", "USD",
               stooq="^vix", twelvedata="VIX", finnhub=None, alphavantage="VIXY",
               weight=1.2, keywords=("volatility", "fear index", "vix")),
    # --------------------------- India indices --------------------------
    # All Indian data is fetched DIRECTLY from nseindia.com (keyless) —
    # see providers/nse.py. Stooq kept only as a fallback for these.
    Instrument("nifty50", "NIFTY 50", "index", "india", "INR",
               stooq="^nsei", twelvedata=None, finnhub=None, alphavantage=None,
               nse_index="NIFTY 50",
               weight=1.5, keywords=("nifty", "nse", "india market")),
    Instrument("sensex", "BSE SENSEX", "index", "india", "INR",
               stooq="^snx", twelvedata=None, finnhub=None, alphavantage=None,
               weight=1.4, keywords=("sensex", "bse", "mumbai")),
    Instrument("niftybank", "NIFTY Bank", "index", "india", "INR",
               stooq="^banknifty", twelvedata=None, finnhub=None, alphavantage=None,
               nse_index="NIFTY BANK",
               weight=1.2, keywords=("banknifty", "banking stocks", "banks")),
    Instrument("niftyit", "NIFTY IT", "index", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse_index="NIFTY IT",
               weight=1.1, keywords=("nifty it", "it stocks", "tech india", "software")),
    Instrument("niftynext50", "NIFTY Next 50", "index", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse_index="NIFTY NEXT 50",
               weight=1.0, keywords=("next 50", "junior nifty")),
    Instrument("niftymidcap150", "NIFTY Midcap 150", "index", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse_index="NIFTY MIDCAP 150",
               weight=1.0, keywords=("midcap", "mid cap")),
    Instrument("niftysmallcap250", "NIFTY Smallcap 250", "index", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse_index="NIFTY SMALLCAP 250",
               weight=0.9, keywords=("smallcap", "small cap")),
    Instrument("niftyfin", "NIFTY Financial Services", "index", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse_index="NIFTY FIN SERVICE",
               weight=1.1, keywords=("financial services", "finnifty")),
    # --------------------------- Europe indices -------------------------
    Instrument("ftse100", "FTSE 100", "index", "europe", "GBp",
               stooq="^ukx", twelvedata=None, finnhub=None, alphavantage=None,
               weight=1.0, keywords=("ftse", "london", "uk market")),
    Instrument("dax", "DAX (Germany)", "index", "europe", "EUR",
               stooq="^dax", twelvedata=None, finnhub=None, alphavantage=None,
               weight=1.0, keywords=("dax", "germany", "frankfurt")),
    Instrument("cac40", "CAC 40 (France)", "index", "europe", "EUR",
               stooq="^cac", twelvedata=None, finnhub=None, alphavantage=None,
               weight=0.9, keywords=("cac", "france", "paris")),
    Instrument("eurostoxx50", "Euro Stoxx 50", "index", "europe", "EUR",
               stooq="^stx50e", twelvedata=None, finnhub=None, alphavantage=None,
               weight=0.9, keywords=("stoxx", "eurozone", "europe")),
    # --------------------------- APAC indices ---------------------------
    Instrument("nikkei225", "Nikkei 225 (Japan)", "index", "apac", "JPY",
               stooq="^nkx", twelvedata=None, finnhub=None, alphavantage=None,
               weight=1.0, keywords=("nikkei", "japan", "tokyo")),
    Instrument("hangseng", "Hang Seng (Hong Kong)", "index", "apac", "HKD",
               stooq="^hsi", twelvedata=None, finnhub=None, alphavantage=None,
               weight=0.9, keywords=("hang seng", "hong kong", "hsi")),
    Instrument("kospi", "KOSPI (South Korea)", "index", "apac", "KRW",
               stooq="^kospi", twelvedata=None, finnhub=None, alphavantage=None,
               weight=0.7, keywords=("kospi", "korea", "seoul")),
    Instrument("asx200", "S&P/ASX 200 (Australia)", "index", "apac", "AUD",
               stooq="^axjo", twelvedata=None, finnhub=None, alphavantage=None,
               weight=0.7, keywords=("asx", "australia", "sydney")),
    # ------------------------- Macro / commodities ----------------------
    Instrument("gold", "Gold (Spot)", "commodity", "macro", "USD",
               stooq="xauusd", twelvedata="XAU/USD", finnhub="OANDA:XAU_USD",
               alphavantage=None, weight=1.0,
               keywords=("gold", "bullion", "xau")),
    Instrument("crude", "Crude Oil WTI", "commodity", "macro", "USD",
               stooq="cl.f", twelvedata="WTI/USD", finnhub=None, alphavantage=None,
               weight=1.0, keywords=("oil", "crude", "wti", "petroleum")),
    Instrument("dxy", "US Dollar Index", "fx", "macro", "USD",
               stooq="^dxy", twelvedata=None, finnhub=None, alphavantage="DX-Y.NYB",
               weight=1.2, keywords=("dollar index", "dxy", "usd strength")),
    Instrument("us10y", "US 10-Year Treasury Yield", "rate", "macro", "%",
               stooq="10yusy.b", twelvedata=None, finnhub=None, alphavantage=None,
               weight=1.2, keywords=("treasury", "bond yield", "10 year", "interest rates")),
    # ------------------------------ FX pairs ----------------------------
    Instrument("usdinr", "USD/INR", "fx", "fx", "INR",
               stooq="usdinr", twelvedata="USD/INR", finnhub=None, alphavantage=None,
               frankfurter="USD:INR",
               weight=1.2, fx_pair=True, keywords=("rupee", "dollar rupee", "inr")),
    Instrument("eurusd", "EUR/USD", "fx", "fx", "USD",
               stooq="eurusd", twelvedata="EUR/USD", finnhub="OANDA:EUR_USD",
               alphavantage=None, frankfurter="EUR:USD",
               weight=1.0, fx_pair=True, keywords=("euro", "eur")),
    Instrument("gbpusd", "GBP/USD", "fx", "fx", "USD",
               stooq="gbpusd", twelvedata="GBP/USD", finnhub="OANDA:GBP_USD",
               alphavantage=None, frankfurter="GBP:USD",
               weight=0.8, fx_pair=True, keywords=("pound", "gbp", "sterling")),
    Instrument("usdjpy", "USD/JPY", "fx", "fx", "JPY",
               stooq="usdjpy", twelvedata="USD/JPY", finnhub="OANDA:USD_JPY",
               alphavantage=None, frankfurter="USD:JPY",
               weight=0.9, fx_pair=True, keywords=("yen", "jpy")),
    Instrument("usdcny", "USD/CNY", "fx", "fx", "CNY",
               stooq="usdcny", twelvedata="USD/CNY", finnhub=None, alphavantage=None,
               frankfurter="USD:CNY",
               weight=0.7, fx_pair=True, keywords=("yuan", "renminbi", "china currency")),
    Instrument("audusd", "AUD/USD", "fx", "fx", "USD",
               stooq="audusd", twelvedata="AUD/USD", finnhub="OANDA:AUD_USD",
               alphavantage=None, frankfurter="AUD:USD",
               weight=0.7, fx_pair=True, keywords=("aussie", "aud")),
    Instrument("usdcad", "USD/CAD", "fx", "fx", "CAD",
               stooq="usdcad", twelvedata="USD/CAD", finnhub="OANDA:USD_CAD",
               alphavantage=None, frankfurter="USD:CAD",
               weight=0.7, fx_pair=True, keywords=("loonie", "cad")),
    Instrument("usdchf", "USD/CHF", "fx", "fx", "CHF",
               stooq="usdchf", twelvedata="USD/CHF", finnhub="OANDA:USD_CHF",
               alphavantage=None, frankfurter="USD:CHF",
               weight=0.6, fx_pair=True, keywords=("franc", "chf", "swiss")),
]}

# Indian stocks (NSE symbols, data direct from nseindia.com) — flagship names
# beyond the dynamic universe so the most-searched tickers are always present.
EXTRA_STOCKS: dict[str, Instrument] = {i.id: i for i in [
    Instrument("reliance", "Reliance Industries", "stock", "india", "INR",
               stooq="reliance.in", twelvedata=None, finnhub=None, alphavantage=None,
               nse="RELIANCE", keywords=("reliance", "ril", "mukesh ambani")),
    Instrument("tcs", "Tata Consultancy Services", "stock", "india", "INR",
               stooq="tcs.in", twelvedata=None, finnhub=None, alphavantage=None,
               nse="TCS", keywords=("tcs", "tata consultancy")),
    Instrument("hdfcbank", "HDFC Bank", "stock", "india", "INR",
               stooq="hdfcbank.in", twelvedata=None, finnhub=None, alphavantage=None,
               nse="HDFCBANK", keywords=("hdfc",)),
    Instrument("infy", "Infosys", "stock", "india", "INR",
               stooq="infy.in", twelvedata=None, finnhub=None, alphavantage=None,
               nse="INFY", keywords=("infosys",)),
    Instrument("icicibank", "ICICI Bank", "stock", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse="ICICIBANK", keywords=("icici",)),
    Instrument("sbin", "State Bank of India", "stock", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse="SBIN", keywords=("sbi", "state bank")),
    Instrument("bhartiartl", "Bharti Airtel", "stock", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse="BHARTIARTL", keywords=("airtel",)),
    Instrument("lt", "Larsen & Toubro", "stock", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse="LT", keywords=("l&t", "larsen", "toubro")),
    Instrument("itc", "ITC Ltd", "stock", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse="ITC", keywords=("itc", "gold flake")),
    Instrument("axisbank", "Axis Bank", "stock", "india", "INR",
               stooq=None, twelvedata=None, finnhub=None, alphavantage=None,
               nse="AXISBANK", keywords=("axis",)),
    Instrument("aapl", "Apple Inc.", "stock", "us", "USD",
               stooq="aapl.us", twelvedata="AAPL", finnhub="AAPL", alphavantage="AAPL",
               keywords=("apple", "iphone")),
    Instrument("msft", "Microsoft Corp.", "stock", "us", "USD",
               stooq="msft.us", twelvedata="MSFT", finnhub="MSFT", alphavantage="MSFT",
               keywords=("microsoft", "windows")),
    Instrument("googl", "Alphabet (Google)", "stock", "us", "USD",
               stooq="googl.us", twelvedata="GOOGL", finnhub="GOOGL", alphavantage="GOOGL",
               keywords=("google", "alphabet")),
    Instrument("tsla", "Tesla Inc.", "stock", "us", "USD",
               stooq="tsla.us", twelvedata="TSLA", finnhub="TSLA", alphavantage="TSLA",
               keywords=("tesla", "elon musk", "ev")),
    Instrument("amzn", "Amazon.com Inc.", "stock", "us", "USD",
               stooq="amzn.us", twelvedata="AMZN", finnhub="AMZN", alphavantage="AMZN",
               keywords=("amazon",)),
    Instrument("nvda", "NVIDIA Corp.", "stock", "us", "USD",
               stooq="nvda.us", twelvedata="NVDA", finnhub="NVDA", alphavantage="NVDA",
               keywords=("nvidia", "gpu", "ai chips")),
]}

ALL: dict[str, Instrument] = {**REGISTRY, **EXTRA_STOCKS}

PROVIDERS = ("nse", "stooq", "twelvedata", "finnhub", "alphavantage")


def get(instrument_id: str) -> Instrument | None:
    return ALL.get(instrument_id.lower().strip())


def symbol_for(instrument: Instrument, provider: str) -> str | None:
    """Provider symbol for an instrument, or None if unsupported there."""
    return getattr(instrument, provider, None)


def search(query: str, limit: int = 8, extra: dict[str, Instrument] | None = None) -> list[Instrument]:
    """Registry search across ids, names and keywords (prefix/substring).

    `extra` merges a dynamic instrument set (e.g. the live NSE universe)
    into the search space without touching the static registry.
    """
    q = query.lower().strip()
    if not q:
        return []
    space = {**ALL, **(extra or {})}
    scored: list[tuple[int, Instrument]] = []
    for inst in space.values():
        hay_ids = [inst.id]
        hay_names = [inst.name.lower()]
        hay_kw = [k.lower() for k in inst.keywords]
        score = 999
        if q == inst.id or q == inst.name.lower():
            score = 0
        elif any(h.startswith(q) for h in hay_ids + hay_names):
            score = 1
        elif any(q in h for h in hay_ids + hay_names):
            score = 2
        elif any(h.startswith(q) or q in h for h in hay_kw):
            score = 3
        if score < 999:
            scored.append((score, inst))
    scored.sort(key=lambda t: (t[0], -t[1].weight, t[1].id))
    return [i for _, i in scored[:limit]]


def by_region() -> dict[str, list[Instrument]]:
    groups: dict[str, list[Instrument]] = {}
    for inst in REGISTRY.values():
        groups.setdefault(inst.region, []).append(inst)
    return groups
