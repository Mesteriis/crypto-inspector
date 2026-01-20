"""Gas tracker sensors - ETH gas prices."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import ScalarSensor, StatusSensor


@register_sensor(category="gas")
class EthGasSlowSensor(ScalarSensor):
    """Slow ETH gas price."""

    config = SensorConfig(
        sensor_id="eth_gas_slow",
        name="ETH Gas Slow",
        name_ru="ETH Gas медленный",
        icon="mdi:speedometer-slow",
        unit="Gwei",
        description="Gas price for slow transactions",
        description_ru="Цена газа для медленных транзакций",
        value_type="int",
        min_value=0,
    )


@register_sensor(category="gas")
class EthGasStandardSensor(ScalarSensor):
    """Standard ETH gas price."""

    config = SensorConfig(
        sensor_id="eth_gas_standard",
        name="ETH Gas Standard",
        name_ru="ETH Gas стандартный",
        icon="mdi:speedometer-medium",
        unit="Gwei",
        description="Gas price for standard transactions",
        description_ru="Цена газа для стандартных транзакций",
        value_type="int",
        min_value=0,
    )


@register_sensor(category="gas")
class EthGasFastSensor(ScalarSensor):
    """Fast ETH gas price."""

    config = SensorConfig(
        sensor_id="eth_gas_fast",
        name="ETH Gas Fast",
        name_ru="ETH Gas быстрый",
        icon="mdi:speedometer",
        unit="Gwei",
        description="Gas price for fast transactions",
        description_ru="Цена газа для быстрых транзакций",
        value_type="int",
        min_value=0,
    )


@register_sensor(category="gas")
class EthGasStatusSensor(StatusSensor):
    """ETH network gas status."""

    config = SensorConfig(
        sensor_id="eth_gas_status",
        name="ETH Gas Status",
        name_ru="Статус ETH Gas",
        icon="mdi:gas-station",
        description="Current network status: low/medium/high",
        description_ru="Текущий статус сети: низкий/средний/высокий",
    )
