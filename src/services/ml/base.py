"""
Base classes for ML forecasters.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from services.ml.models import ForecastResult


class ForecasterProtocol(Protocol):
    """Protocol defining the interface for forecasters."""

    async def predict(self, prices: list[float], horizon: int = 6) -> ForecastResult:
        """Generate price forecast."""
        ...

    def get_model_name(self) -> str:
        """Get model identifier."""
        ...


class BaseForecaster(ABC):
    """Abstract base class for all forecasters."""

    @abstractmethod
    async def predict(self, prices: list[float], horizon: int = 6) -> ForecastResult:
        """
        Generate price forecast.

        Args:
            prices: Historical closing prices
            horizon: Number of future candles to predict

        Returns:
            ForecastResult with predictions and confidence intervals
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get model identifier string."""
        pass

    def _validate_input(self, prices: list[float], horizon: int) -> None:
        """Validate input parameters."""
        if not prices:
            raise ValueError("Prices list cannot be empty")

        if len(prices) < 10:
            raise ValueError("Need at least 10 data points for forecasting")

        if horizon <= 0:
            raise ValueError("Horizon must be positive")

        if horizon > 50:
            raise ValueError("Horizon too large, maximum 50 candles")

    def _calculate_direction(self, current_price: float, predictions: list[float]) -> str:
        """Calculate price direction based on predictions."""
        if not predictions:
            return "neutral"

        final_prediction = predictions[-1]

        if final_prediction > current_price * 1.02:  # 2% threshold
            return "up"
        elif final_prediction < current_price * 0.98:  # 2% threshold
            return "down"
        else:
            return "neutral"

    def _calculate_confidence(self, predictions: list[float], low: list[float], high: list[float]) -> float:
        """Calculate model confidence based on prediction intervals."""
        if not predictions or not low or not high:
            return 50.0

        # Confidence inversely proportional to interval width
        total_width = sum(high[i] - low[i] for i in range(len(predictions)))
        avg_width = total_width / len(predictions)
        avg_price = sum(predictions) / len(predictions)

        if avg_price == 0:
            return 50.0

        # Normalize width as percentage of price
        normalized_width = avg_width / avg_price

        # Convert to confidence (smaller intervals = higher confidence)
        confidence = max(0, min(100, 100 - normalized_width * 1000))
        return round(confidence, 1)
