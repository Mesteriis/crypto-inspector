"""
Backfill API Routes.

Endpoints for historical data backfill management:
- GET /api/backfill/status - Get backfill status
- POST /api/backfill/trigger - Trigger manual backfill
- GET /api/backfill/gaps - Detect data gaps
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.backfill import get_backfill_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backfill", tags=["backfill"])


class TriggerBackfillRequest(BaseModel):
    """Request to trigger backfill."""

    crypto_symbols: list[str] | None = None
    crypto_intervals: list[str] | None = None
    crypto_years: int | None = None
    traditional_symbols: list[str] | None = None
    traditional_years: int | None = None
    force: bool = False


@router.get("/status")
async def get_backfill_status() -> dict[str, Any]:
    """
    Get current backfill status.

    Returns:
        Status including progress, candle counts, completion state
    """
    manager = get_backfill_manager()
    return manager.progress.to_dict()


@router.post("/trigger")
async def trigger_backfill(request: TriggerBackfillRequest) -> dict[str, Any]:
    """
    Trigger manual backfill.

    Args:
        request: Backfill parameters

    Returns:
        Backfill result with counts
    """
    manager = get_backfill_manager()

    if manager.is_running:
        raise HTTPException(status_code=409, detail="Backfill already running")

    results = {}

    # Trigger crypto backfill
    if request.crypto_symbols or request.force:
        try:
            crypto_results = await manager.backfill_crypto(
                symbols=request.crypto_symbols,
                intervals=request.crypto_intervals,
                years=request.crypto_years,
            )
            results["crypto"] = crypto_results
        except Exception as e:
            logger.error(f"Crypto backfill error: {e}")
            results["crypto_error"] = str(e)

    # Trigger traditional backfill
    if request.traditional_symbols or request.force:
        try:
            traditional_results = await manager.backfill_traditional(
                symbols=request.traditional_symbols,
                years=request.traditional_years,
            )
            results["traditional"] = traditional_results
        except Exception as e:
            logger.error(f"Traditional backfill error: {e}")
            results["traditional_error"] = str(e)

    return {
        "status": "completed",
        "results": results,
    }


@router.post("/trigger/crypto")
async def trigger_crypto_backfill(
    symbols: list[str] | None = Query(default=None, description="Symbols to backfill"),
    intervals: list[str] = Query(default=["1d", "4h", "1h"], description="Intervals"),
    years: int = Query(default=10, ge=1, le=15, description="Years of history"),
) -> dict[str, Any]:
    """
    Trigger crypto candlestick backfill.

    Args:
        symbols: Trading pairs to backfill (default: configured symbols)
        intervals: Candle intervals (default: 1d, 4h, 1h)
        years: Years of history (default: 10)
    """
    manager = get_backfill_manager()

    if manager.is_running:
        raise HTTPException(status_code=409, detail="Backfill already running")

    try:
        results = await manager.backfill_crypto(
            symbols=symbols,
            intervals=intervals,
            years=years,
        )

        total = sum(results.values())

        return {
            "status": "completed",
            "results": results,
            "total_candles": total,
        }
    except Exception as e:
        logger.error(f"Crypto backfill error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/traditional")
async def trigger_traditional_backfill(
    symbols: list[str] | None = Query(default=None, description="Assets to backfill"),
    years: int = Query(default=1, ge=1, le=5, description="Years of history"),
) -> dict[str, Any]:
    """
    Trigger traditional asset backfill.

    Args:
        symbols: Assets to backfill (default: all)
        years: Years of history (default: 1)
    """
    manager = get_backfill_manager()

    if manager.is_running:
        raise HTTPException(status_code=409, detail="Backfill already running")

    try:
        results = await manager.backfill_traditional(
            symbols=symbols,
            years=years,
        )

        total = sum(results.values())

        return {
            "status": "completed",
            "results": results,
            "total_records": total,
        }
    except Exception as e:
        logger.error(f"Traditional backfill error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gaps")
async def get_data_gaps(
    symbol: str | None = Query(default=None, description="Symbol to check"),
) -> dict[str, Any]:
    """
    Detect gaps in historical data.

    Args:
        symbol: Specific symbol to check (default: all)

    Returns:
        Detected gaps by symbol/interval
    """
    manager = get_backfill_manager()

    try:
        if symbol:
            # Check specific symbol
            from services.backfill.crypto_backfill import get_crypto_backfill

            crypto = get_crypto_backfill()
            intervals = manager.crypto_intervals

            gaps = {}
            for interval in intervals:
                interval_gaps = await crypto.detect_gaps(symbol, interval)
                if interval_gaps:
                    gaps[f"{symbol}_{interval}"] = [{"start": g[0], "end": g[1]} for g in interval_gaps]

            return {
                "symbol": symbol,
                "gaps": gaps,
                "has_gaps": bool(gaps),
            }
        else:
            # Check all symbols
            all_gaps = await manager.detect_all_gaps()

            formatted_gaps = {}
            for key, gap_list in all_gaps.items():
                formatted_gaps[key] = [{"start": g[0], "end": g[1]} for g in gap_list]

            return {
                "gaps": formatted_gaps,
                "total_gaps": sum(len(g) for g in all_gaps.values()),
                "symbols_with_gaps": list(all_gaps.keys()),
            }
    except Exception as e:
        logger.error(f"Gap detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fill-gaps")
async def fill_data_gaps() -> dict[str, Any]:
    """
    Fill detected gaps in historical data.

    Returns:
        Number of candles filled per symbol/interval
    """
    manager = get_backfill_manager()

    if manager.is_running:
        raise HTTPException(status_code=409, detail="Backfill already running")

    try:
        results = await manager.fill_all_gaps()

        total = sum(results.values())

        return {
            "status": "completed",
            "results": results,
            "total_filled": total,
        }
    except Exception as e:
        logger.error(f"Gap fill error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_data_stats() -> dict[str, Any]:
    """
    Get data statistics.

    Returns:
        Candle counts by symbol/interval
    """
    from sqlalchemy import text

    from db.session import async_session_maker

    try:
        async with async_session_maker() as session:
            # Crypto stats
            crypto_result = await session.execute(
                text("""
                    SELECT symbol, interval, COUNT(*) as count,
                           MIN(timestamp) as earliest,
                           MAX(timestamp) as latest
                    FROM candlestick_records
                    GROUP BY symbol, interval
                    ORDER BY symbol, interval
                """)
            )
            crypto_stats = [
                {
                    "symbol": row[0],
                    "interval": row[1],
                    "count": row[2],
                    "earliest": row[3],
                    "latest": row[4],
                }
                for row in crypto_result.fetchall()
            ]

            # Traditional stats
            traditional_result = await session.execute(
                text("""
                    SELECT symbol, asset_type, COUNT(*) as count,
                           MIN(timestamp) as earliest,
                           MAX(timestamp) as latest
                    FROM traditional_asset_records
                    GROUP BY symbol, asset_type
                    ORDER BY symbol
                """)
            )
            traditional_stats = [
                {
                    "symbol": row[0],
                    "asset_type": row[1],
                    "count": row[2],
                    "earliest": row[3],
                    "latest": row[4],
                }
                for row in traditional_result.fetchall()
            ]

            return {
                "crypto": crypto_stats,
                "traditional": traditional_stats,
                "crypto_total": sum(s["count"] for s in crypto_stats),
                "traditional_total": sum(s["count"] for s in traditional_stats),
            }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
