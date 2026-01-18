"""
Price Alerts Service.

Configurable price alerts for cryptocurrencies:
- Alert when price crosses above/below a level
- Cooldown to prevent spam
- Notification via HA integration

Features:
- Multiple alerts per symbol
- Above/below threshold types
- Percentage-based alerts (e.g., alert if +5% in 1h)
- Cooldown periods
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Type of price alert."""

    ABOVE = "above"  # Alert when price goes above threshold
    BELOW = "below"  # Alert when price goes below threshold
    CHANGE_UP = "change_up"  # Alert on % increase
    CHANGE_DOWN = "change_down"  # Alert on % decrease


class AlertStatus(Enum):
    """Alert status."""

    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    DISABLED = "disabled"


@dataclass
class PriceAlert:
    """Single price alert configuration."""

    id: str
    symbol: str
    alert_type: AlertType
    threshold: float  # Price level or percentage
    created_at: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    triggered_at: datetime | None = None
    triggered_price: float | None = None
    cooldown_minutes: int = 60  # Minimum time between triggers
    expires_at: datetime | None = None  # Optional expiration
    note: str = ""  # User note
    notification_sent: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "alert_type": self.alert_type.value,
            "threshold": self.threshold,
            "threshold_formatted": self._format_threshold(),
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "triggered_price": self.triggered_price,
            "cooldown_minutes": self.cooldown_minutes,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "note": self.note,
        }

    def _format_threshold(self) -> str:
        """Format threshold for display."""
        if self.alert_type in [AlertType.CHANGE_UP, AlertType.CHANGE_DOWN]:
            return f"{self.threshold:+.1f}%"
        return f"${self.threshold:,.2f}"

    def check_trigger(self, current_price: float, prev_price: float | None = None) -> bool:
        """
        Check if alert should be triggered.

        Args:
            current_price: Current price
            prev_price: Previous price (for change alerts)

        Returns:
            True if alert should trigger
        """
        # Check if in cooldown
        if self.triggered_at:
            cooldown_end = self.triggered_at + timedelta(minutes=self.cooldown_minutes)
            if datetime.now() < cooldown_end:
                return False

        # Check expiration
        if self.expires_at and datetime.now() > self.expires_at:
            self.status = AlertStatus.EXPIRED
            return False

        # Check threshold based on type
        if self.alert_type == AlertType.ABOVE:
            return current_price >= self.threshold
        elif self.alert_type == AlertType.BELOW:
            return current_price <= self.threshold
        elif self.alert_type == AlertType.CHANGE_UP and prev_price:
            change_pct = ((current_price - prev_price) / prev_price) * 100
            return change_pct >= self.threshold
        elif self.alert_type == AlertType.CHANGE_DOWN and prev_price:
            change_pct = ((current_price - prev_price) / prev_price) * 100
            return change_pct <= -self.threshold

        return False

    def trigger(self, price: float) -> None:
        """Mark alert as triggered."""
        self.status = AlertStatus.TRIGGERED
        self.triggered_at = datetime.now()
        self.triggered_price = price


@dataclass
class AlertSummary:
    """Summary of all alerts."""

    timestamp: datetime
    total_alerts: int
    active_alerts: int
    triggered_24h: int
    alerts_by_symbol: dict[str, int] = field(default_factory=dict)
    recent_triggers: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_alerts": self.total_alerts,
            "active_alerts": self.active_alerts,
            "triggered_24h": self.triggered_24h,
            "alerts_by_symbol": self.alerts_by_symbol,
            "recent_triggers": self.recent_triggers,
            "summary": f"{self.active_alerts} active, {self.triggered_24h} triggered (24h)",
            "summary_ru": f"{self.active_alerts} активных, {self.triggered_24h} сработало (24ч)",
        }


