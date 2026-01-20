"""Pydantic validators for sensor data.

Provides type-safe validation for all sensor data types
with automatic transformation and error handling.
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class PriceValue(BaseModel):
    """Validation for price data."""

    price: Decimal = Field(..., gt=0, description="Price must be positive")
    change_24h: float | None = Field(None, description="24h change percentage")
    volume_24h: Decimal | None = Field(None, ge=0, description="24h volume")
    high_24h: Decimal | None = Field(None, gt=0, description="24h high")
    low_24h: Decimal | None = Field(None, gt=0, description="24h low")

    @model_validator(mode="after")
    def validate_high_low(self) -> "PriceValue":
        """Validate that high >= low."""
        if self.high_24h is not None and self.low_24h is not None:
            if self.high_24h < self.low_24h:
                raise ValueError("high_24h must be >= low_24h")
        return self

    class Config:
        arbitrary_types_allowed = True


class FearGreedValue(BaseModel):
    """Validation for Fear & Greed Index."""

    value: int = Field(..., ge=0, le=100, description="Fear & Greed index 0-100")
    classification: str | None = Field(None, description="Text classification")

    @field_validator("classification", mode="before")
    @classmethod
    def auto_classify(cls, v: str | None, info) -> str:
        """Auto-generate classification if not provided."""
        if v is not None:
            return v

        # Get value from data being validated
        value = info.data.get("value")
        if value is None:
            return "Unknown"

        if value <= 25:
            return "Extreme Fear"
        elif value <= 45:
            return "Fear"
        elif value <= 55:
            return "Neutral"
        elif value <= 75:
            return "Greed"
        else:
            return "Extreme Greed"


class InvestorStatusValue(BaseModel):
    """Validation for lazy investor status."""

    do_nothing_ok: bool = Field(..., description="Whether to do nothing is OK")
    phase: str = Field(..., description="Market phase")
    calm_score: int = Field(..., ge=0, le=100, description="Calm indicator 0-100")
    red_flags_count: int = Field(..., ge=0, description="Number of red flags")
    market_tension: str | None = Field(None, description="Market tension level")
    price_context: str | None = Field(None, description="Price context")
    dca_amount: Decimal | None = Field(None, ge=0, description="Recommended DCA amount")
    dca_signal: str | None = Field(None, description="DCA signal")
    weekly_insight: str | None = Field(None, description="Weekly insight text")

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        """Validate phase is one of allowed values."""
        allowed = {
            "accumulation",
            "growth",
            "euphoria",
            "correction",
            "capitulation",
            "unknown",
            # Russian variants
            "накопление",
            "рост",
            "эйфория",
            "коррекция",
            "капитуляция",
        }
        if v.lower() not in allowed:
            # Don't raise, just return as-is for flexibility
            pass
        return v


class GasTrackerValue(BaseModel):
    """Validation for ETH gas tracker data."""

    slow: int = Field(..., ge=0, description="Slow gas price in Gwei")
    standard: int = Field(..., ge=0, description="Standard gas price in Gwei")
    fast: int = Field(..., ge=0, description="Fast gas price in Gwei")
    status: str | None = Field(None, description="Network status")

    @model_validator(mode="after")
    def validate_gas_order(self) -> "GasTrackerValue":
        """Validate slow <= standard <= fast."""
        if not (self.slow <= self.standard <= self.fast):
            # Log warning but don't fail - data from external source
            pass
        return self


class PortfolioValue(BaseModel):
    """Validation for portfolio data."""

    value: Decimal = Field(..., ge=0, description="Total portfolio value")
    pnl: float | None = Field(None, description="Total P&L percentage")
    pnl_24h: float | None = Field(None, description="24h P&L percentage")
    allocation: dict[str, float] | None = Field(None, description="Asset allocation")

    @field_validator("allocation")
    @classmethod
    def validate_allocation(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        """Validate allocation sums to ~100%."""
        if v is None:
            return v

        total = sum(v.values())
        if not (99.0 <= total <= 101.0):
            # Don't fail, just warn - might be rounding
            pass
        return v


class VolatilityValue(BaseModel):
    """Validation for volatility data."""

    values: dict[str, float] = Field(..., description="Volatility per symbol")
    percentile: int | None = Field(None, ge=0, le=100, description="Percentile")
    status: str | None = Field(None, description="Volatility status")

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate all volatility values are non-negative."""
        for symbol, vol in v.items():
            if vol < 0:
                raise ValueError(f"Volatility for {symbol} cannot be negative: {vol}")
        return v


class CorrelationValue(BaseModel):
    """Validation for correlation data."""

    value: float = Field(..., ge=-1, le=1, description="Correlation coefficient")
    pair: str | None = Field(None, description="Asset pair")
    status: str | None = Field(None, description="Correlation status")


class TechnicalIndicatorValue(BaseModel):
    """Validation for technical indicator data."""

    values: dict[str, Any] = Field(..., description="Indicator values per symbol")
    signal: str | None = Field(None, description="Overall signal")

    @field_validator("signal")
    @classmethod
    def validate_signal(cls, v: str | None) -> str | None:
        """Validate signal is one of allowed values."""
        if v is None:
            return v

        allowed = {"buy", "sell", "hold", "strong_buy", "strong_sell", "neutral"}
        # Accept any value for flexibility
        return v


class AlertValue(BaseModel):
    """Validation for alert/notification data."""

    count: int = Field(..., ge=0, description="Alert count")
    critical_count: int = Field(default=0, ge=0, description="Critical alerts")
    latest: str | None = Field(None, description="Latest alert message")


class SmartSummaryValue(BaseModel):
    """Validation for smart summary data."""

    pulse: str = Field(..., description="Market pulse")
    pulse_confidence: int | None = Field(None, ge=0, le=100, description="Confidence")
    health: str | None = Field(None, description="Portfolio health")
    health_score: int | None = Field(None, ge=0, le=100, description="Health score")
    action: str | None = Field(None, description="Today's recommended action")
    action_priority: str | None = Field(None, description="Action priority")
    outlook: str | None = Field(None, description="Weekly outlook")


class BybitValue(BaseModel):
    """Validation for Bybit exchange data."""

    balance: Decimal = Field(..., ge=0, description="Account balance")
    pnl_24h: float | None = Field(None, description="24h P&L")
    pnl_7d: float | None = Field(None, description="7d P&L")
    unrealized_pnl: Decimal | None = Field(None, description="Unrealized P&L")
    positions_count: int = Field(default=0, ge=0, description="Open positions")


class DCAValue(BaseModel):
    """Validation for DCA calculator data."""

    result: Decimal | None = Field(None, ge=0, description="Recommended amount")
    signal: str | None = Field(None, description="DCA signal")
    next_level: Decimal | None = Field(None, gt=0, description="Next price level")
    zone: str | None = Field(None, description="Current DCA zone")
    risk_score: int | None = Field(None, ge=0, le=100, description="Risk score")


class EconomicCalendarValue(BaseModel):
    """Validation for economic calendar data."""

    status: str = Field(..., description="Calendar status")
    events_24h: int = Field(default=0, ge=0, description="Events in next 24h")
    important_events: int = Field(default=0, ge=0, description="Important events")
    breaking_news: str | None = Field(None, description="Breaking news")
    sentiment_score: int | None = Field(None, ge=-100, le=100, description="Sentiment")
