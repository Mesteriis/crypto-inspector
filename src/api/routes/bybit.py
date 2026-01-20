"""
Bybit API Routes.

Endpoints for Bybit exchange integration:
- GET /api/bybit/balance - Account balance
- GET /api/bybit/positions - Open positions
- GET /api/bybit/pnl - P&L by period
- GET /api/bybit/trades - Trade history
- GET /api/bybit/export/csv - CSV export
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from service.exchange import get_bybit_portfolio
from service.exchange.bybit_portfolio import PnlPeriod
from service.export import get_csv_exporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bybit", tags=["bybit"])


@router.get("/status")
async def get_bybit_status() -> dict[str, Any]:
    """
    Get Bybit integration status.

    Returns:
        Status information including configuration state
    """
    portfolio = get_bybit_portfolio()
    return {
        "is_configured": portfolio.is_configured,
        "message": (
            "Bybit API настроен и готов к работе"
            if portfolio.is_configured
            else "Bybit API не настроен. Добавьте BYBIT_API_KEY и BYBIT_API_SECRET"
        ),
    }


@router.get("/balance")
async def get_balance() -> dict[str, Any]:
    """
    Get current account balance.

    Returns:
        Account summary with balances and positions
    """
    portfolio = get_bybit_portfolio()

    if not portfolio.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Bybit API не настроен. Добавьте BYBIT_API_KEY и BYBIT_API_SECRET",
        )

    try:
        account = await portfolio.get_account()
        return account.to_dict()
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions() -> dict[str, Any]:
    """
    Get open positions.

    Returns:
        List of open positions with P&L
    """
    portfolio = get_bybit_portfolio()

    if not portfolio.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Bybit API не настроен",
        )

    try:
        positions = await portfolio.get_positions()
        return {
            "positions": [p.to_dict() for p in positions],
            "count": len(positions),
            "total_unrealized_pnl": sum(p.unrealized_pnl for p in positions),
        }
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl")
async def get_pnl(
    period: str = Query(
        default="24h",
        description="Period: 24h, 7d, 30d, ytd, all",
    ),
) -> dict[str, Any]:
    """
    Get P&L for a period.

    Args:
        period: Time period (24h, 7d, 30d, ytd, all)

    Returns:
        P&L summary with breakdown
    """
    portfolio = get_bybit_portfolio()

    if not portfolio.is_configured:
        raise HTTPException(status_code=400, detail="Bybit API не настроен")

    # Parse period
    try:
        pnl_period = PnlPeriod(period)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Неверный период: {period}. Допустимые: 24h, 7d, 30d, ytd, all",
        )

    try:
        pnl = await portfolio.calculate_pnl(pnl_period)
        return pnl.to_dict()
    except Exception as e:
        logger.error(f"Failed to calculate P&L: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl/all")
async def get_all_pnl() -> dict[str, Any]:
    """
    Get P&L for all periods.

    Returns:
        P&L for each period (24h, 7d, 30d, ytd, all)
    """
    portfolio = get_bybit_portfolio()

    if not portfolio.is_configured:
        raise HTTPException(status_code=400, detail="Bybit API не настроен")

    try:
        all_pnl = await portfolio.get_all_pnl_periods()
        return {period: pnl.to_dict() for period, pnl in all_pnl.items()}
    except Exception as e:
        logger.error(f"Failed to get all P&L: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades")
async def get_trades(
    symbol: str | None = Query(default=None, description="Symbol filter (e.g., BTCUSDT)"),
    limit: int = Query(default=50, ge=1, le=100, description="Max trades to return"),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> dict[str, Any]:
    """
    Get trade history.

    Args:
        symbol: Optional symbol filter
        limit: Max number of trades
        start_date: Start date filter
        end_date: End date filter

    Returns:
        List of trades
    """
    portfolio = get_bybit_portfolio()

    if not portfolio.is_configured:
        raise HTTPException(status_code=400, detail="Bybit API не настроен")

    # Parse dates
    start_time = None
    end_time = None
    try:
        if start_date:
            start_time = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_time = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")

    try:
        trades = await portfolio.get_trades(
            start_time=start_time,
            end_time=end_time,
            symbol=symbol,
            limit=limit,
        )
        return {
            "trades": [t.to_dict() for t in trades],
            "count": len(trades),
            "total_pnl": sum(t.realized_pnl for t in trades),
            "total_fees": sum(t.fee for t in trades),
        }
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/trades")
async def export_trades_csv(
    symbol: str | None = Query(default=None, description="Symbol filter"),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> Response:
    """
    Export trade history to CSV.

    Args:
        symbol: Optional symbol filter
        start_date: Start date filter
        end_date: End date filter

    Returns:
        CSV file download
    """
    exporter = get_csv_exporter()

    # Parse dates
    start_time = None
    end_time = None
    try:
        if start_date:
            start_time = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_time = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты")

    try:
        result = await exporter.export_trades(
            start_time=start_time,
            end_time=end_time,
            symbol=symbol,
        )

        return Response(
            content=result.content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"',
                "X-Rows-Count": str(result.rows_count),
            },
        )
    except Exception as e:
        logger.error(f"Failed to export trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/pnl")
async def export_pnl_csv(
    period: str = Query(default="30d", description="Period: 24h, 7d, 30d, ytd, all"),
) -> Response:
    """
    Export P&L summary to CSV.

    Args:
        period: Time period for P&L

    Returns:
        CSV file download
    """
    exporter = get_csv_exporter()

    try:
        pnl_period = PnlPeriod(period)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Неверный период: {period}")

    try:
        result = await exporter.export_pnl_summary(pnl_period)

        return Response(
            content=result.content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"',
            },
        )
    except Exception as e:
        logger.error(f"Failed to export P&L: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/tax")
async def export_tax_report(
    year: int | None = Query(default=None, description="Tax year (default: current)"),
) -> Response:
    """
    Export tax report to CSV.

    Args:
        year: Tax year

    Returns:
        CSV file download
    """
    exporter = get_csv_exporter()

    try:
        result = await exporter.export_tax_report(year)

        return Response(
            content=result.content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"',
            },
        )
    except Exception as e:
        logger.error(f"Failed to export tax report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/positions")
async def export_positions_csv() -> Response:
    """
    Export current positions to CSV.

    Returns:
        CSV file download
    """
    exporter = get_csv_exporter()

    try:
        result = await exporter.export_positions()

        return Response(
            content=result.content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"',
            },
        )
    except Exception as e:
        logger.error(f"Failed to export positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_bybit_summary() -> dict[str, Any]:
    """
    Get Bybit portfolio summary for dashboard.

    Returns:
        Summary with balance, positions, and P&L
    """
    portfolio = get_bybit_portfolio()

    if not portfolio.is_configured:
        return {
            "is_configured": False,
            "message": "Bybit API не настроен",
        }

    try:
        status = await portfolio.get_full_status()
        return status.to_dict()
    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
