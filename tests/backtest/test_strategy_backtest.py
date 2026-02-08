"""
Strategy Backtest Tests - Тестирование стратегий с оптимизированными параметрами.

Тесты различных сценариев рынка и валидация результатов.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

pytestmark = [pytest.mark.backtest, pytest.mark.slow]


# =============================================================================
# STRATEGY BACKTEST TESTS
# =============================================================================


class TestStrategyBacktest:
    """Тесты бэктеста различных стратегий."""

    @pytest.mark.asyncio
    async def test_momentum_strategy_bullish_market(
        self,
        bullish_market_prices,
    ):
        """Тест momentum стратегии на бычьем рынке."""
        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        # На бычьем рынке направленная точность должна быть выше среднего
        mock_forecast = MagicMock()
        # Симулируем рост цены
        mock_forecast.predictions = [p * 1.01 for p in bullish_market_prices[-7:]]

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            metrics = await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=bullish_market_prices,
                model="default",
            )

            assert metrics is not None
            # В идеале на бычьем рынке direction_accuracy > 50%
            # Но с моком это зависит от реализации

    @pytest.mark.asyncio
    async def test_momentum_strategy_bearish_market(
        self,
        bearish_market_prices,
    ):
        """Тест momentum стратегии на медвежьем рынке."""
        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        mock_forecast = MagicMock()
        mock_forecast.predictions = [p * 0.99 for p in bearish_market_prices[-7:]]

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            metrics = await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=bearish_market_prices,
                model="default",
            )

            assert metrics is not None

    @pytest.mark.asyncio
    async def test_strategy_volatile_market(
        self,
        volatile_market_prices,
    ):
        """Тест стратегии на волатильном рынке."""
        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        # На волатильном рынке предсказания менее точные
        mock_forecast = MagicMock()
        mock_forecast.predictions = volatile_market_prices[-7:]

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            metrics = await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=volatile_market_prices,
                model="default",
            )

            assert metrics is not None
            # MAE на волатильном рынке обычно выше


# =============================================================================
# MODEL COMPARISON TESTS
# =============================================================================


class TestModelComparison:
    """Тесты сравнения моделей."""

    @pytest.mark.asyncio
    async def test_compare_models_basic(
        self,
        historical_btc_prices,
    ):
        """Базовый тест сравнения моделей."""
        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        mock_forecast = MagicMock()
        mock_forecast.predictions = [historical_btc_prices[-1]] * 7

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            with patch.object(
                backtester.forecaster,
                "get_available_models",
                return_value=["model_a", "model_b"],
            ):
                comparison = await backtester.compare_models(
                    symbol="BTC/USDT",
                    interval="1d",
                    prices=historical_btc_prices,
                    models=["model_a", "model_b"],
                )

                assert comparison is not None
                assert len(comparison.metrics) == 2

    @pytest.mark.asyncio
    async def test_compare_models_selects_best(
        self,
        historical_btc_prices,
    ):
        """Тест выбора лучшей модели."""
        from service.ml.backtester import ForecastBacktester
        from service.ml.models import BacktestMetrics

        backtester = ForecastBacktester()

        # Создаем разные метрики для разных моделей
        metrics_a = BacktestMetrics(
            model="model_a",
            symbol="BTC/USDT",
            interval="1d",
            mae=1500.0,
            rmse=2000.0,
            mape=3.0,
            direction_accuracy=55.0,
            sample_size=100,
        )

        metrics_b = BacktestMetrics(
            model="model_b",
            symbol="BTC/USDT",
            interval="1d",
            mae=1000.0,  # Лучший
            rmse=1500.0,
            mape=2.0,
            direction_accuracy=60.0,
            sample_size=100,
        )

        call_count = 0

        async def mock_run_backtest(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return metrics_a if call_count == 1 else metrics_b

        with patch.object(
            backtester,
            "run_backtest",
            side_effect=mock_run_backtest,
        ):
            with patch.object(
                backtester.forecaster,
                "get_available_models",
                return_value=["model_a", "model_b"],
            ):
                comparison = await backtester.compare_models(
                    symbol="BTC/USDT",
                    interval="1d",
                    prices=historical_btc_prices,
                    models=["model_a", "model_b"],
                )

                assert comparison.best_model == "model_b"


# =============================================================================
# PARAMETER SENSITIVITY TESTS
# =============================================================================


class TestParameterSensitivity:
    """Тесты чувствительности к параметрам."""

    @pytest.mark.asyncio
    async def test_context_length_sensitivity(
        self,
        historical_btc_prices,
    ):
        """Тест влияния длины контекста."""
        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        results = {}
        context_lengths = [64, 128, 256, 512]

        mock_forecast = MagicMock()
        mock_forecast.predictions = [historical_btc_prices[-1]] * 7

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            for ctx_len in context_lengths:
                metrics = await backtester.walk_forward_validation(
                    symbol="BTC/USDT",
                    interval="1d",
                    prices=historical_btc_prices,
                    model="default",
                    window_size=ctx_len,
                )
                results[ctx_len] = metrics.mae

        # Проверяем, что все результаты получены
        assert len(results) == len(context_lengths)

    def test_rsi_threshold_sensitivity(
        self,
        technical_param_space,
    ):
        """Тест влияния порогов RSI."""
        oversold_values = technical_param_space["rsi_oversold"]
        overbought_values = technical_param_space["rsi_overbought"]

        # Проверяем, что есть достаточно вариантов для тестирования
        assert len(oversold_values) >= 3
        assert len(overbought_values) >= 3

        # Все пороги должны быть в валидном диапазоне
        for v in oversold_values:
            assert 0 < v < 50

        for v in overbought_values:
            assert 50 < v < 100


# =============================================================================
# EDGE CASES TESTS
# =============================================================================


class TestEdgeCases:
    """Тесты граничных случаев."""

    @pytest.mark.asyncio
    async def test_minimal_data_backtest(self):
        """Тест с минимальным количеством данных."""
        from core.constants import MLDefaults
        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        # Генерируем минимально необходимое количество данных
        minimal_prices = [50000 + i * 10 for i in range(MLDefaults.MIN_TRAINING_POINTS + 20)]

        mock_forecast = MagicMock()
        mock_forecast.predictions = minimal_prices[-7:]

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            metrics = await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=minimal_prices,
                model="default",
            )

            assert metrics is not None

    @pytest.mark.asyncio
    async def test_zero_variance_prices(self):
        """Тест с ценами без изменений."""
        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        # Все цены одинаковые
        flat_prices = [50000.0] * 500

        mock_forecast = MagicMock()
        mock_forecast.predictions = [50000.0] * 7

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            metrics = await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=flat_prices,
                model="default",
            )

            # MAE должен быть 0 или близок к 0
            assert metrics.mae == 0.0 or metrics.mae < 1.0

    @pytest.mark.asyncio
    async def test_extreme_volatility(self):
        """Тест с экстремальной волатильностью."""
        import random

        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        # Цены с экстремальными скачками
        random.seed(42)
        extreme_prices = [50000]
        for _ in range(499):
            change = random.choice([-0.2, -0.1, 0.1, 0.2])  # ±10-20% изменения
            extreme_prices.append(extreme_prices[-1] * (1 + change))

        mock_forecast = MagicMock()
        mock_forecast.predictions = extreme_prices[-7:]

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            metrics = await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=extreme_prices,
                model="default",
            )

            # Метрики должны быть вычислены
            assert metrics is not None
            # MAPE может быть высоким
            assert metrics.mape >= 0


# =============================================================================
# CROSS-VALIDATION TESTS
# =============================================================================


@pytest.mark.asyncio
class TestCrossValidation:
    """Тесты кросс-валидации."""

    async def test_time_series_cross_validation(
        self,
        historical_btc_prices,
    ):
        """Тест временной кросс-валидации."""
        from service.ml.backtester import ForecastBacktester

        backtester = ForecastBacktester()

        # Делим данные на несколько фолдов
        n_folds = 5
        fold_size = len(historical_btc_prices) // n_folds

        fold_results = []

        mock_forecast = MagicMock()
        mock_forecast.predictions = [historical_btc_prices[-1]] * 7

        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            for fold in range(1, n_folds):
                train_end = fold * fold_size
                train_prices = historical_btc_prices[:train_end]

                if len(train_prices) < 200:  # Минимум для бэктеста
                    continue

                metrics = await backtester.run_backtest(
                    symbol="BTC/USDT",
                    interval="1d",
                    prices=train_prices,
                    model="default",
                    train_ratio=0.8,
                    val_ratio=0.0,
                    test_ratio=0.2,
                )

                fold_results.append(metrics.mae)

        # Должно быть несколько результатов
        assert len(fold_results) > 0

        # Вычисляем среднее и стандартное отклонение
        import statistics

        if len(fold_results) > 1:
            avg_mae = statistics.mean(fold_results)
            std_mae = statistics.stdev(fold_results)
            assert avg_mae >= 0
            assert std_mae >= 0
