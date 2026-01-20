"""Correlation analysis sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import CountSensor, ScalarSensor, StatusSensor


@register_sensor(category="correlation")
class BtcEthCorrelationSensor(ScalarSensor):
    """BTC/ETH correlation coefficient."""

    config = SensorConfig(
        sensor_id="btc_eth_correlation",
        name="BTC/ETH Correlation",
        name_ru="Корреляция BTC/ETH",
        icon="mdi:link-variant",
        description="Correlation coefficient between BTC and ETH",
        description_ru="Коэффициент корреляции BTC и ETH",
        value_type="float",
        min_value=-1,
        max_value=1,
    )


@register_sensor(category="correlation")
class BtcSp500CorrelationSensor(ScalarSensor):
    """BTC/S&P500 correlation coefficient."""

    config = SensorConfig(
        sensor_id="btc_sp500_correlation",
        name="BTC/S&P500 Correlation",
        name_ru="Корреляция BTC/S&P500",
        icon="mdi:chart-line-variant",
        description="Correlation between crypto and stock market",
        description_ru="Корреляция крипты с фондовым рынком",
        value_type="float",
        min_value=-1,
        max_value=1,
    )


@register_sensor(category="correlation")
class CorrelationStatusSensor(StatusSensor):
    """Overall correlation status."""

    config = SensorConfig(
        sensor_id="correlation_status",
        name="Correlation Status",
        name_ru="Статус корреляции",
        icon="mdi:connection",
        description="Overall correlation status",
        description_ru="Общий статус корреляций",
    )


@register_sensor(category="correlation")
class CorrelationAnalysisStatusSensor(StatusSensor):
    """Correlation analysis system status."""

    config = SensorConfig(
        sensor_id="correlation_analysis_status",
        name="Correlation Analysis",
        name_ru="Анализ корреляций",
        icon="mdi:chart-scatter-plot",
        entity_category="diagnostic",
        description="Status of correlation analysis system",
        description_ru="Статус системы анализа корреляций",
    )


@register_sensor(category="correlation")
class CorrelationSignificantCountSensor(CountSensor):
    """Number of significant correlations."""

    config = SensorConfig(
        sensor_id="correlation_significant_count",
        name="Significant Correlations",
        name_ru="Значимые корреляции",
        icon="mdi:counter",
        entity_category="diagnostic",
        description="Number of significant correlation pairs",
        description_ru="Количество пар со значимой корреляцией",
    )


@register_sensor(category="correlation")
class CorrelationStrongestPositiveSensor(StatusSensor):
    """Strongest positive correlation pair."""

    config = SensorConfig(
        sensor_id="correlation_strongest_positive",
        name="Strongest Positive",
        name_ru="Сильнейшая положительная",
        icon="mdi:trending-up",
        entity_category="diagnostic",
        description="Pair with strongest positive correlation",
        description_ru="Пара с сильнейшей положительной корреляцией",
    )


@register_sensor(category="correlation")
class CorrelationStrongestNegativeSensor(StatusSensor):
    """Strongest negative correlation pair."""

    config = SensorConfig(
        sensor_id="correlation_strongest_negative",
        name="Strongest Negative",
        name_ru="Сильнейшая отрицательная",
        icon="mdi:trending-down",
        entity_category="diagnostic",
        description="Pair with strongest negative correlation",
        description_ru="Пара с сильнейшей отрицательной корреляцией",
    )


@register_sensor(category="correlation")
class CorrelationDominantPatternsSensor(StatusSensor):
    """Dominant correlation patterns."""

    config = SensorConfig(
        sensor_id="correlation_dominant_patterns",
        name="Dominant Patterns",
        name_ru="Доминирующие паттерны",
        icon="mdi:chart-bell-curve-cumulative",
        entity_category="diagnostic",
        description="Dominant correlation patterns in market",
        description_ru="Доминирующие корреляционные паттерны рынка",
    )
