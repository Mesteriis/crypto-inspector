"""
Candlestick Data Fetching Service

An isolated package for loading candlestick (OHLCV) data from multiple
cryptocurrency exchanges using a concurrent race approach.

Usage:
    from services.candlestick import fetch_candlesticks, Candlestick, CandleInterval

    candles = await fetch_candlesticks(
        symbol="BTC/USDT",
        interval=CandleInterval.HOUR_1,
        limit=100,
        start_time=1704067200000,  # Optional: timestamp in milliseconds
        end_time=1704153600000,    # Optional: timestamp in milliseconds
    )
"""

from services.candlestick.fetcher import fetch_candlesticks
from services.candlestick.models import CandleInterval, Candlestick, FetchResult

__all__ = [
    "fetch_candlesticks",
    "Candlestick",
    "CandleInterval",
    "FetchResult",
]
