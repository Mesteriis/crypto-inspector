"""SQLAlchemy model for storing ML prediction results."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class MLPredictionRecord(Base):
    """
    Database model for storing machine learning prediction results.

    This table stores both predicted values and actual realized prices
    for comprehensive backtesting and performance analysis.
    """

    __tablename__ = "ml_prediction_records"

    # === Primary Key ===
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for each prediction record",
    )

    # === Prediction Metadata ===
    symbol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Trading pair symbol (e.g., BTC/USDT, ETH/USDT)",
    )
    interval: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Time interval (e.g., 1h, 4h, 1d)",
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="ML model used for prediction (e.g., chronos-bolt, statsforecast)",
    )

    # === Timing Information ===
    prediction_timestamp: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Unix timestamp when prediction was made (milliseconds)",
    )
    prediction_horizon: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="How many candles ahead was predicted",
    )
    actual_timestamp: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="When the actual price was realized (milliseconds)",
    )

    # === Price Data ===
    predicted_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=False,
        comment="Predicted price value",
    )
    actual_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=True,
        comment="Actual realized price (filled when available)",
    )
    context_prices: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Historical prices used for context (JSON array)",
    )

    # === Confidence Metrics ===
    confidence_percentage: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=False,
        comment="Model confidence level (0-100%)",
    )
    confidence_low: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=True,
        comment="Lower bound of confidence interval",
    )
    confidence_high: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=True,
        comment="Upper bound of confidence interval",
    )
    direction_prediction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Predicted direction (up/down/neutral)",
    )

    # === Error Measurements ===
    absolute_error: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=True,
        comment="Absolute difference between predicted and actual",
    )
    percentage_error: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
        comment="Percentage error ((actual-predicted)/actual * 100)",
    )
    direction_correct: Mapped[bool | None] = mapped_column(
        nullable=True,
        comment="Whether direction prediction was correct",
    )

    # === Performance Tracking ===
    confidence_coefficient: Mapped[float | None] = mapped_column(
        Numeric(precision=5, scale=4),
        nullable=True,
        comment="Model's historical confidence coefficient (0-1)",
    )
    weighted_confidence: Mapped[float | None] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
        comment="Weighted confidence score based on model performance",
    )

    # === Metadata ===
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When this record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When this record was last updated",
    )

    # === Indexes for Performance ===
    __table_args__ = (
        # Index for querying by symbol and interval
        Index("ix_ml_prediction_symbol_interval", "symbol", "interval"),
        # Index for time-based queries
        Index("ix_ml_prediction_timestamp", "prediction_timestamp"),
        # Index for model performance analysis
        Index("ix_ml_prediction_model", "model_name"),
        # Index for retrieving recent predictions
        Index("ix_ml_prediction_created_at", "created_at"),
        # Composite index for backtesting queries
        Index("ix_ml_prediction_symbol_model_timestamp", "symbol", "model_name", "prediction_timestamp"),
        {"comment": "Stores ML prediction results for backtesting and performance analysis"},
    )

    def __repr__(self) -> str:
        return (
            f"<MLPredictionRecord("
            f"id={self.id}, "
            f"symbol={self.symbol!r}, "
            f"model={self.model_name!r}, "
            f"predicted={self.predicted_price}, "
            f"actual={self.actual_price}"
            f")>"
        )


class MLModelPerformance(Base):
    """
    Database model for tracking model performance statistics.

    Stores aggregated performance metrics for each model-symbol combination.
    """

    __tablename__ = "ml_model_performance"

    # === Composite Primary Key ===
    symbol: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Trading pair symbol",
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="ML model name",
    )
    interval: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="Time interval",
    )

    # === Performance Metrics ===
    total_predictions: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Total number of predictions made",
    )
    evaluated_predictions: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Number of predictions with actual results",
    )

    # === Accuracy Metrics ===
    mean_absolute_error: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=True,
        comment="Mean absolute error across all predictions",
    )
    root_mean_square_error: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=True,
        comment="Root mean square error",
    )
    mean_absolute_percentage_error: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
        comment="Mean absolute percentage error",
    )
    direction_accuracy: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
        comment="Percentage of correct direction predictions",
    )

    # === Confidence Statistics ===
    average_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True,
        comment="Average model confidence across predictions",
    )
    confidence_coefficient: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=4),
        nullable=True,
        comment="Calculated confidence coefficient (0-1)",
    )

    # === Timestamps ===
    first_prediction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of first prediction",
    )
    last_prediction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of most recent prediction",
    )
    last_evaluation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When performance was last calculated",
    )

    # === Metadata ===
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_ml_performance_model", "model_name"),
        Index("ix_ml_performance_updated", "updated_at"),
        {"comment": "Aggregated performance statistics for ML models"},
    )

    def __repr__(self) -> str:
        return (
            f"<MLModelPerformance("
            f"symbol={self.symbol!r}, "
            f"model={self.model_name!r}, "
            f"MAE={self.mean_absolute_error}"
            f")>"
        )
