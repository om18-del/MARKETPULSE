"""FX engine: preferred-currency rate grid + converter math.

Rates are derived from the registry's FX pair histories (Stooq keyless
primary). A pair USD/INR at 86.2 means 1 USD = 86.2 INR; inversions are
computed exactly.
"""

from __future__ import annotations

from typing import Any

Row = dict

# currency -> the registry pair id that quotes it against USD
USD_PAIRS: dict[str, str] = {
    "INR": "usdinr", "EUR": "eurusd", "GBP": "gbpusd", "JPY": "usdjpy",
    "CNY": "usdcny", "AUD": "audusd", "CAD": "usdcad", "CHF": "usdchf",
}
CURRENCIES = ["USD"] + list(USD_PAIRS.keys())
FLAG: dict[str, str] = {
    "USD": "🇺🇸", "INR": "🇮🇳", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵",
    "CNY": "🇨🇳", "AUD": "🇦🇺", "CAD": "🇨🇦", "CHF": "🇨🇭",
}
PAIR_NAME: dict[str, str] = {
    "usdinr": "USD/INR", "eurusd": "EUR/USD", "gbpusd": "GBP/USD", "usdjpy": "USD/JPY",
    "usdcny": "USD/CNY", "audusd": "AUD/USD", "usdcad": "USD/CAD", "usdchf": "USD/CHF",
}


def usd_rates_from_pairs(pair_quotes: dict[str, dict[str, Any]]) -> dict[str, float | None]:
    """pair_quotes: {pair_id: {last_price, ...}} -> {currency: units per 1 USD}."""
    rates: dict[str, float | None] = {"USD": 1.0}
    for cur, pair_id in USD_PAIRS.items():
        q = pair_quotes.get(pair_id)
        price = (q or {}).get("last_price")
        if not price:
            rates[cur] = None
            continue
        if pair_id == "eurusd" or pair_id == "gbpusd" or pair_id == "audusd":
            rates[cur] = 1 / price  # pair quotes USD per 1 EUR/GBP/AUD
        else:
            rates[cur] = price      # pair quotes CUR per 1 USD
    return rates


def rate_grid(rates: dict[str, float | None]) -> list[dict[str, Any]]:
    """Full N×N grid with day-change columns prepared by the caller."""
    out = []
    for base in CURRENCIES:
        row = {"base": base, "flag": FLAG.get(base, ""), "rates": {}}
        rb = rates.get(base)
        for quote in CURRENCIES:
            rq = rates.get(quote)
            if rb in (None, 0) or rq in (None, 0):
                row["rates"][quote] = None
            else:
                row["rates"][quote] = round(rq / rb, 4)
        out.append(row)
    return out


def convert(amount: float, from_cur: str, to_cur: str, rates: dict[str, float | None]) -> float | None:
    rf, rt = rates.get(from_cur), rates.get(to_cur)
    if rf in (None, 0) or rt in (None, 0):
        return None
    return round(amount * rt / rf, 4)
