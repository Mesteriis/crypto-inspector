"""
Traditional Assets Backfill Service.

Backfills historical data for traditional assets:
- Metals (Gold, Silver, Platinum)
- Indices (S&P 500, NASDAQ, Dow Jones, DAX)
- Forex (EUR/USD, GBP/USD, DXY)
- Commodities (Oil Brent, WTI, Natural Gas)

Data sources (with fallback):
1. Yahoo Finance via yfinance
2. Stooq.com (free, no API key)
3. FRED (for some economic indicators)
"""

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd
from sqlalchemy import text

from models.session import async_session_maker

logger = logging.getLogger(__name__)

# Yahoo Finance tickers for traditional assets
# Format: symbol -> {yahoo, stooq, name, asset_type}
TRADITIONAL_ASSETS = {
    # Metals
    "GOLD": {
        "yahoo": "GC=F",
        "stooq": "xauusd",  # Spot gold price
        "name": "Gold",
        "asset_type": "metal",
    },
    "SILVER": {
        "yahoo": "SI=F",
        "stooq": "xagusd",  # Spot silver price
        "name": "Silver",
        "asset_type": "metal",
    },
    "PLATINUM": {
        "yahoo": "PL=F",
        "stooq": "xptusd",  # Spot platinum
        "name": "Platinum",
        "asset_type": "metal",
    },
    # Indices
    "SP500": {
        "yahoo": "^GSPC",
        "stooq": "^spx",
        "name": "S&P 500",
        "asset_type": "index",
    },
    "NASDAQ": {
        "yahoo": "^IXIC",
        "stooq": "^ndq",
        "name": "NASDAQ",
        "asset_type": "index",
    },
    "DJI": {
        "yahoo": "^DJI",
        "stooq": "^dji",
        "name": "Dow Jones",
        "asset_type": "index",
    },
    "DAX": {
        "yahoo": "^GDAXI",
        "stooq": "^dax",
        "name": "DAX",
        "asset_type": "index",
    },
    # Forex
    "EUR_USD": {
        "yahoo": "EURUSD=X",
        "stooq": "eurusd",
        "name": "EUR/USD",
        "asset_type": "forex",
    },
    "GBP_USD": {
        "yahoo": "GBPUSD=X",
        "stooq": "gbpusd",
        "name": "GBP/USD",
        "asset_type": "forex",
    },
    "USD_JPY": {
        "yahoo": "USDJPY=X",
        "stooq": "usdjpy",
        "name": "USD/JPY",
        "asset_type": "forex",
    },
    "DXY": {
        "yahoo": "DX-Y.NYB",
        "stooq": "dx.c",  # Dollar Index futures
        "name": "Dollar Index",
        "asset_type": "forex",
    },
    # Commodities - using futures or ETFs on Stooq
    "OIL_BRENT": {
        "yahoo": "BZ=F",
        "stooq": "bno.us",  # Brent Oil ETF
        "name": "Brent Oil",
        "asset_type": "commodity",
    },
    "OIL_WTI": {
        "yahoo": "CL=F",
        "stooq": "cl.c",  # WTI futures
        "name": "WTI Oil",
        "asset_type": "commodity",
    },
    "NATURAL_GAS": {
        "yahoo": "NG=F",
        "stooq": "ng.c",  # Natural gas futures
        "name": "Natural Gas",
        "asset_type": "commodity",
    },
}

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 5.0
MAX_DELAY = 60.0


