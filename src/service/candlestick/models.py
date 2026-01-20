"""Pydantic models for candlestick data."""

from decimal import Decimal
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator


class CandleInterval(str, Enum):
    """Supported candlestick time intervals."""

    MINUTE_1 = "1m"
    MINUTE_3 = "3m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_2 = "2h"
    HOUR_4 = "4h"
    HOUR_6 = "6h"
    HOUR_8 = "8h"
    HOUR_12 = "12h"
    DAY_1 = "1d"
    DAY_3 = "3d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class Candlestick(BaseModel):
    """
    Standardized candlestick (OHLCV) data model.

    All price and volume values are stored as Decimal for precision.
    Timestamp is in milliseconds since Unix epoch.
    """

    timestamp: int = Field(
        ...,
        description="Candle open time as Unix timestamp in milliseconds",
        ge=0,
    )
    open_price: Decimal = Field(
        ...,
        description="Opening price of the candle",
        gt=0,
    )
    high_price: Decimal = Field(
        ...,
        description="Highest price during the candle period",
        gt=0,
    )
    low_price: Decimal = Field(
        ...,
        description="Lowest price during the candle period",
        gt=0,
    )
    close_price: Decimal = Field(
        ...,
        description="Closing price of the candle",
        gt=0,
    )
    volume: Decimal = Field(
        ...,
        description="Trading volume during the candle period",
        ge=0,
    )
    quote_volume: Decimal | None = Field(
        default=None,
        description="Quote asset volume (e.g., USDT volume)",
        ge=0,
    )
    trades_count: int | None = Field(
        default=None,
        description="Number of trades during the candle period",
        ge=0,
    )

    @field_validator("high_price")
    @classmethod
    def high_must_be_highest(cls, v: Decimal, info) -> Decimal:
        """Validate that high price is the highest."""
        if info.data.get("low_price") and v < info.data["low_price"]:
            raise ValueError("high_price must be greater than or equal to low_price")
        return v

    @field_validator("low_price")
    @classmethod
    def low_must_be_lowest(cls, v: Decimal, info) -> Decimal:
        """Validate that low price is the lowest."""
        if info.data.get("high_price") and v > info.data["high_price"]:
            raise ValueError("low_price must be less than or equal to high_price")
        return v

    def __lt__(self, other: Self) -> bool:
        """Allow sorting candlesticks by timestamp."""
        return self.timestamp < other.timestamp

    def __eq__(self, other: object) -> bool:
        """Check equality based on timestamp."""
        if not isinstance(other, Candlestick):
            return NotImplemented
        return self.timestamp == other.timestamp


class FetchResult(BaseModel):
    """Result of a candlestick fetch operation."""

    candlesticks: list[Candlestick] = Field(
        default_factory=list,
        description="List of fetched candlesticks sorted by timestamp ascending",
    )
    exchange: str = Field(
        ...,
        description="Name of the exchange that provided the data",
    )
    symbol: str = Field(
        ...,
        description="Trading pair symbol (e.g., BTC/USDT)",
    )
    interval: CandleInterval = Field(
        ...,
        description="Candlestick interval/granularity",
    )
    fetch_time_ms: float = Field(
        ...,
        description="Time taken to fetch data in milliseconds",
        ge=0,
    )

    @property
    def count(self) -> int:
        """Return the number of candlesticks."""
        return len(self.candlesticks)

    @property
    def is_empty(self) -> bool:
        """Check if result contains any candlesticks."""
        return len(self.candlesticks) == 0


class FetchRequest(BaseModel):
    """Parameters for a candlestick fetch request."""

    symbol: str = Field(
        ...,
        description="Trading pair symbol (e.g., BTC/USDT, ETH/USDT)",
        min_length=1,
    )
    interval: CandleInterval = Field(
        ...,
        description="Candlestick interval/granularity",
    )
    limit: int = Field(
        default=100,
        description="Number of candlesticks to fetch",
        ge=1,
        le=1000,
    )
    start_time: int | None = Field(
        default=None,
        description="Start timestamp in milliseconds (inclusive)",
        ge=0,
    )
    end_time: int | None = Field(
        default=None,
        description="End timestamp in milliseconds (inclusive)",
        ge=0,
    )

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: int | None, info) -> int | None:
        """Validate that end_time is after start_time."""
        start = info.data.get("start_time")
        if v is not None and start is not None and v <= start:
            raise ValueError("end_time must be greater than start_time")
        return v
