"""
Backtest Tests - Тестирование бэктестера и оптимизации гиперпараметров.

Маркеры:
- backtest: все тесты бэктестинга
- slow: медленные тесты (полная оптимизация)
"""

import json
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

# Добавляем src в путь
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

pytestmark = [pytest.mark.backtest]


# =============================================================================
# BACKTESTER UNIT TESTS
# =============================================================================

class TestForecastBacktester:
    """Юнит-тесты для ForecastBacktester."""

    def test_backtester_import(self):
        """Проверка импорта ForecastBacktester."""
        from service.ml.backtester import ForecastBacktester
        assert ForecastBacktester is not None

    def test_backtester_init(self):
        """Проверка инициализации бэктестера."""
        from service.ml.backtester import ForecastBacktester
        backtester = ForecastBacktester()
        assert backtester is not None
        assert backtester.forecaster is not None

    def test_calculate_metrics(self):
        """Тест расчета метрик."""
        from service.ml.backtester import ForecastBacktester
        
        backtester = ForecastBacktester()
        
        # Точные предсказания
        predictions = [100, 200, 300]
        actuals = [100, 200, 300]
        
        metrics = backtester._calculate_metrics(predictions, actuals)
        
        assert metrics["mae"] == 0.0
        assert metrics["rmse"] == 0.0
        assert metrics["mape"] == 0.0
        assert metrics["direction_accuracy"] == 100.0

    def test_calculate_metrics_with_errors(self):
        """Тест расчета метрик с ошибками."""
        from service.ml.backtester import ForecastBacktester
        
        backtester = ForecastBacktester()
        
        predictions = [100, 200, 300]
        actuals = [110, 190, 310]
        
        metrics = backtester._calculate_metrics(predictions, actuals)
        
        assert metrics["mae"] > 0
        assert metrics["rmse"] > 0
        assert metrics["mape"] > 0
        assert 0 <= metrics["direction_accuracy"] <= 100

    def test_get_points_per_day(self):
        """Тест конвертации интервала в точки за день."""
        from service.ml.backtester import ForecastBacktester
        
        backtester = ForecastBacktester()
        
        assert backtester._get_points_per_day("1d") == 1
        assert backtester._get_points_per_day("1h") == 24
        assert backtester._get_points_per_day("4h") == 6
        assert backtester._get_points_per_day("15m") == 96

    @pytest.mark.asyncio
    async def test_run_backtest_insufficient_data(self):
        """Тест бэктеста с недостаточным количеством данных."""
        from service.ml.backtester import ForecastBacktester
        
        backtester = ForecastBacktester()
        
        with pytest.raises(ValueError, match="Insufficient data"):
            await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=[100] * 10,  # Слишком мало данных
                model="default",
            )

    @pytest.mark.asyncio
    async def test_run_backtest_invalid_ratios(self):
        """Тест бэктеста с неверными пропорциями."""
        from service.ml.backtester import ForecastBacktester
        
        backtester = ForecastBacktester()
        
        with pytest.raises(ValueError, match="ratios must sum to 1.0"):
            await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=[100] * 500,
                model="default",
                train_ratio=0.5,
                val_ratio=0.5,
                test_ratio=0.5,  # Сумма > 1
            )


# =============================================================================
# OPTIMIZER UNIT TESTS
# =============================================================================

class TestHyperparameterOptimizer:
    """Юнит-тесты для HyperparameterOptimizer."""

    def test_optimizer_import(self):
        """Проверка импорта оптимизатора."""
        try:
            from service.ml.optimizer import HyperparameterOptimizer
            assert HyperparameterOptimizer is not None
        except ImportError:
            pytest.skip("Optuna not installed")

    def test_optimizer_init(self):
        """Проверка инициализации оптимизатора."""
        try:
            from service.ml.optimizer import HyperparameterOptimizer
            optimizer = HyperparameterOptimizer()
            assert optimizer is not None
            assert optimizer.study_cache == {}
        except ImportError:
            pytest.skip("Optuna not installed")

    def test_suggest_parameters_chronos(self):
        """Тест генерации параметров для Chronos."""
        try:
            import optuna
            from service.ml.optimizer import HyperparameterOptimizer
            from core.constants import MLModels
            
            optimizer = HyperparameterOptimizer()
            
            study = optuna.create_study()
            trial = study.ask()
            
            params = optimizer._suggest_parameters(trial, MLModels.CHRONOS_BOLT)
            
            assert "context_length" in params
            assert "num_samples" in params
            assert "temperature" in params
        except ImportError:
            pytest.skip("Optuna not installed")

    def test_suggest_parameters_arima(self):
        """Тест генерации параметров для ARIMA."""
        try:
            import optuna
            from service.ml.optimizer import HyperparameterOptimizer
            from core.constants import MLModels
            
            optimizer = HyperparameterOptimizer()
            
            study = optuna.create_study()
            trial = study.ask()
            
            params = optimizer._suggest_parameters(trial, MLModels.STATSFORECAST_ARIMA)
            
            assert "season_length" in params
            assert "approximation" in params
            assert "stepwise" in params
        except ImportError:
            pytest.skip("Optuna not installed")


