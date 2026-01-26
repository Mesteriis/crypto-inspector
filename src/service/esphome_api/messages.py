"""ESPHome API message builders.

Builds protobuf-compatible messages for ESPHome Native API.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from .protocol import (
    MSG_DEVICE_INFO_RESPONSE,
    MSG_HELLO_RESPONSE,
    MSG_LIST_ENTITIES_DONE_RESPONSE,
    MSG_LIST_ENTITIES_SENSOR_RESPONSE,
    MSG_LIST_ENTITIES_TEXT_SENSOR_RESPONSE,
    MSG_PING_RESPONSE,
    MSG_SENSOR_STATE_RESPONSE,
    MSG_TEXT_SENSOR_STATE_RESPONSE,
    encode_bool,
    encode_fixed32,
    encode_float,
    encode_frame,
    encode_string,
    encode_uint32,
)


class SensorStateClass(IntEnum):
    """Sensor state class enum."""

    NONE = 0
    MEASUREMENT = 1
    TOTAL = 2
    TOTAL_INCREASING = 3


class EntityCategory(IntEnum):
    """Entity category enum."""

    NONE = 0
    CONFIG = 1
    DIAGNOSTIC = 2


@dataclass
class SensorInfo:
    """Sensor information for ListEntities."""

    object_id: str
    key: int  # Unique key (hash of object_id)
    name: str
    icon: str = ""
    unit_of_measurement: str = ""
    accuracy_decimals: int = 0
    device_class: str = ""
    state_class: SensorStateClass = SensorStateClass.NONE
    entity_category: EntityCategory = EntityCategory.NONE
    disabled_by_default: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any], object_id: str) -> SensorInfo:
        """Create SensorInfo from sensor registry dict."""
        # Generate stable key from object_id
        key = int(hashlib.md5(object_id.encode()).hexdigest()[:8], 16)
        return cls(
            object_id=object_id,
            key=key,
            name=data.get("name_ru", data.get("name", object_id)),
            icon=data.get("icon", ""),
            unit_of_measurement=data.get("unit", "") or "",
            accuracy_decimals=data.get("accuracy_decimals", 0),
            device_class=data.get("device_class", "") or "",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.NONE,
            disabled_by_default=False,
        )


@dataclass
class TextSensorInfo:
    """Text sensor information for ListEntities."""

    object_id: str
    key: int
    name: str
    icon: str = ""
    device_class: str = ""
    entity_category: EntityCategory = EntityCategory.NONE
    disabled_by_default: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any], object_id: str) -> TextSensorInfo:
        """Create TextSensorInfo from sensor registry dict."""
        key = int(hashlib.md5(object_id.encode()).hexdigest()[:8], 16)
        return cls(
            object_id=object_id,
            key=key,
            name=data.get("name_ru", data.get("name", object_id)),
            icon=data.get("icon", ""),
            device_class=data.get("device_class", "") or "",
            entity_category=EntityCategory.NONE,
            disabled_by_default=False,
        )


@dataclass
class DeviceInfo:
    """Device information."""

    name: str = "Crypto Inspect"
    friendly_name: str = "Crypto Inspect"
    mac_address: str = "AA:BB:CC:DD:EE:FF"
    esphome_version: str = "2024.1.0"
    compilation_time: str = ""
    model: str = "Virtual"
    manufacturer: str = "Crypto Inspect"
    project_name: str = "crypto_inspect"
    project_version: str = "1.0.0"


def build_hello_response(
    api_version_major: int = 1,
    api_version_minor: int = 9,
    server_info: str = "Crypto Inspect",
    name: str = "crypto_inspect",
) -> bytes:
    """Build HelloResponse message."""
    payload = b""
    payload += encode_uint32(1, api_version_major)
    payload += encode_uint32(2, api_version_minor)
    payload += encode_string(3, server_info)
    payload += encode_string(4, name)
    return encode_frame(MSG_HELLO_RESPONSE, payload)


def build_device_info_response(info: DeviceInfo | None = None) -> bytes:
    """Build DeviceInfoResponse message."""
    if info is None:
        info = DeviceInfo()

    payload = b""
    payload += encode_bool(1, False)  # uses_password
    payload += encode_string(2, info.name)
    payload += encode_string(3, info.mac_address)
    payload += encode_string(4, info.esphome_version)
    payload += encode_string(5, info.compilation_time)
    payload += encode_string(6, info.model)
    payload += encode_bool(7, False)  # has_deep_sleep
    payload += encode_string(8, info.project_name)
    payload += encode_string(9, info.project_version)
    payload += encode_string(12, info.manufacturer)
    payload += encode_string(13, info.friendly_name)
    return encode_frame(MSG_DEVICE_INFO_RESPONSE, payload)


def build_ping_response() -> bytes:
    """Build PingResponse message (empty)."""
    return encode_frame(MSG_PING_RESPONSE, b"")


def build_list_entities_sensor_response(sensor: SensorInfo) -> bytes:
    """Build ListEntitiesSensorResponse message."""
    payload = b""
    payload += encode_string(1, sensor.object_id)
    payload += encode_fixed32(2, sensor.key)
    payload += encode_string(3, sensor.name)
    if sensor.icon:
        payload += encode_string(5, sensor.icon)
    if sensor.unit_of_measurement:
        payload += encode_string(6, sensor.unit_of_measurement)
    payload += encode_uint32(7, sensor.accuracy_decimals)
    payload += encode_bool(8, False)  # force_update
    if sensor.device_class:
        payload += encode_string(9, sensor.device_class)
    payload += encode_uint32(10, sensor.state_class.value)
    payload += encode_bool(12, sensor.disabled_by_default)
    payload += encode_uint32(13, sensor.entity_category.value)
    return encode_frame(MSG_LIST_ENTITIES_SENSOR_RESPONSE, payload)


def build_list_entities_text_sensor_response(sensor: TextSensorInfo) -> bytes:
    """Build ListEntitiesTextSensorResponse message."""
    payload = b""
    payload += encode_string(1, sensor.object_id)
    payload += encode_fixed32(2, sensor.key)
    payload += encode_string(3, sensor.name)
    if sensor.icon:
        payload += encode_string(5, sensor.icon)
    payload += encode_bool(6, sensor.disabled_by_default)
    payload += encode_uint32(7, sensor.entity_category.value)
    if sensor.device_class:
        payload += encode_string(8, sensor.device_class)
    return encode_frame(MSG_LIST_ENTITIES_TEXT_SENSOR_RESPONSE, payload)


def build_list_entities_done_response() -> bytes:
    """Build ListEntitiesDoneResponse message (empty)."""
    return encode_frame(MSG_LIST_ENTITIES_DONE_RESPONSE, b"")


def build_sensor_state_response(key: int, state: float) -> bytes:
    """Build SensorStateResponse message."""
    payload = b""
    payload += encode_fixed32(1, key)
    payload += encode_float(2, state)
    payload += encode_bool(3, False)  # missing_state
    return encode_frame(MSG_SENSOR_STATE_RESPONSE, payload)


def build_text_sensor_state_response(key: int, state: str) -> bytes:
    """Build TextSensorStateResponse message."""
    payload = b""
    payload += encode_fixed32(1, key)
    payload += encode_string(2, state)
    payload += encode_bool(3, False)  # missing_state
    return encode_frame(MSG_TEXT_SENSOR_STATE_RESPONSE, payload)


def build_sensor_state_missing(key: int) -> bytes:
    """Build SensorStateResponse with missing state."""
    payload = b""
    payload += encode_fixed32(1, key)
    payload += encode_float(2, 0.0)
    payload += encode_bool(3, True)  # missing_state
    return encode_frame(MSG_SENSOR_STATE_RESPONSE, payload)


def build_text_sensor_state_missing(key: int) -> bytes:
    """Build TextSensorStateResponse with missing state."""
    payload = b""
    payload += encode_fixed32(1, key)
    payload += encode_string(2, "")
    payload += encode_bool(3, True)  # missing_state
    return encode_frame(MSG_TEXT_SENSOR_STATE_RESPONSE, payload)
