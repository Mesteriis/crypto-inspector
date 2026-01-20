"""Whale activity sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import CountSensor, StatusSensor


@register_sensor(category="whales")
class WhaleAlerts24hSensor(CountSensor):
    """Whale alerts in last 24h."""

    config = SensorConfig(
        sensor_id="whale_alerts_24h",
        name="Whale Alerts 24h",
        name_ru="Алерты китов 24ч",
        icon="mdi:fish",
        description="Number of large transactions in 24h",
        description_ru="Количество крупных транзакций за 24ч",
    )


@register_sensor(category="whales")
class WhaleNetFlowSensor(StatusSensor):
    """Whale net flow direction."""

    config = SensorConfig(
        sensor_id="whale_net_flow",
        name="Whale Net Flow",
        name_ru="Нетто-поток китов",
        icon="mdi:arrow-decision",
        description="Net inflow/outflow from large wallets",
        description_ru="Чистый приток/отток от крупных кошельков",
    )


@register_sensor(category="whales")
class WhaleLastAlertSensor(StatusSensor):
    """Last whale alert."""

    config = SensorConfig(
        sensor_id="whale_last_alert",
        name="Last Whale Alert",
        name_ru="Последний алерт кита",
        icon="mdi:bell-ring",
        description="Last large transaction",
        description_ru="Последняя крупная транзакция",
    )
