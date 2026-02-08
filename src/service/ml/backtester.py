"""
Forecast Backtester - Evaluate model performance on historical data.
"""

import logging

import numpy as np

from core.constants import MLDefaults
from service.ml.forecaster import PriceForecaster
from service.ml.models import BacktestMetrics, ModelComparison

logger = logging.getLogger(__name__)


class ForecastBacktester:
    """Backtester for evaluating forecasting model performance."""

    def __init__(self):
        """Initialize backtester."""
        self.forecaster = PriceForecaster()

    async def run_backtest(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        model: str = "default",
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
    ) -> BacktestMetrics:
        """
        Run backtest on historical data.

        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval
            prices: Full historical price data
            model: Model to test
            train_ratio: Proportion of data for training
            val_ratio: Proportion of data for validation
            test_ratio: Proportion of data for testing

        Returns:
            BacktestMetrics with performance statistics
        """
        if len(prices) < MLDefaults.MIN_TRAINING_POINTS:
            raise ValueError(f"Insufficient data: {len(prices)} points < {MLDefaults.MIN_TRAINING_POINTS}")

        # Validate ratios
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError("Train/val/test ratios must sum to 1.0")

        # Split data
        n_total = len(prices)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)
        n_test = n_total - n_train - n_val

        if n_test < MLDefaults.PREDICTION_HORIZON:
            raise ValueError("Insufficient test data for evaluation")

        train_data = prices[:n_train]
        val_data = prices[n_train : n_train + n_val]
        test_data = prices[n_train + n_val :]

        logger.info(f"Backtest data split: train={len(train_data)}, val={len(val_data)}, test={len(test_data)}")

        # Generate predictions on test set
        predictions = []
        actuals = []

        # Walk-forward testing
        context_length = max(MLDefaults.CONTEXT_LENGTH, 50)
        horizon = MLDefaults.PREDICTION_HORIZON

        for i in range(0, len(test_data) - horizon, horizon):
            if i + context_length + horizon > len(test_data):
                break

            # Use historical data as context
            context = train_data + val_data + test_data[:i]
            context = context[-context_length:]  # Limit context length

            # Actual future prices
            future_prices = test_data[i : i + horizon]
            actual_final_price = future_prices[-1]
            actuals.append(actual_final_price)

            try:
                # Generate forecast
                forecast = await self.forecaster.predict(
                    symbol=symbol, interval=interval, prices=context, model=model, horizon=horizon
                )

                predicted_final_price = forecast.predictions[-1]
                predictions.append(predicted_final_price)

            except Exception as e:
                logger.warning(f"Prediction failed at step {i}: {e}")
                # Use last known price as fallback
                predictions.append(context[-1])

        if len(predictions) == 0:
            raise RuntimeError("No predictions generated during backtest")

        # Calculate metrics
        metrics = self._calculate_metrics(predictions, actuals)

        return BacktestMetrics(
            model=model,
            symbol=symbol,
            interval=interval,
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            mape=metrics["mape"],
            direction_accuracy=metrics["direction_accuracy"],
            sample_size=len(predictions),
        )

    async def compare_models(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        models: list[str] | None = None,
        train_ratio: float = 0.7,
        test_ratio: float = 0.3,
    ) -> ModelComparison:
        """
        Compare multiple models on the same dataset.

        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval
            prices: Historical price data
            models: List of models to compare (None = all available)
            train_ratio: Training data proportion
            test_ratio: Testing data proportion

        Returns:
            ModelComparison with metrics for all models
        """
        if models is None:
            models = self.forecaster.get_available_models()

        comparison = ModelComparison(symbol=symbol, interval=interval)

        for model in models:
            try:
                logger.info(f"Testing model: {model}")
                metrics = await self.run_backtest(
                    symbol=symbol,
                    interval=interval,
                    prices=prices,
                    model=model,
                    train_ratio=train_ratio,
                    val_ratio=0.0,  # No validation in simple comparison
                    test_ratio=test_ratio,
                )
                comparison.add_metrics(metrics)
                logger.info(f"Model {model} MAE: {metrics.mae:.4f}")

            except Exception as e:
                logger.error(f"Failed to test model {model}: {e}")
                continue

        # Determine best model
        if comparison.metrics:
            best_metric = min(comparison.metrics, key=lambda m: m.mae)
            comparison.best_model = best_metric.model

        return comparison

    def _calculate_metrics(self, predictions: list[float], actuals: list[float]) -> dict:
        """Calculate performance metrics."""
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have same length")

        if len(predictions) == 0:
            return {
                "mae": float("inf"),
                "rmse": float("inf"),
                "mape": float("inf"),
                "direction_accuracy": 0.0,
            }

        # Convert to numpy arrays
        pred_array = np.array(predictions)
        actual_array = np.array(actuals)

        # Mean Absolute Error
        mae = np.mean(np.abs(pred_array - actual_array))

        # Root Mean Square Error
        rmse = np.sqrt(np.mean((pred_array - actual_array) ** 2))

        # Mean Absolute Percentage Error
        # Avoid division by zero
        non_zero_actuals = actual_array != 0
        if np.sum(non_zero_actuals) > 0:
            mape = (
                np.mean(
                    np.abs(
                        (pred_array[non_zero_actuals] - actual_array[non_zero_actuals]) / actual_array[non_zero_actuals]
                    )
                )
                * 100
            )
        else:
            mape = float("inf")

        # Direction accuracy
        pred_directions = np.diff(pred_array) > 0
        actual_directions = np.diff(actual_array) > 0
        direction_accuracy = np.mean(pred_directions == actual_directions) * 100

        return {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
            "direction_accuracy": float(direction_accuracy),
        }

    async def walk_forward_validation(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        model: str,
        window_size: int = 365,  # Days
        horizon: int = MLDefaults.PREDICTION_HORIZON,
    ) -> BacktestMetrics:
        """
        Walk-forward validation with rolling windows.

        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval
            prices: Historical prices
            model: Model to test
            window_size: Size of training window in data points
            horizon: Prediction horizon

        Returns:
            BacktestMetrics from walk-forward validation
        """
        predictions = []
        actuals = []

        # Convert window size to data points based on interval
        points_per_day = self._get_points_per_day(interval)
        window_points = window_size * points_per_day
        step_size = horizon  # Move forward by prediction horizon

        for i in range(0, len(prices) - window_points - horizon, step_size):
            # Training window
            train_end = i + window_points
            train_data = prices[i:train_end]

            # Test period
            test_start = train_end
            test_end = test_start + horizon
            test_data = prices[test_start:test_end]

            if len(test_data) < horizon:
                break

            actual_final = test_data[-1]
            actuals.append(actual_final)

            try:
                # Generate forecast
                forecast = await self.forecaster.predict(
                    symbol=symbol, interval=interval, prices=train_data, model=model, horizon=horizon
                )

                predicted_final = forecast.predictions[-1]
                predictions.append(predicted_final)

            except Exception as e:
                logger.warning(f"Walk-forward prediction failed at index {i}: {e}")
                predictions.append(train_data[-1])  # Fallback

        if not predictions:
            raise RuntimeError("No predictions generated in walk-forward validation")

        metrics = self._calculate_metrics(predictions, actuals)

        return BacktestMetrics(
            model=model,
            symbol=symbol,
            interval=interval,
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            mape=metrics["mape"],
            direction_accuracy=metrics["direction_accuracy"],
            sample_size=len(predictions),
        )

    def _get_points_per_day(self, interval: str) -> int:
        """Get number of data points per day for given interval."""
        mapping = {
            "1m": 1440,  # 24 * 60
            "5m": 288,  # 24 * 12
            "15m": 96,  # 24 * 4
            "30m": 48,  # 24 * 2
            "1h": 24,  # 24
            "4h": 6,  # 24 / 4
            "1d": 1,  # 1
        }
        return mapping.get(interval, 24)  # Default to hourly

    def __del__(self):
        """Cleanup resources."""
        self.forecaster = None
