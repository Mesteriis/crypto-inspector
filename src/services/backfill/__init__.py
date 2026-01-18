"""
Backfill Service.

Handles historical data backfill for:
- Crypto candlesticks (10 years)
- Traditional assets (1 year)
"""

from services.backfill.manager import BackfillManager, get_backfill_manager

__all__ = ["BackfillManager", "get_backfill_manager"]
