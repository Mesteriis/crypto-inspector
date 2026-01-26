"""ESPHome Native API TCP Server.

Implements ESPHome-compatible TCP server for Home Assistant integration.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable

from .messages import (
    DeviceInfo,
    SensorInfo,
    TextSensorInfo,
    build_device_info_response,
    build_hello_response,
    build_list_entities_done_response,
    build_list_entities_sensor_response,
    build_list_entities_text_sensor_response,
    build_ping_response,
    build_sensor_state_response,
    build_text_sensor_state_response,
)
from .protocol import (
    MSG_DEVICE_INFO_REQUEST,
    MSG_DISCONNECT_REQUEST,
    MSG_HELLO_REQUEST,
    MSG_LIST_ENTITIES_REQUEST,
    MSG_PING_REQUEST,
    MSG_SUBSCRIBE_STATES_REQUEST,
    decode_frame,
    decode_protobuf_fields,
    get_string_field,
    get_uint_field,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ESPHome Native API port
ESPHOME_API_PORT = 6053


class ESPHomeClient:
    """Handles a single ESPHome API client connection."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        server: ESPHomeAPIServer,
    ) -> None:
        """Initialize client handler."""
        self.reader = reader
        self.writer = writer
        self.server = server
        self.buffer = b""
        self.subscribed = False
        self.client_info = ""
        self._running = True

    async def handle(self) -> None:
        """Handle client connection."""
        addr = self.writer.get_extra_info("peername")
        logger.info("ESPHome API: Client connected from %s", addr)

        try:
            while self._running:
                data = await self.reader.read(4096)
                if not data:
                    break

                self.buffer += data
                await self._process_buffer()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("ESPHome API: Client error: %s", e)
        finally:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("ESPHome API: Client disconnected from %s", addr)
            self.server.remove_client(self)

    async def _process_buffer(self) -> None:
        """Process buffered data for complete frames."""
        while self.buffer:
            try:
                result = decode_frame(self.buffer)
                if result is None:
                    break  # Incomplete frame

                msg_type, payload, consumed = result
                self.buffer = self.buffer[consumed:]
                await self._handle_message(msg_type, payload)
            except ValueError as e:
                logger.error("ESPHome API: Frame error: %s", e)
                self._running = False
                break

    async def _handle_message(self, msg_type: int, payload: bytes) -> None:
        """Handle incoming message."""
        logger.debug("ESPHome API: Received message type %d", msg_type)

        if msg_type == MSG_HELLO_REQUEST:
            await self._handle_hello(payload)
        elif msg_type == MSG_DEVICE_INFO_REQUEST:
            await self._handle_device_info()
        elif msg_type == MSG_LIST_ENTITIES_REQUEST:
            await self._handle_list_entities()
        elif msg_type == MSG_SUBSCRIBE_STATES_REQUEST:
            await self._handle_subscribe_states()
        elif msg_type == MSG_PING_REQUEST:
            await self._send(build_ping_response())
        elif msg_type == MSG_DISCONNECT_REQUEST:
            self._running = False
        else:
            logger.debug("ESPHome API: Unknown message type %d", msg_type)

    async def _handle_hello(self, payload: bytes) -> None:
        """Handle HelloRequest."""
        fields = decode_protobuf_fields(payload)
        self.client_info = get_string_field(fields, 1)
        api_major = get_uint_field(fields, 2)
        api_minor = get_uint_field(fields, 3)
        logger.info(
            "ESPHome API: Hello from %s (API %d.%d)",
            self.client_info,
            api_major,
            api_minor,
        )
        await self._send(build_hello_response())

    async def _handle_device_info(self) -> None:
        """Handle DeviceInfoRequest."""
        await self._send(build_device_info_response(self.server.device_info))

    async def _handle_list_entities(self) -> None:
        """Handle ListEntitiesRequest - send all sensors."""
        logger.info(
            "ESPHome API: Listing %d sensors, %d text sensors",
            len(self.server.sensors),
            len(self.server.text_sensors),
        )

        # Send numeric sensors
        for sensor in self.server.sensors.values():
            await self._send(build_list_entities_sensor_response(sensor))

        # Send text sensors
        for sensor in self.server.text_sensors.values():
            await self._send(build_list_entities_text_sensor_response(sensor))

        # Send done
        await self._send(build_list_entities_done_response())

    async def _handle_subscribe_states(self) -> None:
        """Handle SubscribeStatesRequest - subscribe to state updates."""
        self.subscribed = True
        logger.info("ESPHome API: Client subscribed to states")

        # Send current states for all sensors
        for object_id, sensor in self.server.sensors.items():
            state = self.server.get_sensor_state(object_id)
            if state is not None:
                msg = build_sensor_state_response(sensor.key, state)
                await self._send(msg)

        for object_id, sensor in self.server.text_sensors.items():
            state = self.server.get_text_sensor_state(object_id)
            if state is not None:
                msg = build_text_sensor_state_response(sensor.key, state)
                await self._send(msg)

    async def send_state_update(
        self,
        key: int,
        state: float | str,
        is_text: bool,
    ) -> None:
        """Send state update to client if subscribed."""
        if not self.subscribed:
            return

        if is_text:
            await self._send(build_text_sensor_state_response(key, str(state)))
        else:
            await self._send(build_sensor_state_response(key, float(state)))

    async def _send(self, data: bytes) -> None:
        """Send data to client."""
        try:
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            logger.error("ESPHome API: Send error: %s", e)
            self._running = False


