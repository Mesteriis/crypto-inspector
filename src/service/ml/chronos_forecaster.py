"""
Chronos Bolt Forecaster - Amazon's lightweight transformer model for time series.
"""

import logging
from datetime import datetime

try:
    import torch
    from chronos import ChronosPipeline

    CHRONOS_AVAILABLE = True
except ImportError:
    CHRONOS_AVAILABLE = False

from core.constants import MLDefaults
from service.ml.base import BaseForecaster
from service.ml.models import ForecastResult

logger = logging.getLogger(__name__)


class ChronosBoltForecaster(BaseForecaster):
    """Price forecaster using Amazon Chronos-T5 model."""

    def __init__(self, model_name: str = "amazon/chronos-t5-tiny"):
        """
        Initialize Chronos Bolt forecaster.

        Args:
            model_name: HuggingFace model identifier
        """
        if not CHRONOS_AVAILABLE:
            raise ImportError("chronos-forecasting not installed. Install with: pip install chronos-forecasting")

        self.model_name = model_name
        self.pipeline = None
        self._load_model()

    def _load_model(self) -> None:
        """Load Chronos pipeline."""
        try:
            logger.info(f"Loading Chronos model: {self.model_name}")
            self.pipeline = ChronosPipeline.from_pretrained(
                self.model_name,
                device_map="cpu",  # CPU-optimized
                dtype=torch.float32,  # Updated parameter name
            )
            logger.info("Chronos model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Chronos model: {e}")
            raise

    async def predict(self, prices: list[float], horizon: int = 6) -> ForecastResult:
        """
        Generate price forecast using Chronos Bolt.

        Args:
            prices: Historical closing prices
            horizon: Number of future candles to predict

        Returns:
            ForecastResult with predictions and confidence intervals
        """
        self._validate_input(prices, horizon)

        try:
            # Prepare data - Chronos expects tensor
            import torch

            context_length = min(len(prices), MLDefaults.CONTEXT_LENGTH)
            recent_prices = prices[-context_length:]

            # Convert to tensor
            context = torch.tensor(recent_prices, dtype=torch.float32).unsqueeze(0)

            # Generate forecast
            forecast = self.pipeline.predict(
                inputs=context,
                prediction_length=horizon,
                num_samples=20,  # For confidence intervals
                temperature=1.0,
            )

            # Extract predictions and quantiles
            # Forecast shape: [batch_size, num_samples, prediction_length]
            # We need: [prediction_length] for median, lower, upper quantiles

            # Convert to numpy for easier manipulation
            import numpy as np

            forecast_np = forecast.numpy()  # Shape: [1, 20, 3]

            # Extract median (50th percentile) across samples
            median_forecast = np.median(forecast_np[0], axis=0).tolist()  # Shape: [3]

            # Extract quantiles (10th and 90th percentiles)
            lower_quantile = np.percentile(forecast_np[0], 10, axis=0).tolist()  # Shape: [3]
            upper_quantile = np.percentile(forecast_np[0], 90, axis=0).tolist()  # Shape: [3]

            # Calculate direction and confidence
            direction = self._calculate_direction(prices[-1], median_forecast)
            confidence = self._calculate_confidence(median_forecast, lower_quantile, upper_quantile)

            return ForecastResult(
                symbol="",  # Will be filled by caller
                interval="",  # Will be filled by caller
                model=self.get_model_name(),
                predictions=[float(p) for p in median_forecast],
                confidence_low=[float(p) for p in lower_quantile],
                confidence_high=[float(p) for p in upper_quantile],
                direction=direction,
                confidence_pct=confidence,
                timestamp=datetime.now(),
                horizon=horizon,
            )

        except Exception as e:
            logger.error(f"Chronos prediction failed: {e}")
            # Fallback to naive forecast
            return self._naive_forecast(prices, horizon)

    def _naive_forecast(self, prices: list[float], horizon: int) -> ForecastResult:
        """Simple fallback forecast if model fails."""
        last_price = prices[-1]
        predictions = [last_price] * horizon
        confidence_range = last_price * 0.02  # ±2%

        return ForecastResult(
            symbol="",
            interval="",
            model=self.get_model_name(),
            predictions=predictions,
            confidence_low=[p - confidence_range for p in predictions],
            confidence_high=[p + confidence_range for p in predictions],
            direction="neutral",
            confidence_pct=30.0,  # Low confidence for fallback
            timestamp=datetime.now(),
            horizon=horizon,
        )

    def get_model_name(self) -> str:
        """Get model identifier."""
        return "chronos-bolt"

    def __del__(self):
        """Cleanup model resources."""
        if hasattr(self, "pipeline") and self.pipeline:
            del self.pipeline
