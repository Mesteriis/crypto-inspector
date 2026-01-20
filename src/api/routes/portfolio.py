"""
Portfolio API Routes.

Endpoints for portfolio management:
- GET /api/portfolio - Get current portfolio status
- POST /api/portfolio/holding - Add/update holding
- DELETE /api/portfolio/holding/{symbol} - Remove holding
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from schemas.api.portfolio import HoldingRequest
from service.portfolio import get_portfolio_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio() -> dict[str, Any]:
    """
    Get current portfolio status.

    Returns:
        Portfolio data with holdings, P&L, and allocation
    """
    try:
        manager = get_portfolio_manager()
        data = await manager.calculate()
        return data.to_dict()
    except Exception as e:
        logger.error(f"Portfolio fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/holdings")
async def get_holdings() -> dict[str, Any]:
    """Get all holdings."""
    manager = get_portfolio_manager()
    holdings = manager.get_holdings()
    return {
        "holdings": [h.to_dict() for h in holdings],
        "count": len(holdings),
    }


@router.post("/holding")
async def add_holding(request: HoldingRequest) -> dict[str, Any]:
    """
    Add or update a holding.

    If holding exists, amount is added and avg_price is recalculated.
    """
    try:
        manager = get_portfolio_manager()
        holding = manager.add_holding(
            symbol=request.symbol,
            amount=request.amount,
            avg_price=request.avg_price,
        )
        return {
            "status": "success",
            "holding": holding.to_dict(),
        }
    except Exception as e:
        logger.error(f"Add holding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/holding/{symbol}")
async def remove_holding(symbol: str) -> dict[str, Any]:
    """Remove a holding."""
    manager = get_portfolio_manager()
    if manager.remove_holding(symbol):
        return {"status": "success", "symbol": symbol.upper()}
    raise HTTPException(status_code=404, detail=f"Holding {symbol} not found")


@router.get("/summary")
async def get_portfolio_summary() -> dict[str, Any]:
    """Get portfolio summary for dashboard."""
    try:
        manager = get_portfolio_manager()
        data = await manager.calculate()
        return {
            "total_value": round(data.total_value, 2),
            "total_value_formatted": data.to_dict()["total_value_formatted"],
            "total_pnl_percent": round(data.total_pnl_percent, 2),
            "change_24h_pct": round(data.change_24h_pct, 2),
            "status": data.status.value,
            "status_ru": data.status_ru,
            "holdings_count": len(data.holdings),
            "best": (
                {"symbol": data.best_performer.symbol, "pnl": data.best_performer.pnl_percent}
                if data.best_performer
                else None
            ),
            "worst": (
                {"symbol": data.worst_performer.symbol, "pnl": data.worst_performer.pnl_percent}
                if data.worst_performer
                else None
            ),
        }
    except Exception as e:
        logger.error(f"Portfolio summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
