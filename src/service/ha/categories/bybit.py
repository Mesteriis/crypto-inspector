"""Bybit exchange sensors."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.composite import CompositeSensor
from service.ha.sensors.scalar import PercentSensor, ScalarSensor


@register_sensor(category="bybit")
class BybitBalanceSensor(ScalarSensor):
    """Bybit account balance."""

    config = SensorConfig(
        sensor_id="bybit_balance",
        name="Bybit Balance",
        name_ru="Баланс Bybit",
        icon="mdi:wallet",
        unit="USDT",
        description="Bybit trading account balance",
        description_ru="Баланс торгового счёта Bybit",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="bybit")
class BybitPnl24hSensor(PercentSensor):
    """Bybit 24h P&L."""

    config = SensorConfig(
        sensor_id="bybit_pnl_24h",
        name="Bybit P&L 24h",
        name_ru="Bybit P&L 24ч",
        icon="mdi:chart-line",
        unit="%",
        description="Profit/loss over 24 hours",
        description_ru="Прибыль/убыток за 24 часа",
    )


@register_sensor(category="bybit")
class BybitPnl7dSensor(PercentSensor):
    """Bybit 7d P&L."""

    config = SensorConfig(
        sensor_id="bybit_pnl_7d",
        name="Bybit P&L 7d",
        name_ru="Bybit P&L 7д",
        icon="mdi:chart-areaspline",
        unit="%",
        description="Profit/loss over 7 days",
        description_ru="Прибыль/убыток за 7 дней",
    )


@register_sensor(category="bybit")
class BybitPositionsSensor(CompositeSensor):
    """Bybit open positions."""

    config = SensorConfig(
        sensor_id="bybit_positions",
        name="Bybit Positions",
        name_ru="Позиции Bybit",
        icon="mdi:format-list-bulleted",
        description="Open positions on Bybit",
        description_ru="Открытые позиции на Bybit",
    )


@register_sensor(category="bybit")
class BybitUnrealizedPnlSensor(ScalarSensor):
    """Bybit unrealized P&L."""

    config = SensorConfig(
        sensor_id="bybit_unrealized_pnl",
        name="Unrealized P&L",
        name_ru="Нереализованный P&L",
        icon="mdi:cash-clock",
        unit="USDT",
        description="Unrealized profit/loss",
        description_ru="Нереализованная прибыль/убыток",
    )


@register_sensor(category="bybit")
class BybitEarnBalanceSensor(ScalarSensor):
    """Bybit Earn balance."""

    config = SensorConfig(
        sensor_id="bybit_earn_balance",
        name="Bybit Earn Balance",
        name_ru="Баланс Bybit Earn",
        icon="mdi:piggy-bank",
        unit="USDT",
        description="Balance in Bybit Earn",
        description_ru="Баланс в Bybit Earn",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="bybit")
class BybitEarnPositionsSensor(CompositeSensor):
    """Bybit Earn positions."""

    config = SensorConfig(
        sensor_id="bybit_earn_positions",
        name="Earn Positions",
        name_ru="Позиции Earn",
        icon="mdi:format-list-bulleted",
        description="Active Earn positions",
        description_ru="Активные Earn позиции",
    )


@register_sensor(category="bybit")
class BybitEarnApySensor(PercentSensor):
    """Bybit Earn APY."""

    config = SensorConfig(
        sensor_id="bybit_earn_apy",
        name="Earn APY",
        name_ru="APY Earn",
        icon="mdi:percent",
        unit="%",
        description="Average Earn yield",
        description_ru="Средняя доходность Earn",
    )


@register_sensor(category="bybit")
class BybitTotalPortfolioSensor(ScalarSensor):
    """Bybit total portfolio value."""

    config = SensorConfig(
        sensor_id="bybit_total_portfolio",
        name="Bybit Portfolio",
        name_ru="Портфель Bybit",
        icon="mdi:bank",
        unit="USDT",
        description="Total value on Bybit",
        description_ru="Общая стоимость на Bybit",
        value_type="float",
        min_value=0,
    )


@register_sensor(category="bybit")
class BybitEarnPnlSensor(ScalarSensor):
    """Bybit Earn total PnL."""

    config = SensorConfig(
        sensor_id="bybit_earn_pnl",
        name="Earn Total PnL",
        name_ru="Общий PnL Earn",
        icon="mdi:cash-plus",
        unit="USDT",
        description="Total accumulated PnL from Earn positions",
        description_ru="Общий накопленный доход от Earn позиций",
        value_type="float",
    )


@register_sensor(category="bybit")
class BybitEarnClaimableSensor(ScalarSensor):
    """Bybit Earn claimable yield."""

    config = SensorConfig(
        sensor_id="bybit_earn_claimable",
        name="Earn Claimable",
        name_ru="Доступно к выводу",
        icon="mdi:cash-check",
        unit="",
        description="Claimable yield from Earn positions",
        description_ru="Доступный для вывода доход от Earn",
        value_type="float",
    )
