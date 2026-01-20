"""SQLAlchemy model for candlestick data storage."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CandlestickRecord(Base):
    """
    Database model for storing candlestick (OHLCV) data.

    Composite primary key (exchange, symbol, interval, timestamp) ensures
    no duplicate candles for a specific currency pair from a specific exchange.
    """

    __tablename__ = "candlestick_records"

    # === Composite Primary Key ===
    # These 4 fields uniquely identify a candlestick
    exchange: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Exchange name (e.g., binance, coinbase, kraken)",
    )
    symbol: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Trading pair symbol (e.g., BTC/USDT)",
    )
    interval: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="Candlestick interval (e.g., 1m, 5m, 1h, 1d)",
    )
    timestamp: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        comment="Candle open time as Unix timestamp in milliseconds",
    )

    # === OHLCV Data ===
    open_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=False,
        comment="Opening price of the candle",
    )
    high_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=False,
        comment="Highest price during the candle period",
    )
    low_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=False,
        comment="Lowest price during the candle period",
    )
    close_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=False,
        comment="Closing price of the candle",
    )
    volume: Mapped[Decimal] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=False,
        comment="Base asset trading volume",
    )
    quote_volume: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=30, scale=10),
        nullable=True,
        comment="Quote asset volume (e.g., USDT volume)",
    )
    trades_count: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Number of trades during the candle period",
    )

    # === Metadata Fields ===
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when this record was loaded into the database",
    )
    fetch_time_ms: Mapped[float | None] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True,
        comment="Time taken to fetch this data from exchange in milliseconds",
    )
    source_raw: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Original raw response from exchange for debugging (JSON string)",
    )
    is_complete: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether this candle is complete (closed) or still forming",
    )

    # === Indexes for common query patterns ===
    __table_args__ = (
        # Index for querying by symbol across all exchanges
        Index("ix_candlestick_symbol", "symbol"),
        # Index for time range queries
        Index("ix_candlestick_timestamp", "timestamp"),
        # Index for fetching latest candles per exchange/symbol
        Index("ix_candlestick_exchange_symbol_interval", "exchange", "symbol", "interval"),
        # Index for loaded_at to track recent inserts
        Index("ix_candlestick_loaded_at", "loaded_at"),
        {"comment": "Stores historical candlestick (OHLCV) data from various exchanges"},
    )

    def __repr__(self) -> str:
        return (
            f"<CandlestickRecord("
            f"exchange={self.exchange!r}, "
            f"symbol={self.symbol!r}, "
            f"interval={self.interval!r}, "
            f"timestamp={self.timestamp}, "
            f"close={self.close_price}"
            f")>"
        )
