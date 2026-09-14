"""Market-data providers. Each provider exposes:

    fetch_history(symbol) -> list[raw row dicts]
    name: str

Providers raise ProviderError on failure; the aggregator decides fallbacks.
"""

from .base import ProviderError
from .stooq import StooqProvider
from .twelvedata import TwelveDataProvider
from .finnhub import FinnhubProvider
from .alphavantage import AlphaVantageProvider
from .frankfurter import FrankfurterProvider

__all__ = [
    "ProviderError",
    "StooqProvider",
    "TwelveDataProvider",
    "FinnhubProvider",
    "AlphaVantageProvider",
    "FrankfurterProvider",
]
