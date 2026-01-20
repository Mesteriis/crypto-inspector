"""
Корневой conftest.py для всех тестов.

Содержит базовые фикстуры и конфигурацию, используемые во всех типах тестов:
- unit/
- integration/
- e2e/
- backtest/
"""

import asyncio
import os
import random
import sys
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from faker import Faker

# Добавляем src в путь для импортов
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, "src"))


# =============================================================================
# FAKER CONFIGURATION
# =============================================================================

@pytest.fixture(scope="session")
def faker() -> Faker:
    """
    Создает Faker инстанс с фиксированным seed для воспроизводимости.
    
    Returns:
        Faker: Инстанс Faker с русской и английской локализацией
    """
    fake = Faker(["ru_RU", "en_US"])
    Faker.seed(42)
    random.seed(42)
    return fake


# =============================================================================
# ASYNC FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Создает event loop для асинхронных тестов.
    
    Scope: session - один loop на весь сеанс тестирования.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# MOCK FIXTURES - БАЗОВЫЕ
# =============================================================================

@pytest.fixture
def mock_async() -> AsyncMock:
    """Создает базовый AsyncMock для асинхронных функций."""
    return AsyncMock()


@pytest.fixture
def mock_sync() -> MagicMock:
    """Создает базовый MagicMock для синхронных функций."""
    return MagicMock()


# =============================================================================
# CRYPTO DATA FIXTURES
# =============================================================================

@pytest.fixture
def crypto_symbols() -> list[str]:
    """Список поддерживаемых криптовалютных пар."""
    return [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "AR/USDT", "TON/USDT",
        "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT"
    ]


@pytest.fixture
def sample_price_data(faker: Faker) -> dict[str, float]:
    """
    Генерирует реалистичные данные о ценах криптовалют.
    
    Returns:
        dict: {symbol: price}
    """
    return {
        "BTC/USDT": faker.pyfloat(min_value=90000, max_value=110000, right_digits=2),
        "ETH/USDT": faker.pyfloat(min_value=3000, max_value=4000, right_digits=2),
        "SOL/USDT": faker.pyfloat(min_value=200, max_value=300, right_digits=2),
        "AR/USDT": faker.pyfloat(min_value=30, max_value=60, right_digits=2),
        "TON/USDT": faker.pyfloat(min_value=5, max_value=10, right_digits=2),
    }


@pytest.fixture
def sample_change_data(faker: Faker) -> dict[str, float]:
    """
    Генерирует данные об изменении цены за 24ч.
    
    Returns:
        dict: {symbol: change_percent}
    """
    return {
        "BTC/USDT": faker.pyfloat(min_value=-10, max_value=10, right_digits=2),
        "ETH/USDT": faker.pyfloat(min_value=-15, max_value=15, right_digits=2),
        "SOL/USDT": faker.pyfloat(min_value=-20, max_value=20, right_digits=2),
        "AR/USDT": faker.pyfloat(min_value=-25, max_value=25, right_digits=2),
        "TON/USDT": faker.pyfloat(min_value=-15, max_value=15, right_digits=2),
    }


# =============================================================================
# CANDLESTICK DATA FIXTURES
# =============================================================================

@pytest.fixture
def candle_factory(faker: Faker):
    """
    Фабрика для создания свечей.
    
    Returns:
        callable: Функция для генерации свечей
    """
    def _create_candle(
        timestamp: int | None = None,
        open_price: float | None = None,
        close_price: float | None = None,
        high_price: float | None = None,
        low_price: float | None = None,
        volume: float | None = None,
    ) -> dict[str, Any]:
        base_price = open_price or faker.pyfloat(min_value=90000, max_value=110000)
        volatility = base_price * 0.02
        
        _open = open_price or base_price
        _close = close_price or (base_price + faker.pyfloat(min_value=-volatility, max_value=volatility))
        _high = high_price or (max(_open, _close) * (1 + faker.pyfloat(min_value=0, max_value=0.015)))
        _low = low_price or (min(_open, _close) * (1 - faker.pyfloat(min_value=0, max_value=0.015)))
        
        return {
            "timestamp": timestamp or int(datetime.now(UTC).timestamp() * 1000),
            "open": round(_open, 2),
            "high": round(_high, 2),
            "low": round(_low, 2),
            "close": round(_close, 2),
            "volume": volume or faker.pyfloat(min_value=1000, max_value=5000),
        }
    
    return _create_candle


