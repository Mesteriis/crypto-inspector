"""
Signals API Routes.

Endpoints for signal history:
- GET /api/signals - List recent signals
- GET /api/signals/stats - Get signal statistics
- POST /api/signals - Record a new signal (internal)
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.analysis.signal_history import (
    SignalSource,
    get_signal_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])


class RecordSignalRequest(BaseModel):
    """Request to record a signal."""

    symbol: str
    signal_type: str  # buy, sell, strong_buy, strong_sell, neutral
    source: str  # divergence, pattern, indicator, composite, investor, alert
    price: float
    confidence: int = 50
    description: str = ""
    description_ru: str = ""


@router.get("")
async def list_signals(
    symbol: str | None = None,
    source: str | None = None,
    hours: int = Query(default=24, description="Get signals from last N hours"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """
    List recent signals.

    Args:
        symbol: Filter by symbol
        source: Filter by source
        hours: Get signals from last N hours
        limit: Maximum number of signals
    """
    manager = get_signal_manager()

    signal_source = None
    if source:
        try:
            signal_source = SignalSource(source)
        except ValueError:
            pass

    since = datetime.now() - timedelta(hours=hours)

    signals = manager.get_signals(
        symbol=symbol,
        source=signal_source,
        since=since,
        limit=limit,
    )

    return {
        "signals": [s.to_dict() for s in signals],
        "count": len(signals),
        "period_hours": hours,
    }


@router.get("/stats")
async def get_signal_stats() -> dict[str, Any]:
    """Get signal statistics."""
    manager = get_signal_manager()
    stats = manager.get_stats()
    return stats.to_dict()


@router.post("")
async def record_signal(request: RecordSignalRequest) -> dict[str, Any]:
    """
    Record a new signal.

    Primarily for internal use by other services.
    """
    try:
        manager = get_signal_manager()
        signal = manager.record_signal(
            symbol=request.symbol,
            signal_type=request.signal_type,
            source=request.source,
            price=request.price,
            confidence=request.confidence,
            description=request.description,
            description_ru=request.description_ru,
        )
        return {
            "status": "success",
            "signal": signal.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Record signal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{signal_id}")
async def get_signal(signal_id: str) -> dict[str, Any]:
    """Get a specific signal by ID."""
    manager = get_signal_manager()
    signal = manager.get_signal(signal_id)

    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

    return signal.to_dict()


@router.get("/by-symbol/{symbol}")
async def get_signals_by_symbol(
    symbol: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Get signals for a specific symbol."""
    manager = get_signal_manager()
    signals = manager.get_signals(symbol=symbol, limit=limit)

    return {
        "symbol": symbol.upper(),
        "signals": [s.to_dict() for s in signals],
        "count": len(signals),
    }


@router.get("/summary")
async def get_signals_summary() -> dict[str, Any]:
    """Get signals summary for dashboard."""
    manager = get_signal_manager()
    stats = manager.get_stats()

    return {
        "win_rate_24h": round(stats.win_rate_24h, 1),
        "win_rate_7d": round(stats.win_rate_7d, 1),
        "signals_24h": stats.signals_24h,
        "total_signals": stats.total_signals,
        "avg_pnl_24h": round(stats.avg_pnl_24h, 2),
        "best_source": max(
            stats.by_source.items(),
            key=lambda x: x[1].get("win_rate", 0),
            default=("none", {}),
        )[0]
        if stats.by_source
        else None,
    }
