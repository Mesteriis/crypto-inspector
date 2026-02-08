"""
Main Price Forecaster - Facade for all ML forecasting models.
"""

import logging

from core.constants import MLDefaults, MLModels
from service.ml.base import BaseForecaster
from service.ml.chronos_forecaster import ChronosBoltForecaster
from service.ml.ensemble_forecaster import EnsembleForecaster
from service.ml.models import ForecastResult
from service.ml.neural_forecaster import NeuralProphetForecaster
from service.ml.stats_forecaster import StatsForecastForecaster

logger = logging.getLogger(__name__)


class PriceForecaster:
    """Main facade for price forecasting with multiple ML models."""

    def __init__(self, default_model: str = MLModels.DEFAULT):
        """
        Initialize price forecaster.

        Args:
            default_model: Default model to use for predictions
        """
        self.default_model = default_model
        self._models: dict[str, BaseForecaster] = {}
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize all available forecasting models."""
        # Initialize models with lazy loading
        # Order matters - first available becomes fallback default
        model_classes = {
            MLModels.STATSFORECAST_ARIMA: StatsForecastForecaster,  # Most reliable, no external deps
            MLModels.NEURALPROPHET: NeuralProphetForecaster,  # Local ML
            MLModels.CHRONOS_BOLT: ChronosBoltForecaster,  # Requires HuggingFace download
            MLModels.ENSEMBLE: EnsembleForecaster,  # Combines all available
        }

        for model_name, model_class in model_classes.items():
            try:
                self._models[model_name] = model_class()
                logger.info(f"Initialized {model_name} forecaster")
            except Exception as e:
                logger.warning(f"Failed to initialize {model_name}: {e}")
                # Will be created on-demand if needed

        # Set fallback default if primary default is unavailable
        if self.default_model not in self._models and self._models:
            fallback = list(self._models.keys())[0]
            logger.warning(f"Default model {self.default_model} unavailable, using {fallback}")
            self.default_model = fallback

        logger.info(f"ML Forecaster ready with {len(self._models)} models: {list(self._models.keys())}")

    def _get_model(self, model_name: str) -> BaseForecaster:
        """Get or create model instance."""
        if model_name not in self._models:
            # Lazy initialization
            model_classes = {
                MLModels.CHRONOS_BOLT: ChronosBoltForecaster,
                MLModels.STATSFORECAST_ARIMA: StatsForecastForecaster,
                MLModels.NEURALPROPHET: NeuralProphetForecaster,
                MLModels.ENSEMBLE: EnsembleForecaster,
            }

            if model_name in model_classes:
                try:
                    self._models[model_name] = model_classes[model_name]()
                    logger.info(f"Dynamically initialized {model_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize {model_name}: {e}")
                    raise
            else:
                raise ValueError(f"Unknown model: {model_name}")

        return self._models[model_name]

    async def predict(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        model: str = "default",
        horizon: int = MLDefaults.PREDICTION_HORIZON,
    ) -> ForecastResult:
        """
        Generate price forecast.

        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            interval: Candlestick interval (e.g., "1h", "4h", "1d")
            prices: Historical closing prices
            model: Model to use ("default", "chronos-bolt", "statsforecast", "neuralprophet", "ensemble")
            horizon: Number of candles to predict ahead

        Returns:
            ForecastResult with predictions and metadata
        """
        # Validate inputs
        if not prices:
            raise ValueError("Prices list cannot be empty")

        if len(prices) < MLDefaults.MIN_TRAINING_POINTS:
            raise ValueError(f"Need at least {MLDefaults.MIN_TRAINING_POINTS} data points")

        if interval not in MLDefaults.SUPPORTED_INTERVALS:
            raise ValueError(f"Unsupported interval: {interval}. Supported: {MLDefaults.SUPPORTED_INTERVALS}")

        # Select model
        if model == "default":
            model = self.default_model

        if model not in MLModels.ALL + [MLModels.ENSEMBLE]:
            raise ValueError(f"Unknown model: {model}")

        # Get model and generate forecast
        forecaster = self._get_model(model)
        result = await forecaster.predict(prices, horizon)

        # Fill metadata
        result.symbol = symbol
        result.interval = interval

        logger.info(
            f"Generated {model} forecast for {symbol} {interval}: "
            f"{result.direction} ({result.confidence_pct:.1f}% confidence)"
        )

        return result

    async def predict_all_models(
        self,
        symbol: str,
        interval: str,
        prices: list[float],
        horizon: int = MLDefaults.PREDICTION_HORIZON,
    ) -> dict[str, ForecastResult]:
        """
        Generate forecasts using all available models.

        Args:
            symbol: Trading pair symbol
            interval: Candlestick interval
            prices: Historical closing prices
            horizon: Prediction horizon

        Returns:
            Dictionary mapping model names to ForecastResults
        """
        results = {}

        for model_name in self.get_available_models():
            try:
                result = await self.predict(symbol, interval, prices, model_name, horizon)
                results[model_name] = result
            except Exception as e:
                logger.error(f"Failed to generate forecast with {model_name}: {e}")
                continue

        return results

    def get_available_models(self) -> list[str]:
        """Get list of available model names."""
        return list(self._models.keys())

    def get_default_model(self) -> str:
        """Get default model name."""
        return self.default_model

    def set_default_model(self, model: str) -> None:
        """
        Set default model.

        Args:
            model: Model name to set as default
        """
        if model not in MLModels.ALL + [MLModels.ENSEMBLE]:
            raise ValueError(f"Invalid model: {model}")

        self.default_model = model
        logger.info(f"Default model set to: {model}")

    async def get_model_info(self) -> dict[str, dict]:
        """
        Get information about all models.

        Returns:
            Dictionary with model info
        """
        info = {}

        for model_name in MLModels.ALL + [MLModels.ENSEMBLE]:
            try:
                model = self._get_model(model_name)
                info[model_name] = {
                    "name": MLModels.get_display_name(model_name),
                    "available": True,
                    "model_id": model.get_model_name(),
                }
            except Exception:
                info[model_name] = {
                    "name": MLModels.get_display_name(model_name),
                    "available": False,
                    "error": "Model initialization failed",
                }

        return info

    def __del__(self):
        """Cleanup resources."""
        self._models.clear()
