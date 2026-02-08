"""ESPHome Native API protocol implementation.

Plaintext protocol format:
[0x00][Payload Size VarInt][Message Type VarInt][Protobuf Data]
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# Message type IDs (from ESPHome api.proto)
MSG_HELLO_REQUEST = 1
MSG_HELLO_RESPONSE = 2
MSG_CONNECT_REQUEST = 3
MSG_CONNECT_RESPONSE = 4
MSG_DISCONNECT_REQUEST = 5
MSG_DISCONNECT_RESPONSE = 6
MSG_PING_REQUEST = 7
MSG_PING_RESPONSE = 8
MSG_DEVICE_INFO_REQUEST = 9
MSG_DEVICE_INFO_RESPONSE = 10
MSG_LIST_ENTITIES_REQUEST = 11
MSG_LIST_ENTITIES_SENSOR_RESPONSE = 16
MSG_LIST_ENTITIES_TEXT_SENSOR_RESPONSE = 18
MSG_LIST_ENTITIES_DONE_RESPONSE = 19
MSG_SUBSCRIBE_STATES_REQUEST = 20
MSG_SENSOR_STATE_RESPONSE = 25
MSG_TEXT_SENSOR_STATE_RESPONSE = 27


def encode_varint(value: int) -> bytes:
    """Encode integer as VarInt (Protocol Buffers style)."""
    result = []
    while value > 127:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode VarInt from bytes. Returns (value, bytes_consumed)."""
    result = 0
    shift = 0
    consumed = 0
    for i, byte in enumerate(data[offset:]):
        consumed += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
        if shift > 35:
            raise ValueError("VarInt too long")
    return result, consumed


def encode_frame(msg_type: int, payload: bytes) -> bytes:
    """Encode message as plaintext ESPHome frame.

    Format: [0x00][size varint][type varint][payload]
    """
    type_bytes = encode_varint(msg_type)
    size = len(type_bytes) + len(payload)
    size_bytes = encode_varint(size)
    return b"\x00" + size_bytes + type_bytes + payload


def decode_frame(data: bytes) -> tuple[int, bytes, int] | None:
    """Decode ESPHome frame.

    Returns: (msg_type, payload, total_bytes_consumed) or None if incomplete.
    """
    if len(data) < 3:
        return None

    if data[0] != 0x00:
        raise ValueError(f"Invalid frame indicator: {data[0]:#x}")

    # Decode size
    try:
        size, size_consumed = decode_varint(data, 1)
    except (IndexError, ValueError):
        return None

    header_len = 1 + size_consumed
    total_len = header_len + size

    if len(data) < total_len:
        return None  # Incomplete frame

    # Decode message type
    payload_start = header_len
    msg_type, type_consumed = decode_varint(data, payload_start)

    # Extract payload
    payload = data[payload_start + type_consumed : total_len]

    return msg_type, payload, total_len


# Simple protobuf field encoding/decoding
def encode_string(field_num: int, value: str) -> bytes:
    """Encode string field (wire type 2)."""
    encoded = value.encode("utf-8")
    tag = (field_num << 3) | 2  # wire type 2 = length-delimited
    return encode_varint(tag) + encode_varint(len(encoded)) + encoded


def encode_uint32(field_num: int, value: int) -> bytes:
    """Encode uint32 field (wire type 0)."""
    tag = (field_num << 3) | 0  # wire type 0 = varint
    return encode_varint(tag) + encode_varint(value)


def encode_float(field_num: int, value: float) -> bytes:
    """Encode float field (wire type 5)."""
    tag = (field_num << 3) | 5  # wire type 5 = 32-bit
    return encode_varint(tag) + struct.pack("<f", value)


def encode_bool(field_num: int, value: bool) -> bytes:
    """Encode bool field (wire type 0)."""
    tag = (field_num << 3) | 0
    return encode_varint(tag) + encode_varint(1 if value else 0)


def encode_fixed32(field_num: int, value: int) -> bytes:
    """Encode fixed32 field (wire type 5)."""
    tag = (field_num << 3) | 5
    return encode_varint(tag) + struct.pack("<I", value)


@dataclass
class ParsedField:
    """Parsed protobuf field."""

    field_num: int
    wire_type: int
    value: bytes | int


def decode_protobuf_fields(data: bytes) -> list[ParsedField]:
    """Decode protobuf message into fields."""
    fields = []
    offset = 0
    while offset < len(data):
        tag, consumed = decode_varint(data, offset)
        offset += consumed
        field_num = tag >> 3
        wire_type = tag & 0x07

        if wire_type == 0:  # Varint
            value, consumed = decode_varint(data, offset)
            offset += consumed
            fields.append(ParsedField(field_num, wire_type, value))
        elif wire_type == 2:  # Length-delimited
            length, consumed = decode_varint(data, offset)
            offset += consumed
            value = data[offset : offset + length]
            offset += length
            fields.append(ParsedField(field_num, wire_type, value))
        elif wire_type == 5:  # 32-bit
            value = data[offset : offset + 4]
            offset += 4
            fields.append(ParsedField(field_num, wire_type, value))
        else:
            raise ValueError(f"Unsupported wire type: {wire_type}")

    return fields


def get_string_field(fields: list[ParsedField], field_num: int) -> str:
    """Get string value from parsed fields."""
    for f in fields:
        if f.field_num == field_num and f.wire_type == 2:
            if isinstance(f.value, bytes):
                return f.value.decode("utf-8")
            return ""
    return ""


def get_uint_field(fields: list[ParsedField], field_num: int) -> int:
    """Get uint value from parsed fields."""
    for f in fields:
        if f.field_num == field_num and f.wire_type == 0:
            return f.value if isinstance(f.value, int) else 0
    return 0
