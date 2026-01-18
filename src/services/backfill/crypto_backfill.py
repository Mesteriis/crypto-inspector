"""
Crypto Candlestick Backfill Service.

Backfills historical candlestick data for cryptocurrencies.
- Supports up to 10 years of history
- Uses existing CandlestickFetcher with pagination
- Rate limiting to avoid API bans
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import text

from db.session import async_session_maker
from services.candlestick.fetcher import CandlestickFetcher
from services.candlestick.models import CandleInterval

logger = logging.getLogger(__name__)

# Interval to milliseconds mapping
INTERVAL_MS = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,
}

# Rate limiting
BATCH_DELAY_SECONDS = 0.5
MAX_CANDLES_PER_REQUEST = 1000


class CryptoBackfill:
    """
    Crypto candlestick backfill service.

    Fetches and stores historical candlestick data.
    """

    def __init__(self):
        self._fetcher: CandlestickFetcher | None = None
        self._is_running = False
        self._progress: dict[str, dict] = {}

    def _get_fetcher(self) -> CandlestickFetcher:
        """Get or create fetcher instance."""
        if self._fetcher is None:
            self._fetcher = CandlestickFetcher(timeout=30.0)
        return self._fetcher

    async def get_earliest_timestamp(
        self,
        symbol: str,
        interval: str,
    ) -> int | None:
        """
        Get earliest candlestick timestamp in database.

        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            interval: Candle interval

        Returns:
            Earliest timestamp in ms or None
        """
        async with async_session_maker() as session:
            result = await session.execute(
                text("""
                    SELECT MIN(timestamp) FROM candlestick_records
                    WHERE symbol = :symbol AND interval = :interval
                """),
                {"symbol": symbol, "interval": interval},
            )
            row = result.scalar_one_or_none()
            return row

    async def get_latest_timestamp(
        self,
        symbol: str,
        interval: str,
    ) -> int | None:
        """
        Get latest candlestick timestamp in database.

        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            interval: Candle interval

        Returns:
            Latest timestamp in ms or None
        """
        async with async_session_maker() as session:
            result = await session.execute(
                text("""
                    SELECT MAX(timestamp) FROM candlestick_records
                    WHERE symbol = :symbol AND interval = :interval
                """),
                {"symbol": symbol, "interval": interval},
            )
            row = result.scalar_one_or_none()
            return row

    async def count_candles(
        self,
        symbol: str,
        interval: str,
    ) -> int:
        """Count existing candles for symbol/interval."""
        async with async_session_maker() as session:
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM candlestick_records
                    WHERE symbol = :symbol AND interval = :interval
                """),
                {"symbol": symbol, "interval": interval},
            )
            return result.scalar_one() or 0

    async def backfill_symbol(
        self,
        symbol: str,
        interval: str,
        years: int = 10,
        progress_callback=None,
    ) -> int:
        """
        Backfill historical data for a symbol.

        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            interval: Candle interval (e.g., 1d, 4h, 1h)
            years: Years of history to fetch
            progress_callback: Optional callback(symbol, interval, progress_pct, total_candles)

        Returns:
            Total number of candles saved
        """
        logger.info(f"Starting backfill for {symbol} {interval} ({years} years)")

        try:
            interval_enum = CandleInterval(interval)
        except ValueError:
            logger.error(f"Invalid interval: {interval}")
            return 0

        interval_ms = INTERVAL_MS.get(interval, 86400000)

        # Calculate start time (years ago)
        start_date = datetime.utcnow() - timedelta(days=years * 365)
        start_time = int(start_date.timestamp() * 1000)
        end_time = int(datetime.utcnow().timestamp() * 1000)

        # Check if we already have data
        earliest = await self.get_earliest_timestamp(symbol, interval)
        if earliest and earliest <= start_time:
            logger.info(f"{symbol} {interval}: Data already exists from {datetime.fromtimestamp(earliest/1000)}")
            # Just update recent candles
            return await self._update_recent(symbol, interval, interval_enum)

        # Backfill from start
        total_candles = 0
        current_start = start_time
        batch_num = 0

        fetcher = self._get_fetcher()

        while current_start < end_time:
            batch_num += 1

            try:
                result = await fetcher.fetch(
                    symbol=symbol,
                    interval=interval_enum,
                    limit=MAX_CANDLES_PER_REQUEST,
                    start_time=current_start,
                )

                if result.is_empty:
                    logger.warning(f"No data for {symbol} starting from {datetime.fromtimestamp(current_start/1000)}")
                    # Move forward by batch size
                    current_start += interval_ms * MAX_CANDLES_PER_REQUEST
                    continue

                # Save to database
                count = await self._save_candles(result)
                total_candles += count

                # Move to next batch
                if result.candlesticks:
                    last_ts = max(c.timestamp for c in result.candlesticks)
                    current_start = last_ts + interval_ms
                else:
                    current_start += interval_ms * MAX_CANDLES_PER_REQUEST

                # Progress callback
                if progress_callback:
                    progress = min(100, int((current_start - start_time) / (end_time - start_time) * 100))
                    progress_callback(symbol, interval, progress, total_candles)

                logger.debug(f"Batch {batch_num}: {count} candles, total {total_candles}")

                # Rate limiting
                await asyncio.sleep(BATCH_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"Error fetching {symbol} {interval} batch {batch_num}: {e}")
                # Continue to next batch
                current_start += interval_ms * MAX_CANDLES_PER_REQUEST
                await asyncio.sleep(1.0)  # Extra delay on error

        logger.info(f"Backfill complete: {symbol} {interval} - {total_candles} candles")
        return total_candles

    async def _update_recent(
        self,
        symbol: str,
        interval: str,
        interval_enum: CandleInterval,
    ) -> int:
        """Update recent candles only."""
        fetcher = self._get_fetcher()

        try:
            result = await fetcher.fetch(
                symbol=symbol,
                interval=interval_enum,
                limit=100,
            )

            if not result.is_empty:
                return await self._save_candles(result)

        except Exception as e:
            logger.error(f"Error updating recent {symbol} {interval}: {e}")

        return 0

    async def _save_candles(self, result) -> int:
        """Save candlesticks to database."""
        if not result.candlesticks:
            return 0

        async with async_session_maker() as session:
            for candle in result.candlesticks:
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
                        is_complete = EXCLUDED.is_complete,
                        loaded_at = EXCLUDED.loaded_at
                """)
                await session.execute(
                    stmt,
                    {
                        "exchange": result.exchange,
                        "symbol": result.symbol,
                        "interval": result.interval.value,
                        "timestamp": candle.timestamp,
                        "open_price": float(candle.open_price),
                        "high_price": float(candle.high_price),
                        "low_price": float(candle.low_price),
                        "close_price": float(candle.close_price),
                        "volume": float(candle.volume),
                        "quote_volume": float(candle.quote_volume) if candle.quote_volume else None,
                        "trades_count": candle.trades_count,
                        "fetch_time_ms": result.fetch_time_ms,
                        "is_complete": True,
                        "loaded_at": datetime.utcnow(),
                    },
                )
            await session.commit()

        return len(result.candlesticks)

    async def detect_gaps(
        self,
        symbol: str,
        interval: str,
        max_gap_ratio: float = 2.0,
    ) -> list[tuple[int, int]]:
        """
        Detect gaps in historical data.

        Args:
            symbol: Trading pair
            interval: Candle interval
            max_gap_ratio: Gap threshold as multiple of interval

        Returns:
            List of (gap_start, gap_end) tuples
        """
        interval_ms = INTERVAL_MS.get(interval, 86400000)
        max_gap = int(interval_ms * max_gap_ratio)

        async with async_session_maker() as session:
            result = await session.execute(
                text("""
                    SELECT timestamp FROM candlestick_records
                    WHERE symbol = :symbol AND interval = :interval
                    ORDER BY timestamp ASC
                """),
                {"symbol": symbol, "interval": interval},
            )
            timestamps = [row[0] for row in result.fetchall()]

        if len(timestamps) < 2:
            return []

        gaps = []
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i - 1]
            if gap > max_gap:
                gaps.append((timestamps[i - 1], timestamps[i]))

        return gaps

    async def fill_gaps(
        self,
        symbol: str,
        interval: str,
        gaps: list[tuple[int, int]],
    ) -> int:
        """
        Fill detected gaps with historical data.

        Args:
            symbol: Trading pair
            interval: Candle interval
            gaps: List of (gap_start, gap_end) tuples

        Returns:
            Total candles filled
        """
        if not gaps:
            return 0

        try:
            interval_enum = CandleInterval(interval)
        except ValueError:
            return 0

        fetcher = self._get_fetcher()
        total_filled = 0

        for gap_start, gap_end in gaps:
            try:
                result = await fetcher.fetch(
                    symbol=symbol,
                    interval=interval_enum,
                    limit=MAX_CANDLES_PER_REQUEST,
                    start_time=gap_start,
                    end_time=gap_end,
                )

                if not result.is_empty:
                    count = await self._save_candles(result)
                    total_filled += count
                    logger.info(f"Filled gap for {symbol} {interval}: {count} candles")

                await asyncio.sleep(BATCH_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"Error filling gap for {symbol} {interval}: {e}")

        return total_filled

    @property
    def progress(self) -> dict:
        """Get current backfill progress."""
        return self._progress.copy()


# Global instance
_crypto_backfill: CryptoBackfill | None = None


def get_crypto_backfill() -> CryptoBackfill:
    """Get or create crypto backfill instance."""
    global _crypto_backfill
    if _crypto_backfill is None:
        _crypto_backfill = CryptoBackfill()
    return _crypto_backfill
