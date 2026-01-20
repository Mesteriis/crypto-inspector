"""Technical analysis sensors - RSI, MACD, Bollinger Bands, trends."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import IndicatorDictSensor
from service.ha.sensors.scalar import PercentSensor, StatusSensor


@register_sensor(category="technical")
class TaRsiSensor(IndicatorDictSensor):
    """RSI(14) for all coins."""

    config = SensorConfig(
        sensor_id="ta_rsi",
        name="RSI Indicator",
        name_ru="RSI индикатор",
        icon="mdi:chart-line",
        description='RSI(14) for all coins. Format: {"BTC": 65}',
        description_ru='RSI(14) для всех монет. Формат: {"BTC": 65}',
    )

    min_value = 0
    max_value = 100


@register_sensor(category="technical")
class TaMacdSignalSensor(IndicatorDictSensor):
    """MACD signals for all coins."""

    config = SensorConfig(
        sensor_id="ta_macd_signal",
        name="MACD Signals",
        name_ru="MACD сигналы",
        icon="mdi:signal",
        description='MACD signals. Format: {"BTC": "bullish"}',
        description_ru='MACD сигналы. Формат: {"BTC": "bullish"}',
    )


@register_sensor(category="technical")
class TaBbPositionSensor(IndicatorDictSensor):
    """Bollinger Bands position for all coins."""

    config = SensorConfig(
        sensor_id="ta_bb_position",
        name="BB Position",
        name_ru="Позиция BB",
        icon="mdi:chart-bell-curve",
        description='Position in Bollinger Bands. Format: {"BTC": 0.7}',
        description_ru='Позиция в Bollinger Bands. Формат: {"BTC": 0.7}',
    )


@register_sensor(category="technical")
class TaTrendSensor(IndicatorDictSensor):
    """Trend direction for all coins."""

    config = SensorConfig(
        sensor_id="ta_trend",
        name="Trends",
        name_ru="Тренды",
        icon="mdi:trending-up",
        description='Trend direction. Format: {"BTC": "uptrend"}',
        description_ru='Направление тренда. Формат: {"BTC": "uptrend"}',
    )


@register_sensor(category="technical")
class TaSupportSensor(IndicatorDictSensor):
    """Support levels for all coins."""

    config = SensorConfig(
        sensor_id="ta_support",
        name="Support Levels",
        name_ru="Уровни поддержки",
        icon="mdi:arrow-down-bold",
        description='Nearest support levels. Format: {"BTC": 90000}',
        description_ru='Ближайшие уровни поддержки. Формат: {"BTC": 90000}',
    )


@register_sensor(category="technical")
class TaResistanceSensor(IndicatorDictSensor):
    """Resistance levels for all coins."""

    config = SensorConfig(
        sensor_id="ta_resistance",
        name="Resistance Levels",
        name_ru="Уровни сопротивления",
        icon="mdi:arrow-up-bold",
        description='Nearest resistance levels. Format: {"BTC": 100000}',
        description_ru='Ближайшие уровни сопротивления. Формат: {"BTC": 100000}',
    )


@register_sensor(category="technical")
class TaTrendMtfSensor(StatusSensor):
    """Multi-timeframe trends."""

    config = SensorConfig(
        sensor_id="ta_trend_mtf",
        name="MTF Trends",
        name_ru="MTF тренды",
        icon="mdi:clock-outline",
        description="Trends across different timeframes",
        description_ru="Тренды на разных таймфреймах",
    )


@register_sensor(category="technical")
class TaConfluenceSensor(PercentSensor):
    """Technical analysis confluence score."""

    config = SensorConfig(
        sensor_id="ta_confluence",
        name="TA Confluence",
        name_ru="Конфлюенс TA",
        icon="mdi:check-all",
        description="Indicator convergence score (0-100)",
        description_ru="Скор схождения индикаторов (0-100)",
    )


@register_sensor(category="technical")
class TaSignalSensor(StatusSensor):
    """Overall TA signal."""

    config = SensorConfig(
        sensor_id="ta_signal",
        name="TA Signal",
        name_ru="TA сигнал",
        icon="mdi:traffic-light",
        description="Overall TA signal: buy/sell/hold",
        description_ru="Общий сигнал TA: buy/sell/hold",
    )
