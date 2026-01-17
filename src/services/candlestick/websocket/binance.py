"""Binance WebSocket stream for real-time candlestick data."""

import logging

from services.candlestick.models import CandleInterval, Candlestick
from services.candlestick.websocket.base import BaseWebSocketStream, StreamConfig

logger = logging.getLogger(__name__)


# Binance interval mapping
BINANCE_INTERVALS = {
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


class BinanceWebSocketStream(BaseWebSocketStream):
    """
    Binance WebSocket stream for candlestick data.

    Binance WebSocket Streams:
    - URL: wss://stream.binance.com:9443/ws/<stream>
    - Stream: <symbol>@kline_<interval>
    - Free, no API key required

    Message format:
    {
        "e": "kline",
        "E": 1672325760000,  // Event time
        "s": "BTCUSDT",      // Symbol
        "k": {
            "t": 1672325760000,  // Kline start time
            "T": 1672325819999,  // Kline close time
            "s": "BTCUSDT",      // Symbol
            "i": "1m",           // Interval
            "f": 100,            // First trade ID
            "L": 200,            // Last trade ID
            "o": "16649.50",     // Open price
            "c": "16650.00",     // Close price
            "h": "16650.00",     // High price
            "l": "16649.50",     // Low price
            "v": "2.001",        // Volume
            "n": 100,            // Number of trades
            "x": false,          // Is this kline closed?
            "q": "33330.01",     // Quote asset volume
            "V": "1.001",        // Taker buy base asset volume
            "Q": "16650.01"      // Taker buy quote asset volume
        }
    }
    """

    EXCHANGE_NAME = "binance"
    WS_BASE_URL = "wss://stream.binance.com:9443/ws"

    def _convert_symbol(self, symbol: str) -> str:
        """Convert BTC/USDT to btcusdt (Binance uses lowercase)."""
        return symbol.replace("/", "").lower()

    def _get_interval_string(self) -> str:
        """Get Binance interval string."""
        return BINANCE_INTERVALS.get(self.config.interval, "1m")

    def _build_ws_url(self) -> str:
        """Build WebSocket URL with stream name in URL (Binance style)."""
        symbol = self._convert_symbol(self.config.symbol)
        interval = self._get_interval_string()
        stream = f"{symbol}@kline_{interval}"
        return f"{self.WS_BASE_URL}/{stream}"

    def _get_subscribe_message(self) -> dict | None:
        """Binance subscribes via URL, no message needed."""
        return None

    def _parse_message(self, data: dict) -> tuple[Candlestick, bool] | None:
        """
        Parse Binance kline message.

        Returns:
            Tuple of (Candlestick, is_closed) or None if not a kline message.
        """
        # Check if it's a kline event
        event_type = data.get("e")
        if event_type != "kline":
            return None

        kline = data.get("k")
        if not kline:
            return None

        try:
            candle = Candlestick(
                timestamp=int(kline["t"]),  # Kline start time
                open_price=self._safe_decimal(kline["o"]),
                high_price=self._safe_decimal(kline["h"]),
                low_price=self._safe_decimal(kline["l"]),
                close_price=self._safe_decimal(kline["c"]),
                volume=self._safe_decimal(kline["v"]),
                quote_volume=self._safe_decimal(kline["q"]) if kline.get("q") else None,
                trades_count=int(kline["n"]) if kline.get("n") else None,
            )

            # x=true means kline is closed
            is_closed = kline.get("x", False)

            return candle, is_closed

        except Exception as e:
            logger.warning(f"[Binance] Failed to parse kline: {e}")
            return None


def create_binance_stream(
    symbol: str,
    interval: CandleInterval = CandleInterval.MINUTE_1,
    on_candle=None,
    on_connect=None,
    on_disconnect=None,
    on_error=None,
) -> BinanceWebSocketStream:
    """
    Create a Binance WebSocket stream.

    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        interval: Candle interval
        on_candle: Callback for candle updates (symbol, candle, is_closed)
        on_connect: Callback on connection
        on_disconnect: Callback on disconnect (reason)
        on_error: Callback on error (exception)

    Returns:
        BinanceWebSocketStream instance
    """
    config = StreamConfig(
        symbol=symbol,
        interval=interval,
        on_candle=on_candle,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        on_error=on_error,
    )
    return BinanceWebSocketStream(config)
