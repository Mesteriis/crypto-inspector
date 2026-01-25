"""SQLAlchemy model for sensor state persistence."""

from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class SensorState(Base):
    """
    Database model for storing sensor states.

    Persists sensor values asynchronously for recovery and history.
    """

    __tablename__ = "sensor_states"

    unique_id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        comment="Unique sensor identifier (e.g., crypto_inspect_prices)",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable sensor name",
    )
    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Sensor value (JSON string for complex values)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp",
    )

    def __repr__(self) -> str:
        return f"<SensorState(unique_id={self.unique_id!r}, name={self.name!r})>"
