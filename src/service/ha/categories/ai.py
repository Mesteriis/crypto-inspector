"""AI/ML analytics sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import DictSensor
from service.ha.sensors.scalar import ScalarSensor, StatusSensor


@register_sensor(category="ai")
class AiDailySummarySensor(StatusSensor):
    """AI daily market summary."""

    config = SensorConfig(
        sensor_id="ai_daily_summary",
        name="AI Daily Summary",
        name_ru="AI дневная сводка",
        icon="mdi:robot",
        description="Daily AI market summary",
        description_ru="Ежедневная AI-сводка по рынку",
    )


@register_sensor(category="ai")
class AiMarketSentimentSensor(StatusSensor):
    """AI market sentiment assessment."""

    config = SensorConfig(
        sensor_id="ai_market_sentiment",
        name="AI Market Sentiment",
        name_ru="AI настроение",
        icon="mdi:brain",
        description="AI assessment of market sentiment",
        description_ru="Оценка настроения рынка от AI",
    )


@register_sensor(category="ai")
class AiRecommendationSensor(StatusSensor):
    """AI recommendation for actions."""

    config = SensorConfig(
        sensor_id="ai_recommendation",
        name="AI Recommendation",
        name_ru="AI рекомендация",
        icon="mdi:lightbulb",
        description="AI recommendation for actions",
        description_ru="Рекомендация AI по действиям",
    )


@register_sensor(category="ai")
class AiLastAnalysisSensor(ScalarSensor):
    """Time of last AI analysis."""

    config = SensorConfig(
        sensor_id="ai_last_analysis",
        name="AI Last Analysis",
        name_ru="AI последний анализ",
        icon="mdi:clock-outline",
        description="Time of last AI analysis",
        description_ru="Время последнего AI-анализа",
    )


@register_sensor(category="ai")
class AiProviderSensor(StatusSensor):
    """Used AI provider."""

    config = SensorConfig(
        sensor_id="ai_provider",
        name="AI Provider",
        name_ru="AI провайдер",
        icon="mdi:cog",
        entity_category="diagnostic",
        description="Used AI provider",
        description_ru="Используемый AI-провайдер",
    )


@register_sensor(category="ai")
class AiTrendsSensor(DictSensor):
    """AI-predicted trends for all currencies."""

    config = SensorConfig(
        sensor_id="ai_trends",
        name="AI Trends",
        name_ru="AI Тренды",
        icon="mdi:brain",
        entity_category="diagnostic",
        description='AI-predicted trends for all currencies. Format: {"BTC": "Bullish", "ETH": "Neutral"}',
        description_ru='AI-предсказанные тренды для всех валют. Формат: {"BTC": "Bullish", "ETH": "Neutral"}',
    )


@register_sensor(category="ai")
class AiConfidencesSensor(DictSensor):
    """AI prediction confidences for all currencies."""

    config = SensorConfig(
        sensor_id="ai_confidences",
        name="AI Confidences",
        name_ru="AI Уверенности",
        icon="mdi:percent",
        unit="%",
        entity_category="diagnostic",
        description='AI prediction confidences for all currencies. Format: {"BTC": 85, "ETH": 78}',
        description_ru='Уровни уверенности AI-предсказаний для всех валют. Формат: {"BTC": 85, "ETH": 78}',
    )


@register_sensor(category="ai")
class AiPriceForecasts24hSensor(DictSensor):
    """AI 24h price forecasts."""

    config = SensorConfig(
        sensor_id="ai_price_forecasts_24h",
        name="AI 24h Price Forecasts",
        name_ru="AI Прогнозы цен 24ч",
        icon="mdi:chart-line",
        unit="USDT",
        entity_category="diagnostic",
        description='AI-predicted prices in 24 hours for all currencies. Format: {"BTC": 95000, "ETH": 3200}',
        description_ru='AI-прогнозы цен через 24 часа для всех валют. Формат: {"BTC": 95000, "ETH": 3200}',
    )
