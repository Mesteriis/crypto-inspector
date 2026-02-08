"""
Stream Manager with Bybit → Binance → REST fallback chain.

Manages WebSocket connections for real-time candlestick streaming with
automatic fallback to alternative sources when primary fails.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from service.candlestick.models import CandleInterval, Candlestick
from service.candlestick.websocket.base import (
    BaseWebSocketStream,
    ConnectionState,
    ReconnectConfig,
    StreamConfig,
)
from service.candlestick.websocket.binance import BinanceWebSocketStream
from service.candlestick.websocket.bybit import BybitWebSocketStream

logger = logging.getLogger(__name__)


class StreamSource(StrEnum):
    """Stream data source."""

    BYBIT = "bybit"
    BINANCE = "binance"
    REST = "rest"
    NONE = "none"


@dataclass
class SymbolStreamState:
    """State for a single symbol's stream."""

    symbol: str
    interval: CandleInterval
    current_source: StreamSource = StreamSource.NONE
    stream: BaseWebSocketStream | None = None
    last_candle: Candlestick | None = None
    last_candle_time: float = 0
    error_count: int = 0


@dataclass
class ManagerConfig:
    """Stream manager configuration."""

    # Symbols to stream
    symbols: list[str] = field(default_factory=list)
    interval: CandleInterval = CandleInterval.MINUTE_1

    # Fallback settings
    fallback_timeout: float = 30.0  # Switch to fallback after N seconds without data
    max_errors_before_fallback: int = 3

    # REST polling interval when in REST mode
    rest_poll_interval: float = 60.0

    # Callbacks
    on_candle: Callable[[str, Candlestick, bool, str], Any] | None = None
    on_source_change: Callable[[str, StreamSource, StreamSource], Any] | None = None
    on_all_failed: Callable[[str], Any] | None = None


