"""Miscellaneous sensors - liquidations, arbitrage, unlocks, divergences, signals, goals."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import DictSensor
from service.ha.sensors.scalar import (
    CountSensor,
    PercentSensor,
    ScalarSensor,
    StatusSensor,
)

# === Liquidations ===


@register_sensor(category="misc")
class LiqLevelsSensor(DictSensor):
    """Liquidation price levels."""

    config = SensorConfig(
        sensor_id="liq_levels",
        name="Liquidation Levels",
        name_ru="Уровни ликвидаций",
        icon="mdi:arrow-expand-vertical",
        description="Price levels of mass liquidations",
        description_ru="Ценовые уровни массовых ликвидаций",
    )


@register_sensor(category="misc")
class LiqRiskLevelSensor(StatusSensor):
    """Liquidation risk level."""

    config = SensorConfig(
        sensor_id="liq_risk_level",
        name="Liquidation Risk",
        name_ru="Риск ликвидаций",
        icon="mdi:alert-decagram",
        description="Risk level: low/medium/high",
        description_ru="Уровень риска: низкий/средний/высокий",
    )


# === Divergences ===


@register_sensor(category="misc")
class DivergencesSensor(DictSensor):
    """Price and indicator divergences."""

    config = SensorConfig(
        sensor_id="divergences",
        name="Divergences",
        name_ru="Дивергенции",
        icon="mdi:call-split",
        description="Price and indicator divergences",
        description_ru="Расхождения цены и индикаторов",
    )


@register_sensor(category="misc")
class DivergencesActiveSensor(CountSensor):
    """Active divergences count."""

    config = SensorConfig(
        sensor_id="divergences_active",
        name="Active Divergences",
        name_ru="Активные дивергенции",
        icon="mdi:call-merge",
        description="Number of active divergences",
        description_ru="Количество активных дивергенций",
    )


# === Signals ===


@register_sensor(category="misc")
class SignalsWinRateSensor(PercentSensor):
    """Signals win rate."""

    config = SensorConfig(
        sensor_id="signals_win_rate",
        name="Signals Win Rate",
        name_ru="Винрейт сигналов",
        icon="mdi:trophy",
        unit="%",
        description="Percentage of successful signals",
        description_ru="Процент успешных сигналов",
    )


@register_sensor(category="misc")
class SignalsTodaySensor(CountSensor):
    """Signals today count."""

    config = SensorConfig(
        sensor_id="signals_today",
        name="Today's Signals",
        name_ru="Сигналы сегодня",
        icon="mdi:signal",
        description="Number of signals today",
        description_ru="Количество сигналов за сегодня",
    )


@register_sensor(category="misc")
class SignalsLastSensor(StatusSensor):
    """Last trading signal."""

    config = SensorConfig(
        sensor_id="signals_last",
        name="Last Signal",
        name_ru="Последний сигнал",
        icon="mdi:traffic-light",
        description="Last trading signal",
        description_ru="Последний торговый сигнал",
    )


# === Arbitrage ===


@register_sensor(category="misc")
class ArbSpreadsSensor(DictSensor):
    """Arbitrage spreads between exchanges."""

    config = SensorConfig(
        sensor_id="arb_spreads",
        name="Arbitrage Spreads",
        name_ru="Спреды арбитража",
        icon="mdi:swap-horizontal-bold",
        description="Price differences between exchanges",
        description_ru="Разница цен между биржами",
    )


@register_sensor(category="misc")
class FundingArbBestSensor(StatusSensor):
    """Best funding arbitrage opportunity."""

    config = SensorConfig(
        sensor_id="funding_arb_best",
        name="Best Funding Arbitrage",
        name_ru="Лучший фандинг-арб",
        icon="mdi:cash-multiple",
        description="Best funding arbitrage opportunity",
        description_ru="Лучшая возможность для фандинг-арбитража",
    )


@register_sensor(category="misc")
class ArbOpportunitySensor(StatusSensor):
    """Arbitrage opportunity status."""

    config = SensorConfig(
        sensor_id="arb_opportunity",
        name="Arbitrage Opportunity",
        name_ru="Возможность арбитража",
        icon="mdi:lightning-bolt",
        description="Is there an arbitrage opportunity",
        description_ru="Есть ли арбитражная возможность",
    )


# === Take Profit ===


@register_sensor(category="misc")
class TpLevelsSensor(DictSensor):
    """Take profit levels."""

    config = SensorConfig(
        sensor_id="tp_levels",
        name="Take Profit Levels",
        name_ru="Уровни фиксации",
        icon="mdi:target-variant",
        description="Recommended Take Profit levels",
        description_ru="Рекомендуемые уровни Take Profit",
    )


@register_sensor(category="misc")
class ProfitActionSensor(StatusSensor):
    """Profit action recommendation."""

    config = SensorConfig(
        sensor_id="profit_action",
        name="Profit Action",
        name_ru="Действие по прибыли",
        icon="mdi:cash-check",
        description="Recommendation: hold/take profit",
        description_ru="Рекомендация: держать/фиксировать",
    )


@register_sensor(category="misc")
class GreedLevelSensor(PercentSensor):
    """Market greed level (overbought)."""

    config = SensorConfig(
        sensor_id="greed_level",
        name="Greed Level",
        name_ru="Уровень жадности",
        icon="mdi:emoticon-devil",
        description="How overbought the market is (0-100)",
        description_ru="Насколько перекуплен рынок (0-100)",
    )


# === Token Unlocks ===


@register_sensor(category="misc")
class UnlocksNext7dSensor(CountSensor):
    """Token unlocks in next 7 days."""

    config = SensorConfig(
        sensor_id="unlocks_next_7d",
        name="Unlocks Next 7d",
        name_ru="Разблокировки 7д",
        icon="mdi:lock-open-variant",
        description="Token unlocks in next 7 days",
        description_ru="Разблокировки токенов за 7 дней",
    )


@register_sensor(category="misc")
class UnlockNextEventSensor(StatusSensor):
    """Next token unlock event."""

    config = SensorConfig(
        sensor_id="unlock_next_event",
        name="Next Unlock Event",
        name_ru="Следующий анлок",
        icon="mdi:calendar-lock",
        description="Next token unlock event",
        description_ru="Ближайшая разблокировка",
    )


@register_sensor(category="misc")
class UnlockRiskLevelSensor(StatusSensor):
    """Unlock risk level."""

    config = SensorConfig(
        sensor_id="unlock_risk_level",
        name="Unlock Risk Level",
        name_ru="Риск анлоков",
        icon="mdi:alert-circle",
        description="Risk level from unlocks",
        description_ru="Уровень риска от разблокировок",
    )


# === Goals ===


@register_sensor(category="misc")
class GoalTargetSensor(ScalarSensor):
    """Goal target amount."""

    config = SensorConfig(
        sensor_id="goal_target",
        name="Goal Target",
        name_ru="Цель",
        icon="mdi:flag-checkered",
        unit="USDT",
        description="Target portfolio amount",
        description_ru="Целевая сумма портфеля",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="misc")
class GoalProgressSensor(PercentSensor):
    """Goal progress percentage."""

    config = SensorConfig(
        sensor_id="goal_progress",
        name="Goal Progress",
        name_ru="Прогресс цели",
        icon="mdi:progress-check",
        unit="%",
        description="Goal achievement percentage",
        description_ru="Процент достижения цели",
    )


@register_sensor(category="misc")
class GoalRemainingSensor(ScalarSensor):
    """Remaining amount to goal."""

    config = SensorConfig(
        sensor_id="goal_remaining",
        name="Goal Remaining",
        name_ru="Осталось до цели",
        icon="mdi:cash-minus",
        unit="USDT",
        description="Amount remaining to reach goal",
        description_ru="Сколько осталось до цели",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="misc")
class GoalDaysEstimateSensor(CountSensor):
    """Estimated days to goal."""

    config = SensorConfig(
        sensor_id="goal_days_estimate",
        name="Days to Goal",
        name_ru="Дней до цели",
        icon="mdi:calendar-clock",
        description="Estimated days to achievement",
        description_ru="Оценка дней до достижения",
    )


@register_sensor(category="misc")
class GoalStatusSensor(StatusSensor):
    """Goal status."""

    config = SensorConfig(
        sensor_id="goal_status",
        name="Goal Status",
        name_ru="Статус цели",
        icon="mdi:trophy",
        description="Status: in progress/reached/postponed",
        description_ru="Статус: в процессе/достигнута/отложена",
    )


@register_sensor(category="misc")
class GoalCurrentSensor(ScalarSensor):
    """Current value towards goal."""

    config = SensorConfig(
        sensor_id="goal_current",
        name="Goal Current",
        name_ru="Текущее значение",
        icon="mdi:cash",
        unit="USDT",
        description="Current value towards goal",
        description_ru="Текущее значение к цели",
        value_type="float",
        min_value=0,
    )


# === System ===


@register_sensor(category="misc")
class ReadySensor(StatusSensor):
    """System ready status."""

    config = SensorConfig(
        sensor_id="ready",
        name="System Ready",
        name_ru="Система готова",
        icon="mdi:check-circle",
        description="System initialization status",
        description_ru="Статус инициализации системы",
    )


@register_sensor(category="misc")
class StopLossRecommendationSensor(StatusSensor):
    """Stop loss recommendation."""

    config = SensorConfig(
        sensor_id="stop_loss_recommendation",
        name="Stop Loss",
        name_ru="Стоп-лосс",
        icon="mdi:shield-off",
        description="Recommended stop loss action",
        description_ru="Рекомендация по стоп-лоссу",
    )


@register_sensor(category="misc")
class UnlocksNextEventSensor(StatusSensor):
    """Next unlock event (alias)."""

    config = SensorConfig(
        sensor_id="unlocks_next_event",
        name="Next Unlock",
        name_ru="Следующий анлок",
        icon="mdi:calendar-lock",
        description="Next token unlock event",
        description_ru="Ближайшая разблокировка токенов",
    )


# === Unified/Consolidated Sensors ===


@register_sensor(category="unified")
class PricePredictionsSensor(DictSensor):
    """Price predictions for all currencies."""

    config = SensorConfig(
        sensor_id="price_predictions",
        name="Price Predictions",
        name_ru="Прогнозы цен",
        icon="mdi:crystal-ball",
        description='Price predictions for all currencies. Format: {"BTC": 95000, "ETH": 3200}',
        description_ru='Прогнозы цен для всех валют. Формат: {"BTC": 95000, "ETH": 3200}',
    )


@register_sensor(category="unified")
class AiTrendDirectionsSensor(DictSensor):
    """AI trend directions for all currencies."""

    config = SensorConfig(
        sensor_id="ai_trend_directions",
        name="AI Trend Directions",
        name_ru="AI направления трендов",
        icon="mdi:trending-up",
        description='AI trend directions. Format: {"BTC": "Bullish", "ETH": "Neutral"}',
        description_ru='AI направления трендов. Формат: {"BTC": "Bullish", "ETH": "Neutral"}',
    )


@register_sensor(category="unified")
class TechnicalIndicatorsSensor(DictSensor):
    """Technical indicators for all currencies."""

    config = SensorConfig(
        sensor_id="technical_indicators",
        name="Technical Indicators",
        name_ru="Технические индикаторы",
        icon="mdi:chart-line",
        description='Technical indicators. Format: {"BTC": {"RSI": 55, "MACD": "buy"}}',
        description_ru='Технические индикаторы. Формат: {"BTC": {"RSI": 55, "MACD": "buy"}}',
    )


@register_sensor(category="unified")
class MarketVolatilitySensor(DictSensor):
    """Market volatility for all currencies."""

    config = SensorConfig(
        sensor_id="market_volatility",
        name="Market Volatility",
        name_ru="Волатильность рынка",
        icon="mdi:chart-bell-curve-cumulative",
        description='Market volatility. Format: {"BTC": 3.5, "ETH": 4.2}',
        description_ru='Волатильность рынка. Формат: {"BTC": 3.5, "ETH": 4.2}',
    )


@register_sensor(category="unified")
class MarketSentimentUnifiedSensor(DictSensor):
    """Market sentiment for all currencies."""

    config = SensorConfig(
        sensor_id="market_sentiment",
        name="Market Sentiment",
        name_ru="Настроение рынка",
        icon="mdi:emoticon-outline",
        description='Market sentiment. Format: {"BTC": 65, "ETH": 58}',
        description_ru='Настроение рынка. Формат: {"BTC": 65, "ETH": 58}',
    )
