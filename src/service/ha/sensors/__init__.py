"""Sensor type classes."""

from service.ha.sensors.composite import CompositeSensor
from service.ha.sensors.dict import DictSensor
from service.ha.sensors.scalar import (
    CountSensor,
    PercentSensor,
    PnlPercentSensor,
    ScalarSensor,
    StatusSensor,
)

__all__ = [
    "ScalarSensor",
    "PercentSensor",
    "PnlPercentSensor",
    "StatusSensor",
    "CountSensor",
    "DictSensor",
    "CompositeSensor",
]
