"""Volatility sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import DictSensor
from service.ha.sensors.scalar import PercentSensor, StatusSensor


@register_sensor(category="volatility")
class Volatility30dSensor(DictSensor):
    """30-day volatility by coin."""

    config = SensorConfig(
        sensor_id="volatility_30d",
        name="30d Volatility",
        name_ru="Волатильность 30д",
        icon="mdi:chart-bell-curve",
        description='30-day volatility. Format: {"BTC": 45}',
        description_ru='30-дневная волатильность. Формат: {"BTC": 45}',
    )


@register_sensor(category="volatility")
class VolatilityPercentileSensor(PercentSensor):
    """Volatility percentile in historical distribution."""

    config = SensorConfig(
        sensor_id="volatility_percentile",
        name="Volatility Percentile",
        name_ru="Перцентиль волатильности",
        icon="mdi:percent-box",
        description="Position in historical distribution",
        description_ru="Позиция в историческом распределении",
    )


@register_sensor(category="volatility")
class VolatilityStatusSensor(StatusSensor):
    """Volatility status."""

    config = SensorConfig(
        sensor_id="volatility_status",
        name="Volatility Status",
        name_ru="Статус волатильности",
        icon="mdi:pulse",
        description="Low/medium/high volatility",
        description_ru="Низкая/средняя/высокая волатильность",
    )
