"""Market indicators - Fear & Greed, dominance, derivatives, altseason, stablecoins."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.composite import CompositeSensor
from service.ha.sensors.scalar import PercentSensor, ScalarSensor, StatusSensor


@register_sensor(category="market")
class FearGreedSensor(ScalarSensor):
    """Fear & Greed Index (0-100)."""

    config = SensorConfig(
        sensor_id="fear_greed",
        name="Fear & Greed Index",
        name_ru="Индекс страха и жадности",
        icon="mdi:emoticon-neutral",
        description="Fear & Greed Index (0-100). 0=fear, 100=greed",
        description_ru="Fear & Greed Index (0-100). 0=страх, 100=жадность",
        value_type="int",
        min_value=0,
        max_value=100,
    )

    def format_state(self, value: int) -> str:
        """Format with emoji and classification."""
        if value <= 25:
            return f"🔴 {value} (Extreme Fear)"
        elif value <= 45:
            return f"🟠 {value} (Fear)"
        elif value <= 55:
            return f"⚪ {value} (Neutral)"
        elif value <= 75:
            return f"🟢 {value} (Greed)"
        else:
            return f"🟢 {value} (Extreme Greed)"


@register_sensor(category="market")
class BtcDominanceSensor(PercentSensor):
    """Bitcoin market dominance."""

    config = SensorConfig(
        sensor_id="btc_dominance",
        name="BTC Dominance",
        name_ru="Доминация BTC",
        icon="mdi:crown",
        unit="%",
        description="Bitcoin share in the market (%)",
        description_ru="Доля Bitcoin на рынке (%)",
    )


@register_sensor(category="market")
class DerivativesSensor(CompositeSensor):
    """Derivatives market data."""

    config = SensorConfig(
        sensor_id="derivatives",
        name="Derivatives",
        name_ru="Деривативы",
        icon="mdi:chart-timeline-variant",
        description="Futures and options data",
        description_ru="Данные по фьючерсам и опционам",
    )


@register_sensor(category="market")
class AltseasonIndexSensor(ScalarSensor):
    """Altseason index (0-100)."""

    config = SensorConfig(
        sensor_id="altseason_index",
        name="Altseason Index",
        name_ru="Индекс альтсезона",
        icon="mdi:rocket-launch",
        description="Altcoin season index (0-100)",
        description_ru="Индекс альткоин сезона (0-100)",
        value_type="int",
        min_value=0,
        max_value=100,
    )


@register_sensor(category="market")
class AltseasonStatusSensor(StatusSensor):
    """Altseason status."""

    config = SensorConfig(
        sensor_id="altseason_status",
        name="Altseason Status",
        name_ru="Статус альтсезона",
        icon="mdi:weather-sunny",
        description="Bitcoin season / Altseason / Neutral",
        description_ru="Биткоин сезон / Альтсезон / Нейтрально",
    )


@register_sensor(category="market")
class StablecoinTotalSensor(ScalarSensor):
    """Total stablecoin market cap."""

    config = SensorConfig(
        sensor_id="stablecoin_total",
        name="Stablecoin Volume",
        name_ru="Объём стейблкоинов",
        icon="mdi:currency-usd-circle",
        description="Total stablecoin volume in the market",
        description_ru="Общий объём стейблкоинов на рынке",
    )


@register_sensor(category="market")
class StablecoinFlowSensor(StatusSensor):
    """Stablecoin flow to/from exchanges."""

    config = SensorConfig(
        sensor_id="stablecoin_flow",
        name="Stablecoin Flow",
        name_ru="Поток стейблкоинов",
        icon="mdi:swap-horizontal",
        description="Inflow/outflow of stablecoins to exchanges",
        description_ru="Приток/отток стейблкоинов на биржи",
    )


@register_sensor(category="market")
class StablecoinDominanceSensor(PercentSensor):
    """Stablecoin market dominance."""

    config = SensorConfig(
        sensor_id="stablecoin_dominance",
        name="Stablecoin Dominance",
        name_ru="Доминация стейблкоинов",
        icon="mdi:chart-pie",
        unit="%",
        description="Share of stablecoins in the market (%)",
        description_ru="Доля стейблкоинов на рынке (%)",
    )
