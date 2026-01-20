"""Repository classes for data access.

Provides data access layer with:
- BaseRepository with common CRUD operations
- CandlestickRepository for OHLCV data
- MLPredictionRepository for ML predictions
"""

from models.repositories.base import BaseRepository
from models.repositories.candlestick import CandlestickRepository
from models.repositories.ml_predictions import MLPredictionRepository

__all__ = [
    "BaseRepository",
    "CandlestickRepository",
    "MLPredictionRepository",
]
