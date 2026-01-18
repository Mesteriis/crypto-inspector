"""
API routes for smart summary features.

Provides endpoints for market pulse, portfolio health, today's action,
and weekly outlook data.
"""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services.analysis.smart_summary import SmartSummaryService

router = APIRouter(prefix="/summary", tags=["summary"])

# Service instance
_summary_service = SmartSummaryService()


# =============================================================================
# Response Models
# =============================================================================


class MarketPulseResponse(BaseModel):
    """Market pulse response."""

    sentiment: str
    sentiment_en: str
    sentiment_ru: str
    confidence: int
    reason: str
    reason_ru: str
    factors: list[str]
    factors_ru: list[str]


class PortfolioHealthResponse(BaseModel):
    """Portfolio health response."""

    status: str
    status_en: str
    status_ru: str
    score: int
    main_issue: str
    main_issue_ru: str
    metrics: dict[str, Any] | None = None


class TodayActionResponse(BaseModel):
    """Today's action response."""

    action: str
    action_en: str
    action_ru: str
    priority: str
    priority_en: str
    priority_ru: str
    details: str
    details_ru: str


class WeeklyOutlookResponse(BaseModel):
    """Weekly outlook response."""

    outlook: str
    outlook_en: str
    outlook_ru: str
    confidence: int
    key_events: list[str]
    key_events_ru: list[str]
    risk_factors: list[str]
    risk_factors_ru: list[str]
    opportunities: list[str]
    opportunities_ru: list[str]


class FullSummaryResponse(BaseModel):
    """Full summary with all components."""

    market_pulse: MarketPulseResponse
    portfolio_health: PortfolioHealthResponse
    today_action: TodayActionResponse
    weekly_outlook: WeeklyOutlookResponse


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
        Dict ready for MQTT sensor updates.
    """
    return _summary_service.format_sensor_attributes()