class TraditionalBackfill:
    """
    Traditional assets backfill service.

    Uses multiple data sources with fallback:
    1. Yahoo Finance (yfinance)
    2. Stooq.com (free CSV API)
    """

    def __init__(self):
        self._yf = None
        self._progress: dict[str, dict] = {}
        self._http_client: httpx.AsyncClient | None = None

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

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for Stooq."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                },
            )
        return self._http_client

    async def _fetch_from_stooq(
        self, stooq_symbol: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """
        Fetch data from Stooq.com (free, no API key needed).

        Stooq URL format:
        https://stooq.com/q/d/l/?s={symbol}&d1={YYYYMMDD}&d2={YYYYMMDD}&i=d

        Returns DataFrame with Date, Open, High, Low, Close, Volume columns.
        """
        client = await self._get_http_client()

        # Format dates for Stooq
        d1 = start_date.strftime("%Y%m%d")
        d2 = end_date.strftime("%Y%m%d")

        url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&d1={d1}&d2={d2}&i=d"

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.get(url)

                if response.status_code == 429:
                    delay = min(BASE_DELAY * (2**attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Stooq rate limited, retrying in {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                content = response.text

                # Parse CSV
                if "No data" in content or len(content.strip()) < 50:
                    logger.warning(f"No data from Stooq for {stooq_symbol}")
                    return pd.DataFrame()

                # Stooq returns CSV: Date,Open,High,Low,Close,Volume
                from io import StringIO

                df = pd.read_csv(StringIO(content))

                if df.empty or "Date" not in df.columns:
                    return pd.DataFrame()

                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)

                logger.info(f"Fetched {len(df)} records from Stooq for {stooq_symbol}")
                return df

            except httpx.HTTPStatusError as e:
                if attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2**attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Stooq HTTP error: {e}, retrying in {delay:.1f}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Stooq fetch failed for {stooq_symbol}: {e}")
                    return pd.DataFrame()
            except Exception as e:
                logger.error(f"Stooq fetch error for {stooq_symbol}: {e}")
                return pd.DataFrame()

        return pd.DataFrame()

    async def _fetch_from_yahoo(
        self, yahoo_ticker: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Fetch data from Yahoo Finance with retry."""
        for attempt in range(MAX_RETRIES):
            try:
                yf = self._get_yfinance()

                loop = asyncio.get_event_loop()
                ticker = yf.Ticker(yahoo_ticker)

                df = await loop.run_in_executor(
                    None,
                    lambda: ticker.history(
                        start=start_date.strftime("%Y-%m-%d"),
                        end=end_date.strftime("%Y-%m-%d"),
                        interval="1d",
                    ),
                )

                if df.empty:
                    if attempt < MAX_RETRIES - 1:
                        delay = min(BASE_DELAY * (2**attempt) + random.uniform(0, 1), MAX_DELAY)
                        logger.warning(
                            f"No Yahoo data for {yahoo_ticker}, attempt {attempt + 1}/{MAX_RETRIES}, "
                            f"retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    return pd.DataFrame()

                logger.info(f"Fetched {len(df)} records from Yahoo for {yahoo_ticker}")
                return df

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2**attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Yahoo error for {yahoo_ticker}: {e}, retrying in {delay:.1f}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Yahoo fetch failed for {yahoo_ticker}: {e}")
                    return pd.DataFrame()

        return pd.DataFrame()

    async def get_history_status(self) -> dict[str, dict[str, str | None]]:
        """
        Get history status for all traditional assets.

        Returns:
            Dict of {symbol: {start: "YYYY-MM-DD", stop: "YYYY-MM-DD"}}
        """
        result = {}
        async with async_session_maker() as session:
            query_result = await session.execute(
                text("""
                    SELECT symbol, MIN(timestamp) as start_ts, MAX(timestamp) as stop_ts
                    FROM traditional_asset_records
                    GROUP BY symbol
                    ORDER BY symbol
                """)
            )
            for row in query_result.fetchall():
                start_ts = row[1]
                stop_ts = row[2]
                result[row[0]] = {
                    "start": datetime.fromtimestamp(start_ts / 1000, tz=UTC).strftime("%Y-%m-%d") if start_ts else None,
                    "stop": datetime.fromtimestamp(stop_ts / 1000, tz=UTC).strftime("%Y-%m-%d") if stop_ts else None,
                }

        # Add missing symbols with None
        for symbol in TRADITIONAL_ASSETS.keys():
            if symbol not in result:
                result[symbol] = {"start": None, "stop": None}

        return result

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

        Tries Yahoo Finance first, falls back to Stooq if needed.

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
        stooq_symbol = config.get("stooq")
        asset_type = config["asset_type"]

        logger.info(f"Starting backfill for {symbol} ({config['name']}) - {years} year(s)")

        # Calculate date range
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=years * 365)

        df = pd.DataFrame()
        data_source = None

        # Try Yahoo Finance first
        try:
            df = await self._fetch_from_yahoo(yahoo_ticker, start_date, end_date)
            if not df.empty:
                data_source = "Yahoo"
        except Exception as e:
            logger.warning(f"Yahoo fetch failed for {symbol}: {e}")

        # Fallback to Stooq if Yahoo failed
        if df.empty and stooq_symbol:
            logger.info(f"Trying Stooq fallback for {symbol}")
            try:
                df = await self._fetch_from_stooq(stooq_symbol, start_date, end_date)
                if not df.empty:
                    data_source = "Stooq"
            except Exception as e:
                logger.warning(f"Stooq fetch failed for {symbol}: {e}")

        if df.empty:
            logger.error(f"All data sources failed for {symbol}")
            return 0

        # Normalize column names (Stooq uses different names)
        column_map = {
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume",
        }

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

                open_col = "Open" if "Open" in row else "open"
                high_col = "High" if "High" in row else "high"
                low_col = "Low" if "Low" in row else "low"
                close_col = "Close" if "Close" in row else "close"
                vol_col = "Volume" if "Volume" in row else "volume"

                await session.execute(
                    stmt,
                    {
                        "asset_type": asset_type,
                        "symbol": symbol,
                        "timestamp": timestamp,
                        "open_price": float(row.get(open_col, 0)) if row.get(open_col) else None,
                        "high_price": float(row.get(high_col, 0)) if row.get(high_col) else None,
                        "low_price": float(row.get(low_col, 0)) if row.get(low_col) else None,
                        "close_price": float(row.get(close_col, 0)) if row.get(close_col) else None,
                        "volume": float(row.get(vol_col, 0)) if row.get(vol_col) else None,
                        "loaded_at": datetime.now(UTC),
                    },
                )
                total_records += 1

            await session.commit()

        if progress_callback:
            progress_callback(symbol, 100, total_records)

        logger.info(f"Backfill complete: {symbol} - {total_records} records from {data_source}")
        return total_records

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

            # Longer delay between assets to avoid rate limiting
            await asyncio.sleep(3.0)

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
