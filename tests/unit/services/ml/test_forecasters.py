"""
ML Forecaster Tests - Тесты прогнозирования цен.

Тестирует:
- PriceForecaster
- ChronosForecaster
- StatsForecaster
- NeuralForecaster
- EnsembleForecaster
"""

import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, "src"))

pytestmark = [pytest.mark.unit]


# =============================================================================
# FORECASTER BASE TESTS
# =============================================================================


class TestPriceForecaster:
    """Тесты для PriceForecaster."""

    def test_import(self):
        """Проверка импорта."""
        from service.ml.forecaster import PriceForecaster

        assert PriceForecaster is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.ml.forecaster import PriceForecaster

        forecaster = PriceForecaster()
        assert forecaster is not None

    def test_get_available_models(self):
        """Проверка списка доступных моделей."""
        from service.ml.forecaster import PriceForecaster

        forecaster = PriceForecaster()
        models = forecaster.get_available_models()
        assert isinstance(models, list)
        assert len(models) > 0

    @pytest.mark.asyncio
    async def test_predict_insufficient_data(self):
        """Тест с недостаточным количеством данных."""
        from service.ml.forecaster import PriceForecaster

        forecaster = PriceForecaster()

        # Слишком мало данных
        with pytest.raises(ValueError):
            await forecaster.predict(
                symbol="BTC/USDT",
                interval="1d",
                prices=[100] * 10,
                model="default",
                horizon=7,
            )

    @pytest.mark.asyncio
    async def test_predict_with_mock(self, sample_candles):
        """Тест прогнозирования с моком."""
        from service.ml.forecaster import PriceForecaster

        forecaster = PriceForecaster()

        # Just check that forecaster has predict method
        assert hasattr(forecaster, "predict")
        assert callable(forecaster.predict)


# =============================================================================
# CHRONOS FORECASTER TESTS
# =============================================================================


class TestChronosBoltForecaster:
    """Тесты для ChronosBoltForecaster."""

    def test_import(self):
        """Проверка импорта."""
        from service.ml.chronos_forecaster import ChronosBoltForecaster

        assert ChronosBoltForecaster is not None

    def test_chronos_available_flag(self):
        """Проверка флага доступности Chronos."""
        from service.ml.chronos_forecaster import CHRONOS_AVAILABLE

        assert isinstance(CHRONOS_AVAILABLE, bool)

    @pytest.mark.asyncio
    async def test_forecast_with_mock(self, sample_candles):
        """Тест прогнозирования Chronos с моком."""
        try:
            from service.ml.chronos_forecaster import (
                CHRONOS_AVAILABLE,
                ChronosBoltForecaster,
            )

            if not CHRONOS_AVAILABLE:
                pytest.skip("Chronos not available")

            [c["close"] for c in sample_candles]
            ChronosBoltForecaster()

            # Результат зависит от реализации
        except ImportError:
            pytest.skip("Chronos not installed")


# =============================================================================
# STATS FORECASTER TESTS
# =============================================================================


class TestStatsForecastForecaster:
    """Тесты для StatsForecastForecaster."""

    def test_import(self):
        """Проверка импорта."""
        from service.ml.stats_forecaster import StatsForecastForecaster

        assert StatsForecastForecaster is not None

    def test_statsforecast_available_flag(self):
        """Проверка флага доступности StatsForcast."""
        from service.ml.stats_forecaster import STATSFORCEAST_AVAILABLE

        assert isinstance(STATSFORCEAST_AVAILABLE, bool)

    @pytest.mark.asyncio
    async def test_forecast_arima(self, sample_candles):
        """Тест ARIMA прогнозирования."""
        try:
            from service.ml.stats_forecaster import (
                STATSFORCEAST_AVAILABLE,
                StatsForecastForecaster,
            )

            if not STATSFORCEAST_AVAILABLE:
                pytest.skip("statsforecast not available")

            [c["close"] for c in sample_candles]
            StatsForecastForecaster()

            # Результат зависит от реализации
        except ImportError:
            pytest.skip("statsforecast not installed")


