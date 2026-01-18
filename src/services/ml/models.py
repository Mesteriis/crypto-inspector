"""
Dataclasses for ML forecasting models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ForecastResult:
    """Result of a price forecast."""

    symbol: str
    interval: str
    model: str  # Model identifier

    # Predictions
    predictions: list[float]  # Forecasted prices for next N candles
    confidence_low: list[float]  # Lower bound of 80% confidence interval
    confidence_high: list[float]  # Upper bound of 80% confidence interval

    # Analysis
    direction: str  # "up" / "down" / "neutral"
    confidence_pct: float  # Model confidence 0-100%

    # Metadata
    timestamp: datetime
    horizon: int = 6  # Number of candles predicted

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "model": self.model,
            "predictions": [round(p, 2) for p in self.predictions],
            "confidence_low": [round(p, 2) for p in self.confidence_low],
            "confidence_high": [round(p, 2) for p in self.confidence_high],
            "direction": self.direction,
            "confidence_pct": round(self.confidence_pct, 1),
            "timestamp": self.timestamp.isoformat(),
            "horizon": self.horizon,
        }


@dataclass
class BacktestMetrics:
    """Metrics from backtesting a forecasting model."""

    model: str
    symbol: str
    interval: str

    # Error metrics
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Square Error
    mape: float  # Mean Absolute Percentage Error

    # Direction accuracy
    direction_accuracy: float  # Percentage of correct directions

    # Statistical significance
    sample_size: int  # Number of predictions tested
    confidence_level: float = 0.95  # Statistical confidence level

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "model": self.model,
            "symbol": self.symbol,
            "interval": self.interval,
            "mae": round(self.mae, 4),
            "rmse": round(self.rmse, 4),
            "mape": round(self.mape, 2),
            "direction_accuracy": round(self.direction_accuracy, 2),
            "sample_size": self.sample_size,
            "confidence_level": self.confidence_level,
        }


@dataclass
class ModelComparison:
    """Comparison of multiple models on the same dataset."""

    symbol: str
    interval: str
    metrics: list[BacktestMetrics] = field(default_factory=list)
    best_model: str = ""

    def add_metrics(self, metrics: BacktestMetrics) -> None:
        """Add metrics for a model."""
        self.metrics.append(metrics)

    def get_ranked_models(self) -> list[tuple[str, float]]:
        """Get models ranked by MAE (ascending)."""
        return sorted([(m.model, m.mae) for m in self.metrics], key=lambda x: x[1])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        ranked = self.get_ranked_models()
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "models": [m.to_dict() for m in self.metrics],
            "best_model": self.best_model,
            "rankings": [{"model": model, "mae": round(mae, 4)} for model, mae in ranked],
        }
