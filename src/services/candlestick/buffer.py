"""
Buffered candlestick writer for WebSocket streams.

Accumulates candles in memory and flushes to database in batches
to avoid overloading the connection.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.candlestick.models import Candlestick

logger = logging.getLogger(__name__)


@dataclass
class BufferConfig:
    """Configuration for candle buffer."""

    max_buffer_size: int = 100  # Flush when buffer reaches this size
    flush_interval_seconds: float = 30.0  # Flush every N seconds
    retry_on_error: bool = True
    max_retries: int = 3


@dataclass
class BufferedCandle:
    """Candle with metadata for buffering."""

    symbol: str
    interval: str
    exchange: str
    candle: "Candlestick"
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class CandleBuffer:
    """
    Buffered writer for candlestick data.

    Accumulates closed candles and writes to DB in batches.
    """

    def __init__(self, config: BufferConfig | None = None):
        self.config = config or BufferConfig()
        self._buffer: list[BufferedCandle] = []
        self._flush_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._should_stop = False
        self._stats = {
            "buffered": 0,
            "flushed": 0,
            "errors": 0,
        }

    @property
    def buffer_size(self) -> int:
        """Current buffer size."""
        return len(self._buffer)

    @property
    def stats(self) -> dict:
        """Get buffer statistics."""
        return {
            **self._stats,
            "current_buffer_size": self.buffer_size,
        }

    async def add(
        self,
        symbol: str,
        candle: "Candlestick",
        exchange: str = "websocket",
        interval: str = "1m",
    ) -> None:
        """
        Add a candle to the buffer.

        Args:
            symbol: Trading pair symbol
            candle: Candlestick data
            exchange: Exchange name
            interval: Candle interval
        """
        async with self._lock:
            self._buffer.append(
                BufferedCandle(
                    symbol=symbol,
                    interval=interval,
                    exchange=exchange,
                    candle=candle,
                )
            )
            self._stats["buffered"] += 1

        # Check if we should flush
        if len(self._buffer) >= self.config.max_buffer_size:
            await self.flush()

    async def flush(self) -> int:
        """
        Flush buffer to database.

        Returns:
            Number of records written.
        """
        async with self._lock:
            if not self._buffer:
                return 0

            # Take all buffered candles
            to_flush = self._buffer.copy()
            self._buffer.clear()

        if not to_flush:
            return 0

        logger.info(f"[Buffer] Flushing {len(to_flush)} candles to database")

        try:
            count = await self._write_to_db(to_flush)
            self._stats["flushed"] += count
            logger.info(f"[Buffer] Successfully wrote {count} candles")
            return count

        except Exception as e:
            logger.error(f"[Buffer] Failed to flush: {e}")
            self._stats["errors"] += 1

            # Put back in buffer for retry
            if self.config.retry_on_error:
                async with self._lock:
                    self._buffer = to_flush + self._buffer
                    # Trim if too large
                    if len(self._buffer) > self.config.max_buffer_size * 2:
                        self._buffer = self._buffer[-self.config.max_buffer_size :]

            return 0

    async def _write_to_db(self, candles: list[BufferedCandle]) -> int:
        """Write candles to database."""
        # Import here to avoid circular imports
        from db.session import async_session_maker

        # Group by symbol/interval/exchange for efficient upsert
        grouped: dict[tuple, list] = defaultdict(list)
        for bc in candles:
            key = (bc.exchange, bc.symbol, bc.interval)
            grouped[key].append(bc)

        total_written = 0

        async with async_session_maker() as session:
            for (exchange, symbol, interval), buffered_candles in grouped.items():
                records = []
                for bc in buffered_candles:
                    c = bc.candle
                    records.append(
                        {
                            "exchange": exchange,
                            "symbol": symbol,
                            "interval": interval,
                            "timestamp": c.timestamp,
                            "open_price": c.open_price,
                            "high_price": c.high_price,
                            "low_price": c.low_price,
                            "close_price": c.close_price,
                            "volume": c.volume,
                            "quote_volume": c.quote_volume,
                            "trades_count": c.trades_count,
                            "fetch_time_ms": 0,
                            "is_complete": True,
                            "loaded_at": datetime.now(UTC),
                        }
                    )

                if records:
                    # Use raw SQL for upsert to avoid model import issues
                    from sqlalchemy import text

                    # Detect dialect
                    dialect = session.bind.dialect.name if session.bind else "sqlite"

                    for record in records:
                        if dialect == "postgresql":
                            stmt = text("""
                                INSERT INTO candlestick_records
                                (exchange, symbol, interval, timestamp, open_price, high_price,
                                 low_price, close_price, volume, quote_volume, trades_count,
                                 fetch_time_ms, is_complete, loaded_at)
                                VALUES (:exchange, :symbol, :interval, :timestamp, :open_price,
                                        :high_price, :low_price, :close_price, :volume,
                                        :quote_volume, :trades_count, :fetch_time_ms,
                                        :is_complete, :loaded_at)
                                ON CONFLICT (exchange, symbol, interval, timestamp)
                                DO UPDATE SET
                                    open_price = EXCLUDED.open_price,
                                    high_price = EXCLUDED.high_price,
                                    low_price = EXCLUDED.low_price,
                                    close_price = EXCLUDED.close_price,
                                    volume = EXCLUDED.volume,
                                    quote_volume = EXCLUDED.quote_volume,
                                    trades_count = EXCLUDED.trades_count,
                                    is_complete = EXCLUDED.is_complete,
                                    loaded_at = EXCLUDED.loaded_at
                            """)
                        else:
                            # SQLite
                            stmt = text("""
                                INSERT OR REPLACE INTO candlestick_records
                                (exchange, symbol, interval, timestamp, open_price, high_price,
                                 low_price, close_price, volume, quote_volume, trades_count,
                                 fetch_time_ms, is_complete, loaded_at)
                                VALUES (:exchange, :symbol, :interval, :timestamp, :open_price,
                                        :high_price, :low_price, :close_price, :volume,
                                        :quote_volume, :trades_count, :fetch_time_ms,
                                        :is_complete, :loaded_at)
                            """)

                        await session.execute(stmt, record)
                        total_written += 1

            await session.commit()

        return total_written

    async def _periodic_flush(self) -> None:
        """Periodic flush task."""
        while not self._should_stop:
            await asyncio.sleep(self.config.flush_interval_seconds)

            if self._should_stop:
                break

            if self._buffer:
                await self.flush()

    async def start(self) -> None:
        """Start the periodic flush task."""
        self._should_stop = False
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("[Buffer] Started periodic flush task")

    async def stop(self) -> None:
        """Stop and flush remaining buffer."""
        self._should_stop = True

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        if self._buffer:
            logger.info(f"[Buffer] Final flush of {len(self._buffer)} candles")
            await self.flush()

        logger.info(f"[Buffer] Stopped. Stats: {self.stats}")


# Global buffer instance
_candle_buffer: CandleBuffer | None = None


def get_candle_buffer() -> CandleBuffer | None:
    """Get the global candle buffer."""
    return _candle_buffer


async def init_candle_buffer(config: BufferConfig | None = None) -> CandleBuffer:
    """Initialize and start the global candle buffer."""
    global _candle_buffer

    if _candle_buffer:
        await _candle_buffer.stop()

    _candle_buffer = CandleBuffer(config)
    await _candle_buffer.start()
    return _candle_buffer


async def stop_candle_buffer() -> None:
    """Stop the global candle buffer."""
    global _candle_buffer

    if _candle_buffer:
        await _candle_buffer.stop()
        _candle_buffer = None