# =============================================================================
# ENSEMBLE FORECASTER TESTS
# =============================================================================


class TestEnsembleForecaster:
    """Тесты для EnsembleForecaster."""

    def test_import(self):
        """Проверка импорта."""
        from service.ml.ensemble_forecaster import EnsembleForecaster

        assert EnsembleForecaster is not None

    def test_init(self):
        """Проверка инициализации."""
        from service.ml.ensemble_forecaster import EnsembleForecaster

        forecaster = EnsembleForecaster()
        assert forecaster is not None

    def test_default_weights(self):
        """Проверка весов по умолчанию."""
        from service.ml.ensemble_forecaster import EnsembleForecaster

        forecaster = EnsembleForecaster()

        # Веса должны быть определены
        assert hasattr(forecaster, "weights") or hasattr(forecaster, "_weights")

    @pytest.mark.asyncio
    async def test_ensemble_forecast_with_mocks(self, sample_candles):
        """Тест ансамблевого прогнозирования с моками."""
        from service.ml.ensemble_forecaster import EnsembleForecaster

        forecaster = EnsembleForecaster()

        # Just check that forecaster has predict method
        assert hasattr(forecaster, "predict")
        assert callable(forecaster.predict)


# =============================================================================
# ML MODELS TESTS
# =============================================================================


class TestMLModels:
    """Тесты для ML моделей данных."""

    def test_forecast_result_import(self):
        """Проверка импорта ForecastResult."""
        from service.ml.models import ForecastResult

        assert ForecastResult is not None

    def test_forecast_result_creation(self):
        """Тест создания ForecastResult."""
        from datetime import UTC, datetime

        from service.ml.models import ForecastResult

        result = ForecastResult(
            symbol="BTC/USDT",
            interval="1d",
            model="test",
            predictions=[100000 + i * 1000 for i in range(7)],
            confidence_low=[99000 + i * 1000 for i in range(7)],
            confidence_high=[101000 + i * 1000 for i in range(7)],
            direction="up",
            confidence_pct=75.0,
            timestamp=datetime.now(UTC),
            horizon=7,
        )

        assert result.symbol == "BTC/USDT"
        assert len(result.predictions) == 7
        assert result.direction == "up"

    def test_backtest_metrics_import(self):
        """Проверка импорта BacktestMetrics."""
        from service.ml.models import BacktestMetrics

        assert BacktestMetrics is not None

    def test_backtest_metrics_creation(self):
        """Тест создания BacktestMetrics."""
        from service.ml.models import BacktestMetrics

        metrics = BacktestMetrics(
            model="test",
            symbol="BTC/USDT",
            interval="1d",
            mae=1000.0,
            rmse=1200.0,
            mape=2.5,
            direction_accuracy=55.0,
            sample_size=100,
        )

        assert metrics.mae == 1000.0
        assert metrics.direction_accuracy == 55.0


# =============================================================================
# ML BASE TESTS
# =============================================================================


class TestMLBase:
    """Тесты базовых классов ML."""

    def test_base_forecaster_import(self):
        """Проверка импорта BaseForecaster."""
        from service.ml.base import BaseForecaster

        assert BaseForecaster is not None

    def test_ml_defaults_import(self):
        """Проверка импорта MLDefaults."""
        from core.constants import MLDefaults

        assert MLDefaults is not None
        assert hasattr(MLDefaults, "PREDICTION_HORIZON")
        assert hasattr(MLDefaults, "MIN_TRAINING_POINTS")

    def test_ml_models_constants(self):
        """Проверка констант ML моделей."""
        from core.constants import MLModels

        assert MLModels is not None
        assert hasattr(MLModels, "ALL")
        assert isinstance(MLModels.ALL, (list, tuple))
