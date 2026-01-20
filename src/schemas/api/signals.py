"""Signals API schemas."""

from pydantic import BaseModel


class RecordSignalRequest(BaseModel):
    """Request to record a signal."""

    symbol: str
    signal_type: str  # buy, sell, strong_buy, strong_sell, neutral
    source: str  # divergence, pattern, indicator, composite, investor, alert
    price: float
    confidence: int = 50
    description: str = ""
    description_ru: str = ""
