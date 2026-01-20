"""Home Assistant integration module.

This module provides a modular, type-safe sensor management system
for Home Assistant integration via Supervisor REST API.

Usage:
    from service.ha import get_ha_manager

    manager = get_ha_manager()
    await manager.register_sensors()
    await manager.publish_sensor("prices", {"BTC": 95000})
"""

from service.ha.core.base import BaseSensor, SensorConfig
from service.ha.core.manager import (
    HAIntegrationManager,
    get_currency_list,
    get_ha_manager,
    get_sensors_manager,
)
from service.ha.core.publisher import SupervisorPublisher
from service.ha.core.registry import SensorRegistry, register_sensor

__all__ = [
    # Main API
    "HAIntegrationManager",
    "get_ha_manager",
    "get_sensors_manager",  # Backward compatibility
    "get_currency_list",  # Backward compatibility
    # Core classes
    "BaseSensor",
    "SensorConfig",
    "SensorRegistry",
    "register_sensor",
    "SupervisorPublisher",
]
