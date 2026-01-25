"""Economic calendar sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import CountSensor, ScalarSensor, StatusSensor


@register_sensor(category="economic")
class EconomicCalendarStatusSensor(StatusSensor):
    """Economic calendar system status."""

    config = SensorConfig(
        sensor_id="economic_calendar_status",
        name="Economic Calendar",
        name_ru="Экономический календарь",
        icon="mdi:calendar-clock",
        entity_category="diagnostic",
        description="Status of economic calendar system",
        description_ru="Статус системы экономического календаря",
    )


@register_sensor(category="economic")
class EconomicUpcomingEvents24hSensor(CountSensor):
    """Events in next 24 hours."""

    config = SensorConfig(
        sensor_id="economic_upcoming_events_24h",
        name="Events 24h",
        name_ru="События 24ч",
        icon="mdi:calendar-today",
        entity_category="diagnostic",
        description="Number of economic events in next 24 hours",
        description_ru="Количество экономических событий за 24 часа",
    )


@register_sensor(category="economic")
class EconomicImportantEventsSensor(CountSensor):
    """Important economic events."""

    config = SensorConfig(
        sensor_id="economic_important_events",
        name="Important Events",
        name_ru="Важные события",
        icon="mdi:star",
        entity_category="diagnostic",
        description="Number of important upcoming events",
        description_ru="Количество важных предстоящих событий",
    )


@register_sensor(category="economic")
class EconomicBreakingNewsSensor(StatusSensor):
    """Breaking economic news."""

    config = SensorConfig(
        sensor_id="economic_breaking_news",
        name="Breaking News",
        name_ru="Срочные новости",
        icon="mdi:newspaper-variant-outline",
        entity_category="diagnostic",
        description="Latest breaking economic news",
        description_ru="Последние срочные экономические новости",
    )


@register_sensor(category="economic")
class EconomicSentimentScoreSensor(ScalarSensor):
    """Economic sentiment score."""

    config = SensorConfig(
        sensor_id="economic_sentiment_score",
        name="Economic Sentiment",
        name_ru="Экономические настроения",
        icon="mdi:emoticon-outline",
        entity_category="diagnostic",
        description="Overall economic sentiment score (-100 to 100)",
        description_ru="Общий скор экономических настроений (-100 до 100)",
        value_type="int",
        min_value=-100,
        max_value=100,
    )

    def format_state(self, value: int) -> str:
        """Format with emoji based on sentiment."""
        if value <= -50:
            return f"🔴 {value} (Очень негативный)"
        elif value <= -20:
            return f"🟠 {value} (Негативный)"
        elif value <= 20:
            return f"⚪ {value} (Нейтральный)"
        elif value <= 50:
            return f"🔵 {value} (Позитивный)"
        else:
            return f"🟢 {value} (Очень позитивный)"


@register_sensor(category="economic")
class NextMacroEventSensor(StatusSensor):
    """Next macroeconomic event."""

    config = SensorConfig(
        sensor_id="next_macro_event",
        name="Next Macro Event",
        name_ru="Следующее макрособытие",
        icon="mdi:calendar-star",
        description="Next important macroeconomic event",
        description_ru="Ближайшее важное макрособытие",
    )


@register_sensor(category="economic")
class DaysToFomcSensor(CountSensor):
    """Days until Fed meeting."""

    config = SensorConfig(
        sensor_id="days_to_fomc",
        name="Days to FOMC",
        name_ru="Дней до FOMC",
        icon="mdi:calendar-clock",
        description="Days until Fed meeting",
        description_ru="Дней до заседания ФРС",
    )


@register_sensor(category="economic")
class MacroRiskWeekSensor(StatusSensor):
    """Weekly macro risk level."""

    config = SensorConfig(
        sensor_id="macro_risk_week",
        name="Macro Risk Week",
        name_ru="Макрориск недели",
        icon="mdi:calendar-alert",
        description="Weekly risk: low/medium/high",
        description_ru="Риск на неделе: низкий/средний/высокий",
    )
