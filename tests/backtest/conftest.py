"""
Конфигурация и фикстуры для backtest тестов.

Включает:
- Фикстуры для генерации исторических данных
- Конфигурации backtester
- Пространства гиперпараметров
"""

import os
import random
import sys
from typing import Any

import pytest

# Добавляем src в путь
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))


# =============================================================================
# BACKTEST CONFIGURATION FIXTURES
# =============================================================================


@pytest.fixture
def backtest_base_config() -> dict[str, Any]:
    """Базовая конфигурация для backtesting."""
    return {
        "symbol": "BTC/USDT",
        "interval": "1d",
        "train_ratio": 0.7,
        "val_ratio": 0.15,
        "test_ratio": 0.15,
        "min_data_points": 365,
    }


@pytest.fixture
def walk_forward_config() -> dict[str, Any]:
    """Конфигурация для walk-forward валидации."""
    return {
        "window_size": 180,  # 6 месяцев
        "horizon": 7,  # 7 дней прогноз
        "step_size": 7,  # Сдвиг окна на 7 дней
    }


@pytest.fixture
def hyperparameter_config() -> dict[str, Any]:
    """Конфигурация для оптимизации гиперпараметров."""
    return {
        "n_trials": 20,  # Сокращено для тестов
        "timeout": 300,  # 5 минут максимум
        "seed": 42,
    }


# =============================================================================
# DATA GENERATION FIXTURES
# =============================================================================


@pytest.fixture
def generate_price_series():
    """Фабрика для генерации ценовых серий."""

    def _generate(
        n_points: int = 365,
        start_price: float = 50000,
        trend: str = "random",  # "bullish", "bearish", "sideways", "random"
        volatility: float = 0.02,
    ) -> list[float]:
        prices = [start_price]

        if trend == "bullish":
            drift = 0.003
        elif trend == "bearish":
            drift = -0.003
        elif trend == "sideways":
            drift = 0.0
        else:
            drift = random.gauss(0, 0.001)

        for _ in range(n_points - 1):
            daily_return = random.gauss(drift, volatility)
            new_price = prices[-1] * (1 + daily_return)
            prices.append(max(new_price, 100))  # Минимальная цена

        return prices

    return _generate


@pytest.fixture
def historical_btc_prices(generate_price_series) -> list[float]:
    """Генерирует 2 года исторических данных BTC."""
    return generate_price_series(
        n_points=730,  # ~2 года
        start_price=30000,
        trend="random",
        volatility=0.025,
    )


@pytest.fixture
def historical_eth_prices(generate_price_series) -> list[float]:
    """Генерирует 2 года исторических данных ETH."""
    return generate_price_series(
        n_points=730,
        start_price=2000,
        trend="random",
        volatility=0.03,
    )


@pytest.fixture
def bullish_market_prices(generate_price_series) -> list[float]:
    """Генерирует данные бычьего рынка."""
    return generate_price_series(
        n_points=365,
        start_price=40000,
        trend="bullish",
        volatility=0.02,
    )


@pytest.fixture
def bearish_market_prices(generate_price_series) -> list[float]:
    """Генерирует данные медвежьего рынка."""
    return generate_price_series(
        n_points=365,
        start_price=60000,
        trend="bearish",
        volatility=0.025,
    )


@pytest.fixture
def volatile_market_prices(generate_price_series) -> list[float]:
    """Генерирует высоковолатильные данные."""
    return generate_price_series(
        n_points=365,
        start_price=50000,
        trend="sideways",
        volatility=0.05,
    )


# =============================================================================
# HYPERPARAMETER SPACE FIXTURES
# =============================================================================


@pytest.fixture
def chronos_param_space() -> dict[str, list]:
    """Пространство параметров для Chronos."""
    return {
        "context_length": [128, 256, 512],
        "num_samples": [10, 20, 50],
        "temperature": [0.5, 1.0, 1.5],
    }


@pytest.fixture
def arima_param_space() -> dict[str, list]:
    """Пространство параметров для ARIMA."""
    return {
        "season_length": [12, 24, 168],
        "approximation": [True, False],
        "stepwise": [True, False],
    }


@pytest.fixture
def neuralprophet_param_space() -> dict[str, list]:
    """Пространство параметров для NeuralProphet."""
    return {
        "learning_rate": [0.001, 0.01, 0.1],
        "epochs": [5, 15, 30],
        "batch_size": [16, 32, 64],
        "seasonality_mode": ["additive", "multiplicative"],
    }


@pytest.fixture
def ensemble_param_space() -> dict[str, list]:
    """Пространство весов для ансамбля."""
    return {
        "chronos_weight": [0.2, 0.3, 0.4, 0.5],
        "arima_weight": [0.2, 0.3, 0.4],
        "ets_weight": [0.1, 0.2, 0.3],
    }


@pytest.fixture
def technical_param_space() -> dict[str, list]:
    """Пространство параметров технического анализа."""
    return {
        "rsi_oversold": [20, 25, 30, 35],
        "rsi_overbought": [65, 70, 75, 80],
        "macd_fast": [8, 12, 16],
        "macd_slow": [21, 26, 30],
        "macd_signal": [7, 9, 11],
        "bb_period": [15, 20, 25],
        "bb_std": [1.5, 2.0, 2.5],
        "sma_short": [20, 50],
        "sma_long": [100, 200],
    }


# =============================================================================
# RESULTS STORAGE FIXTURES
# =============================================================================


@pytest.fixture
def optimization_results_path(tmp_path) -> str:
    """Временный путь для сохранения результатов оптимизации."""
    results_dir = tmp_path / "optimization_results"
    results_dir.mkdir()
    return str(results_dir)


@pytest.fixture
def best_params_storage() -> dict[str, dict]:
    """Хранилище лучших параметров."""
    return {}


# =============================================================================
# MOCK FIXTURES FOR SLOW TESTS
# =============================================================================


@pytest.fixture
def mock_backtest_metrics():
    """Мок метрик бэктеста."""
    return {
        "mae": 1500.0,
        "rmse": 2000.0,
        "mape": 3.5,
        "direction_accuracy": 55.0,
        "sample_size": 52,
    }


@pytest.fixture
def mock_optimization_result():
    """Мок результата оптимизации."""
    return {
        "best_params": {
            "context_length": 256,
            "num_samples": 20,
            "temperature": 1.0,
        },
        "best_mae": 1200.0,
        "n_trials": 20,
    }
