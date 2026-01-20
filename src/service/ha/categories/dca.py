"""DCA calculator sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import PercentSensor, ScalarSensor, StatusSensor


@register_sensor(category="dca")
class DcaNextLevelSensor(ScalarSensor):
    """Next DCA price level."""

    config = SensorConfig(
        sensor_id="dca_next_level",
        name="DCA Next Level",
        name_ru="Следующий уровень DCA",
        icon="mdi:target",
        unit="USDT",
        description="Price for next DCA purchase",
        description_ru="Цена для следующей покупки DCA",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="dca")
class DcaZoneSensor(StatusSensor):
    """Current DCA zone."""

    config = SensorConfig(
        sensor_id="dca_zone",
        name="DCA Zone",
        name_ru="Зона DCA",
        icon="mdi:map-marker-radius",
        description="Current zone: buy/accumulate/wait",
        description_ru="Текущая зона: покупка/накопление/ожидание",
    )


@register_sensor(category="dca")
class DcaRiskScoreSensor(PercentSensor):
    """DCA risk score."""

    config = SensorConfig(
        sensor_id="dca_risk_score",
        name="DCA Risk Score",
        name_ru="Риск-скор DCA",
        icon="mdi:gauge",
        description="Risk assessment for DCA (0-100)",
        description_ru="Оценка риска для DCA (0-100)",
    )