@pytest.fixture
def sample_candles(candle_factory) -> list[dict]:
    """
    Генерирует список свечей для тестирования (300 дней).
    
    Returns:
        list[dict]: Список свечей
    """
    candles = []
    base_price = 50000
    start_date = datetime.now(UTC) - timedelta(days=300)
    
    for i in range(300):
        daily_return = random.gauss(0.001, 0.02)
        base_price *= (1 + daily_return)
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        candles.append(candle_factory(timestamp=ts, open_price=base_price))
    
    return candles


@pytest.fixture
def bullish_candles() -> list[dict]:
    """Генерирует свечи с бычьим трендом."""
    candles = []
    base_price = 40000
    start_date = datetime.now(UTC) - timedelta(days=300)
    
    for i in range(300):
        daily_return = random.gauss(0.004, 0.015)  # Сильный бычий bias
        base_price *= (1 + daily_return)
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        
        candles.append({
            "timestamp": ts,
            "open": round(base_price * random.uniform(0.995, 1.005), 2),
            "high": round(base_price * random.uniform(1.0, 1.025), 2),
            "low": round(base_price * random.uniform(0.975, 1.0), 2),
            "close": round(base_price, 2),
            "volume": random.uniform(1000, 5000),
        })
    
    return candles


@pytest.fixture
def bearish_candles() -> list[dict]:
    """Генерирует свечи с медвежьим трендом."""
    candles = []
    base_price = 60000
    start_date = datetime.now(UTC) - timedelta(days=300)
    
    for i in range(300):
        daily_return = random.gauss(-0.003, 0.015)  # Медвежий bias
        base_price *= (1 + daily_return)
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        
        candles.append({
            "timestamp": ts,
            "open": round(base_price * random.uniform(0.995, 1.005), 2),
            "high": round(base_price * random.uniform(1.0, 1.025), 2),
            "low": round(base_price * random.uniform(0.975, 1.0), 2),
            "close": round(base_price, 2),
            "volume": random.uniform(1000, 5000),
        })
    
    return candles


@pytest.fixture
def sideways_candles() -> list[dict]:
    """Генерирует свечи с боковым движением."""
    candles = []
    base_price = 50000
    start_date = datetime.now(UTC) - timedelta(days=300)
    
    for i in range(300):
        daily_return = random.gauss(0, 0.01)  # Нет bias
        base_price *= (1 + daily_return)
        # Держим цену в диапазоне
        base_price = max(45000, min(55000, base_price))
        ts = int((start_date + timedelta(days=i)).timestamp() * 1000)
        
        candles.append({
            "timestamp": ts,
            "open": round(base_price * random.uniform(0.995, 1.005), 2),
            "high": round(base_price * random.uniform(1.0, 1.015), 2),
            "low": round(base_price * random.uniform(0.985, 1.0), 2),
            "close": round(base_price, 2),
            "volume": random.uniform(1000, 5000),
        })
    
    return candles


# =============================================================================
# TECHNICAL ANALYSIS FIXTURES
# =============================================================================

@pytest.fixture
def sample_ta_indicators(faker: Faker) -> dict[str, dict[str, Any]]:
    """
    Генерирует данные технического анализа.
    
    Returns:
        dict: Технические индикаторы по символам
    """
    return {
        "BTC/USDT": {
            "rsi": faker.pyfloat(min_value=30, max_value=70),
            "macd_signal": faker.random_element(["bullish", "bearish", "neutral"]),
            "bb_position": faker.pyfloat(min_value=0, max_value=100),
            "trend": faker.random_element(["uptrend", "downtrend", "sideways"]),
            "support": faker.pyfloat(min_value=85000, max_value=95000),
            "resistance": faker.pyfloat(min_value=105000, max_value=115000),
        },
        "ETH/USDT": {
            "rsi": faker.pyfloat(min_value=30, max_value=70),
            "macd_signal": faker.random_element(["bullish", "bearish", "neutral"]),
            "bb_position": faker.pyfloat(min_value=0, max_value=100),
            "trend": faker.random_element(["uptrend", "downtrend", "sideways"]),
            "support": faker.pyfloat(min_value=2800, max_value=3200),
            "resistance": faker.pyfloat(min_value=3800, max_value=4200),
        },
    }


@pytest.fixture
def oversold_indicators() -> dict[str, Any]:
    """Индикаторы перепроданности (сигнал к покупке)."""
    return {
        "rsi": 25.0,
        "macd": {"line": -50, "signal": -30, "histogram": -20},
        "bollinger": {"upper": 105000, "middle": 100000, "lower": 95000, "position": 10},
        "trend": "oversold",
    }


