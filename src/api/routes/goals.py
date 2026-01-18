"""
API routes for goal tracking features.

Provides endpoints for portfolio goal management, progress tracking,
and milestone celebrations.
"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from core.config import settings
from services.portfolio.goals import GoalTracker

router = APIRouter(prefix="/goals", tags=["goals"])

# Service instance - initialize from config
_goal_tracker: GoalTracker | None = None


def get_goal_tracker() -> GoalTracker:
    """Get or create goal tracker from config."""
    global _goal_tracker
    if _goal_tracker is None:
        _goal_tracker = GoalTracker(
            goal_name=settings.GOAL_NAME,
            goal_name_ru=settings.GOAL_NAME_RU,
            target_value=Decimal(str(settings.GOAL_TARGET_VALUE)),
        )
    return _goal_tracker


# =============================================================================
# Response Models
# =============================================================================


class MilestoneResponse(BaseModel):
    """Milestone response."""

    percentage: int
    label: str
    label_ru: str
    message: str
    message_ru: str
    reached: bool
    reached_at: str | None = None


class GoalProgressResponse(BaseModel):
    """Goal progress response."""

    name: str
    name_en: str
    name_ru: str
    target_value: float
    current_value: float
    remaining: float
    progress_percent: float
    days_to_goal: int | None
    status: str
    status_en: str
    status_ru: str
    milestone_message: str
    milestone_message_ru: str
    milestones: list[MilestoneResponse]
    emoji: str


class GoalConfigResponse(BaseModel):
    """Goal configuration response."""

    enabled: bool
    name: str
    name_ru: str
    target_value: float
    start_date: str | None = None
    target_date: str | None = None


class GoalUpdateRequest(BaseModel):
    """Goal update request."""

    name: str | None = None
    name_ru: str | None = None
    target_value: float | None = None
    target_date: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/config", response_model=GoalConfigResponse)
async def get_goal_config() -> dict[str, Any]:
    """
    Get current goal configuration.

    Returns:
        Goal settings from configuration.
    """
    tracker = get_goal_tracker()
    return {
        "enabled": settings.GOAL_ENABLED,
        "name": tracker.goal_name,
        "name_ru": tracker.goal_name_ru,
        "target_value": float(tracker.target_value),
        "start_date": tracker.start_date.isoformat() if tracker.start_date else None,
        "target_date": tracker.target_date.isoformat() if tracker.target_date else None,
    }


@router.get("/progress")
async def get_goal_progress(
    current_value: float = Query(..., description="Current portfolio value"),
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get goal progress with current portfolio value.

    Args:
        current_value: Current portfolio value in USDT

    Returns:
        Progress percentage, status, milestones, and time estimate.
    """
    if not settings.GOAL_ENABLED:
        return {
            "enabled": False,
            "error": "Goal tracking is not enabled",
            "error_ru": "Отслеживание целей не включено",
        }

    tracker = get_goal_tracker()
    goal = await tracker.calculate_progress(Decimal(str(current_value)))
    result = goal.to_dict(lang)
    result["enabled"] = True
    return result


@router.get("/estimate")
async def estimate_time_to_goal(
    current_value: float = Query(..., description="Current portfolio value"),
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Estimate time to reach goal based on historical growth.

    Returns:
        Days estimate and formatted time string.
    """
    if not settings.GOAL_ENABLED:
        return {
            "error": "Goal tracking is not enabled",
            "error_ru": "Отслеживание целей не включено",
        }

    tracker = get_goal_tracker()
    days = await tracker.estimate_time_to_goal(Decimal(str(current_value)))

    return {
        "days": days,
        "formatted": tracker.format_time_estimate(days, "en"),
        "formatted_ru": tracker.format_time_estimate(days, "ru"),
        "achievable": days is not None and days >= 0,
    }


@router.post("/record")
async def record_value(
    value: float = Query(..., description="Current portfolio value"),
    note: str | None = Query(None, description="Optional note"),
) -> dict[str, Any]:
    """
    Record current portfolio value for progress tracking.

    This helps improve time-to-goal estimates by tracking
    historical growth rate.

    Returns:
        Confirmation with current progress.
    """
    if not settings.GOAL_ENABLED:
        return {
            "error": "Goal tracking is not enabled",
            "error_ru": "Отслеживание целей не включено",
        }

    tracker = get_goal_tracker()
    tracker.record_value(Decimal(str(value)), note)

    # Calculate current progress
    goal = await tracker.calculate_progress(Decimal(str(value)))

    return {
        "success": True,
        "recorded_value": value,
        "note": note,
        "current_progress": goal.progress_percent,
        "message": f"Value recorded: ${value:,.2f}",
        "message_ru": f"Значение записано: ${value:,.2f}",
    }


@router.get("/milestones")
async def get_milestones(
    current_value: float = Query(..., description="Current portfolio value"),
    lang: str = Query("en", description="Language: 'en' or 'ru'"),
) -> dict[str, Any]:
    """
    Get milestone progress details.

    Returns:
        List of milestones with reached status and next milestone.
    """
    if not settings.GOAL_ENABLED:
        return {
            "error": "Goal tracking is not enabled",
            "error_ru": "Отслеживание целей не включено",
        }

    tracker = get_goal_tracker()
    goal = await tracker.calculate_progress(Decimal(str(current_value)))

    return {
        "milestones": [m.to_dict(lang) for m in goal.milestones],
        "reached_count": len([m for m in goal.milestones if m.reached]),
        "total_count": len(goal.milestones),
        "next_milestone": next((m.to_dict(lang) for m in goal.milestones if not m.reached), None),
    }


@router.post("/update")
async def update_goal(
    name: str | None = Query(None, description="New goal name (EN)"),
    name_ru: str | None = Query(None, description="New goal name (RU)"),
    target_value: float | None = Query(None, description="New target value"),
) -> dict[str, Any]:
    """
    Update goal configuration.

    Note: This only updates the in-memory configuration.
    To persist changes, update config.yaml.

    Returns:
        Updated goal configuration.
    """
    tracker = get_goal_tracker()
    tracker.update_config(
        goal_name=name,
        goal_name_ru=name_ru,
        target_value=Decimal(str(target_value)) if target_value else None,
    )

    return {
        "success": True,
        "name": tracker.goal_name,
        "name_ru": tracker.goal_name_ru,
        "target_value": float(tracker.target_value),
        "message": "Goal configuration updated",
        "message_ru": "Конфигурация цели обновлена",
    }


@router.get("/sensor-data")
async def get_goal_sensor_data(
    current_value: float = Query(..., description="Current portfolio value"),
) -> dict[str, Any]:
    """
    Get goal data formatted for Home Assistant sensors.

    Returns:
        Dict ready for MQTT sensor updates.
    """
    if not settings.GOAL_ENABLED:
        return {
            "goal_enabled": False,
            "goal_status": "disabled",
            "goal_status_en": "Disabled",
            "goal_status_ru": "Отключено",
        }

    tracker = get_goal_tracker()
    return tracker.format_sensor_attributes(Decimal(str(current_value)))


@router.get("/history")
async def get_goal_history(
    limit: int = Query(30, description="Number of records to return"),
) -> dict[str, Any]:
    """
    Get recorded value history.

    Returns:
        Historical portfolio values recorded for this goal.
    """
    if not settings.GOAL_ENABLED:
        return {
            "error": "Goal tracking is not enabled",
            "error_ru": "Отслеживание целей не включено",
        }

    tracker = get_goal_tracker()
    history = tracker.history[-limit:] if limit else tracker.history

    return {
        "records": [h.to_dict() for h in history],
        "count": len(history),
        "total_records": len(tracker.history),
    }
