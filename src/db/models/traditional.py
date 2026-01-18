"""SQLAlchemy model for traditional asset data storage."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class TraditionalAssetRecord(Base):
    """
    Database model for storing traditional asset OHLCV data.

    Stores historical data for:
    - Metals (Gold, Silver, Platinum)
    - Indices (S&P 500, NASDAQ, Dow Jones, DAX)
    - Forex (EUR/USD, GBP/USD, DXY)
    - Commodities (Oil Brent, WTI, Natural Gas)

    Composite primary key (symbol, timestamp) ensures no duplicates.
    """

    __tablename__ = "traditional_asset_records"

    # === Primary Key ===
    symbol: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Asset symbol (e.g., GOLD, SP500, EUR_USD)",
    )
    timestamp: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        comment="Candle open time as Unix timestamp in milliseconds",
    )

    # === Asset Classification ===
    asset_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Asset type: metal, index, forex, commodity",
    )

    # === OHLCV Data ===
    open_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=6),
        nullable=True,
        comment="Opening price",
    )
    high_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=6),
        nullable=True,
        comment="Highest price",
    )
    low_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=6),
        nullable=True,
        comment="Lowest price",
    )
    close_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=6),
        nullable=True,
        comment="Closing price",
    )
    volume: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
        nullable=True,
        comment="Trading volume",
    )

    # === Metadata ===
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when this record was loaded",
    )

    # === Indexes ===
    __table_args__ = (
        Index("ix_traditional_asset_type", "asset_type"),
        Index("ix_traditional_timestamp", "timestamp"),
        Index("ix_traditional_symbol_timestamp", "symbol", "timestamp"),
        {"comment": "Stores historical OHLCV data for traditional assets (metals, indices, forex, commodities)"},
    )

    def __repr__(self) -> str:
        return f"<TraditionalAssetRecord(symbol={self.symbol!r}, timestamp={self.timestamp}, close={self.close_price})>"
