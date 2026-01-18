"""
Historical Data Loader for E2E Testing.

Loads historical candlestick data from the database or generates synthetic
test data for backtesting validation.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CandleData:
    """Single candle data point."""

    timestamp: int  # Unix ms
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime."""
        return datetime.fromtimestamp(self.timestamp / 1000, tz=UTC)

    def to_dict(self) -> dict:
        """Convert to dictionary format expected by analysis services."""
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass
class BacktestPeriod:
    """
    A test period with input data and known outcomes.

    The signal_date is when we generate our prediction.
    The outcome_window is how long after the signal we measure the outcome.
    """

    name: str
    symbol: str
    signal_date: datetime
    outcome_window_days: int = 7  # Days to measure outcome
    candles: list[CandleData] = field(default_factory=list)

    @property
    def input_candles(self) -> list[dict]:
        """Get candles up to and including signal_date as dicts."""
        signal_ts = int(self.signal_date.timestamp() * 1000)
        return [c.to_dict() for c in self.candles if c.timestamp <= signal_ts]

    @property
    def outcome_candles(self) -> list[dict]:
        """Get candles after signal_date within outcome window."""
        signal_ts = int(self.signal_date.timestamp() * 1000)
        outcome_end_ts = int((self.signal_date + timedelta(days=self.outcome_window_days)).timestamp() * 1000)
        return [c.to_dict() for c in self.candles if signal_ts < c.timestamp <= outcome_end_ts]

    @property
    def signal_price(self) -> float | None:
        """Get the closing price at signal time."""
        signal_ts = int(self.signal_date.timestamp() * 1000)
        for c in self.candles:
            if c.timestamp == signal_ts:
                return c.close
        # Return closest candle before signal
        before_signal = [c for c in self.candles if c.timestamp <= signal_ts]
        if before_signal:
            return before_signal[-1].close
        return None

    @property
    def outcome_price(self) -> float | None:
        """Get the closing price at end of outcome window."""
        outcome = self.outcome_candles
        if outcome:
            return outcome[-1]["close"]
        return None

    @property
    def actual_return_pct(self) -> float | None:
        """Calculate actual return from signal to outcome."""
        if self.signal_price and self.outcome_price:
            return ((self.outcome_price - self.signal_price) / self.signal_price) * 100
        return None

    @property
    def max_gain_pct(self) -> float | None:
        """Calculate maximum gain during outcome period."""
        if not self.signal_price or not self.outcome_candles:
            return None
        max_high = max(c["high"] for c in self.outcome_candles)
        return ((max_high - self.signal_price) / self.signal_price) * 100

    @property
    def max_drawdown_pct(self) -> float | None:
        """Calculate maximum drawdown during outcome period."""
        if not self.signal_price or not self.outcome_candles:
            return None
        min_low = min(c["low"] for c in self.outcome_candles)
        return ((self.signal_price - min_low) / self.signal_price) * 100


