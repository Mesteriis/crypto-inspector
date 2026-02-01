"""
Unit Tests Configuration.

Содержит фикстуры, специфичные для unit тестов:
- Моки сервисов
- Изолированные данные
- Фабрики моделей
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

# =============================================================================
# SERVICE MOCKS
# =============================================================================


@pytest.fixture
def mock_technical_analyzer():
    """Мок для TechnicalAnalyzer."""
    with patch("service.analysis.technical.TechnicalAnalyzer") as mock:
        instance = mock.return_value
        instance.calc_rsi = MagicMock(return_value=55.0)
        instance.calc_sma = MagicMock(return_value=50000.0)
        instance.calc_macd = MagicMock(return_value=(100.0, 80.0, 20.0))
        instance.calc_bollinger_bands = MagicMock(return_value=(105000, 100000, 95000, 50.0))
        yield instance


@pytest.fixture
def mock_pattern_detector():
    """Мок для PatternDetector."""
    with patch("service.analysis.patterns.PatternDetector") as mock:
        instance = mock.return_value
        instance.detect_all = MagicMock(return_value=[])
        yield instance


@pytest.fixture
def mock_scoring_engine():
    """Мок для ScoringEngine."""
    with patch("service.analysis.scoring.ScoringEngine") as mock:
        instance = mock.return_value
        score_result = MagicMock()
        score_result.to_dict = MagicMock(
            return_value={
                "score": {"total": 65, "technical": 60, "pattern": 70},
                "confidence": 70,
                "signal": "buy",
            }
        )
        instance.calculate = MagicMock(return_value=score_result)
        yield instance


@pytest.fixture
def mock_candlestick_fetcher():
    """Мок для CandlestickFetcher."""
    with patch("service.candlestick.fetcher.CandlestickFetcher") as mock:
        instance = mock.return_value
        instance.fetch = AsyncMock(return_value=[])
        instance.fetch_multiple = AsyncMock(return_value={})
        yield instance


@pytest.fixture
def mock_investor_analyzer():
    """Мок для анализатора инвестора."""
    with patch("service.analysis.investor") as mock:
        mock.get_investor_status = AsyncMock(
            return_value={
                "do_nothing_ok": True,
                "phase": "accumulation",
                "calm_indicator": 75,
                "red_flags": [],
            }
        )
        yield mock


# =============================================================================
# ML SERVICE MOCKS
# =============================================================================


@pytest.fixture
def mock_chronos_forecaster():
    """Мок для ChronosForecaster."""
    with patch("service.ml.chronos_forecaster.ChronosForecaster") as mock:
        instance = mock.return_value
        instance.forecast = AsyncMock(
            return_value={
                "predictions": [100000, 101000, 102000],
                "confidence_low": [98000, 99000, 100000],
                "confidence_high": [102000, 103000, 104000],
            }
        )
        yield instance


@pytest.fixture
def mock_stats_forecaster():
    """Мок для StatsForecaster."""
    with patch("service.ml.stats_forecaster.StatsForecaster") as mock:
        instance = mock.return_value
        instance.forecast = AsyncMock(
            return_value={
                "predictions": [100000, 101000, 102000],
                "model": "AutoARIMA",
            }
        )
        yield instance


@pytest.fixture
def mock_ensemble_forecaster():
    """Мок для EnsembleForecaster."""
    with patch("service.ml.ensemble_forecaster.EnsembleForecaster") as mock:
        instance = mock.return_value
        instance.forecast = AsyncMock(
            return_value={
                "predictions": [100000, 101000, 102000],
                "models_used": ["chronos", "arima", "ets"],
                "confidence": 75,
            }
        )
        yield instance


@pytest.fixture
def mock_optimizer():
    """Мок для Optimizer."""
    with patch("service.ml.optimizer.HyperparameterOptimizer") as mock:
        instance = mock.return_value
        instance.optimize = AsyncMock(
            return_value={
                "best_params": {"rsi_oversold": 25, "rsi_overbought": 75},
                "best_score": 0.65,
                "trials": 100,
            }
        )
        yield instance


# =============================================================================
# DATABASE MOCKS
# =============================================================================


@pytest.fixture
def mock_candlestick_repository():
    """Мок для CandlestickRepository."""
    with patch("models.repositories.candlestick.CandlestickRepository") as mock:
        instance = mock.return_value
        instance.get_candles = AsyncMock(return_value=[])
        instance.save_candles = AsyncMock(return_value=True)
        instance.get_latest = AsyncMock(return_value=None)
        yield instance


@pytest.fixture
def mock_ml_predictions_repository():
    """Мок для MLPredictionsRepository."""
    with patch("models.repositories.ml_predictions.MLPredictionsRepository") as mock:
        instance = mock.return_value
        instance.save_prediction = AsyncMock(return_value=True)
        instance.get_predictions = AsyncMock(return_value=[])
        instance.get_latest_prediction = AsyncMock(return_value=None)
        yield instance


# =============================================================================
# HA INTEGRATION MOCKS
# =============================================================================


@pytest.fixture
def mock_mqtt_client():
    """Мок для MQTT клиента."""
    client = MagicMock()
    client.publish = MagicMock(return_value=MagicMock(rc=0))
    client.is_connected = MagicMock(return_value=True)
    client.connect = MagicMock()
    client.disconnect = MagicMock()
    client.loop_start = MagicMock()
    client.loop_stop = MagicMock()
    return client


@pytest.fixture
def mock_ha_manager(mock_mqtt_client):
    """Мок для HAIntegrationManager."""
    with patch("service.ha.HAIntegrationManager") as mock:
        instance = mock.return_value
        instance._mqtt_client = mock_mqtt_client
        instance.publish_sensor = MagicMock(return_value=True)
        instance.publish_sensors = MagicMock(return_value=True)
        instance.get_sensor_value = MagicMock(return_value=None)
        yield instance


# =============================================================================
# EXCHANGE MOCKS
# =============================================================================


@pytest.fixture
def mock_bybit_client():
    """Мок для BybitClient."""
    with patch("service.exchange.bybit_client.BybitClient") as mock:
        instance = mock.return_value
        instance.get_balance = AsyncMock(return_value={"USDT": 50000.0})
        instance.get_positions = AsyncMock(return_value=[])
        instance.get_earn_positions = AsyncMock(return_value=[])
        yield instance


@pytest.fixture
def mock_binance_exchange():
    """Мок для BinanceExchange."""
    with patch("service.candlestick.exchanges.binance.BinanceExchange") as mock:
        instance = mock.return_value
        instance.fetch_candles = AsyncMock(return_value=[])
        instance.get_ticker = AsyncMock(return_value={"price": 100000})
        yield instance


# =============================================================================
# MODEL FACTORIES
# =============================================================================


@pytest.fixture
def candlestick_model_factory(faker: Faker):
    """Фабрика для создания Candlestick моделей."""

    def _create(symbol: str = "BTC/USDT", interval: str = "1d", **kwargs) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "interval": interval,
            "timestamp": kwargs.get("timestamp", int(datetime.now(UTC).timestamp() * 1000)),
            "open": kwargs.get("open", faker.pyfloat(min_value=90000, max_value=100000)),
            "high": kwargs.get("high", faker.pyfloat(min_value=100000, max_value=105000)),
            "low": kwargs.get("low", faker.pyfloat(min_value=85000, max_value=90000)),
            "close": kwargs.get("close", faker.pyfloat(min_value=90000, max_value=100000)),
            "volume": kwargs.get("volume", faker.pyfloat(min_value=1000, max_value=10000)),
        }

    return _create


@pytest.fixture
def prediction_model_factory(faker: Faker):
    """Фабрика для создания Prediction моделей."""

    def _create(symbol: str = "BTC/USDT", **kwargs) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "model": kwargs.get("model", "ensemble"),
            "horizon": kwargs.get("horizon", 7),
            "predictions": kwargs.get("predictions", [100000 + i * 1000 for i in range(7)]),
            "confidence": kwargs.get("confidence", faker.pyfloat(min_value=50, max_value=90)),
            "created_at": kwargs.get("created_at", datetime.now(UTC).isoformat()),
        }

    return _create


@pytest.fixture
def signal_model_factory(faker: Faker):
    """Фабрика для создания Signal моделей."""

    def _create(symbol: str = "BTC/USDT", **kwargs) -> dict[str, Any]:
        return {
            "id": kwargs.get("id", f"sig_{faker.uuid4()[:8]}"),
            "symbol": symbol,
            "signal_type": kwargs.get(
                "signal_type", faker.random_element(["rsi_oversold", "macd_bullish", "golden_cross"])
            ),
            "direction": kwargs.get("direction", faker.random_element(["long", "short", "neutral"])),
            "strength": kwargs.get("strength", faker.pyint(min_value=50, max_value=100)),
            "price_at_signal": kwargs.get("price_at_signal", faker.pyfloat(min_value=90000, max_value=110000)),
            "timestamp": kwargs.get("timestamp", datetime.now(UTC).isoformat()),
            "outcome": kwargs.get("outcome", None),
        }

    return _create


# =============================================================================
# VALIDATION HELPERS
# =============================================================================


@pytest.fixture
def assert_dict_has_keys():
    """Хелпер для проверки наличия ключей в словаре."""

    def _assert(d: dict, keys: list[str]) -> None:
        for key in keys:
            assert key in d, f"Ключ '{key}' отсутствует в словаре"

    return _assert


@pytest.fixture
def assert_in_range():
    """Хелпер для проверки значения в диапазоне."""

    def _assert(value: float, min_val: float, max_val: float, name: str = "value") -> None:
        assert min_val <= value <= max_val, f"{name}={value} не в диапазоне [{min_val}, {max_val}]"

    return _assert


@pytest.fixture
def golden_cross_candles():
    """Candles with golden cross pattern (SMA50 crosses above SMA200)."""
    import random

    random.seed(42)

    # Generate 250 candles with price pattern where SMA50 crosses SMA200
    candles = []
    base_price = 50000

    # First 200 candles: downtrend (SMA50 below SMA200)
    for i in range(200):
        price = base_price - (i * 50) + random.uniform(-500, 500)
        candles.append(
            {
                "open": price,
                "high": price + random.uniform(100, 500),
                "low": price - random.uniform(100, 500),
                "close": price + random.uniform(-200, 200),
                "volume": random.uniform(1000, 5000),
                "timestamp": 1700000000000 + i * 86400000,
            }
        )

    # Last 50 candles: strong uptrend (SMA50 will cross above SMA200)
    for i in range(50):
        price = base_price - 10000 + (i * 400) + random.uniform(-300, 300)
        candles.append(
            {
                "open": price,
                "high": price + random.uniform(200, 800),
                "low": price - random.uniform(100, 400),
                "close": price + random.uniform(100, 400),
                "volume": random.uniform(2000, 8000),
                "timestamp": 1700000000000 + (200 + i) * 86400000,
            }
        )

    return candles
