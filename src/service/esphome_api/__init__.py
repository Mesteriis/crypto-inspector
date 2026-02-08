"""ESPHome Native API Server for Home Assistant integration.

This module implements ESPHome-compatible Native API server,
allowing Home Assistant to discover and integrate Crypto Inspect
as an ESPHome device without custom components.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .discovery import (
    ESPHomeDiscovery,
    get_esphome_discovery,
    start_esphome_discovery,
    stop_esphome_discovery,
)
from .messages import DeviceInfo, SensorInfo, TextSensorInfo
from .server import (
    ESPHomeAPIServer,
    get_esphome_server,
    start_esphome_server,
    stop_esphome_server,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

__all__ = [
    # Server
    "ESPHomeAPIServer",
    "get_esphome_server",
    "start_esphome_server",
    "stop_esphome_server",
    # Discovery
    "ESPHomeDiscovery",
    "get_esphome_discovery",
    "start_esphome_discovery",
    "stop_esphome_discovery",
    # Messages
    "DeviceInfo",
    "SensorInfo",
    "TextSensorInfo",
    # Integration
    "setup_esphome_api",
    "start_esphome_api",
    "stop_esphome_api",
]


async def setup_esphome_api(
    state_getter: Callable[[str], Any],
    sensor_registry: dict[str, dict],
) -> None:
    """Setup ESPHome API with sensors from registry.

    Args:
        state_getter: Function to get current sensor value by object_id.
        sensor_registry: Dictionary of sensor metadata from SensorRegistry.
    """
    server = get_esphome_server()
    server.set_state_getter(state_getter)

    # Classify and register sensors
    numeric_count = 0
    text_count = 0

    for object_id, metadata in sensor_registry.items():
        # Determine if sensor is numeric or text based on value_type
        value_type = metadata.get("value_type", "any")
        unit = metadata.get("unit")

        # Numeric sensors: have unit or numeric value_type
        is_numeric = (
            unit is not None
            or value_type in ("float", "int", "percentage", "currency")
            or metadata.get("device_class")
            in (
                "temperature",
                "humidity",
                "pressure",
                "power",
                "energy",
                "monetary",
                "battery",
                "voltage",
                "current",
            )
        )

        if is_numeric:
            sensor = SensorInfo.from_dict(metadata, object_id)
            server.register_sensor(sensor)
            numeric_count += 1
        else:
            sensor = TextSensorInfo.from_dict(metadata, object_id)
            server.register_text_sensor(sensor)
            text_count += 1

    logger.info(
        "ESPHome API: Registered %d numeric, %d text sensors",
        numeric_count,
        text_count,
    )


async def start_esphome_api() -> bool:
    """Start ESPHome API server and discovery."""
    # Start server
    server_ok = await start_esphome_server()
    if not server_ok:
        return False

    # Start mDNS discovery
    await start_esphome_discovery()

    logger.info("ESPHome API: Started successfully")
    return True


async def stop_esphome_api() -> None:
    """Stop ESPHome API server and discovery."""
    await stop_esphome_discovery()
    await stop_esphome_server()
    logger.info("ESPHome API: Stopped")
