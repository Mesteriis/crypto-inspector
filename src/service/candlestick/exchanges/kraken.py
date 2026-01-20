"""Kraken exchange adapter for candlestick data."""

import logging
from decimal import Decimal
from typing import Any

from service.candlestick.exceptions import DataParsingError
from service.candlestick.exchanges.base import BaseExchange
from service.candlestick.models import CandleInterval, Candlestick

logger = logging.getLogger(__name__)


class KrakenExchange(BaseExchange):
    """
    Kraken exchange adapter.

    API Documentation: https://docs.kraken.com/rest/
    """

    EXCHANGE_NAME = "kraken"
    BASE_URL = "https://api.kraken.com"

    # Kraken uses interval in minutes
    INTERVAL_MAP = {
        CandleInterval.MINUTE_1: 1,
        CandleInterval.MINUTE_5: 5,
        CandleInterval.MINUTE_15: 15,
        CandleInterval.MINUTE_30: 30,
        CandleInterval.HOUR_1: 60,
        CandleInterval.HOUR_4: 240,
        CandleInterval.DAY_1: 1440,
        CandleInterval.WEEK_1: 10080,
    }

    # Kraken uses different symbol names
    SYMBOL_MAP = {
        "BTC": "XBT",
        "DOGE": "XDG",
    }

    def convert_symbol(self, symbol: str) -> str:
        """
        Convert standard symbol to Kraken format.

        Kraken uses XBT instead of BTC and has specific pair naming.
        Example: BTC/USDT -> XBTUSDT
        """
        base, quote = symbol.upper().split("/")

        # Map to Kraken-specific symbols
        base = self.SYMBOL_MAP.get(base, base)
        quote = self.SYMBOL_MAP.get(quote, quote)

        return f"{base}{quote}"

    async def fetch_candlesticks(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Candlestick]:
        """Fetch candlestick data from Kraken."""
        pair = self.convert_symbol(symbol)
        interval_minutes = self.INTERVAL_MAP.get(interval, 60)

        params: dict[str, Any] = {
            "pair": pair,
            "interval": interval_minutes,
        }

        # Kraken 'since' is a Unix timestamp (seconds) used as a marker
        # for returning data after that point
        if start_time is not None:
            # Convert milliseconds to seconds
            params["since"] = start_time // 1000

        logger.debug(f"[Kraken] Fetching candlesticks for {pair}")

        data = await self._make_request("GET", "/0/public/OHLC", params=params)
        return self._parse_candlesticks(data)[:limit]

    def _parse_candlesticks(self, data: Any) -> list[Candlestick]:
        """
        Parse Kraken OHLC response.

        Kraken returns data as:
        {
            "error": [],
            "result": {
                "XXBTZUSD": [
                    [
                        1688671200,     // 0: time (Unix timestamp)
                        "30306.1",      // 1: open
                        "30306.2",      // 2: high
                        "30306.1",      // 3: low
                        "30306.1",      // 4: close
                        "30306.1",      // 5: vwap
                        "0.00080000",   // 6: volume
                        1               // 7: count
                    ],
                    ...
                ],
                "last": 1688671200
            }
        }
        """
        if not isinstance(data, dict):
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Expected dict response",
            )

        # Check for API errors
        if data.get("error") and len(data["error"]) > 0:
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason=str(data["error"]),
            )

        result = data.get("result", {})
        if not result:
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="Empty result in response",
            )

        # Find the OHLC data (first key that's not 'last')
        ohlc_data = None
        for key, value in result.items():
            if key != "last" and isinstance(value, list):
                ohlc_data = value
                break

        if not ohlc_data:
            raise DataParsingError(
                exchange=self.EXCHANGE_NAME,
                reason="No OHLC data found in response",
            )

        candlesticks = []
        for item in ohlc_data:
            try:
                if not isinstance(item, list) or len(item) < 7:
                    logger.warning(f"[Kraken] Skipping invalid OHLC item: {item}")
                    continue

                # Convert timestamp from seconds to milliseconds
                timestamp_ms = int(item[0]) * 1000

                candlestick = Candlestick(
                    timestamp=timestamp_ms,
                    open_price=Decimal(str(item[1])),
                    high_price=Decimal(str(item[2])),
                    low_price=Decimal(str(item[3])),
                    close_price=Decimal(str(item[4])),
                    volume=Decimal(str(item[6])),
                    trades_count=int(item[7]) if len(item) > 7 else None,
                )
                candlesticks.append(candlestick)
            except Exception as e:
                logger.warning(f"[Kraken] Failed to parse OHLC item: {e}")
                continue

        return sorted(candlesticks)
