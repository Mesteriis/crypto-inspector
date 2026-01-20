"""Coinbase exchange adapter for candlestick data."""

import logging
from decimal import Decimal
from typing import Any

from service.candlestick.exceptions import DataParsingError
from service.candlestick.exchanges.base import BaseExchange
from service.candlestick.models import CandleInterval, Candlestick

logger = logging.getLogger(__name__)


class CoinbaseExchange(BaseExchange):
    """
    Coinbase (Advanced Trade API) exchange adapter.

    API Documentation: https://docs.cloud.coinbase.com/advanced-trade-api/reference
    """

    EXCHANGE_NAME = "coinbase"
    BASE_URL = "https://api.exchange.coinbase.com"

    # Coinbase uses granularity in seconds for some intervals
    INTERVAL_MAP = {
        CandleInterval.MINUTE_1: "ONE_MINUTE",
        CandleInterval.MINUTE_5: "FIVE_MINUTE",
        CandleInterval.MINUTE_15: "FIFTEEN_MINUTE",
        CandleInterval.MINUTE_30: "THIRTY_MINUTE",
        CandleInterval.HOUR_1: "ONE_HOUR",
        CandleInterval.HOUR_2: "TWO_HOUR",
        CandleInterval.HOUR_6: "SIX_HOUR",
        CandleInterval.DAY_1: "ONE_DAY",
    }

    # Granularity in seconds for the public API
    GRANULARITY_SECONDS = {
        CandleInterval.MINUTE_1: 60,
        CandleInterval.MINUTE_5: 300,
        CandleInterval.MINUTE_15: 900,
        CandleInterval.HOUR_1: 3600,
        CandleInterval.HOUR_6: 21600,
        CandleInterval.DAY_1: 86400,
    }

    def convert_symbol(self, symbol: str) -> str:
        """Convert BTC/USDT to BTC-USDT (Coinbase uses dash separator)."""
        return symbol.replace("/", "-").upper()

    async def fetch_candlesticks(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Candlestick]:
        """Fetch candlestick data from Coinbase."""
        product_id = self.convert_symbol(symbol)

        # Coinbase uses granularity in seconds
        granularity = self.GRANULARITY_SECONDS.get(interval)
        if granularity is None:
            # Fall back to 1 hour if interval not directly supported
            granularity = 3600

        params: dict[str, Any] = {
            "granularity": granularity,
        }

        # Coinbase expects ISO timestamps or Unix timestamps in seconds
        if start_time is not None:
            params["start"] = start_time // 1000  # Convert ms to seconds
        if end_time is not None:
            params["end"] = end_time // 1000  # Convert ms to seconds

        logger.debug(f"[Coinbase] Fetching candlesticks for {product_id}")

        endpoint = f"/products/{product_id}/candles"
        data = await self._make_request("GET", endpoint, params=params)
        return self._parse_candlesticks(data)[:limit]

    def _parse_candlesticks(self, data: Any) -> list[Candlestick]:
        """
        Parse Coinbase candles response.

        Coinbase returns data as array of arrays:
        [
            [
                time,    // 0: bucket start time (Unix timestamp in seconds)
                low,     // 1: lowest price during the bucket interval
                high,    // 2: highest price during the bucket interval
                open,    // 3: opening price (first trade) in the bucket interval
                close,   // 4: closing price (last trade) in the bucket interval
                volume   // 5: volume of trading activity during the bucket interval
            ]
        ]
        Note: Coinbase returns newest first, so we need to reverse.
        """
        if not isinstance(data, list):
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Expected list of candles",
            )

        candlesticks = []
        for item in data:
            try:
                if not isinstance(item, list) or len(item) < 6:
                    logger.warning(f"[Coinbase] Skipping invalid candle item: {item}")
                    continue

                # Convert timestamp from seconds to milliseconds
                timestamp_ms = int(item[0]) * 1000

                candlestick = Candlestick(
                    timestamp=timestamp_ms,
                    open_price=Decimal(str(item[3])),
                    high_price=Decimal(str(item[2])),
                    low_price=Decimal(str(item[1])),
                    close_price=Decimal(str(item[4])),
                    volume=Decimal(str(item[5])),
                )
                candlesticks.append(candlestick)
            except Exception as e:
                logger.warning(f"[Coinbase] Failed to parse candle item: {e}")
                continue

        # Sort by timestamp ascending (Coinbase returns newest first)
        return sorted(candlesticks)