class PriceAlertManager:
    """
    Price alert management service.

    Manages price alerts and triggers notifications.
    """

    def __init__(self):
        self._alerts: dict[str, PriceAlert] = {}
        self._price_cache: dict[str, float] = {}  # Last known prices

    def create_alert(
        self,
        symbol: str,
        alert_type: AlertType | str,
        threshold: float,
        cooldown_minutes: int = 60,
        expires_hours: int | None = None,
        note: str = "",
    ) -> PriceAlert:
        """
        Create a new price alert.

        Args:
            symbol: Trading symbol (e.g., "BTC")
            alert_type: Type of alert
            threshold: Price level or percentage
            cooldown_minutes: Cooldown between triggers
            expires_hours: Optional expiration in hours
            note: User note

        Returns:
            Created alert
        """
        if isinstance(alert_type, str):
            alert_type = AlertType(alert_type)

        alert_id = str(uuid.uuid4())[:8]

        expires_at = None
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)

        alert = PriceAlert(
            id=alert_id,
            symbol=symbol.upper(),
            alert_type=alert_type,
            threshold=threshold,
            created_at=datetime.now(),
            cooldown_minutes=cooldown_minutes,
            expires_at=expires_at,
            note=note,
        )

        self._alerts[alert_id] = alert
        logger.info(f"Created alert {alert_id}: {symbol} {alert_type.value} {threshold}")

        return alert

    def get_alert(self, alert_id: str) -> PriceAlert | None:
        """Get alert by ID."""
        return self._alerts.get(alert_id)

    def get_alerts(
        self,
        symbol: str | None = None,
        status: AlertStatus | None = None,
    ) -> list[PriceAlert]:
        """
        Get alerts with optional filtering.

        Args:
            symbol: Filter by symbol
            status: Filter by status

        Returns:
            List of matching alerts
        """
        alerts = list(self._alerts.values())

        if symbol:
            alerts = [a for a in alerts if a.symbol == symbol.upper()]

        if status:
            alerts = [a for a in alerts if a.status == status]

        return sorted(alerts, key=lambda x: x.created_at, reverse=True)

    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert."""
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            logger.info(f"Deleted alert {alert_id}")
            return True
        return False

    def disable_alert(self, alert_id: str) -> bool:
        """Disable an alert."""
        if alert_id in self._alerts:
            self._alerts[alert_id].status = AlertStatus.DISABLED
            return True
        return False

    def enable_alert(self, alert_id: str) -> bool:
        """Re-enable a disabled alert."""
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            if alert.status == AlertStatus.DISABLED:
                alert.status = AlertStatus.ACTIVE
                return True
        return False

    async def check_prices(self, prices: dict[str, float]) -> list[tuple[PriceAlert, float]]:
        """
        Check all alerts against current prices.

        Args:
            prices: Dict of symbol -> current price

        Returns:
            List of (triggered_alert, price) tuples
        """
        triggered = []

        for alert in self._alerts.values():
            if alert.status != AlertStatus.ACTIVE:
                continue

            current_price = prices.get(alert.symbol)
            if current_price is None:
                continue

            prev_price = self._price_cache.get(alert.symbol)

            if alert.check_trigger(current_price, prev_price):
                alert.trigger(current_price)
                triggered.append((alert, current_price))
                logger.info(
                    f"Alert triggered: {alert.id} - {alert.symbol} {alert.alert_type.value} at ${current_price}"
                )

        # Update price cache
        self._price_cache.update(prices)

        return triggered

    def get_summary(self) -> AlertSummary:
        """Get alert summary."""
        now = datetime.now()
        day_ago = now - timedelta(hours=24)

        all_alerts = list(self._alerts.values())
        active = [a for a in all_alerts if a.status == AlertStatus.ACTIVE]
        triggered_24h = [a for a in all_alerts if a.triggered_at and a.triggered_at > day_ago]

        # Count by symbol
        by_symbol: dict[str, int] = {}
        for alert in active:
            by_symbol[alert.symbol] = by_symbol.get(alert.symbol, 0) + 1

        # Recent triggers
        recent = sorted(triggered_24h, key=lambda x: x.triggered_at or now, reverse=True)[:5]

        return AlertSummary(
            timestamp=now,
            total_alerts=len(all_alerts),
            active_alerts=len(active),
            triggered_24h=len(triggered_24h),
            alerts_by_symbol=by_symbol,
            recent_triggers=[
                {
                    "id": a.id,
                    "symbol": a.symbol,
                    "type": a.alert_type.value,
                    "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
                    "price": a.triggered_price,
                }
                for a in recent
            ],
        )

    def generate_notification(self, alert: PriceAlert, price: float) -> dict[str, Any]:
        """Generate notification data for triggered alert."""
        type_messages = {
            AlertType.ABOVE: f"выше ${alert.threshold:,.0f}",
            AlertType.BELOW: f"ниже ${alert.threshold:,.0f}",
            AlertType.CHANGE_UP: f"вырос на {alert.threshold}%+",
            AlertType.CHANGE_DOWN: f"упал на {alert.threshold}%+",
        }

        msg = type_messages.get(alert.alert_type, str(alert.threshold))

        return {
            "title": f"💰 {alert.symbol} Alert",
            "message": f"{alert.symbol} {msg}\nТекущая цена: ${price:,.2f}",
            "notification_id": f"price_alert_{alert.id}",
            "data": {
                "alert_id": alert.id,
                "symbol": alert.symbol,
                "price": price,
                "threshold": alert.threshold,
                "type": alert.alert_type.value,
            },
        }


# Global instance
_alert_manager: PriceAlertManager | None = None


def get_alert_manager() -> PriceAlertManager:
    """Get global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = PriceAlertManager()
    return _alert_manager
