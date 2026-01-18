"""Repository for candlestick database operations."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.candlestick import CandlestickRecord
from services.candlestick.models import FetchResult

logger = logging.getLogger(__name__)


class CandlestickRepository:
    """Repository for candlestick CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_candlesticks(
        self,
        result: FetchResult,
        is_complete: bool = True,
    ) -> int:
        """
        Upsert candlesticks from fetch result into database.

        Uses INSERT ... ON CONFLICT DO UPDATE to handle duplicates.

        Args:
            result: FetchResult containing candlesticks and metadata.
            is_complete: Whether these candles are complete (closed).

        Returns:
            Number of records upserted.
        """
        if not result.candlesticks:
            return 0

        records = []
        for candle in result.candlesticks:
            records.append(
                {
                    "exchange": result.exchange,
                    "symbol": result.symbol,
                    "interval": result.interval.value,
                    "timestamp": candle.timestamp,
                    "open_price": candle.open_price,
                    "high_price": candle.high_price,
                    "low_price": candle.low_price,
                    "close_price": candle.close_price,
                    "volume": candle.volume,
                    "quote_volume": candle.quote_volume,
                    "trades_count": candle.trades_count,
                    "fetch_time_ms": result.fetch_time_ms,
                    "is_complete": is_complete,
                    "loaded_at": datetime.now(UTC),
                }
            )

        # Detect database type and use appropriate insert
        dialect = self.session.bind.dialect.name if self.session.bind else "sqlite"

        if dialect == "postgresql":
            stmt = pg_insert(CandlestickRecord).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["exchange", "symbol", "interval", "timestamp"],
                set_={
                    "open_price": stmt.excluded.open_price,
                    "high_price": stmt.excluded.high_price,
                    "low_price": stmt.excluded.low_price,
                    "close_price": stmt.excluded.close_price,
                    "volume": stmt.excluded.volume,
                    "quote_volume": stmt.excluded.quote_volume,
                    "trades_count": stmt.excluded.trades_count,
                    "fetch_time_ms": stmt.excluded.fetch_time_ms,
                    "is_complete": stmt.excluded.is_complete,
                    "loaded_at": stmt.excluded.loaded_at,
                },
            )
        else:
            # SQLite
            stmt = sqlite_insert(CandlestickRecord).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["exchange", "symbol", "interval", "timestamp"],
                set_={
                    "open_price": stmt.excluded.open_price,
                    "high_price": stmt.excluded.high_price,
                    "low_price": stmt.excluded.low_price,
                    "close_price": stmt.excluded.close_price,
                    "volume": stmt.excluded.volume,
                    "quote_volume": stmt.excluded.quote_volume,
                    "trades_count": stmt.excluded.trades_count,
                    "fetch_time_ms": stmt.excluded.fetch_time_ms,
                    "is_complete": stmt.excluded.is_complete,
                    "loaded_at": stmt.excluded.loaded_at,
                },
            )

        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(
            f"Upserted {len(records)} candlesticks for "
            f"{result.symbol} {result.interval.value} from {result.exchange}"
        )

        return len(records)

    async def get_latest_timestamp(
        self,
        symbol: str,
        interval: str,
    ) -> int | None:
        """
        Get the latest candlestick timestamp for a symbol/interval.

        Args:
            symbol: Trading pair symbol.
            interval: Candlestick interval.

        Returns:
            Latest timestamp in milliseconds, or None if no data.
        """
        stmt = (
            select(CandlestickRecord.timestamp)
            .where(
                CandlestickRecord.symbol == symbol,
                CandlestickRecord.interval == interval,
            )
            .order_by(CandlestickRecord.timestamp.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def get_candlesticks(
        self,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[CandlestickRecord]:
        """
        Get candlesticks from database.

        Args:
            symbol: Trading pair symbol.
            interval: Candlestick interval.
            start_time: Start timestamp in milliseconds.
            end_time: End timestamp in milliseconds.
            limit: Maximum records to return.

        Returns:
            List of CandlestickRecord objects.
        """
        stmt = (
            select(CandlestickRecord)
            .where(
                CandlestickRecord.symbol == symbol,
                CandlestickRecord.interval == interval,
            )
            .order_by(CandlestickRecord.timestamp.desc())
            .limit(limit)
        )

        if start_time:
            stmt = stmt.where(CandlestickRecord.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(CandlestickRecord.timestamp <= end_time)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_candlesticks(
        self,
        symbol: str | None = None,
        interval: str | None = None,
    ) -> int:
        """Count candlesticks with optional filters."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(CandlestickRecord)

        if symbol:
            stmt = stmt.where(CandlestickRecord.symbol == symbol)
        if interval:
            stmt = stmt.where(CandlestickRecord.interval == interval)

        result = await self.session.execute(stmt)
        return result.scalar_one()
