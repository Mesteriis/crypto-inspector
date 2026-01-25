"""
StatsForecast Forecaster - Statistical models like AutoARIMA.
"""

import logging
from datetime import datetime

try:
    import numpy as np
    import pandas as pd
    from statsforecast import StatsForecast
    from statsforecast.models import AutoARIMA

    STATSFORCEAST_AVAILABLE = True
except ImportError:
    STATSFORCEAST_AVAILABLE = False

from core.constants import MLDefaults
from service.ml.base import BaseForecaster
from service.ml.models import ForecastResult

logger = logging.getLogger(__name__)


class StatsForecastForecaster(BaseForecaster):
    """Price forecaster using StatsForecast AutoARIMA model."""

    def __init__(self):
        """Initialize StatsForecast forecaster."""
        if not STATSFORCEAST_AVAILABLE:
            raise ImportError("statsforecast not installed. Install with: pip install statsforecast")

        self.model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the forecasting model."""
        try:
            self.model = StatsForecast(
                models=[AutoARIMA(season_length=24)],  # Daily seasonality for hourly data
                freq=1,  # Frequency of observations
            )
            logger.info("StatsForecast AutoARIMA initialized")
        except Exception as e:
            logger.error(f"Failed to initialize StatsForecast: {e}")
            raise

    async def predict(self, prices: list[float], horizon: int = 6) -> ForecastResult:
        """
        Generate price forecast using AutoARIMA.

        Args:
            prices: Historical closing prices
            horizon: Number of future candles to predict

        Returns:
            ForecastResult with predictions and confidence intervals
        """
        self._validate_input(prices, horizon)

        try:
            # Prepare data for StatsForecast
            # Need to convert to DataFrame with time index
            n_points = min(len(prices), MLDefaults.CONTEXT_LENGTH)
            recent_prices = prices[-n_points:]

            # Create time series data with required unique_id
            df = pd.DataFrame(
                {
                    "unique_id": ["series_1"] * len(recent_prices),  # Required by StatsForecast
                    "ds": range(len(recent_prices)),  # Time index
                    "y": recent_prices,  # Values
                }
            )

            # Fit model and predict
            fitted_model = self.model.fit(df)
            forecast_df = fitted_model.predict(h=horizon)

            # Extract predictions
            predictions = forecast_df["AutoARIMA"].tolist()

            # Calculate confidence intervals (using residuals)
            fitted_values = fitted_model.forecast(df)["fitted"]
            residuals = np.array(recent_prices) - np.array(fitted_values)
            std_residual = np.std(residuals)

            # 80% confidence intervals
            confidence_width = 1.28 * std_residual  # 80% z-score
            confidence_low = [p - confidence_width for p in predictions]
            confidence_high = [p + confidence_width for p in predictions]

            # Calculate direction and confidence
            direction = self._calculate_direction(prices[-1], predictions)
            confidence = self._calculate_confidence(predictions, confidence_low, confidence_high)

            return ForecastResult(
                symbol="",  # Will be filled by caller
                interval="",  # Will be filled by caller
                model=self.get_model_name(),
                predictions=[float(p) for p in predictions],
                confidence_low=[float(p) for p in confidence_low],
                confidence_high=[float(p) for p in confidence_high],
                direction=direction,
                confidence_pct=confidence,
                timestamp=datetime.now(),
                horizon=horizon,
            )

        except Exception as e:
            logger.error(f"StatsForecast prediction failed: {e}")
            # Fallback to trend-based forecast
            return self._fallback_forecast(prices, horizon)

    def _fallback_forecast(self, prices: list[float], horizon: int) -> ForecastResult:
        """Fallback forecast using linear trend."""
        last_price = prices[-1]

        # Calculate trend from last few points
        if len(prices) >= 5:
            recent_trend = (prices[-1] - prices[-5]) / 5
        else:
            recent_trend = 0

        # Generate predictions with trend
        predictions = [last_price + recent_trend * (i + 1) for i in range(horizon)]

        # Confidence intervals
        confidence_range = last_price * 0.03  # ±3%
        confidence_low = [p - confidence_range for p in predictions]
        confidence_high = [p + confidence_range for p in predictions]

        return ForecastResult(
            symbol="",
            interval="",
            model=self.get_model_name(),
            predictions=predictions,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
            direction="neutral" if abs(recent_trend) < 0.001 else ("up" if recent_trend > 0 else "down"),
            confidence_pct=25.0,  # Low confidence for fallback
            timestamp=datetime.now(),
            horizon=horizon,
        )

    def get_model_name(self) -> str:
        """Get model identifier."""
        return "statsforecast"

    def __del__(self):
        """Cleanup model resources."""
        self.model = None
