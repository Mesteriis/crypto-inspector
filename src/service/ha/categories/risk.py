"""Risk management sensors - Sharpe, Sortino, drawdown, VaR."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import PercentSensor, ScalarSensor, StatusSensor


@register_sensor(category="risk")
class PortfolioSharpeSensor(ScalarSensor):
    """Sharpe ratio."""

    config = SensorConfig(
        sensor_id="portfolio_sharpe",
        name="Sharpe Ratio",
        name_ru="Коэффициент Шарпа",
        icon="mdi:chart-areaspline",
        description="Return to risk ratio",
        description_ru="Соотношение доходности к риску",
        value_type="float",
    )


@register_sensor(category="risk")
class PortfolioSortinoSensor(ScalarSensor):
    """Sortino ratio."""

    config = SensorConfig(
        sensor_id="portfolio_sortino",
        name="Sortino Ratio",
        name_ru="Коэффициент Сортино",
        icon="mdi:chart-line-variant",
        description="Risk assessment considering drawdowns",
        description_ru="Оценка риска с учётом падений",
        value_type="float",
    )


@register_sensor(category="risk")
class PortfolioMaxDrawdownSensor(PercentSensor):
    """Maximum historical drawdown."""

    config = SensorConfig(
        sensor_id="portfolio_max_drawdown",
        name="Max Drawdown",
        name_ru="Макс. просадка",
        icon="mdi:trending-down",
        unit="%",
        description="Maximum historical drawdown",
        description_ru="Максимальная историческая просадка",
    )


@register_sensor(category="risk")
class PortfolioCurrentDrawdownSensor(PercentSensor):
    """Current drawdown from peak."""

    config = SensorConfig(
        sensor_id="portfolio_current_drawdown",
        name="Current Drawdown",
        name_ru="Текущая просадка",
        icon="mdi:arrow-down",
        unit="%",
        description="Current drawdown from peak",
        description_ru="Текущая просадка от максимума",
    )


@register_sensor(category="risk")
class PortfolioVar95Sensor(PercentSensor):
    """Value at Risk (95% confidence)."""

    config = SensorConfig(
        sensor_id="portfolio_var_95",
        name="VaR 95%",
        name_ru="VaR 95%",
        icon="mdi:alert",
        unit="%",
        description="Value at Risk (95% confidence)",
        description_ru="Стоимость под риском (95% доверия)",
    )


@register_sensor(category="risk")
class RiskStatusSensor(StatusSensor):
    """Overall risk status."""

    config = SensorConfig(
        sensor_id="risk_status",
        name="Risk Status",
        name_ru="Статус риска",
        icon="mdi:shield-alert",
        description="Overall status: low/medium/high",
        description_ru="Общий статус: низкий/средний/высокий",
    )