# =============================================================================
# BACKTEST METRICS TESTS
# =============================================================================

class TestBacktestMetrics:
    """Тесты для моделей метрик бэктеста."""

    def test_metrics_model_import(self):
        """Проверка импорта моделей метрик."""
        from service.ml.models import BacktestMetrics, ModelComparison
        assert BacktestMetrics is not None
        assert ModelComparison is not None

    def test_backtest_metrics_creation(self):
        """Тест создания BacktestMetrics."""
        from service.ml.models import BacktestMetrics
        
        metrics = BacktestMetrics(
            model="test_model",
            symbol="BTC/USDT",
            interval="1d",
            mae=1000.0,
            rmse=1200.0,
            mape=2.5,
            direction_accuracy=60.0,
            sample_size=100,
        )
        
        assert metrics.model == "test_model"
        assert metrics.mae == 1000.0
        assert metrics.direction_accuracy == 60.0

    def test_model_comparison_creation(self):
        """Тест создания ModelComparison."""
        from service.ml.models import BacktestMetrics, ModelComparison
        
        comparison = ModelComparison(symbol="BTC/USDT", interval="1d")
        
        metrics1 = BacktestMetrics(
            model="model_1",
            symbol="BTC/USDT",
            interval="1d",
            mae=1000.0,
            rmse=1200.0,
            mape=2.5,
            direction_accuracy=60.0,
            sample_size=100,
        )
        
        metrics2 = BacktestMetrics(
            model="model_2",
            symbol="BTC/USDT",
            interval="1d",
            mae=800.0,  # Лучший MAE
            rmse=1000.0,
            mape=2.0,
            direction_accuracy=65.0,
            sample_size=100,
        )
        
        comparison.add_metrics(metrics1)
        comparison.add_metrics(metrics2)
        
        assert len(comparison.metrics) == 2


# =============================================================================
# INTEGRATION TESTS - BACKTEST WITH MOCK DATA
# =============================================================================

@pytest.mark.slow
@pytest.mark.asyncio
class TestBacktestIntegration:
    """Интеграционные тесты бэктестера с мок-данными."""

    async def test_backtest_with_mocked_forecaster(
        self,
        historical_btc_prices,
    ):
        """Тест полного бэктеста с замоканным прогнозатором."""
        from service.ml.backtester import ForecastBacktester
        
        backtester = ForecastBacktester()
        
        # Мокаем прогнозатор
        mock_forecast = MagicMock()
        mock_forecast.predictions = [historical_btc_prices[-1] * 1.02] * 7
        
        with patch.object(
            backtester.forecaster,
            "predict",
            new_callable=AsyncMock,
            return_value=mock_forecast,
        ):
            metrics = await backtester.run_backtest(
                symbol="BTC/USDT",
                interval="1d",
                prices=historical_btc_prices,
                model="default",
            )
            
            assert metrics is not None
            assert metrics.mae >= 0
            assert 0 <= metrics.direction_accuracy <= 100

    async def test_walk_forward_validation_mocked(
        self,
        historical_btc_prices,
    ):
        """Тест walk-forward валидации с моком."""
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
            metrics = await backtester.walk_forward_validation(
                symbol="BTC/USDT",
                interval="1d",
                prices=historical_btc_prices,
                model="default",
                window_size=180,
                horizon=7,
            )
            
            assert metrics is not None
            assert metrics.sample_size > 0


# =============================================================================
# SLOW TESTS - FULL OPTIMIZATION
# =============================================================================

