"""
API routes for smart summary features.

Provides endpoints for market pulse, portfolio health, today's action,
and weekly outlook data.
"""

from typing import Any

from fastapi import APIRouter, Query

from schemas.api.summary import (
    FullSummaryResponse,
    MarketPulseResponse,
    PortfolioHealthResponse,
    TodayActionResponse,
    WeeklyOutlookResponse,
)
from service.analysis.smart_summary import SmartSummaryService

router = APIRouter(prefix="/summary", tags=["summary"])

# Service instance
_summary_service = SmartSummaryService()


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/market-pulse", response_model=MarketPulseResponse)
async def get_market_pulse(
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get current market pulse/sentiment.

    Returns:
        Market sentiment with confidence level and contributing factors.
    """
    pulse = await _summary_service.get_market_pulse()
    return pulse.to_dict()


@router.get("/portfolio-health", response_model=PortfolioHealthResponse)
async def get_portfolio_health(
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get portfolio health status.

    Returns:
        Portfolio health score and status with main issues if any.
    """
    health = await _summary_service.get_portfolio_health()
    return health.to_dict()


@router.get("/today-action", response_model=TodayActionResponse)
async def get_today_action(
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get recommended action for today.

    Returns:
        Action recommendation with priority level and details.
    """
    action = await _summary_service.get_today_action()
    return action.to_dict()


@router.get("/weekly-outlook", response_model=WeeklyOutlookResponse)
async def get_weekly_outlook(
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get weekly market outlook.

    Returns:
        Weekly outlook with key events, risk factors, and opportunities.
    """
    outlook = await _summary_service.get_weekly_outlook()
    return outlook.to_dict()


@router.get("/full", response_model=FullSummaryResponse)
async def get_full_summary(
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get complete summary with all components.

    Returns:
        Full summary including market pulse, portfolio health,
        today's action, and weekly outlook.
    """
    pulse = await _summary_service.get_market_pulse()
    health = await _summary_service.get_portfolio_health()
    action = await _summary_service.get_today_action()
    outlook = await _summary_service.get_weekly_outlook()

    return {
        "market_pulse": pulse.to_dict(),
        "portfolio_health": health.to_dict(),
        "today_action": action.to_dict(),
        "weekly_outlook": outlook.to_dict(),
    }


@router.get("/sensor-data")
async def get_sensor_data() -> dict[str, Any]:
    """
    Get data formatted for Home Assistant sensors.

    Returns:
        Dict ready for HA sensor updates.
    """
    return _summary_service.format_sensor_attributes()
