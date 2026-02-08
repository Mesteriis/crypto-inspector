"""
Pytest configuration and fixtures for E2E tests.

Наследует базовые фикстуры из корневого conftest.py и добавляет
специфичные для E2E тестирования.
"""

import os
import random
import sys
from datetime import UTC, datetime, timedelta

import pytest

# Add src to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

# Маркер для всех E2E тестов
pytestmark = [pytest.mark.e2e]


@pytest.fixture
def bullish_candles() -> list[dict]:
    """Generate bullish trending candle data."""

    candles = []
    base_price = 40000
    start_date = datetime.now(UTC) - timedelta(days=300)

    for i in range(300):
        # Strong upward bias
        daily_return = random.gauss(0.004, 0.015)
        base_price *= 1 + daily_return

        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)

        candles.append(
            {
                "timestamp": ts,
                "open": round(base_price * random.uniform(0.995, 1.005), 2),
                "high": round(base_price * random.uniform(1.0, 1.025), 2),
                "low": round(base_price * random.uniform(0.975, 1.0), 2),
                "close": round(base_price, 2),
                "volume": random.uniform(1000, 5000),
            }
        )

    return candles


@pytest.fixture
def bearish_candles() -> list[dict]:
    """Generate bearish trending candle data."""

    candles = []
    base_price = 60000
    start_date = datetime.now(UTC) - timedelta(days=300)

    for i in range(300):
        # Strong downward bias
        daily_return = random.gauss(-0.003, 0.015)
        base_price *= 1 + daily_return

        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)

        candles.append(
            {
                "timestamp": ts,
                "open": round(base_price * random.uniform(0.995, 1.005), 2),
                "high": round(base_price * random.uniform(1.0, 1.025), 2),
                "low": round(base_price * random.uniform(0.975, 1.0), 2),
                "close": round(base_price, 2),
                "volume": random.uniform(1000, 5000),
            }
        )

    return candles


@pytest.fixture
def rsi_oversold_candles() -> list[dict]:
    """Generate candles that create RSI oversold conditions."""

    candles = []
    base_price = 50000
    start_date = datetime.now(UTC) - timedelta(days=100)

    # Phase 1: Sharp selloff (30 days)
    for i in range(30):
        daily_return = random.gauss(-0.025, 0.01)
        base_price *= 1 + daily_return
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        candles.append(_make_candle(ts, base_price))

    # Phase 2: Recovery (70 days)
    for i in range(30, 100):
        daily_return = random.gauss(0.01, 0.02)
        base_price *= 1 + daily_return
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        candles.append(_make_candle(ts, base_price))

    return candles


@pytest.fixture
def golden_cross_candles() -> list[dict]:
    """Generate candles with golden cross pattern."""

    candles = []
    base_price = 50000
    start_date = datetime.now(UTC) - timedelta(days=300)

    # Phase 1: Downtrend (100 days)
    for i in range(100):
        daily_return = random.gauss(-0.003, 0.015)
        base_price *= 1 + daily_return
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        candles.append(_make_candle(ts, base_price))

    # Phase 2: Consolidation (50 days)
    for i in range(100, 150):
        daily_return = random.gauss(0.001, 0.01)
        base_price *= 1 + daily_return
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        candles.append(_make_candle(ts, base_price))

    # Phase 3: Uptrend (150 days)
    for i in range(150, 300):
        daily_return = random.gauss(0.004, 0.015)
        base_price *= 1 + daily_return
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        candles.append(_make_candle(ts, base_price))

    return candles


def _make_candle(timestamp: int, close: float) -> dict:
    """Helper to create a candle dict."""

    open_price = close * random.uniform(0.995, 1.005)
    high = max(open_price, close) * random.uniform(1.0, 1.015)
    low = min(open_price, close) * random.uniform(0.985, 1.0)

    return {
        "timestamp": timestamp,
        "open": round(open_price, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "close": round(close, 2),
        "volume": random.uniform(1000, 5000),
    }


@pytest.fixture
def data_loader():
    """Create a HistoricalDataLoader instance."""
    from tests.e2e.framework.data_loader import HistoricalDataLoader

    return HistoricalDataLoader()


@pytest.fixture
def signal_validator():
    """Create a SignalValidator instance."""
    from tests.e2e.framework.signal_validator import SignalValidator

    return SignalValidator()


@pytest.fixture
def backtest_config():
    """Create a default BacktestConfig."""
    from tests.e2e.framework.backtest_runner import BacktestConfig

    return BacktestConfig(
        symbol="BTC/USDT",
        interval="1d",
        signal_frequency_days=7,
        outcome_window_days=7,
        min_candles_for_analysis=200,
    )


@pytest.fixture
def backtest_runner(backtest_config):
    """Create a BacktestRunner instance."""
    from tests.e2e.framework.backtest_runner import BacktestRunner

    return BacktestRunner(config=backtest_config)
