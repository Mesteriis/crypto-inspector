"""Bybit WebSocket stream for real-time candlestick data."""

import logging

from service.candlestick.models import CandleInterval, Candlestick
from service.candlestick.websocket.base import BaseWebSocketStream, StreamConfig

logger = logging.getLogger(__name__)


# Bybit interval mapping
BYBIT_INTERVALS = {
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


class BybitWebSocketStream(BaseWebSocketStream):
    """
    Bybit WebSocket stream for candlestick data.

    Bybit V5 Public WebSocket:
    - URL: wss://stream.bybit.com/v5/public/spot
    - Topic: kline.{interval}.{symbol}
    - Free, no API key required

    Message format:
    {
        "topic": "kline.1.BTCUSDT",
        "data": [{
            "start": 1672325760000,
            "end": 1672325819999,
            "interval": "1",
            "open": "16649.5",
            "close": "16650",
            "high": "16650",
            "low": "16649.5",
            "volume": "2.001",
            "turnover": "33330.0065",
            "confirm": false,
            "timestamp": 1672325760000
        }],
        "ts": 1672325760000,
        "type": "snapshot"
    }
    """

    EXCHANGE_NAME = "bybit"
    WS_URL = "wss://stream.bybit.com/v5/public/spot"

    def _convert_symbol(self, symbol: str) -> str:
        """Convert BTC/USDT to BTCUSDT."""
        return symbol.replace("/", "").upper()

    def _get_interval_string(self) -> str:
        """Get Bybit interval string."""
        return BYBIT_INTERVALS.get(self.config.interval, "1")

    def _build_ws_url(self) -> str:
        """Build WebSocket URL (Bybit uses base URL, subscribes via message)."""
        return self.WS_URL

    def _get_subscribe_message(self) -> dict | None:
        """Get Bybit subscription message."""
        symbol = self._convert_symbol(self.config.symbol)
        interval = self._get_interval_string()

        return {
            "op": "subscribe",
            "args": [f"kline.{interval}.{symbol}"],
        }

    def _parse_message(self, data: dict) -> tuple[Candlestick, bool] | None:
        """
        Parse Bybit kline message.

        Returns:
            Tuple of (Candlestick, is_closed) or None if not a kline message.
        """
        # Check if it's a kline message
        topic = data.get("topic", "")
        if not topic.startswith("kline."):
            # Could be subscription confirmation, ping/pong, etc.
            if data.get("op") == "subscribe" and data.get("success"):
                logger.debug(f"[Bybit] Subscribed successfully: {data.get('conn_id')}")
            return None

        # Parse kline data
        klines = data.get("data", [])
        if not klines:
            return None

        # Get the latest kline
        kline = klines[0]

        try:
            candle = Candlestick(
                timestamp=int(kline["start"]),
                open_price=self._safe_decimal(kline["open"]),
                high_price=self._safe_decimal(kline["high"]),
                low_price=self._safe_decimal(kline["low"]),
                close_price=self._safe_decimal(kline["close"]),
                volume=self._safe_decimal(kline["volume"]),
                quote_volume=self._safe_decimal(kline["turnover"]) if kline.get("turnover") else None,
            )

            # confirm=true means candle is closed
            is_closed = kline.get("confirm", False)

            return candle, is_closed

        except Exception as e:
            logger.warning(f"[Bybit] Failed to parse kline: {e}")
            return None


def create_bybit_stream(
    symbol: str,
    interval: CandleInterval = CandleInterval.MINUTE_1,
    on_candle=None,
    on_connect=None,
    on_disconnect=None,
    on_error=None,
) -> BybitWebSocketStream:
    """
    Create a Bybit WebSocket stream.

    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        interval: Candle interval
        on_candle: Callback for candle updates (symbol, candle, is_closed)
        on_connect: Callback on connection
        on_disconnect: Callback on disconnect (reason)
        on_error: Callback on error (exception)

    Returns:
        BybitWebSocketStream instance
    """
    config = StreamConfig(
        symbol=symbol,
        interval=interval,
        on_candle=on_candle,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        on_error=on_error,
    )
    return BybitWebSocketStream(config)
