"""Bybit exchange adapter for candlestick data."""

import logging
from decimal import Decimal
from typing import Any

from services.candlestick.exceptions import DataParsingError
from services.candlestick.exchanges.base import BaseExchange
from services.candlestick.models import CandleInterval, Candlestick

logger = logging.getLogger(__name__)


class BybitExchange(BaseExchange):
    """
    Bybit exchange adapter.

    API Documentation: https://bybit-exchange.github.io/docs/v5/intro
    """

    EXCHANGE_NAME = "bybit"
    BASE_URL = "https://api.bybit.com"

    # Bybit V5 interval notation
    INTERVAL_MAP = {
        CandleInterval.MINUTE_1: "1",
        CandleInterval.MINUTE_3: "3",
        CandleInterval.MINUTE_5: "5",
        CandleInterval.MINUTE_15: "15",
        CandleInterval.MINUTE_30: "30",
        CandleInterval.HOUR_1: "60",
        CandleInterval.HOUR_2: "120",
        CandleInterval.HOUR_4: "240",
        CandleInterval.HOUR_6: "360",
        CandleInterval.HOUR_12: "720",
        CandleInterval.DAY_1: "D",
        CandleInterval.WEEK_1: "W",
        CandleInterval.MONTH_1: "M",
    }

    def convert_symbol(self, symbol: str) -> str:
        """Convert BTC/USDT to BTCUSDT (Bybit uses no separator)."""
        return symbol.replace("/", "").upper()

    async def fetch_candlesticks(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Candlestick]:
        """Fetch candlestick data from Bybit V5 API."""
        bybit_symbol = self.convert_symbol(symbol)
        bybit_interval = self.get_interval_string(interval)

        params: dict[str, Any] = {
            "category": "spot",  # Use spot market
            "symbol": bybit_symbol,
            "interval": bybit_interval,
            "limit": min(limit, 1000),  # Bybit max is 1000
        }

        # Bybit uses 'start' and 'end' in milliseconds
        if start_time is not None:
            params["start"] = start_time
        if end_time is not None:
            params["end"] = end_time

        logger.debug(f"[Bybit] Fetching candlesticks for {bybit_symbol}")

        data = await self._make_request("GET", "/v5/market/kline", params=params)
        return self._parse_candlesticks(data)

    def _parse_candlesticks(self, data: Any) -> list[Candlestick]:
        """
        Parse Bybit V5 kline response.

        Bybit V5 returns data as:
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "symbol": "BTCUSDT",
                "category": "spot",
                "list": [
                    [
                        "1670608800000",  // 0: Start time (ms timestamp)
                        "17071",          // 1: Open price
                        "17073",          // 2: High price
                        "17027",          // 3: Low price
                        "17055.5",        // 4: Close price
                        "268.611",        // 5: Volume
                        "4585929.11618"   // 6: Turnover (quote volume)
                    ],
                    ...
                ]
            }
        }
        Note: Bybit returns newest first.
        """
        if not isinstance(data, dict):
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Expected dict response",
            )

        # Check for API errors
        if data.get("retCode") != 0:
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason=f"API error: {data.get('retMsg', 'Unknown error')}",
            )

        result = data.get("result", {})
        candles_data = result.get("list", [])

        if not isinstance(candles_data, list):
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Expected list of candles in result.list",
            )

        candlesticks = []
        for item in candles_data:
            try:
                if not isinstance(item, list) or len(item) < 6:
                    logger.warning(f"[Bybit] Skipping invalid candle item: {item}")
                    continue

                candlestick = Candlestick(
                    timestamp=int(item[0]),
                    open_price=Decimal(str(item[1])),
                    high_price=Decimal(str(item[2])),
                    low_price=Decimal(str(item[3])),
                    close_price=Decimal(str(item[4])),
                    volume=Decimal(str(item[5])),
                    quote_volume=Decimal(str(item[6])) if len(item) > 6 and item[6] else None,
                )
                candlesticks.append(candlestick)
            except Exception as e:
                logger.warning(f"[Bybit] Failed to parse candle item: {e}")
                continue

        # Sort by timestamp ascending (Bybit returns newest first)
        return sorted(candlesticks)