class ESPHomeAPIServer:
    """ESPHome Native API Server."""

    def __init__(
        self,
        port: int = ESPHOME_API_PORT,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialize server."""
        self.port = port
        self.device_info = device_info or DeviceInfo()
        self.sensors: dict[str, SensorInfo] = {}
        self.text_sensors: dict[str, TextSensorInfo] = {}
        self._clients: list[ESPHomeClient] = []
        self._server: asyncio.Server | None = None
        self._state_getter: Callable[[str], Any] | None = None

    def set_state_getter(self, getter: Callable[[str], Any]) -> None:
        """Set callback to get sensor states."""
        self._state_getter = getter

    def register_sensor(self, sensor: SensorInfo) -> None:
        """Register a numeric sensor."""
        self.sensors[sensor.object_id] = sensor
        logger.debug("ESPHome API: Registered sensor %s", sensor.object_id)

    def register_text_sensor(self, sensor: TextSensorInfo) -> None:
        """Register a text sensor."""
        self.text_sensors[sensor.object_id] = sensor
        logger.debug("ESPHome API: Registered text sensor %s", sensor.object_id[:40])

    def get_sensor_state(self, object_id: str) -> float | None:
        """Get current sensor state."""
        if self._state_getter:
            value = self._state_getter(object_id)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        return None

    def get_text_sensor_state(self, object_id: str) -> str | None:
        """Get current text sensor state."""
        if self._state_getter:
            value = self._state_getter(object_id)
            if value is not None:
                return str(value)
        return None

    async def start(self) -> bool:
        """Start the server."""
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                "0.0.0.0",
                self.port,
            )
            logger.info("ESPHome API: Server started on port %d", self.port)
            return True
        except OSError as e:
            logger.error("ESPHome API: Failed to start server: %s", e)
            return False

    async def stop(self) -> None:
        """Stop the server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Close all clients
        for client in self._clients[:]:
            client._running = False

        logger.info("ESPHome API: Server stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle new client connection."""
        client = ESPHomeClient(reader, writer, self)
        self._clients.append(client)
        await client.handle()

    def remove_client(self, client: ESPHomeClient) -> None:
        """Remove client from list."""
        if client in self._clients:
            self._clients.remove(client)

    async def broadcast_state(
        self,
        object_id: str,
        state: float | str,
    ) -> None:
        """Broadcast state update to all subscribed clients."""
        # Find sensor
        sensor = self.sensors.get(object_id)
        text_sensor = self.text_sensors.get(object_id)

        if sensor:
            for client in self._clients:
                await client.send_state_update(
                    sensor.key, state, is_text=False
                )
        elif text_sensor:
            for client in self._clients:
                await client.send_state_update(
                    text_sensor.key, state, is_text=True
                )


# Global server instance
_server: ESPHomeAPIServer | None = None


def get_esphome_server() -> ESPHomeAPIServer:
    """Get or create global ESPHome API server."""
    global _server
    if _server is None:
        _server = ESPHomeAPIServer()
    return _server


async def start_esphome_server() -> bool:
    """Start global ESPHome API server."""
    server = get_esphome_server()
    return await server.start()


async def stop_esphome_server() -> None:
    """Stop global ESPHome API server."""
    global _server
    if _server:
        await _server.stop()
        _server = None
