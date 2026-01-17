"""KuCoin exchange adapter for candlestick data."""

import logging
from decimal import Decimal
from typing import Any

from services.candlestick.exceptions import DataParsingError
from services.candlestick.exchanges.base import BaseExchange
from services.candlestick.models import CandleInterval, Candlestick

logger = logging.getLogger(__name__)


class KucoinExchange(BaseExchange):
    """
    KuCoin exchange adapter.

    API Documentation: https://docs.kucoin.com/
    """

    EXCHANGE_NAME = "kucoin"
    BASE_URL = "https://api.kucoin.com"

    # KuCoin interval notation
    INTERVAL_MAP = {
        CandleInterval.MINUTE_1: "1min",
        CandleInterval.MINUTE_3: "3min",
        CandleInterval.MINUTE_5: "5min",
        CandleInterval.MINUTE_15: "15min",
        CandleInterval.MINUTE_30: "30min",
        CandleInterval.HOUR_1: "1hour",
        CandleInterval.HOUR_2: "2hour",
        CandleInterval.HOUR_4: "4hour",
        CandleInterval.HOUR_6: "6hour",
        CandleInterval.HOUR_8: "8hour",
        CandleInterval.HOUR_12: "12hour",
        CandleInterval.DAY_1: "1day",
        CandleInterval.WEEK_1: "1week",
    }

    def convert_symbol(self, symbol: str) -> str:
        """Convert BTC/USDT to BTC-USDT (KuCoin uses dash separator)."""
        return symbol.replace("/", "-").upper()

    async def fetch_candlesticks(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Candlestick]:
        """Fetch candlestick data from KuCoin."""
        kucoin_symbol = self.convert_symbol(symbol)
        kucoin_type = self.get_interval_string(interval)

        params: dict[str, Any] = {
            "symbol": kucoin_symbol,
            "type": kucoin_type,
        }

        # KuCoin uses 'startAt' and 'endAt' in seconds
        if start_time is not None:
            params["startAt"] = start_time // 1000
        if end_time is not None:
            params["endAt"] = end_time // 1000

        logger.debug(f"[KuCoin] Fetching candlesticks for {kucoin_symbol}")

        data = await self._make_request("GET", "/api/v1/market/candles", params=params)
        return self._parse_candlesticks(data)[:limit]

    def _parse_candlesticks(self, data: Any) -> list[Candlestick]:
        """
        Parse KuCoin candles response.

        KuCoin returns data as:
        {
            "code": "200000",
            "data": [
                [
                    "1545904980",     // 0: Start time (Unix timestamp in seconds)
                    "0.058",          // 1: Opening price
                    "0.049",          // 2: Closing price
                    "0.058",          // 3: Highest price
                    "0.049",          // 4: Lowest price
                    "0.018",          // 5: Volume (base currency)
                    "0.000945"        // 6: Amount (quote currency)
                ],
                ...
            ]
        }
        Note: KuCoin returns newest first.
        """
        if not isinstance(data, dict):
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Expected dict response",
            )

        # Check for API errors
        if data.get("code") != "200000":
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason=f"API error: {data.get('msg', 'Unknown error')}",
            )

        candles_data = data.get("data", [])
        if not isinstance(candles_data, list):
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Expected list of candles in data",
            )

        candlesticks = []
        for item in candles_data:
            try:
                if not isinstance(item, list) or len(item) < 6:
                    logger.warning(f"[KuCoin] Skipping invalid candle item: {item}")
                    continue

                # Convert timestamp from seconds to milliseconds
                timestamp_ms = int(item[0]) * 1000

                candlestick = Candlestick(
                    timestamp=timestamp_ms,
                    open_price=Decimal(str(item[1])),
                    close_price=Decimal(str(item[2])),
                    high_price=Decimal(str(item[3])),
                    low_price=Decimal(str(item[4])),
                    volume=Decimal(str(item[5])),
                    quote_volume=Decimal(str(item[6])) if len(item) > 6 and item[6] else None,
                )
                candlesticks.append(candlestick)
            except Exception as e:
                logger.warning(f"[KuCoin] Failed to parse candle item: {e}")
                continue

        # Sort by timestamp ascending (KuCoin returns newest first)
        return sorted(candlesticks)