class HistoricalDataLoader:
    """
    Loads historical data for backtesting.

    Supports:
    - Loading from database
    - Loading from CSV files
    - Generating synthetic test data
    """

    def __init__(self):
        self._cache: dict[str, list[CandleData]] = {}

    async def load_from_database(
        self,
        symbol: str,
        interval: str = "1d",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 1000,
    ) -> list[CandleData]:
        """
        Load historical candles from database.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            interval: Candle interval
            start_date: Start of period
            end_date: End of period
            limit: Maximum candles to load

        Returns:
            List of CandleData objects
        """
        from sqlalchemy import text

        from db.session import async_session_maker

        query_params: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }

        conditions = ["symbol = :symbol", "interval = :interval"]

        if start_date:
            query_params["start_ts"] = int(start_date.timestamp() * 1000)
            conditions.append("timestamp >= :start_ts")

        if end_date:
            query_params["end_ts"] = int(end_date.timestamp() * 1000)
            conditions.append("timestamp <= :end_ts")

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT timestamp, open_price, high_price, low_price, close_price, volume
            FROM candlestick_records
            WHERE {where_clause}
            ORDER BY timestamp ASC
            LIMIT :limit
        """)

        candles: list[CandleData] = []

        try:
            async with async_session_maker() as session:
                result = await session.execute(query, query_params)
                rows = result.fetchall()

                for row in rows:
                    candles.append(
                        CandleData(
                            timestamp=row[0],
                            open=float(row[1]),
                            high=float(row[2]),
                            low=float(row[3]),
                            close=float(row[4]),
                            volume=float(row[5]) if row[5] else 0,
                        )
                    )

            logger.info(f"Loaded {len(candles)} candles for {symbol} {interval}")
            self._cache[f"{symbol}_{interval}"] = candles

        except Exception as e:
            logger.error(f"Failed to load data from database: {e}")
            raise

        return candles

    def load_from_list(self, data: list[dict]) -> list[CandleData]:
        """
        Load candles from a list of dictionaries.

        Args:
            data: List of candle dicts with timestamp, open, high, low, close, volume

        Returns:
            List of CandleData objects
        """
        candles = []
        for row in data:
            candles.append(
                CandleData(
                    timestamp=row.get("timestamp", 0),
                    open=float(row.get("open", row.get("open_price", 0))),
                    high=float(row.get("high", row.get("high_price", 0))),
                    low=float(row.get("low", row.get("low_price", 0))),
                    close=float(row.get("close", row.get("close_price", 0))),
                    volume=float(row.get("volume", 0)),
                )
            )
        return candles

    def create_test_period(
        self,
        name: str,
        symbol: str,
        candles: list[CandleData],
        signal_date: datetime,
        outcome_window_days: int = 7,
    ) -> BacktestPeriod:
        """
        Create a test period from candle data.

        Args:
            name: Descriptive name for the test period
            symbol: Trading pair symbol
            candles: Full historical candles
            signal_date: Date when signal is generated
            outcome_window_days: Days to measure outcome

        Returns:
            BacktestPeriod object
        """
        return BacktestPeriod(
            name=name,
            symbol=symbol,
            signal_date=signal_date,
            outcome_window_days=outcome_window_days,
            candles=candles,
        )

    def generate_synthetic_bullish_period(
        self,
        base_price: float = 50000,
        days: int = 200,
        start_date: datetime | None = None,
    ) -> list[CandleData]:
        """
        Generate synthetic bullish market data for testing.

        Creates data where price trends upward with realistic noise.
        """
        import random

        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=days)

        candles = []
        price = base_price

        for i in range(days):
            # Upward bias with noise
            daily_return = random.gauss(0.003, 0.02)  # 0.3% daily gain avg
            price *= 1 + daily_return

            # Generate OHLC
            open_price = price * random.uniform(0.995, 1.005)
            high = price * random.uniform(1.0, 1.02)
            low = price * random.uniform(0.98, 1.0)
            close = price

            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            ts = int((start_date + timedelta(days=i)).timestamp() * 1000)

            candles.append(
                CandleData(
                    timestamp=ts,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=random.uniform(1000, 5000),
                )
            )

        return candles

    def generate_synthetic_bearish_period(
        self,
        base_price: float = 50000,
        days: int = 200,
        start_date: datetime | None = None,
    ) -> list[CandleData]:
        """
        Generate synthetic bearish market data for testing.

        Creates data where price trends downward with realistic noise.
        """
        import random

        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=days)

        candles = []
        price = base_price

        for i in range(days):
            # Downward bias with noise
            daily_return = random.gauss(-0.002, 0.02)  # -0.2% daily avg
            price *= 1 + daily_return

            # Generate OHLC
            open_price = price * random.uniform(0.995, 1.005)
            high = price * random.uniform(1.0, 1.02)
            low = price * random.uniform(0.98, 1.0)
            close = price

            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            ts = int((start_date + timedelta(days=i)).timestamp() * 1000)

            candles.append(
                CandleData(
                    timestamp=ts,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=random.uniform(1000, 5000),
                )
            )

        return candles

    def generate_golden_cross_scenario(
        self,
        base_price: float = 50000,
        start_date: datetime | None = None,
    ) -> tuple[list[CandleData], datetime]:
        """
        Generate data with a golden cross pattern.

        Returns:
            Tuple of (candles, golden_cross_date)
        """
        import random

        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=300)

        candles = []
        price = base_price

        # Phase 1: Downtrend (100 days)
        for i in range(100):
            daily_return = random.gauss(-0.003, 0.015)
            price *= 1 + daily_return

            ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
            candles.append(self._make_candle(ts, price))

        # Phase 2: Consolidation (50 days)
        for i in range(100, 150):
            daily_return = random.gauss(0.001, 0.01)
            price *= 1 + daily_return

            ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
            candles.append(self._make_candle(ts, price))

        # Golden cross occurs around day 150
        golden_cross_date = start_date + timedelta(days=150)

        # Phase 3: Uptrend (100 days post golden cross)
        for i in range(150, 250):
            daily_return = random.gauss(0.004, 0.015)
            price *= 1 + daily_return

            ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
            candles.append(self._make_candle(ts, price))

        return candles, golden_cross_date

    def generate_rsi_oversold_scenario(
        self,
        base_price: float = 50000,
        start_date: datetime | None = None,
    ) -> tuple[list[CandleData], datetime]:
        """
        Generate data with RSI reaching oversold levels and bouncing.

        Returns:
            Tuple of (candles, oversold_date)
        """
        import random

        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=100)

        candles = []
        price = base_price

        # Phase 1: Sharp selloff to create oversold (30 days)
        for i in range(30):
            daily_return = random.gauss(-0.025, 0.01)  # Strong down
            price *= 1 + daily_return

            ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
            candles.append(self._make_candle(ts, price))

        # RSI oversold point
        oversold_date = start_date + timedelta(days=30)

        # Phase 2: Recovery bounce (70 days)
        for i in range(30, 100):
            daily_return = random.gauss(0.01, 0.02)
            price *= 1 + daily_return

            ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
            candles.append(self._make_candle(ts, price))

        return candles, oversold_date

    def _make_candle(self, timestamp: int, close: float) -> CandleData:
        """Create a candle from close price with realistic OHLC."""
        import random

        open_price = close * random.uniform(0.995, 1.005)
        high = max(open_price, close) * random.uniform(1.0, 1.015)
        low = min(open_price, close) * random.uniform(0.985, 1.0)

        return CandleData(
            timestamp=timestamp,
            open=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=random.uniform(1000, 5000),
        )
