"""Backtest sensors - strategy comparison results."""

from service.ha.core.base import SensorConfig
from service.ha.core.registry import register_sensor
from service.ha.sensors.scalar import PnlPercentSensor, StatusSensor


@register_sensor(category="backtest")
class BacktestDcaRoiSensor(PnlPercentSensor):
    """DCA strategy backtest ROI."""

    config = SensorConfig(
        sensor_id="backtest_dca_roi",
        name="Backtest DCA ROI",
        name_ru="DCA бэктест ROI",
        icon="mdi:percent",
        unit="%",
        description="ROI of DCA strategy in backtest",
        description_ru="Доходность DCA стратегии в бэктесте",
    )


@register_sensor(category="backtest")
class BacktestSmartDcaRoiSensor(PnlPercentSensor):
    """Smart DCA strategy backtest ROI."""

    config = SensorConfig(
        sensor_id="backtest_smart_dca_roi",
        name="Backtest Smart DCA ROI",
        name_ru="Smart DCA ROI",
        icon="mdi:brain",
        unit="%",
        description="ROI of smart DCA",
        description_ru="Доходность умного DCA",
    )


@register_sensor(category="backtest")
class BacktestLumpSumRoiSensor(PnlPercentSensor):
    """Lump sum strategy backtest ROI."""

    config = SensorConfig(
        sensor_id="backtest_lump_sum_roi",
        name="Backtest Lump Sum ROI",
        name_ru="Lump Sum ROI",
        icon="mdi:cash",
        unit="%",
        description="ROI of lump sum purchase",
        description_ru="Доходность единоразовой покупки",
    )


@register_sensor(category="backtest")
class BacktestBestStrategySensor(StatusSensor):
    """Best strategy according to backtest."""

    config = SensorConfig(
        sensor_id="backtest_best_strategy",
        name="Best Backtest Strategy",
        name_ru="Лучшая стратегия",
        icon="mdi:trophy",
        description="Best strategy according to backtest",
        description_ru="Лучшая стратегия по бэктесту",
    )