class CandleStreamManager:
    """
    Manages WebSocket streams with automatic fallback.

    Fallback chain:
    1. Bybit WebSocket (primary)
    2. Binance WebSocket (secondary)
    3. REST API polling (last resort)
    """

    def __init__(self, config: ManagerConfig):
        self.config = config
        self._streams: dict[str, SymbolStreamState] = {}
        self._rest_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None
        self._should_stop = False

    @property
    def active_sources(self) -> dict[str, StreamSource]:
        """Get current active source for each symbol."""
        return {symbol: state.current_source for symbol, state in self._streams.items()}

    async def _handle_candle(
        self,
        symbol: str,
        candle: Candlestick,
        is_closed: bool,
        source: StreamSource,
    ) -> None:
        """Handle received candle from any source."""
        import time

        state = self._streams.get(symbol)
        if state:
            state.last_candle = candle
            state.last_candle_time = time.time()
            state.error_count = 0

        if self.config.on_candle:
            try:
                result = self.config.on_candle(symbol, candle, is_closed, source.value)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"[Manager] Candle callback error: {e}")

    async def _on_source_change(self, symbol: str, old_source: StreamSource, new_source: StreamSource) -> None:
        """Handle source change."""
        logger.info(f"[Manager] {symbol}: Source changed {old_source.value} → {new_source.value}")

        if self.config.on_source_change:
            try:
                result = self.config.on_source_change(symbol, old_source, new_source)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"[Manager] Source change callback error: {e}")

    def _create_bybit_stream(self, symbol: str) -> BybitWebSocketStream:
        """Create Bybit stream for symbol."""

        async def on_candle(sym: str, candle: Candlestick, is_closed: bool):
            await self._handle_candle(sym, candle, is_closed, StreamSource.BYBIT)

        async def on_disconnect(reason: str):
            state = self._streams.get(symbol)
            if state:
                state.error_count += 1
                if state.error_count >= self.config.max_errors_before_fallback:
                    await self._switch_to_fallback(symbol)

        config = StreamConfig(
            symbol=symbol,
            interval=self.config.interval,
            on_candle=on_candle,
            on_disconnect=on_disconnect,
        )
        return BybitWebSocketStream(config, ReconnectConfig(max_retries=3))

    def _create_binance_stream(self, symbol: str) -> BinanceWebSocketStream:
        """Create Binance stream for symbol."""

        async def on_candle(sym: str, candle: Candlestick, is_closed: bool):
            await self._handle_candle(sym, candle, is_closed, StreamSource.BINANCE)

        async def on_disconnect(reason: str):
            state = self._streams.get(symbol)
            if state:
                state.error_count += 1
                if state.error_count >= self.config.max_errors_before_fallback:
                    await self._switch_to_rest(symbol)

        config = StreamConfig(
            symbol=symbol,
            interval=self.config.interval,
            on_candle=on_candle,
            on_disconnect=on_disconnect,
        )
        return BinanceWebSocketStream(config, ReconnectConfig(max_retries=3))

    async def _switch_to_fallback(self, symbol: str) -> None:
        """Switch symbol from Bybit to Binance."""
        state = self._streams.get(symbol)
        if not state:
            return

        old_source = state.current_source

        # Stop current stream
        if state.stream:
            await state.stream.stop()
            state.stream = None

        # Try Binance
        state.current_source = StreamSource.BINANCE
        state.error_count = 0
        state.stream = self._create_binance_stream(symbol)
        await state.stream.start()

        await self._on_source_change(symbol, old_source, StreamSource.BINANCE)

        # Check if Binance connected
        await asyncio.sleep(5)
        if state.stream and state.stream.state == ConnectionState.FAILED:
            await self._switch_to_rest(symbol)

    async def _switch_to_rest(self, symbol: str) -> None:
        """Switch symbol to REST polling mode."""
        state = self._streams.get(symbol)
        if not state:
            return

        old_source = state.current_source

        # Stop current stream
        if state.stream:
            await state.stream.stop()
            state.stream = None

        state.current_source = StreamSource.REST
        state.error_count = 0

        await self._on_source_change(symbol, old_source, StreamSource.REST)

        # Start REST polling if not already running
        if not self._rest_task or self._rest_task.done():
            self._rest_task = asyncio.create_task(self._rest_polling_loop())

    async def _switch_to_primary(self, symbol: str) -> None:
        """Switch symbol back to primary (Bybit)."""
        state = self._streams.get(symbol)
        if not state or state.current_source == StreamSource.BYBIT:
            return

        old_source = state.current_source

        # Stop current stream
        if state.stream:
            await state.stream.stop()
            state.stream = None

        state.current_source = StreamSource.BYBIT
        state.error_count = 0
        state.stream = self._create_bybit_stream(symbol)
        await state.stream.start()

        await self._on_source_change(symbol, old_source, StreamSource.BYBIT)

    async def _rest_polling_loop(self) -> None:
        """REST API polling loop for symbols in REST mode."""
        from service.candlestick import fetch_candlesticks

        logger.info("[Manager] Starting REST polling loop")

        while not self._should_stop:
            try:
                # Get symbols in REST mode
                rest_symbols = [
                    sym for sym, state in self._streams.items() if state.current_source == StreamSource.REST
                ]

                if not rest_symbols:
                    await asyncio.sleep(5)
                    continue

                for symbol in rest_symbols:
                    if self._should_stop:
                        break

                    try:
                        candles = await fetch_candlesticks(
                            symbol=symbol,
                            interval=self.config.interval,
                            limit=1,
                        )

                        if candles:
                            await self._handle_candle(symbol, candles[-1], True, StreamSource.REST)

                    except Exception as e:
                        logger.warning(f"[Manager] REST fetch failed for {symbol}: {e}")
                        state = self._streams.get(symbol)
                        if state:
                            state.error_count += 1

                await asyncio.sleep(self.config.rest_poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Manager] REST polling error: {e}")
                await asyncio.sleep(5)

        logger.info("[Manager] REST polling loop stopped")

    async def _monitor_loop(self) -> None:
        """Monitor stream health and trigger fallbacks."""
        import time

        logger.info("[Manager] Starting health monitor")

        while not self._should_stop:
            try:
                await asyncio.sleep(10)

                current_time = time.time()

                for symbol, state in self._streams.items():
                    # Skip REST mode - handled separately
                    if state.current_source == StreamSource.REST:
                        continue

                    # Check if stream is dead (no data for too long)
                    time_since_data = current_time - state.last_candle_time

                    if state.last_candle_time > 0 and time_since_data > self.config.fallback_timeout:
                        logger.warning(f"[Manager] {symbol}: No data for {time_since_data:.0f}s, switching fallback")
                        if state.current_source == StreamSource.BYBIT:
                            await self._switch_to_fallback(symbol)
                        else:
                            await self._switch_to_rest(symbol)

                    # Check connection state
                    if state.stream and state.stream.state == ConnectionState.FAILED:
                        logger.warning(f"[Manager] {symbol}: Connection failed, switching")
                        if state.current_source == StreamSource.BYBIT:
                            await self._switch_to_fallback(symbol)
                        else:
                            await self._switch_to_rest(symbol)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Manager] Monitor error: {e}")

        logger.info("[Manager] Health monitor stopped")

    async def start(self) -> None:
        """Start streaming for all configured symbols."""
        if not self.config.symbols:
            logger.warning("[Manager] No symbols configured")
            return

        self._should_stop = False

        logger.info(f"[Manager] Starting streams for {len(self.config.symbols)} symbols")

        for symbol in self.config.symbols:
            state = SymbolStreamState(
                symbol=symbol,
                interval=self.config.interval,
                current_source=StreamSource.BYBIT,
            )

            # Start with Bybit
            state.stream = self._create_bybit_stream(symbol)
            await state.stream.start()

            self._streams[symbol] = state

        # Start monitor
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info("[Manager] All streams started")

    async def stop(self) -> None:
        """Stop all streams."""
        self._should_stop = True

        # Stop monitor
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Stop REST polling
        if self._rest_task:
            self._rest_task.cancel()
            try:
                await self._rest_task
            except asyncio.CancelledError:
                pass

        # Stop all streams
        for state in self._streams.values():
            if state.stream:
                await state.stream.stop()

        self._streams.clear()
        logger.info("[Manager] All streams stopped")

    async def retry_primary(self, symbol: str | None = None) -> None:
        """
        Retry switching to primary (Bybit) for symbol(s).

        Args:
            symbol: Specific symbol or None for all non-primary symbols
        """
        symbols = [symbol] if symbol else list(self._streams.keys())

        for sym in symbols:
            state = self._streams.get(sym)
            if state and state.current_source != StreamSource.BYBIT:
                await self._switch_to_primary(sym)

    def get_status(self) -> dict[str, Any]:
        """Get manager status."""
        return {
            "symbols": {
                symbol: {
                    "source": state.current_source.value,
                    "connected": state.stream.is_connected if state.stream else False,
                    "last_candle_price": float(state.last_candle.close_price) if state.last_candle else None,
                    "error_count": state.error_count,
                }
                for symbol, state in self._streams.items()
            },
            "rest_polling_active": self._rest_task is not None and not self._rest_task.done(),
        }


# Singleton instance
_manager: CandleStreamManager | None = None


def get_stream_manager() -> CandleStreamManager | None:
    """Get the global stream manager instance."""
    return _manager


async def init_stream_manager(
    symbols: list[str],
    interval: CandleInterval = CandleInterval.MINUTE_1,
    on_candle: Callable | None = None,
    on_source_change: Callable | None = None,
) -> CandleStreamManager:
    """
    Initialize and start the global stream manager.

    Args:
        symbols: List of symbols to stream
        interval: Candle interval
        on_candle: Callback for candle updates
        on_source_change: Callback for source changes

    Returns:
        Initialized CandleStreamManager
    """
    global _manager

    if _manager:
        await _manager.stop()

    config = ManagerConfig(
        symbols=symbols,
        interval=interval,
        on_candle=on_candle,
        on_source_change=on_source_change,
    )

    _manager = CandleStreamManager(config)
    await _manager.start()

    return _manager


async def stop_stream_manager() -> None:
    """Stop the global stream manager."""
    global _manager

    if _manager:
        await _manager.stop()
        _manager = None
