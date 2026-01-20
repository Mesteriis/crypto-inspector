"""OKX exchange adapter for candlestick data."""

import logging
from decimal import Decimal
from typing import Any

from service.candlestick.exceptions import DataParsingError
from service.candlestick.exchanges.base import BaseExchange
from service.candlestick.models import CandleInterval, Candlestick

logger = logging.getLogger(__name__)


class OKXExchange(BaseExchange):
    """
    OKX exchange adapter.

    API Documentation: https://www.okx.com/docs-v5/en/
    """

    EXCHANGE_NAME = "okx"
    BASE_URL = "https://www.okx.com"

    # OKX interval notation
    INTERVAL_MAP = {
        CandleInterval.MINUTE_1: "1m",
        CandleInterval.MINUTE_3: "3m",
        CandleInterval.MINUTE_5: "5m",
        CandleInterval.MINUTE_15: "15m",
        CandleInterval.MINUTE_30: "30m",
        CandleInterval.HOUR_1: "1H",
        CandleInterval.HOUR_2: "2H",
        CandleInterval.HOUR_4: "4H",
        CandleInterval.HOUR_6: "6H",
        CandleInterval.HOUR_12: "12H",
        CandleInterval.DAY_1: "1D",
        CandleInterval.DAY_3: "3D",
        CandleInterval.WEEK_1: "1W",
        CandleInterval.MONTH_1: "1M",
    }

    def convert_symbol(self, symbol: str) -> str:
        """Convert BTC/USDT to BTC-USDT (OKX uses dash separator)."""
        return symbol.replace("/", "-").upper()

    async def fetch_candlesticks(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Candlestick]:
        """Fetch candlestick data from OKX."""
        inst_id = self.convert_symbol(symbol)
        bar = self.get_interval_string(interval)

        params: dict[str, Any] = {
            "instId": inst_id,
            "bar": bar,
            "limit": min(limit, 300),  # OKX max is 300
        }

        # OKX uses 'after' and 'before' in milliseconds
        if end_time is not None:
            params["before"] = end_time
        if start_time is not None:
            params["after"] = start_time

        logger.debug(f"[OKX] Fetching candlesticks for {inst_id}")

        data = await self._make_request("GET", "/api/v5/market/candles", params=params)
        return self._parse_candlesticks(data)

    def _parse_candlesticks(self, data: Any) -> list[Candlestick]:
        """
        Parse OKX candles response.

        OKX returns data as:
        {
            "code": "0",
            "msg": "",
            "data": [
                [
                    "1597026383085",    // 0: Opening time (ms timestamp)
                    "3.721",            // 1: Open price
                    "3.743",            // 2: Highest price
                    "3.677",            // 3: Lowest price
                    "3.708",            // 4: Close price
                    "8422410",          // 5: Volume (base currency)
                    "22698348.04828491",// 6: Volume (quote currency)
                    "12698348.04828491",// 7: Volume (quote currency) in USDT
                    "0"                 // 8: Confirm flag (0=not confirmed)
                ],
                ...
            ]
        }
        Note: OKX returns newest first.
        """
        if not isinstance(data, dict):
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Expected dict response",
            )

        # Check for API errors
        if data.get("code") != "0":
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
                    logger.warning(f"[OKX] Skipping invalid candle item: {item}")
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
                logger.warning(f"[OKX] Failed to parse candle item: {e}")
                continue

        # Sort by timestamp ascending (OKX returns newest first)
        return sorted(candlesticks)
