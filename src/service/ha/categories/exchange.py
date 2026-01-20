"""Exchange flow sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import DictSensor
from service.ha.sensors.scalar import StatusSensor


@register_sensor(category="exchange")
class ExchangeNetflowsSensor(DictSensor):
    """Net flows to exchanges by coin."""

    config = SensorConfig(
        sensor_id="exchange_netflows",
        name="Exchange Netflows",
        name_ru="Потоки на биржи",
        icon="mdi:bank-transfer",
        description='Net flows to exchanges. Format: {"BTC": -500, "ETH": 200}',
        description_ru='Нетто-потоки на биржи. Формат: {"BTC": -500, "ETH": 200}',
    )


@register_sensor(category="exchange")
class ExchangeFlowSignalSensor(StatusSensor):
    """Exchange flow signal."""

    config = SensorConfig(
        sensor_id="exchange_flow_signal",
        name="Flow Signal",
        name_ru="Сигнал потоков",
        icon="mdi:trending-up",
        description="Signal: accumulation/distribution/neutral",
        description_ru="Сигнал: накопление/распределение/нейтрально",
    )