@pytest.fixture
def overbought_indicators() -> dict[str, Any]:
    """Индикаторы перекупленности (сигнал к продаже)."""
    return {
        "rsi": 78.0,
        "macd": {"line": 50, "signal": 30, "histogram": 20},
        "bollinger": {"upper": 105000, "middle": 100000, "lower": 95000, "position": 92},
        "trend": "overbought",
    }


# =============================================================================
# INVESTOR/PORTFOLIO FIXTURES
# =============================================================================

@pytest.fixture
def sample_investor_data(faker: Faker) -> dict[str, Any]:
    """
    Генерирует данные инвестора.
    
    Returns:
        dict: Данные инвестора
    """
    return {
        "do_nothing_ok": faker.boolean(chance_of_getting_true=70),
        "phase": faker.random_element(["accumulation", "markup", "distribution", "markdown"]),
        "calm_indicator": faker.pyint(min_value=0, max_value=100),
        "red_flags": [],
        "market_tension": faker.random_element(["low", "medium", "high"]),
        "dca_signal": faker.random_element(["buy", "hold", "sell"]),
    }


@pytest.fixture
def sample_portfolio_data(faker: Faker) -> dict[str, Any]:
    """
    Генерирует данные портфеля.
    
    Returns:
        dict: Данные портфеля
    """
    total_value = faker.pyfloat(min_value=50000, max_value=200000)
    total_cost = total_value * faker.pyfloat(min_value=0.8, max_value=1.2)
    
    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_value - total_cost, 2),
        "total_pnl_percent": round((total_value / total_cost - 1) * 100, 2),
        "holdings": [
            {"symbol": "BTC", "amount": 0.5, "value": total_value * 0.6},
            {"symbol": "ETH", "amount": 5.0, "value": total_value * 0.3},
            {"symbol": "SOL", "amount": 20.0, "value": total_value * 0.1},
        ],
    }


# =============================================================================
# MARKET DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_market_data(faker: Faker) -> dict[str, Any]:
    """
    Генерирует рыночные данные.
    
    Returns:
        dict: Рыночные данные
    """
    fear_greed_value = faker.pyint(min_value=0, max_value=100)
    
    if fear_greed_value < 25:
        classification = "Extreme Fear"
    elif fear_greed_value < 45:
        classification = "Fear"
    elif fear_greed_value < 55:
        classification = "Neutral"
    elif fear_greed_value < 75:
        classification = "Greed"
    else:
        classification = "Extreme Greed"
    
    return {
        "fear_greed": {"value": fear_greed_value, "classification": classification},
        "btc_dominance": faker.pyfloat(min_value=45, max_value=60),
        "altseason_index": faker.pyint(min_value=0, max_value=100),
        "stablecoin_total": faker.pyint(min_value=130_000_000_000, max_value=170_000_000_000),
    }


# =============================================================================
# BACKTEST FIXTURES
# =============================================================================

@pytest.fixture
def backtest_config() -> dict[str, Any]:
    """
    Базовая конфигурация для backtesting.
    
    Returns:
        dict: Конфигурация backtest
    """
    return {
        "symbol": "BTC/USDT",
        "interval": "1d",
        "start_date": datetime.now(UTC) - timedelta(days=365),
        "end_date": datetime.now(UTC),
        "signal_frequency_days": 7,
        "outcome_window_days": 7,
        "min_candles_for_analysis": 200,
    }


@pytest.fixture
def hyperparameter_space() -> dict[str, list]:
    """
    Пространство гиперпараметров для оптимизации.
    
    Returns:
        dict: Параметры и их возможные значения
    """
    return {
        "rsi_oversold": [20, 25, 30],
        "rsi_overbought": [70, 75, 80],
        "macd_fast": [8, 12, 16],
        "macd_slow": [21, 26, 30],
        "macd_signal": [7, 9, 11],
        "bb_period": [15, 20, 25],
        "bb_std": [1.5, 2.0, 2.5],
        "sma_short": [20, 50],
        "sma_long": [100, 200],
    }


# =============================================================================
# DATABASE/API MOCK FIXTURES
# =============================================================================

@pytest.fixture
def mock_db_session() -> MagicMock:
    """Создает mock для сессии базы данных."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Создает mock для Redis клиента."""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=False)
    return client


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Создает mock для HTTP клиента."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.close = AsyncMock()
    return client


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def make_candle(timestamp: int, close: float) -> dict:
    """
    Хелпер для создания одной свечи.
    
    Args:
        timestamp: Временная метка в миллисекундах
        close: Цена закрытия
        
    Returns:
        dict: Данные свечи
    """
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
