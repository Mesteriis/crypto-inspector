"""Price sensors - prices, changes, volumes, highs, lows.

All sensors use dict format: {"BTC": value, "ETH": value}
"""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import DictSensor, PercentDictSensor, PriceDictSensor


@register_sensor(category="price")
class PricesSensor(PriceDictSensor):
    """Current prices of all coins."""

    config = SensorConfig(
        sensor_id="prices",
        name="Crypto Prices",
        name_ru="Крипто цены",
        icon="mdi:currency-usd",
        unit="USDT",
        description='Current prices of all coins. Format: {"BTC": 95000, "ETH": 3200}',
        description_ru='Текущие цены всех монет. Формат: {"BTC": 95000, "ETH": 3200}',
    )


@register_sensor(category="price")
class Changes24hSensor(PercentDictSensor):
    """24h price changes for all coins."""

    config = SensorConfig(
        sensor_id="changes_24h",
        name="24h Change",
        name_ru="Изменение 24ч",
        icon="mdi:percent",
        unit="%",
        description='Price change over 24 hours (%). Format: {"BTC": 2.5}',
        description_ru='Изменение цены за 24 часа (%). Формат: {"BTC": 2.5}',
    )


@register_sensor(category="price")
class Volumes24hSensor(DictSensor):
    """24h trading volumes for all coins."""

    config = SensorConfig(
        sensor_id="volumes_24h",
        name="24h Volumes",
        name_ru="Объёмы 24ч",
        icon="mdi:chart-bar",
        unit="USDT",
        description='Trading volume over 24 hours. Format: {"BTC": 50000000000}',
        description_ru='Объём торгов за 24 часа. Формат: {"BTC": 50000000000}',
    )


@register_sensor(category="price")
class Highs24hSensor(PriceDictSensor):
    """24h high prices for all coins."""

    config = SensorConfig(
        sensor_id="highs_24h",
        name="24h Highs",
        name_ru="Максимумы 24ч",
        icon="mdi:arrow-up-bold",
        unit="USDT",
        description='Highest price over 24 hours. Format: {"BTC": 96000}',
        description_ru='Максимальная цена за 24 часа. Формат: {"BTC": 96000}',
    )


@register_sensor(category="price")
class Lows24hSensor(PriceDictSensor):
    """24h low prices for all coins."""

    config = SensorConfig(
        sensor_id="lows_24h",
        name="24h Lows",
        name_ru="Минимумы 24ч",
        icon="mdi:arrow-down-bold",
        unit="USDT",
        description='Lowest price over 24 hours. Format: {"BTC": 94000}',
        description_ru='Минимальная цена за 24 часа. Формат: {"BTC": 94000}',
    )
