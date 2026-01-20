"""
Ensemble Forecaster - Combines multiple models with weighted averaging.
"""

import asyncio
import logging
from datetime import datetime

from core.constants import MLModels
from service.ml.base import BaseForecaster
from service.ml.chronos_forecaster import ChronosBoltForecaster
from service.ml.models import ForecastResult
from service.ml.neural_forecaster import NeuralProphetForecaster
from service.ml.stats_forecaster import StatsForecastForecaster

logger = logging.getLogger(__name__)


class EnsembleForecaster(BaseForecaster):
    """Ensemble forecaster combining multiple models with weighted averaging."""

    def __init__(self):
        """Initialize ensemble forecaster with all component models."""
        self.models: dict[str, BaseForecaster] = {}
        self.weights: dict[str, float] = {
            MLModels.CHRONOS_BOLT: 0.4,  # Highest weight
            MLModels.STATSFORECAST_ARIMA: 0.3,  # Medium weight
            MLModels.NEURALPROPHET: 0.3,  # Medium weight
        }
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize all component forecasters."""
        try:
            self.models[MLModels.CHRONOS_BOLT] = ChronosBoltForecaster()
            logger.info("Chronos Bolt forecaster initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Chronos Bolt: {e}")
            self.weights[MLModels.CHRONOS_BOLT] = 0

        try:
            self.models[MLModels.STATSFORECAST_ARIMA] = StatsForecastForecaster()
            logger.info("StatsForecast forecaster initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize StatsForecast: {e}")
            self.weights[MLModels.STATSFORECAST_ARIMA] = 0

        try:
            self.models[MLModels.NEURALPROPHET] = NeuralProphetForecaster()
            logger.info("NeuralProphet forecaster initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize NeuralProphet: {e}")
            self.weights[MLModels.NEURALPROPHET] = 0

        # Normalize weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            for model in self.weights:
                self.weights[model] /= total_weight
        else:
            # Fallback: equal weights
            equal_weight = 1.0 / len([w for w in self.weights.values() if w > 0])
            for model in self.weights:
                if self.weights[model] > 0:
                    self.weights[model] = equal_weight

    async def predict(self, prices: list[float], horizon: int = 6) -> ForecastResult:
        """
        Generate ensemble forecast by combining all available models.

        Args:
            prices: Historical closing prices
            horizon: Number of future candles to predict

        Returns:
            ForecastResult with ensemble predictions
        """
        self._validate_input(prices, horizon)

        if not self.models:
            raise RuntimeError("No models available for ensemble forecasting")

        # Get predictions from all models concurrently
        tasks = []
        active_models = []

        for model_name, model in self.models.items():
            if self.weights[model_name] > 0:
                task = asyncio.create_task(model.predict(prices, horizon))
                tasks.append(task)
                active_models.append(model_name)

        if not tasks:
            raise RuntimeError("No active models available")

        # Wait for all predictions
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and calculate ensemble
        valid_results = []
        valid_weights = []

        for i, (model_name, result) in enumerate(zip(active_models, results)):
            if isinstance(result, Exception):
                logger.warning(f"Model {model_name} failed: {result}")
                continue

            if isinstance(result, ForecastResult):
                valid_results.append(result)
                valid_weights.append(self.weights[model_name])

        if not valid_results:
            raise RuntimeError("All models failed to produce forecasts")

        # Calculate ensemble prediction
        ensemble_pred = self._weighted_average([r.predictions for r in valid_results], valid_weights)

        ensemble_low = self._weighted_average([r.confidence_low for r in valid_results], valid_weights)

        ensemble_high = self._weighted_average([r.confidence_high for r in valid_results], valid_weights)

        # Ensemble confidence and direction
        avg_confidence = sum(r.confidence_pct * w for r, w in zip(valid_results, valid_weights)) / sum(valid_weights)
        ensemble_direction = self._calculate_direction(prices[-1], ensemble_pred)

        # List of contributing models
        model_list = ", ".join([r.model for r in valid_results])

        return ForecastResult(
            symbol="",  # Will be filled by caller
            interval="",  # Will be filled by caller
            model=f"ensemble[{model_list}]",
            predictions=ensemble_pred,
            confidence_low=ensemble_low,
            confidence_high=ensemble_high,
            direction=ensemble_direction,
            confidence_pct=avg_confidence,
            timestamp=datetime.now(),
            horizon=horizon,
        )

    def _weighted_average(self, arrays: list[list[float]], weights: list[float]) -> list[float]:
        """Calculate weighted average of arrays."""
        if not arrays or not weights or len(arrays) != len(weights):
            return []

        # Check if we have single values instead of arrays
        if all(isinstance(arr, (int, float)) for arr in arrays):
            # Weighted average of single values
            weighted_sum = sum(val * weight for val, weight in zip(arrays, weights))
            total_weight = sum(weights)
            return [weighted_sum / total_weight if total_weight > 0 else 0]

        # Regular array averaging
        length = len(arrays[0])
        result = []

        for i in range(length):
            weighted_sum = sum(arr[i] * weights[j] for j, arr in enumerate(arrays))
            total_weight = sum(weights)
            result.append(weighted_sum / total_weight if total_weight > 0 else 0)

        return result

    def update_weights(self, new_weights: dict[str, float]) -> None:
        """
        Update model weights.

        Args:
            new_weights: Dictionary mapping model names to weights
        """
        # Validate weights
        for model in new_weights:
            if model not in self.weights:
                raise ValueError(f"Unknown model: {model}")

        # Update weights
        total = sum(new_weights.values())
        if total <= 0:
            raise ValueError("Weights must sum to positive value")

        # Normalize
        for model in new_weights:
            self.weights[model] = new_weights[model] / total

        logger.info(f"Updated ensemble weights: {self.weights}")

    def get_model_weights(self) -> dict[str, float]:
        """Get current model weights."""
        return self.weights.copy()

    def get_active_models(self) -> list[str]:
        """Get list of currently active models."""
        return [name for name, weight in self.weights.items() if weight > 0]

    def get_model_name(self) -> str:
        """Get model identifier."""
        return "ensemble"

    def __del__(self):
        """Cleanup model resources."""
        self.models.clear()
