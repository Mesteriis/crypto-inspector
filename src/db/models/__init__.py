"""Database models package."""

from db.models.candlestick import CandlestickRecord
from db.models.traditional import TraditionalAssetRecord

__all__ = ["CandlestickRecord", "TraditionalAssetRecord"]
