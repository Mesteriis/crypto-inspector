"""
WebSocket streaming for real-time candlestick data.

Provides WebSocket connections to Bybit and Binance for real-time kline updates
with automatic fallback chain: Bybit → Binance → REST.
"""

from service.candlestick.websocket.base import (
    BaseWebSocketStream,
    ConnectionState,
    ReconnectConfig,
    StreamConfig,
)
from service.candlestick.websocket.binance import (
    BinanceWebSocketStream,
    create_binance_stream,
)
from service.candlestick.websocket.bybit import (
    BybitWebSocketStream,
    create_bybit_stream,
)
from service.candlestick.websocket.manager import (
    CandleStreamManager,
    ManagerConfig,
    StreamSource,
    get_stream_manager,
    init_stream_manager,
    stop_stream_manager,
)

__all__ = [
    # Base
    "BaseWebSocketStream",
    "ConnectionState",
    "ReconnectConfig",
    "StreamConfig",
    # Bybit
    "BybitWebSocketStream",
    "create_bybit_stream",
    # Binance
    "BinanceWebSocketStream",
    "create_binance_stream",
    # Manager
    "CandleStreamManager",
    "ManagerConfig",
    "StreamSource",
    "get_stream_manager",
    "init_stream_manager",
    "stop_stream_manager",
]
