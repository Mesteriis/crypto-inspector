"""Lazy investor sensors - market phase, calm indicator, DCA signals, etc."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import BoolSensor, CountSensor, PercentSensor, ScalarSensor, StatusSensor


@register_sensor(category="investor")
class DoNothingOkSensor(BoolSensor):
    """Whether it's OK to do nothing (hold)."""

    config = SensorConfig(
        sensor_id="do_nothing_ok",
        name="Do Nothing OK",
        name_ru="Можно ничего не делать",
        icon="mdi:meditation",
        description="Yes/No - whether you can just hold now",
        description_ru="Да/Нет - можно ли сейчас просто держать",
    )

    true_text = "Yes"
    false_text = "No"


@register_sensor(category="investor")
class InvestorPhaseSensor(StatusSensor):
    """Current market phase for investor."""

    config = SensorConfig(
        sensor_id="investor_phase",
        name="Investor Phase",
        name_ru="Фаза рынка",
        icon="mdi:chart-timeline-variant-shimmer",
        description="Phase: Accumulation/Growth/Euphoria/Correction/Capitulation",
        description_ru="Фаза: Накопление/Рост/Эйфория/Коррекция/Капитуляция",
    )


@register_sensor(category="investor")
class CalmIndicatorSensor(PercentSensor):
    """Market calm indicator (0-100)."""

    config = SensorConfig(
        sensor_id="calm_indicator",
        name="Calm Indicator",
        name_ru="Индикатор спокойствия",
        icon="mdi:emoticon-cool",
        description="How calm the market is (0-100)",
        description_ru="Насколько спокоен рынок (0-100)",
        value_type="int",
        min_value=0,
        max_value=100,
    )


@register_sensor(category="investor")
class RedFlagsSensor(CountSensor):
    """Number of warning red flags."""

    config = SensorConfig(
        sensor_id="red_flags",
        name="Red Flags",
        name_ru="Красные флаги",
        icon="mdi:flag-variant",
        description="Number of warning signals",
        description_ru="Количество предупреждающих сигналов",
    )


@register_sensor(category="investor")
class MarketTensionSensor(StatusSensor):
    """Market tension level."""

    config = SensorConfig(
        sensor_id="market_tension",
        name="Market Tension",
        name_ru="Напряжённость рынка",
        icon="mdi:gauge",
        description="Level of market tension",
        description_ru="Уровень напряжённости рынка",
    )


@register_sensor(category="investor")
class PriceContextSensor(StatusSensor):
    """Price context relative to ATH/ATL."""

    config = SensorConfig(
        sensor_id="price_context",
        name="Price Context",
        name_ru="Контекст цены",
        icon="mdi:chart-box",
        description="Current price position relative to ATH/ATL",
        description_ru="Позиция текущей цены относительно ATH/ATL",
    )


@register_sensor(category="investor")
class DcaResultSensor(ScalarSensor):
    """Recommended DCA amount."""

    config = SensorConfig(
        sensor_id="dca_result",
        name="DCA Result",
        name_ru="Результат DCA",
        icon="mdi:cash-check",
        unit="€",
        description="Recommended amount for DCA",
        description_ru="Рекомендуемая сумма для DCA",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="investor")
class DcaSignalSensor(StatusSensor):
    """DCA buy signal."""

    config = SensorConfig(
        sensor_id="dca_signal",
        name="DCA Signal",
        name_ru="Сигнал DCA",
        icon="mdi:cash-plus",
        description="Buy signal: Buy/Wait/Do not buy",
        description_ru="Сигнал для покупки: Покупать/Ждать/Не покупать",
    )


@register_sensor(category="investor")
class WeeklyInsightSensor(StatusSensor):
    """Weekly market insight."""

    config = SensorConfig(
        sensor_id="weekly_insight",
        name="Weekly Insight",
        name_ru="Недельный обзор",
        icon="mdi:newspaper-variant",
        description="Brief market overview for the week",
        description_ru="Краткий обзор рынка за неделю",
    )


@register_sensor(category="investor")
class NextActionTimerSensor(StatusSensor):
    """Timer until next recommended action."""

    config = SensorConfig(
        sensor_id="next_action_timer",
        name="Next Action Timer",
        name_ru="Таймер действия",
        icon="mdi:timer-outline",
        description="Time until next check",
        description_ru="Время до следующей проверки",
    )
