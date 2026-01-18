"""
NeuralProphet Forecaster - Facebook's neural forecasting model.
"""

import logging
from datetime import datetime

try:
    import numpy as np
    import pandas as pd
    from neuralprophet import NeuralProphet

    NEURALPROPHET_AVAILABLE = True
except ImportError:
    NEURALPROPHET_AVAILABLE = False

from core.constants import MLDefaults
from services.ml.base import BaseForecaster
from services.ml.models import ForecastResult

logger = logging.getLogger(__name__)


class NeuralProphetForecaster(BaseForecaster):
    """Price forecaster using NeuralProphet model."""

    def __init__(self):
        """Initialize NeuralProphet forecaster."""
        if not NEURALPROPHET_AVAILABLE:
            raise ImportError("neuralprophet not installed. " "Install with: pip install neuralprophet")

        self.model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the NeuralProphet model."""
        # Note: Model will be created fresh for each prediction to avoid "already fitted" errors
        self.model = None
        logger.info("NeuralProphet ready for on-demand initialization")

    async def predict(self, prices: list[float], horizon: int = 6) -> ForecastResult:
        """
        Generate price forecast using NeuralProphet.

        Args:
            prices: Historical closing prices
            horizon: Number of future candles to predict

        Returns:
            ForecastResult with predictions and confidence intervals
        """
        self._validate_input(prices, horizon)

        try:
            # Create fresh model for each prediction to avoid "already fitted" errors
            self.model = NeuralProphet(
                growth="linear",
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=True,
                seasonality_mode="additive",
                epochs=5,  # Reduced epochs for speed
                batch_size=16,
                learning_rate=0.01,
                collect_metrics=["MAE"],
            )

            # Prepare data for NeuralProphet
            n_points = min(len(prices), MLDefaults.CONTEXT_LENGTH)
            recent_prices = prices[-n_points:]

            # Create DataFrame with datetime index
            dates = pd.date_range(
                start="2024-01-01",
                periods=len(recent_prices),
                freq="H",  # Hourly frequency
            )

            df = pd.DataFrame(
                {
                    "ds": dates,
                    "y": recent_prices,
                }
            )

            # Fit model
            metrics = self.model.fit(df, freq="H")
            logger.debug(f"NeuralProphet training metrics: {metrics}")

            # Create future dataframe for predictions
            future = self.model.make_future_dataframe(df, periods=horizon, n_historic_predictions=False)

            # Generate forecast
            forecast = self.model.predict(future)

            # Extract predictions
            predictions = forecast["yhat1"].tail(horizon).tolist()

            # Extract uncertainty intervals
            if "yhat1_lower" in forecast.columns and "yhat1_upper" in forecast.columns:
                confidence_low = forecast["yhat1_lower"].tail(horizon).tolist()
                confidence_high = forecast["yhat1_upper"].tail(horizon).tolist()
            else:
                # Fallback confidence intervals
                std_dev = np.std(recent_prices[-20:]) if len(recent_prices) >= 20 else np.std(recent_prices)
                confidence_range = 1.28 * std_dev  # 80% confidence
                confidence_low = [p - confidence_range for p in predictions]
                confidence_high = [p + confidence_range for p in predictions]

            # Handle NaN values
            predictions = [p if not np.isnan(p) else prices[-1] for p in predictions]
            confidence_low = [p if not np.isnan(p) else prices[-1] * 0.98 for p in confidence_low]
            confidence_high = [p if not np.isnan(p) else prices[-1] * 1.02 for p in confidence_high]

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
            logger.error(f"NeuralProphet prediction failed: {e}")
            # Fallback to exponential smoothing
            return self._fallback_forecast(prices, horizon)

    def _fallback_forecast(self, prices: list[float], horizon: int) -> ForecastResult:
        """Fallback forecast using exponential smoothing."""
        last_price = prices[-1]

        # Simple exponential smoothing with trend
        alpha = 0.3  # Smoothing factor
        if len(prices) >= 2:
            trend = prices[-1] - prices[-2]
        else:
            trend = 0

        predictions = []
        current_price = last_price
        for i in range(horizon):
            current_price = alpha * (current_price + trend) + (1 - alpha) * current_price
            predictions.append(current_price)

        # Confidence intervals
        confidence_range = last_price * 0.025  # ±2.5%
        confidence_low = [p - confidence_range for p in predictions]
        confidence_high = [p + confidence_range for p in predictions]

        return ForecastResult(
            symbol="",
            interval="",
            model=self.get_model_name(),
            predictions=predictions,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
            direction="neutral" if abs(trend) < 1 else ("up" if trend > 0 else "down"),
            confidence_pct=20.0,  # Low confidence for fallback
            timestamp=datetime.now(),
            horizon=horizon,
        )

    def get_model_name(self) -> str:
        """Get model identifier."""
        return "neuralprophet"

    def __del__(self):
        """Cleanup model resources."""
        self.model = None