@pytest.mark.slow
@pytest.mark.asyncio
class TestFullOptimization:
    """Полные тесты оптимизации (медленные)."""

    async def test_full_chronos_optimization(
        self,
        historical_btc_prices,
        hyperparameter_config,
        optimization_results_path,
    ):
        """Полный тест оптимизации Chronos (медленный)."""
        try:
            from service.ml.optimizer import HyperparameterOptimizer
            from core.constants import MLModels
        except ImportError:
            pytest.skip("Required dependencies not installed")
        
        optimizer = HyperparameterOptimizer()
        
        # Мокаем бэктестер для ускорения
        mock_metrics = MagicMock()
        mock_metrics.mae = 1000.0
        mock_metrics.rmse = 1200.0
        mock_metrics.mape = 2.5
        mock_metrics.direction_accuracy = 55.0
        
        with patch.object(
            optimizer.backtester,
            "walk_forward_validation",
            new_callable=AsyncMock,
            return_value=mock_metrics,
        ):
            result = await optimizer.optimize(
                symbol="BTC/USDT",
                interval="1d",
                prices=historical_btc_prices,
                model=MLModels.CHRONOS_BOLT,
                n_trials=hyperparameter_config["n_trials"],
                timeout=hyperparameter_config["timeout"],
            )
            
            assert "best_params" in result
            assert "best_mae" in result
            assert result["n_trials"] == hyperparameter_config["n_trials"]
            
            # Сохраняем результаты
            results_file = os.path.join(
                optimization_results_path,
                "chronos_optimization.json"
            )
            with open(results_file, "w") as f:
                json.dump(result, f, indent=2, default=str)

    async def test_ensemble_weight_optimization(
        self,
        historical_btc_prices,
    ):
        """Тест оптимизации весов ансамбля."""
        try:
            from service.ml.optimizer import HyperparameterOptimizer
        except ImportError:
            pytest.skip("Optuna not installed")
        
        optimizer = HyperparameterOptimizer()
        
        # Мокаем бэктестер
        mock_metrics = MagicMock()
        mock_metrics.mae = 1000.0
        
        with patch.object(
            optimizer.backtester,
            "walk_forward_validation",
            new_callable=AsyncMock,
            return_value=mock_metrics,
        ):
            with patch.object(
                optimizer.backtester.forecaster,
                "get_available_models",
                return_value=["chronos", "arima", "ets"],
            ):
                weights = await optimizer.optimize_ensemble_weights(
                    symbol="BTC/USDT",
                    interval="1d",
                    prices=historical_btc_prices,
                    n_trials=10,
                )
                
                assert isinstance(weights, dict)
                # Веса должны суммироваться примерно до 1
                total_weight = sum(weights.values())
                assert abs(total_weight - 1.0) < 0.01


# =============================================================================
# PARAMETER SPACE VALIDATION TESTS
# =============================================================================

class TestParameterSpaceValidation:
    """Тесты валидации пространства параметров."""

    def test_chronos_param_space_valid(self, chronos_param_space):
        """Проверка валидности пространства Chronos."""
        assert "context_length" in chronos_param_space
        assert all(v > 0 for v in chronos_param_space["context_length"])
        assert all(v > 0 for v in chronos_param_space["num_samples"])
        assert all(v > 0 for v in chronos_param_space["temperature"])

    def test_arima_param_space_valid(self, arima_param_space):
        """Проверка валидности пространства ARIMA."""
        assert "season_length" in arima_param_space
        assert all(v > 0 for v in arima_param_space["season_length"])

    def test_technical_param_space_consistency(self, technical_param_space):
        """Проверка согласованности параметров ТА."""
        # RSI oversold должен быть меньше overbought
        min_oversold = min(technical_param_space["rsi_oversold"])
        max_overbought = max(technical_param_space["rsi_overbought"])
        assert min_oversold < max_overbought
        
        # MACD fast должен быть меньше slow
        max_fast = max(technical_param_space["macd_fast"])
        min_slow = min(technical_param_space["macd_slow"])
        assert max_fast < min_slow
        
        # SMA short должен быть меньше long
        max_short = max(technical_param_space["sma_short"])
        min_long = min(technical_param_space["sma_long"])
        assert max_short < min_long


# =============================================================================
# RESULTS PERSISTENCE TESTS
# =============================================================================

class TestResultsPersistence:
    """Тесты сохранения результатов оптимизации."""

    def test_save_optimization_results(
        self,
        optimization_results_path,
        mock_optimization_result,
    ):
        """Тест сохранения результатов в файл."""
        results_file = os.path.join(
            optimization_results_path,
            "test_results.json"
        )
        
        with open(results_file, "w") as f:
            json.dump(mock_optimization_result, f, indent=2)
        
        assert os.path.exists(results_file)
        
        with open(results_file) as f:
            loaded = json.load(f)
        
        assert loaded["best_params"] == mock_optimization_result["best_params"]
        assert loaded["best_mae"] == mock_optimization_result["best_mae"]

    def test_best_params_storage(self, best_params_storage):
        """Тест хранилища лучших параметров."""
        best_params_storage["BTC/USDT_1d_chronos"] = {
            "context_length": 256,
            "num_samples": 20,
        }
        
        assert "BTC/USDT_1d_chronos" in best_params_storage
        assert best_params_storage["BTC/USDT_1d_chronos"]["context_length"] == 256
