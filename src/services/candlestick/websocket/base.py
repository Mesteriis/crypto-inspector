"""Base WebSocket client for real-time candlestick streaming."""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from services.candlestick.models import CandleInterval, Candlestick

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """WebSocket connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class StreamConfig:
    """Configuration for a WebSocket stream."""

    symbol: str  # e.g., "BTC/USDT"
    interval: CandleInterval = CandleInterval.MINUTE_1

    # Callbacks
    on_candle: Callable[[str, Candlestick, bool], Any] | None = None  # symbol, candle, is_closed
    on_connect: Callable[[], Any] | None = None
    on_disconnect: Callable[[str], Any] | None = None  # reason
    on_error: Callable[[Exception], Any] | None = None


@dataclass
class ReconnectConfig:
    """Reconnection configuration with exponential backoff."""

    max_retries: int = 10
    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0

    # State
    current_retry: int = field(default=0, init=False)
    current_delay: float = field(default=1.0, init=False)

    def reset(self) -> None:
        """Reset reconnection state."""
        self.current_retry = 0
        self.current_delay = self.initial_delay

    def next_delay(self) -> float | None:
        """Get next delay or None if max retries reached."""
        if self.current_retry >= self.max_retries:
            return None

        delay = self.current_delay
        self.current_retry += 1
        self.current_delay = min(self.current_delay * self.multiplier, self.max_delay)
        return delay


class BaseWebSocketStream(ABC):
    """
    Abstract base class for WebSocket candlestick streams.

    Provides:
    - Auto-reconnect with exponential backoff
    - Connection state management
    - Standardized candle parsing
    """

    EXCHANGE_NAME: str = "base"
    WS_URL: str = ""

    def __init__(
        self,
        config: StreamConfig,
        reconnect_config: ReconnectConfig | None = None,
    ):
        self.config = config
        self.reconnect = reconnect_config or ReconnectConfig()

        self._ws: ClientConnection | None = None
        self._state = ConnectionState.DISCONNECTED
        self._run_task: asyncio.Task | None = None
        self._should_stop = False

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state == ConnectionState.CONNECTED

    @abstractmethod
    def _build_ws_url(self) -> str:
        """Build the WebSocket URL for subscription."""
        pass

    @abstractmethod
    def _parse_message(self, data: dict) -> tuple[Candlestick, bool] | None:
        """
        Parse WebSocket message into a Candlestick.

        Returns:
            Tuple of (Candlestick, is_closed) or None if not a candle message.
        """
        pass

    @abstractmethod
    def _get_subscribe_message(self) -> dict | None:
        """Get subscription message to send after connect (if needed)."""
        pass

    def _convert_symbol(self, symbol: str) -> str:
        """Convert standard symbol to exchange format. Override if needed."""
        return symbol.replace("/", "").lower()

    async def _on_candle(self, candle: Candlestick, is_closed: bool) -> None:
        """Handle received candle."""
        if self.config.on_candle:
            try:
                result = self.config.on_candle(self.config.symbol, candle, is_closed)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"[{self.EXCHANGE_NAME}] Candle callback error: {e}")

    async def _on_connect(self) -> None:
        """Handle successful connection."""
        self._state = ConnectionState.CONNECTED
        self.reconnect.reset()
        logger.info(f"[{self.EXCHANGE_NAME}] Connected to {self.config.symbol}")

        if self.config.on_connect:
            try:
                result = self.config.on_connect()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"[{self.EXCHANGE_NAME}] Connect callback error: {e}")

    async def _on_disconnect(self, reason: str) -> None:
        """Handle disconnection."""
        self._state = ConnectionState.DISCONNECTED
        logger.warning(f"[{self.EXCHANGE_NAME}] Disconnected: {reason}")

        if self.config.on_disconnect:
            try:
                result = self.config.on_disconnect(reason)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"[{self.EXCHANGE_NAME}] Disconnect callback error: {e}")

    async def _on_error(self, error: Exception) -> None:
        """Handle error."""
        logger.error(f"[{self.EXCHANGE_NAME}] Error: {error}")

        if self.config.on_error:
            try:
                result = self.config.on_error(error)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"[{self.EXCHANGE_NAME}] Error callback error: {e}")

    async def _connect(self) -> bool:
        """Establish WebSocket connection."""
        self._state = ConnectionState.CONNECTING
        url = self._build_ws_url()

        try:
            logger.debug(f"[{self.EXCHANGE_NAME}] Connecting to {url}")
            self._ws = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )

            # Send subscribe message if needed
            sub_msg = self._get_subscribe_message()
            if sub_msg:
                import json

                await self._ws.send(json.dumps(sub_msg))
                logger.debug(f"[{self.EXCHANGE_NAME}] Sent subscribe: {sub_msg}")

            await self._on_connect()
            return True

        except Exception as e:
            logger.error(f"[{self.EXCHANGE_NAME}] Connection failed: {e}")
            await self._on_error(e)
            return False

    async def _reconnect(self) -> bool:
        """Attempt reconnection with backoff."""
        delay = self.reconnect.next_delay()

        if delay is None:
            self._state = ConnectionState.FAILED
            logger.error(f"[{self.EXCHANGE_NAME}] Max reconnect attempts reached")
            return False

        self._state = ConnectionState.RECONNECTING
        logger.info(
            f"[{self.EXCHANGE_NAME}] Reconnecting in {delay:.1f}s "
            f"(attempt {self.reconnect.current_retry}/{self.reconnect.max_retries})"
        )

        await asyncio.sleep(delay)

        if self._should_stop:
            return False

        return await self._connect()

    async def _receive_loop(self) -> None:
        """Main message receive loop."""
        import json

        while not self._should_stop and self._ws:
            try:
                message = await self._ws.recv()
                data = json.loads(message)

                result = self._parse_message(data)
                if result:
                    candle, is_closed = result
                    await self._on_candle(candle, is_closed)

            except websockets.ConnectionClosed as e:
                await self._on_disconnect(f"Connection closed: {e.code}")
                break
            except json.JSONDecodeError as e:
                logger.warning(f"[{self.EXCHANGE_NAME}] Invalid JSON: {e}")
            except Exception as e:
                logger.error(f"[{self.EXCHANGE_NAME}] Receive error: {e}")
                await self._on_error(e)
                break

    async def _run(self) -> None:
        """Main run loop with auto-reconnect."""
        while not self._should_stop:
            # Connect
            if not await self._connect():
                if not await self._reconnect():
                    break
                continue

            # Receive messages
            await self._receive_loop()

            # Reconnect if not stopped
            if not self._should_stop:
                if not await self._reconnect():
                    break

    async def start(self) -> None:
        """Start the WebSocket stream."""
        if self._run_task and not self._run_task.done():
            logger.warning(f"[{self.EXCHANGE_NAME}] Stream already running")
            return

        self._should_stop = False
        self._run_task = asyncio.create_task(self._run())
        logger.info(f"[{self.EXCHANGE_NAME}] Started stream for {self.config.symbol}")

    async def stop(self) -> None:
        """Stop the WebSocket stream."""
        self._should_stop = True

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            self._run_task = None

        self._state = ConnectionState.DISCONNECTED
        logger.info(f"[{self.EXCHANGE_NAME}] Stopped stream for {self.config.symbol}")

    @staticmethod
    def _safe_decimal(value: Any) -> Decimal:
        """Safely convert value to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
