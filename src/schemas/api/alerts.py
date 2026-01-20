"""Alerts API schemas."""

from pydantic import BaseModel


class CreateAlertRequest(BaseModel):
    """Request to create a price alert."""

    symbol: str
    alert_type: str  # above, below, change_up, change_down
    threshold: float
    cooldown_minutes: int = 60
    expires_hours: int | None = None
    note: str = ""
