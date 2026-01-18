"""
Traditional Assets Backfill Service.

Backfills historical data for traditional assets:
- Metals (Gold, Silver, Platinum)
- Indices (S&P 500, NASDAQ, Dow Jones, DAX)
- Forex (EUR/USD, GBP/USD, DXY)
- Commodities (Oil Brent, WTI, Natural Gas)

Uses Yahoo Finance API via yfinance library.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from db.session import async_session_maker

logger = logging.getLogger(__name__)

# Yahoo Finance tickers for traditional assets
TRADITIONAL_ASSETS = {
    # Metals
    "GOLD": {
        "yahoo": "GC=F",
        "name": "Gold",
        "asset_type": "metal",
    },
    "SILVER": {
        "yahoo": "SI=F",
        "name": "Silver",
        "asset_type": "metal",
    },
    "PLATINUM": {
        "yahoo": "PL=F",
        "name": "Platinum",
        "asset_type": "metal",
    },
    # Indices
    "SP500": {
        "yahoo": "^GSPC",
        "name": "S&P 500",
        "asset_type": "index",
    },
    "NASDAQ": {
        "yahoo": "^IXIC",
        "name": "NASDAQ",
        "asset_type": "index",
    },
    "DJI": {
        "yahoo": "^DJI",
        "name": "Dow Jones",
        "asset_type": "index",
    },
    "DAX": {
        "yahoo": "^GDAXI",
        "name": "DAX",
        "asset_type": "index",
    },
    # Forex
    "EUR_USD": {
        "yahoo": "EURUSD=X",
        "name": "EUR/USD",
        "asset_type": "forex",
    },
    "GBP_USD": {
        "yahoo": "GBPUSD=X",
        "name": "GBP/USD",
        "asset_type": "forex",
    },
    "USD_JPY": {
        "yahoo": "USDJPY=X",
        "name": "USD/JPY",
        "asset_type": "forex",
    },
    "DXY": {
        "yahoo": "DX-Y.NYB",
        "name": "Dollar Index",
        "asset_type": "forex",
    },
    # Commodities
    "OIL_BRENT": {
        "yahoo": "BZ=F",
        "name": "Brent Oil",
        "asset_type": "commodity",
    },
    "OIL_WTI": {
        "yahoo": "CL=F",
        "name": "WTI Oil",
        "asset_type": "commodity",
    },
    "NATURAL_GAS": {
        "yahoo": "NG=F",
        "name": "Natural Gas",
        "asset_type": "commodity",
    },
}


class TraditionalBackfill:
    """
    Traditional assets backfill service.

    Uses yfinance to fetch historical OHLCV data.
    """

    def __init__(self):
        self._yf = None
        self._progress: dict[str, dict] = {}

    def _get_yfinance(self):
        """Lazy import yfinance."""
        if self._yf is None:
            try:
                import yfinance as yf

                self._yf = yf
            except ImportError:
                logger.error("yfinance not installed. Run: pip install yfinance")
                raise
        return self._yf

    async def count_records(self, symbol: str) -> int:
        """Count existing records for a symbol."""
        async with async_session_maker() as session:
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM traditional_asset_records
                    WHERE symbol = :symbol
                """),
                {"symbol": symbol},
            )
            return result.scalar_one() or 0

    async def get_latest_timestamp(self, symbol: str) -> int | None:
        """Get latest timestamp for a symbol."""
        async with async_session_maker() as session:
            result = await session.execute(
                text("""
                    SELECT MAX(timestamp) FROM traditional_asset_records
                    WHERE symbol = :symbol
                """),
                {"symbol": symbol},
            )
            return result.scalar_one_or_none()

    async def backfill_asset(
        self,
        symbol: str,
        years: int = 1,
        progress_callback=None,
    ) -> int:
        """
        Backfill historical data for a traditional asset.

        Args:
            symbol: Asset symbol (e.g., GOLD, SP500)
            years: Years of history to fetch
            progress_callback: Optional callback(symbol, progress_pct, total_records)

        Returns:
            Total number of records saved
        """
        if symbol not in TRADITIONAL_ASSETS:
            logger.error(f"Unknown asset: {symbol}")
            return 0

        config = TRADITIONAL_ASSETS[symbol]
        yahoo_ticker = config["yahoo"]
        asset_type = config["asset_type"]

        logger.info(f"Starting backfill for {symbol} ({config['name']}) - {years} year(s)")

        try:
            yf = self._get_yfinance()

            # Calculate date range
            end_date = datetime.now(UTC)
            start_date = end_date - timedelta(days=years * 365)

            # Fetch data from Yahoo Finance (sync call, run in executor)
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(yahoo_ticker)

            # Run the blocking call in a thread pool
            df = await loop.run_in_executor(
                None,
                lambda: ticker.history(
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    interval="1d",
                ),
            )

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return 0

            # Save to database
            total_records = 0
            async with async_session_maker() as session:
                for idx, row in df.iterrows():
                    timestamp = int(idx.timestamp() * 1000)

                    stmt = text("""
                        INSERT INTO traditional_asset_records
                        (asset_type, symbol, timestamp, open_price, high_price,
                         low_price, close_price, volume, loaded_at)
                        VALUES (:asset_type, :symbol, :timestamp, :open_price,
                                :high_price, :low_price, :close_price, :volume, :loaded_at)
                        ON CONFLICT (symbol, timestamp)
                        DO UPDATE SET
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume,
                            loaded_at = EXCLUDED.loaded_at
                    """)

                    await session.execute(
                        stmt,
                        {
                            "asset_type": asset_type,
                            "symbol": symbol,
                            "timestamp": timestamp,
                            "open_price": float(row["Open"]) if row["Open"] else None,
                            "high_price": float(row["High"]) if row["High"] else None,
                            "low_price": float(row["Low"]) if row["Low"] else None,
                            "close_price": float(row["Close"]) if row["Close"] else None,
                            "volume": float(row["Volume"]) if row.get("Volume") else None,
                            "loaded_at": datetime.now(UTC),
                        },
                    )
                    total_records += 1

                await session.commit()

            if progress_callback:
                progress_callback(symbol, 100, total_records)

            logger.info(f"Backfill complete: {symbol} - {total_records} records")
            return total_records

        except Exception as e:
            logger.error(f"Error backfilling {symbol}: {e}")
            return 0

    async def backfill_all(
        self,
        years: int = 1,
        asset_types: list[str] | None = None,
    ) -> dict[str, int]:
        """
        Backfill all traditional assets.

        Args:
            years: Years of history to fetch
            asset_types: Filter by asset types (metal, index, forex, commodity)

        Returns:
            Dict of {symbol: record_count}
        """
        results = {}

        for symbol, config in TRADITIONAL_ASSETS.items():
            # Filter by asset type if specified
            if asset_types and config["asset_type"] not in asset_types:
                continue

            count = await self.backfill_asset(symbol, years=years)
            results[symbol] = count

            # Small delay between assets
            await asyncio.sleep(0.5)

        total = sum(results.values())
        logger.info(f"Traditional backfill complete: {total} total records")

        return results

    @property
    def progress(self) -> dict:
        """Get current backfill progress."""
        return self._progress.copy()


# Global instance
_traditional_backfill: TraditionalBackfill | None = None


def get_traditional_backfill() -> TraditionalBackfill:
    """Get or create traditional backfill instance."""
    global _traditional_backfill
    if _traditional_backfill is None:
        _traditional_backfill = TraditionalBackfill()
    return _traditional_backfill
