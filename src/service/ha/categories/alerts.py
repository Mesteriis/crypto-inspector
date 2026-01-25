"""Alert and notification sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import DictSensor
from service.ha.sensors.scalar import BoolSensor, CountSensor, StatusSensor


@register_sensor(category="alerts")
class ActiveAlertsCountSensor(CountSensor):
    """Active alerts count."""

    config = SensorConfig(
        sensor_id="active_alerts_count",
        name="Active Alerts Count",
        name_ru="Активные алерты",
        icon="mdi:bell-badge",
        description="Number of active notifications",
        description_ru="Количество активных оповещений",
    )


@register_sensor(category="alerts")
class TriggeredAlerts24hSensor(CountSensor):
    """Triggered alerts in last 24h."""

    config = SensorConfig(
        sensor_id="triggered_alerts_24h",
        name="Triggered Alerts 24h",
        name_ru="Сработавшие алерты 24ч",
        icon="mdi:bell-check",
        description="Alerts in the last 24 hours",
        description_ru="Алерты за последние 24 часа",
    )


@register_sensor(category="alerts")
class PendingAlertsCountSensor(CountSensor):
    """Pending alerts count."""

    config = SensorConfig(
        sensor_id="pending_alerts_count",
        name="Pending Alerts Count",
        name_ru="Ожидающие алерты",
        icon="mdi:bell-badge",
        description="Number of unprocessed alerts",
        description_ru="Количество необработанных алертов",
    )


@register_sensor(category="alerts")
class PendingAlertsCriticalSensor(CountSensor):
    """Critical pending alerts."""

    config = SensorConfig(
        sensor_id="pending_alerts_critical",
        name="Critical Alerts Count",
        name_ru="Критические алерты",
        icon="mdi:bell-alert",
        description="Number of critical alerts",
        description_ru="Количество критических алертов",
    )


@register_sensor(category="alerts")
class DailyDigestReadySensor(BoolSensor):
    """Daily digest ready status."""

    config = SensorConfig(
        sensor_id="daily_digest_ready",
        name="Daily Digest Ready",
        name_ru="Дневной дайджест",
        icon="mdi:newspaper",
        description="Is daily digest ready",
        description_ru="Готов ли дневной дайджест",
    )

    true_text = "Ready"
    false_text = "Not Ready"


@register_sensor(category="alerts")
class NotificationModeSensor(StatusSensor):
    """Notification mode."""

    config = SensorConfig(
        sensor_id="notification_mode",
        name="Notification Mode",
        name_ru="Режим уведомлений",
        icon="mdi:bell-cog",
        description="Current mode: all/important/quiet",
        description_ru="Текущий режим: все/важные/тихий",
    )


@register_sensor(category="alerts")
class AdaptiveNotificationsStatusSensor(StatusSensor):
    """Adaptive notifications system status."""

    config = SensorConfig(
        sensor_id="adaptive_notifications_status",
        name="Adaptive Notifications",
        name_ru="Адаптивные уведомления",
        icon="mdi:bell-ring",
        entity_category="diagnostic",
        description="Status of adaptive notification system",
        description_ru="Статус системы адаптивных уведомлений",
    )


@register_sensor(category="alerts")
class AdaptiveVolatilitiesSensor(DictSensor):
    """Current volatility levels for adaptive notifications."""

    config = SensorConfig(
        sensor_id="adaptive_volatilities",
        name="Adaptive Volatilities",
        name_ru="Адаптивные уровни волатильности",
        icon="mdi:wave",
        entity_category="diagnostic",
        description='Current volatility levels for all currencies. Format: {"BTC": "High", "ETH": "Medium"}',
        description_ru='Текущие уровни волатильности для всех валют. Формат: {"BTC": "High", "ETH": "Medium"}',
    )


@register_sensor(category="alerts")
class AdaptiveNotificationCount24hSensor(CountSensor):
    """Notifications count in last 24h."""

    config = SensorConfig(
        sensor_id="adaptive_notification_count_24h",
        name="Notifications 24h",
        name_ru="Уведомлений за 24ч",
        icon="mdi:counter",
        unit="alerts",
        entity_category="diagnostic",
        description="Number of notifications sent in last 24 hours",
        description_ru="Количество уведомлений за последние 24 часа",
    )


@register_sensor(category="alerts")
class AdaptiveAdaptationFactorsSensor(DictSensor):
    """Adaptation factors for notifications."""

    config = SensorConfig(
        sensor_id="adaptive_adaptation_factors",
        name="Adaptation Factors",
        name_ru="Факторы адаптации",
        icon="mdi:tune",
        entity_category="diagnostic",
        description='Current adaptation factors. Format: {"BTC": 1.2, "ETH": 0.8}',
        description_ru='Текущие факторы адаптации. Формат: {"BTC": 1.2, "ETH": 0.8}',
    )


@register_sensor(category="alerts")
class PriceAlertSensor(StatusSensor):
    """Price alert status."""

    config = SensorConfig(
        sensor_id="price_alert",
        name="Price Alert",
        name_ru="Ценовой алерт",
        icon="mdi:cash-alert",
        description="Last price alert details",
        description_ru="Детали последнего ценового алерта",
    )


@register_sensor(category="alerts")
class FearGreedAlertSensor(StatusSensor):
    """Fear & Greed alert status."""

    config = SensorConfig(
        sensor_id="fear_greed_alert",
        name="Fear & Greed Alert",
        name_ru="Алерт страха и жадности",
        icon="mdi:emoticon-angry",
        description="Fear & Greed index alert",
        description_ru="Алерт индекса страха и жадности",
    )
