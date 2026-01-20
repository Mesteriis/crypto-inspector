"""Smart summary sensors - market pulse, portfolio health, actions, outlook."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import PercentSensor, ScalarSensor, StatusSensor


@register_sensor(category="smart_summary")
class MarketPulseSensor(StatusSensor):
    """Overall market sentiment pulse."""

    config = SensorConfig(
        sensor_id="market_pulse",
        name="Market Pulse",
        name_ru="Пульс рынка",
        icon="mdi:pulse",
        description="Overall market sentiment",
        description_ru="Общее настроение рынка",
    )


@register_sensor(category="smart_summary")
class MarketPulseConfidenceSensor(PercentSensor):
    """Confidence in market pulse assessment."""

    config = SensorConfig(
        sensor_id="market_pulse_confidence",
        name="Market Pulse Confidence",
        name_ru="Уверенность пульса",
        icon="mdi:percent",
        unit="%",
        description="Confidence in market assessment (%)",
        description_ru="Уверенность в оценке рынка (%)",
    )


@register_sensor(category="smart_summary")
class PortfolioHealthSensor(StatusSensor):
    """Portfolio health assessment."""

    config = SensorConfig(
        sensor_id="portfolio_health",
        name="Portfolio Health",
        name_ru="Здоровье портфеля",
        icon="mdi:shield-check",
        description="Overall portfolio health assessment",
        description_ru="Общая оценка здоровья портфеля",
    )


@register_sensor(category="smart_summary")
class PortfolioHealthScoreSensor(PercentSensor):
    """Portfolio health score."""

    config = SensorConfig(
        sensor_id="portfolio_health_score",
        name="Portfolio Health Score",
        name_ru="Скор здоровья",
        icon="mdi:counter",
        unit="%",
        description="Portfolio health assessment (0-100%)",
        description_ru="Оценка здоровья портфеля (0-100%)",
    )


@register_sensor(category="smart_summary")
class TodayActionSensor(StatusSensor):
    """Recommended action for today."""

    config = SensorConfig(
        sensor_id="today_action",
        name="Today's Action",
        name_ru="Действие сегодня",
        icon="mdi:clipboard-check",
        description="Recommended action for today",
        description_ru="Рекомендуемое действие на сегодня",
    )


@register_sensor(category="smart_summary")
class TodayActionPrioritySensor(StatusSensor):
    """Action priority/urgency."""

    config = SensorConfig(
        sensor_id="today_action_priority",
        name="Action Priority",
        name_ru="Приоритет действия",
        icon="mdi:alert-circle",
        description="Urgency: low/medium/high",
        description_ru="Срочность: низкая/средняя/высокая",
    )


@register_sensor(category="smart_summary")
class WeeklyOutlookSensor(StatusSensor):
    """Weekly market outlook."""

    config = SensorConfig(
        sensor_id="weekly_outlook",
        name="Weekly Outlook",
        name_ru="Прогноз на неделю",
        icon="mdi:calendar-week",
        description="Brief forecast for the week",
        description_ru="Краткий прогноз на неделю",
    )


@register_sensor(category="smart_summary")
class MorningBriefingSensor(StatusSensor):
    """Morning briefing."""

    config = SensorConfig(
        sensor_id="morning_briefing",
        name="Morning Briefing",
        name_ru="Утренний брифинг",
        icon="mdi:weather-sunny",
        description="Morning market summary",
        description_ru="Утренняя сводка по рынку",
    )


@register_sensor(category="smart_summary")
class EveningBriefingSensor(StatusSensor):
    """Evening briefing."""

    config = SensorConfig(
        sensor_id="evening_briefing",
        name="Evening Briefing",
        name_ru="Вечерний брифинг",
        icon="mdi:weather-night",
        description="Evening market summary",
        description_ru="Вечерняя сводка по рынку",
    )


@register_sensor(category="smart_summary")
class BriefingLastSentSensor(ScalarSensor):
    """Time of last briefing sent."""

    config = SensorConfig(
        sensor_id="briefing_last_sent",
        name="Last Briefing Sent",
        name_ru="Последний брифинг",
        icon="mdi:clock-check",
        device_class="timestamp",
        description="Time of last briefing",
        description_ru="Время последнего брифинга",
    )
