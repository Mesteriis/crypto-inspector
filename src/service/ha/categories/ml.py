"""Machine Learning prediction sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import DictSensor
from service.ha.sensors.scalar import CountSensor, PercentSensor, StatusSensor


@register_sensor(category="ml")
class MlSystemStatusSensor(StatusSensor):
    """ML system status."""

    config = SensorConfig(
        sensor_id="ml_system_status",
        name="ML System Status",
        name_ru="Статус ML системы",
        icon="mdi:robot",
        description="ML system operational status",
        description_ru="Операционный статус ML системы",
    )


@register_sensor(category="ml")
class MlPortfolioHealthSensor(StatusSensor):
    """ML portfolio health assessment."""

    config = SensorConfig(
        sensor_id="ml_portfolio_health",
        name="ML Portfolio Health",
        name_ru="ML оценка здоровья портфеля",
        icon="mdi:shield-check",
        description="ML-based portfolio health assessment",
        description_ru="ML-оценка здоровья портфеля",
    )


@register_sensor(category="ml")
class MlMarketConfidenceSensor(StatusSensor):
    """ML market confidence level."""

    config = SensorConfig(
        sensor_id="ml_market_confidence",
        name="ML Market Confidence",
        name_ru="ML уверенность рынка",
        icon="mdi:chart-donut",
        description="ML confidence in market direction",
        description_ru="ML уверенность в направлении рынка",
    )


@register_sensor(category="ml")
class MlInvestmentOpportunitySensor(StatusSensor):
    """ML investment opportunity detection."""

    config = SensorConfig(
        sensor_id="ml_investment_opportunity",
        name="ML Investment Opportunity",
        name_ru="ML инвестиционные возможности",
        icon="mdi:lightbulb-on",
        description="ML-detected investment opportunities",
        description_ru="ML-обнаруженные инвестиционные возможности",
    )


@register_sensor(category="ml")
class MlRiskWarningSensor(StatusSensor):
    """ML risk warning level."""

    config = SensorConfig(
        sensor_id="ml_risk_warning",
        name="ML Risk Warning",
        name_ru="ML предупреждение о рисках",
        icon="mdi:alert-circle",
        description="ML-based risk warning level",
        description_ru="ML-предупреждение об уровне риска",
    )


@register_sensor(category="ml")
class MlAccuracyRateSensor(PercentSensor):
    """ML prediction accuracy rate."""

    config = SensorConfig(
        sensor_id="ml_accuracy_rate",
        name="ML Accuracy Rate",
        name_ru="Точность ML",
        icon="mdi:target",
        unit="%",
        description="ML prediction accuracy percentage",
        description_ru="Процент точности ML предсказаний",
    )


@register_sensor(category="ml")
class MlCorrectPredictionsSensor(CountSensor):
    """ML correct predictions count."""

    config = SensorConfig(
        sensor_id="ml_correct_predictions",
        name="ML Correct Predictions",
        name_ru="Верные предсказания ML",
        icon="mdi:check-circle",
        description="Number of correct ML predictions",
        description_ru="Количество верных ML предсказаний",
    )


@register_sensor(category="ml")
class MlLatestPredictionsSensor(DictSensor):
    """Latest ML predictions for all coins."""

    config = SensorConfig(
        sensor_id="ml_latest_predictions",
        name="ML Latest Predictions",
        name_ru="Последние предсказания ML",
        icon="mdi:crystal-ball",
        description='Latest ML predictions. Format: {"BTC": "bullish", "ETH": "neutral"}',
        description_ru='Последние ML предсказания. Формат: {"BTC": "bullish", "ETH": "neutral"}',
    )


@register_sensor(category="ml")
class MlSuccessRateSensor(PercentSensor):
    """ML overall success rate."""

    config = SensorConfig(
        sensor_id="success_rate",
        name="Success Rate",
        name_ru="Успешность",
        icon="mdi:percent",
        unit="%",
        description="Overall ML prediction success rate",
        description_ru="Общий процент успешных ML предсказаний",
    )
