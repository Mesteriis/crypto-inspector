"""Portfolio sensors - value, P&L, allocation."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.composite import CompositeSensor
from service.ha.sensors.scalar import PnlPercentSensor, ScalarSensor, StatusSensor


@register_sensor(category="portfolio")
class PortfolioValueSensor(ScalarSensor):
    """Total portfolio value."""

    config = SensorConfig(
        sensor_id="portfolio_value",
        name="Portfolio Value",
        name_ru="Стоимость портфеля",
        icon="mdi:wallet",
        unit="USDT",
        description="Total portfolio value",
        description_ru="Общая стоимость портфеля",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="portfolio")
class PortfolioPnlSensor(PnlPercentSensor):
    """Total portfolio P&L."""

    config = SensorConfig(
        sensor_id="portfolio_pnl",
        name="Portfolio P&L",
        name_ru="Прибыль/Убыток",
        icon="mdi:chart-line",
        unit="%",
        description="Total portfolio profit/loss (%)",
        description_ru="Общий P&L портфеля (%)",
    )


@register_sensor(category="portfolio")
class PortfolioPnl24hSensor(PnlPercentSensor):
    """24h portfolio change."""

    config = SensorConfig(
        sensor_id="portfolio_pnl_24h",
        name="Portfolio 24h Change",
        name_ru="Портфель изм. 24ч",
        icon="mdi:chart-areaspline",
        unit="%",
        description="Portfolio change over 24 hours (%)",
        description_ru="Изменение портфеля за 24 часа (%)",
    )


@register_sensor(category="portfolio")
class PortfolioAllocationSensor(CompositeSensor):
    """Portfolio asset allocation."""

    config = SensorConfig(
        sensor_id="portfolio_allocation",
        name="Portfolio Allocation",
        name_ru="Распределение",
        icon="mdi:chart-donut",
        description="Asset allocation in portfolio",
        description_ru="Распределение активов в портфеле",
    )


@register_sensor(category="portfolio")
class PortfolioBestSensor(StatusSensor):
    """Best performing asset in portfolio."""

    config = SensorConfig(
        sensor_id="portfolio_best",
        name="Best Performer",
        name_ru="Лучший актив",
        icon="mdi:trophy",
        description="Best performing asset in portfolio",
        description_ru="Лучший актив в портфеле",
    )


@register_sensor(category="portfolio")
class PortfolioWorstSensor(StatusSensor):
    """Worst performing asset in portfolio."""

    config = SensorConfig(
        sensor_id="portfolio_worst",
        name="Worst Performer",
        name_ru="Худший актив",
        icon="mdi:arrow-down-bold",
        description="Worst performing asset in portfolio",
        description_ru="Худший актив в портфеле",
    )
