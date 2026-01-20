"""Binance exchange adapter for candlestick data."""

import logging
from decimal import Decimal
from typing import Any

from service.candlestick.exceptions import DataParsingError
from service.candlestick.exchanges.base import BaseExchange
from service.candlestick.models import CandleInterval, Candlestick

logger = logging.getLogger(__name__)


class BinanceExchange(BaseExchange):
    """
    Binance exchange adapter.

    API Documentation: https://binance-docs.github.io/apidocs/spot/en/
    """

    EXCHANGE_NAME = "binance"
    BASE_URL = "https://api.binance.com"

    # Binance uses standard interval notation
    INTERVAL_MAP = {
        CandleInterval.MINUTE_1: "1m",
        CandleInterval.MINUTE_3: "3m",
        CandleInterval.MINUTE_5: "5m",
        CandleInterval.MINUTE_15: "15m",
        CandleInterval.MINUTE_30: "30m",
        CandleInterval.HOUR_1: "1h",
        CandleInterval.HOUR_2: "2h",
        CandleInterval.HOUR_4: "4h",
        CandleInterval.HOUR_6: "6h",
        CandleInterval.HOUR_8: "8h",
        CandleInterval.HOUR_12: "12h",
        CandleInterval.DAY_1: "1d",
        CandleInterval.DAY_3: "3d",
        CandleInterval.WEEK_1: "1w",
        CandleInterval.MONTH_1: "1M",
    }

    def convert_symbol(self, symbol: str) -> str:
        """Convert BTC/USDT to BTCUSDT."""
        return symbol.replace("/", "").upper()

    async def fetch_candlesticks(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Candlestick]:
        """Fetch candlestick data from Binance."""
        params: dict[str, Any] = {
            "symbol": self.convert_symbol(symbol),
            "interval": self.get_interval_string(interval),
            "limit": min(limit, 1000),  # Binance max is 1000
        }

        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        logger.debug(f"[Binance] Fetching candlesticks for {symbol} with params: {params}")

        data = await self._make_request("GET", "/api/v3/klines", params=params)
        return self._parse_candlesticks(data)

    def _parse_candlesticks(self, data: Any) -> list[Candlestick]:
        """
        Parse Binance klines response.

        Binance returns data as array of arrays:
        [
            [
                1499040000000,      // 0: Open time
                "0.01634000",       // 1: Open
                "0.80000000",       // 2: High
                "0.01575800",       // 3: Low
                "0.01577100",       // 4: Close
                "148976.11427815",  // 5: Volume
                1499644799999,      // 6: Close time
                "2434.19055334",    // 7: Quote asset volume
                308,                // 8: Number of trades
                "1756.87402397",    // 9: Taker buy base asset volume
                "28.46694368",      // 10: Taker buy quote asset volume
                "0"                 // 11: Ignore
            ]
        ]
        """
        if not isinstance(data, list):
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Expected list of klines",
            )

        candlesticks = []
        for item in data:
            try:
                if not isinstance(item, list) or len(item) < 9:
                    logger.warning(f"[Binance] Skipping invalid kline item: {item}")
                    continue

                candlestick = Candlestick(
                    timestamp=int(item[0]),
                    open_price=Decimal(str(item[1])),
                    high_price=Decimal(str(item[2])),
                    low_price=Decimal(str(item[3])),
                    close_price=Decimal(str(item[4])),
                    volume=Decimal(str(item[5])),
                    quote_volume=Decimal(str(item[7])) if item[7] else None,
                    trades_count=int(item[8]) if item[8] else None,
                )
                candlesticks.append(candlestick)
            except Exception as e:
                logger.warning(f"[Binance] Failed to parse kline item: {e}")
                continue

        return sorted(candlesticks)
