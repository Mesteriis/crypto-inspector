"""
Price Alerts API Routes.

Endpoints for managing price alerts:
- GET /api/alerts - List all alerts
- POST /api/alerts - Create new alert
- DELETE /api/alerts/{id} - Delete alert
- GET /api/alerts/summary - Get alerts summary
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from schemas.api.alerts import CreateAlertRequest
from service.alerts import get_alert_manager
from service.alerts.price_alerts import AlertStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    symbol: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """
    List all alerts with optional filtering.

    Args:
        symbol: Filter by symbol
        status: Filter by status (active, triggered, expired, disabled)
    """
    manager = get_alert_manager()

    alert_status = None
    if status:
        try:
            alert_status = AlertStatus(status)
        except ValueError:
            pass

    alerts = manager.get_alerts(symbol=symbol, status=alert_status)

    return {
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


@router.post("")
async def create_alert(request: CreateAlertRequest) -> dict[str, Any]:
    """Create a new price alert."""
    try:
        manager = get_alert_manager()
        alert = manager.create_alert(
            symbol=request.symbol,
            alert_type=request.alert_type,
            threshold=request.threshold,
            cooldown_minutes=request.cooldown_minutes,
            expires_hours=request.expires_hours,
            note=request.note,
        )
        return {
            "status": "success",
            "alert": alert.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Create alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_alerts_summary() -> dict[str, Any]:
    """Get alerts summary for dashboard."""
    manager = get_alert_manager()
    summary = manager.get_summary()
    return summary.to_dict()


@router.get("/{alert_id}")
async def get_alert(alert_id: str) -> dict[str, Any]:
    """Get a specific alert by ID."""
    manager = get_alert_manager()
    alert = manager.get_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    return alert.to_dict()


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str) -> dict[str, Any]:
    """Delete an alert."""
    manager = get_alert_manager()

    if manager.delete_alert(alert_id):
        return {"status": "success", "alert_id": alert_id}

    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@router.post("/{alert_id}/disable")
async def disable_alert(alert_id: str) -> dict[str, Any]:
    """Disable an alert."""
    manager = get_alert_manager()

    if manager.disable_alert(alert_id):
        return {"status": "success", "alert_id": alert_id, "state": "disabled"}

    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@router.post("/{alert_id}/enable")
async def enable_alert(alert_id: str) -> dict[str, Any]:
    """Enable a disabled alert."""
    manager = get_alert_manager()

    if manager.enable_alert(alert_id):
        return {"status": "success", "alert_id": alert_id, "state": "active"}

    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
