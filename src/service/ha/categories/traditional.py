"""Traditional finance sensors - gold, stocks, forex, commodities."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.dict import DictSensor
from service.ha.sensors.scalar import ScalarSensor


@register_sensor(category="traditional")
class TraditionalHistoryStatusSensor(DictSensor):
    """History data status for traditional assets.

    Returns dict with start/stop timestamps for each symbol:
    {"GOLD": {"start": 1704067200000, "stop": 1737849600000}, ...}
    """

    config = SensorConfig(
        sensor_id="traditional_history_status",
        name="Traditional History Status",
        name_ru="Статус истории традиционных активов",
        icon="mdi:database-clock",
        description="History data range for each traditional asset",
        description_ru="Диапазон исторических данных по каждому активу",
    )


@register_sensor(category="traditional")
class GoldPriceSensor(ScalarSensor):
    """Gold price XAU/USD."""

    config = SensorConfig(
        sensor_id="gold_price",
        name="Gold Price",
        name_ru="Золото",
        icon="mdi:gold",
        unit="USD",
        description="Gold price XAU/USD",
        description_ru="Цена золота XAU/USD",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class SilverPriceSensor(ScalarSensor):
    """Silver price XAG/USD."""

    config = SensorConfig(
        sensor_id="silver_price",
        name="Silver Price",
        name_ru="Серебро",
        icon="mdi:circle-outline",
        unit="USD",
        description="Silver price XAG/USD",
        description_ru="Цена серебра XAG/USD",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class PlatinumPriceSensor(ScalarSensor):
    """Platinum price."""

    config = SensorConfig(
        sensor_id="platinum_price",
        name="Platinum Price",
        name_ru="Платина",
        icon="mdi:diamond-stone",
        unit="USD",
        description="Platinum price",
        description_ru="Цена платины",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class Sp500PriceSensor(ScalarSensor):
    """S&P 500 index."""

    config = SensorConfig(
        sensor_id="sp500_price",
        name="S&P 500 Index",
        name_ru="Индекс S&P 500",
        icon="mdi:chart-line",
        unit="USD",
        description="American stock index S&P 500",
        description_ru="Американский фондовый индекс S&P 500",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class NasdaqPriceSensor(ScalarSensor):
    """NASDAQ index."""

    config = SensorConfig(
        sensor_id="nasdaq_price",
        name="NASDAQ Index",
        name_ru="Индекс NASDAQ",
        icon="mdi:chart-areaspline",
        unit="USD",
        description="Technology companies index NASDAQ",
        description_ru="Индекс технологических компаний NASDAQ",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class DjiPriceSensor(ScalarSensor):
    """Dow Jones Industrial index."""

    config = SensorConfig(
        sensor_id="dji_price",
        name="Dow Jones Index",
        name_ru="Индекс Dow Jones",
        icon="mdi:chart-bar",
        unit="USD",
        description="Industrial index Dow Jones",
        description_ru="Промышленный индекс Dow Jones",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class DaxPriceSensor(ScalarSensor):
    """DAX index."""

    config = SensorConfig(
        sensor_id="dax_price",
        name="DAX Index",
        name_ru="Индекс DAX",
        icon="mdi:chart-timeline-variant",
        unit="EUR",
        description="German stock index DAX",
        description_ru="Немецкий фондовый индекс DAX",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class EurUsdSensor(ScalarSensor):
    """EUR/USD exchange rate."""

    config = SensorConfig(
        sensor_id="eur_usd",
        name="EUR/USD Rate",
        name_ru="Курс EUR/USD",
        icon="mdi:currency-eur",
        description="Euro to dollar exchange rate",
        description_ru="Курс евро к доллару",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class GbpUsdSensor(ScalarSensor):
    """GBP/USD exchange rate."""

    config = SensorConfig(
        sensor_id="gbp_usd",
        name="GBP/USD Rate",
        name_ru="Курс GBP/USD",
        icon="mdi:currency-gbp",
        description="Pound to dollar exchange rate",
        description_ru="Курс фунта к доллару",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class DxyIndexSensor(ScalarSensor):
    """Dollar index DXY."""

    config = SensorConfig(
        sensor_id="dxy_index",
        name="Dollar Index",
        name_ru="Индекс доллара",
        icon="mdi:currency-usd",
        description="DXY Index - dollar strength",
        description_ru="Индекс DXY - сила доллара",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class OilBrentSensor(ScalarSensor):
    """Brent oil price."""

    config = SensorConfig(
        sensor_id="oil_brent",
        name="Brent Oil",
        name_ru="Нефть Brent",
        icon="mdi:barrel",
        unit="USD",
        description="Brent oil price",
        description_ru="Цена нефти Brent",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class OilWtiSensor(ScalarSensor):
    """WTI oil price."""

    config = SensorConfig(
        sensor_id="oil_wti",
        name="WTI Oil",
        name_ru="Нефть WTI",
        icon="mdi:barrel",
        unit="USD",
        description="WTI oil price",
        description_ru="Цена нефти WTI",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class NaturalGasSensor(ScalarSensor):
    """Natural gas price."""

    config = SensorConfig(
        sensor_id="natural_gas",
        name="Natural Gas",
        name_ru="Природный газ",
        icon="mdi:fire",
        unit="USD",
        description="Natural gas price",
        description_ru="Цена природного газа",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class VixIndexSensor(ScalarSensor):
    """VIX volatility index."""

    config = SensorConfig(
        sensor_id="vix_index",
        name="VIX Index",
        name_ru="Индекс VIX",
        icon="mdi:chart-bell-curve-cumulative",
        description="CBOE Volatility Index",
        description_ru="Индекс волатильности CBOE",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="traditional")
class TreasuryYield2ySensor(ScalarSensor):
    """2-year US Treasury yield."""

    config = SensorConfig(
        sensor_id="treasury_yield_2y",
        name="Treasury Yield 2Y",
        name_ru="Доходность 2г",
        icon="mdi:percent",
        unit="%",
        description="2-year US Treasury yield",
        description_ru="Доходность 2-летних облигаций США",
        value_type="float",
    )


@register_sensor(category="traditional")
class TreasuryYield10ySensor(ScalarSensor):
    """10-year US Treasury yield."""

    config = SensorConfig(
        sensor_id="treasury_yield_10y",
        name="Treasury Yield 10Y",
        name_ru="Доходность 10л",
        icon="mdi:percent",
        unit="%",
        description="10-year US Treasury yield",
        description_ru="Доходность 10-летних облигаций США",
        value_type="float",
    )

