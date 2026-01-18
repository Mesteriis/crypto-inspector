"""
API routes for briefing features.

Provides endpoints for morning/evening briefings and notification management.
"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...services.alerts.notification_manager import (
    NotificationManager,
    NotificationMode,
)
from ...services.analysis.briefing import BriefingService

router = APIRouter(prefix="/briefing", tags=["briefing"])

# Service instances
_briefing_service = BriefingService()
_notification_manager = NotificationManager()


# =============================================================================
# Response Models
# =============================================================================


class BriefingSectionResponse(BaseModel):
    """Briefing section response."""

    header: str
    header_en: str
    header_ru: str
    content: str
    content_en: str
    content_ru: str
    emoji: str


class BriefingResponse(BaseModel):
    """Briefing response."""

    type: str
    title: str
    title_en: str
    title_ru: str
    greeting: str
    greeting_en: str
    greeting_ru: str
    sections: list[BriefingSectionResponse]
    message: str  # Formatted message
    message_ru: str


class DigestResponse(BaseModel):
    """Daily digest response."""

    type: str
    title: str
    title_ru: str
    summary: str
    summary_ru: str
    total_alerts: int
    critical_count: int
    important_count: int
    info_count: int
    message: str
    message_ru: str


class NotificationStatsResponse(BaseModel):
    """Notification statistics response."""

    pending_total: int
    pending_critical: int
    pending_important: int
    pending_info: int
    sent_today: int
    digest_ready: bool
    current_mode: str
    current_mode_en: str
    current_mode_ru: str


# =============================================================================
# Briefing Endpoints
# =============================================================================


@router.get("/morning", response_model=BriefingResponse)
async def get_morning_briefing(
    btc_price: float | None = Query(None, description="Current BTC price"),
    btc_change: float | None = Query(None, description="BTC 24h change %"),
    fear_greed: int | None = Query(None, description="Fear & Greed Index"),
    portfolio_value: float | None = Query(None, description="Portfolio value"),
    portfolio_change: float | None = Query(None, description="Portfolio change %"),
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Generate morning briefing.

    Returns:
        Comprehensive morning briefing with overnight changes,
        sentiment, portfolio status, and recommended actions.
    """
    briefing = await _briefing_service.generate_morning_briefing(
        btc_price=Decimal(str(btc_price)) if btc_price else None,
        btc_change_24h=btc_change,
        fear_greed=fear_greed,
        portfolio_value=Decimal(str(portfolio_value)) if portfolio_value else None,
        portfolio_change=portfolio_change,
    )

    result = briefing.to_dict(lang)
    result["message"] = briefing.format_message("en")
    result["message_ru"] = briefing.format_message("ru")
    return result


@router.get("/evening", response_model=BriefingResponse)
async def get_evening_briefing(
    btc_price: float | None = Query(None, description="Current BTC price"),
    btc_change: float | None = Query(None, description="BTC 24h change %"),
    portfolio_value: float | None = Query(None, description="Portfolio value"),
    portfolio_change: float | None = Query(None, description="Portfolio change %"),
    day_high: float | None = Query(None, description="BTC day high"),
    day_low: float | None = Query(None, description="BTC day low"),
    alerts_count: int = Query(0, description="Alerts triggered today"),
    include_weekly: bool = Query(False, description="Include weekly summary"),
    weekly_change: float | None = Query(None, description="Weekly change %"),
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Generate evening briefing.

    Returns:
        Evening summary with day's performance, key events,
        and tomorrow's preview.
    """
    briefing = await _briefing_service.generate_evening_briefing(
        btc_price=Decimal(str(btc_price)) if btc_price else None,
        btc_change_24h=btc_change,
        portfolio_value=Decimal(str(portfolio_value)) if portfolio_value else None,
        portfolio_change=portfolio_change,
        day_high=Decimal(str(day_high)) if day_high else None,
        day_low=Decimal(str(day_low)) if day_low else None,
        alerts_count=alerts_count,
        include_weekly=include_weekly,
        weekly_change=weekly_change,
    )

    result = briefing.to_dict(lang)
    result["message"] = briefing.format_message("en")
    result["message_ru"] = briefing.format_message("ru")
    return result


@router.get("/sensor-data")
async def get_briefing_sensor_data() -> dict[str, Any]:
    """
    Get briefing data formatted for Home Assistant sensors.

    Returns:
        Dict ready for MQTT sensor updates.
    """
    return _briefing_service.format_sensor_attributes()


# =============================================================================
# Notification Endpoints
# =============================================================================


@router.get("/notifications/stats", response_model=NotificationStatsResponse)
async def get_notification_stats() -> dict[str, Any]:
    """
    Get notification statistics.

    Returns:
        Pending alerts count, sent today, digest status, and current mode.
    """
    stats = _notification_manager.get_stats()
    return stats.to_dict()


@router.get("/notifications/digest", response_model=DigestResponse)
async def get_daily_digest(
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get daily digest of pending alerts.

    Returns:
        Aggregated daily digest with categorized alerts.
    """
    digest = await _notification_manager.get_daily_digest()
    result = digest.to_dict(lang)
    result["message"] = digest.format_message("en")
    result["message_ru"] = digest.format_message("ru")
    return result


@router.get("/notifications/weekly", response_model=DigestResponse)
async def get_weekly_summary(
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get weekly summary of all alerts.

    Returns:
        Weekly summary with categorized historical alerts.
    """
    digest = await _notification_manager.get_weekly_summary()
    result = digest.to_dict(lang)
    result["message"] = digest.format_message("en")
    result["message_ru"] = digest.format_message("ru")
    return result


@router.post("/notifications/mode")
async def set_notification_mode(
    mode: str = Query(..., description="Mode: all, smart, digest_only, critical_only, silent"),
) -> dict[str, Any]:
    """
    Set notification delivery mode.

    Returns:
        Confirmation of mode change.
    """
    try:
        notification_mode = NotificationMode(mode)
        _notification_manager.set_mode(notification_mode)
        return {
            "success": True,
            "mode": mode,
            "message": f"Notification mode set to: {mode}",
            "message_ru": f"Режим уведомлений установлен: {mode}",
        }
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid mode: {mode}",
            "valid_modes": [m.value for m in NotificationMode],
        }


@router.post("/notifications/mark-sent")
async def mark_digest_sent() -> dict[str, Any]:
    """
    Mark daily digest as sent and clear pending alerts.

    Returns:
        Confirmation with cleared count.
    """
    stats_before = _notification_manager.get_stats()
    await _notification_manager.mark_digest_sent()

    return {
        "success": True,
        "cleared_count": stats_before.pending_total,
        "message": f"Marked {stats_before.pending_total} alerts as sent",
        "message_ru": f"Отмечено {stats_before.pending_total} оповещений как отправленные",
    }


@router.get("/notifications/sensor-data")
async def get_notification_sensor_data() -> dict[str, Any]:
    """
    Get notification data formatted for Home Assistant sensors.

    Returns:
        Dict ready for MQTT sensor updates.
    """
    return _notification_manager.format_sensor_attributes()
