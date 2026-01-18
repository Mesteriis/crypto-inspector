"""Home Assistant integration services.

This module provides:
1. Supervisor API client for notifications
2. MQTT Discovery for automatic sensor creation
"""

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum

import httpx

from core.constants import APP_VERSION

logger = logging.getLogger(__name__)

# Supervisor API token is automatically available in add-ons
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
SUPERVISOR_URL = "http://supervisor"


class NotificationType(str, Enum):
    """Notification types for HA."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class HANotification:
    """Home Assistant notification data."""

    title: str
    message: str
    notification_id: str | None = None


class SupervisorAPIClient:
    """Client for Home Assistant Supervisor API."""

    def __init__(self):
        self.base_url = SUPERVISOR_URL
        self.token = SUPERVISOR_TOKEN
        self._client: httpx.AsyncClient | None = None

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @property
    def is_available(self) -> bool:
        """Check if Supervisor API is available."""
        return bool(self.token)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def set_state(
        self,
        entity_id: str,
        state: str,
        attributes: dict | None = None,
    ) -> bool:
        """
        Set state for an entity (creates if not exists).

        Args:
            entity_id: Full entity ID (e.g., 'sensor.crypto_inspect_status')
            state: Entity state value
            attributes: Optional attributes dict

        Returns:
            True if successful
        """
        if not self.is_available:
            logger.debug("Supervisor API not available")
            return False

        client = await self._get_client()
        url = f"/core/api/states/{entity_id}"

        data = {"state": state}
        if attributes:
            data["attributes"] = attributes

        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            logger.debug(f"Set state for {entity_id}: {state}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to set state for {entity_id}: {e}")
            return False

    async def create_sensor(
        self,
        sensor_id: str,
        state: str,
        friendly_name: str,
        icon: str = "mdi:chart-line",
        unit: str | None = None,
        device_class: str | None = None,
        attributes: dict | None = None,
    ) -> bool:
        """
        Create or update a sensor entity.

        Args:
            sensor_id: Sensor ID without 'sensor.' prefix
            state: Initial state value
            friendly_name: Display name
            icon: MDI icon
            unit: Unit of measurement
            device_class: HA device class
            attributes: Additional attributes

        Returns:
            True if successful
        """
        entity_id = f"sensor.crypto_inspect_{sensor_id}"

        attrs = {
            "friendly_name": friendly_name,
            "icon": icon,
        }
        if unit:
            attrs["unit_of_measurement"] = unit
        if device_class:
            attrs["device_class"] = device_class
        if attributes:
            attrs.update(attributes)

        return await self.set_state(entity_id, state, attrs)

    async def update_sensor(self, sensor_id: str, state: str, attributes: dict | None = None) -> bool:
        """
        Update sensor state (preserves existing attributes).

        Args:
            sensor_id: Sensor ID without 'sensor.' prefix
            state: New state value
            attributes: Attributes to update/add

        Returns:
            True if successful
        """
        entity_id = f"sensor.crypto_inspect_{sensor_id}"
        return await self.set_state(entity_id, state, attributes)

    async def call_service(
        self,
        domain: str,
        service: str,
        data: dict | None = None,
    ) -> bool:
        """
        Call a Home Assistant service.

        Args:
            domain: Service domain (e.g., 'notify', 'persistent_notification')
            service: Service name (e.g., 'create', 'mobile_app_phone')
            data: Service data

        Returns:
            True if successful
        """
        client = await self._get_client()
        url = f"/core/api/services/{domain}/{service}"

        try:
            response = await client.post(url, json=data or {})
            response.raise_for_status()
            logger.info(f"Called HA service {domain}.{service}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to call HA service {domain}.{service}: {e}")
            return False

    async def send_persistent_notification(
        self,
        message: str,
        title: str = "Crypto Inspect",
        notification_id: str | None = None,
    ) -> bool:
        """
        Send a persistent notification to HA UI.

        Args:
            message: Notification message
            title: Notification title
            notification_id: Optional ID for updating/dismissing

        Returns:
            True if successful
        """
        data = {
            "message": message,
            "title": title,
        }
        if notification_id:
            data["notification_id"] = notification_id

        return await self.call_service(
            domain="persistent_notification",
            service="create",
            data=data,
        )

    async def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a persistent notification."""
        return await self.call_service(
            domain="persistent_notification",
            service="dismiss",
            data={"notification_id": notification_id},
        )

    async def fire_event(self, event_type: str, event_data: dict | None = None) -> bool:
        """
        Fire a custom event in Home Assistant.

        Args:
            event_type: Event type name
            event_data: Event data dictionary

        Returns:
            True if successful
        """
        client = await self._get_client()
        url = f"/core/api/events/{event_type}"

        try:
            response = await client.post(url, json=event_data or {})
            response.raise_for_status()
            logger.info(f"Fired HA event: {event_type}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to fire HA event {event_type}: {e}")
            return False


class MQTTDiscoveryClient:
    """
    MQTT Discovery client for auto-creating HA entities.

    Publishes discovery configs to homeassistant/<component>/<node_id>/<object_id>/config
    """

    DISCOVERY_PREFIX = "homeassistant"
    DEVICE_ID = "crypto_inspect"
    DEVICE_NAME = "Crypto Inspect"

    def __init__(self, mqtt_client=None):
        """
        Initialize MQTT Discovery client.

        Args:
            mqtt_client: MQTT client instance (e.g., aiomqtt.Client)
        """
        self._mqtt = mqtt_client
        self._registered_entities: set[str] = set()

    @property
    def device_info(self) -> dict:
        """Base device information for all entities."""
        return {
            "identifiers": [self.DEVICE_ID],
            "name": self.DEVICE_NAME,
            "model": "Crypto Data Collector",
            "manufacturer": "Crypto Inspect Add-on",
            "sw_version": APP_VERSION,
        }

    def _get_discovery_topic(self, component: str, object_id: str) -> str:
        """Get MQTT discovery topic for an entity."""
        return f"{self.DISCOVERY_PREFIX}/{component}/{self.DEVICE_ID}/{object_id}/config"

    def _get_state_topic(self, object_id: str) -> str:
        """Get MQTT state topic for an entity."""
        return f"{self.DEVICE_ID}/{object_id}/state"

    def _get_attributes_topic(self, object_id: str) -> str:
        """Get MQTT attributes topic for an entity."""
        return f"{self.DEVICE_ID}/{object_id}/attributes"

    async def register_sensor(
        self,
        object_id: str,
        name: str,
        unit: str | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        icon: str | None = None,
        entity_category: str | None = None,
    ) -> bool:
        """
        Register a sensor entity via MQTT Discovery.

        Args:
            object_id: Unique ID for this sensor
            name: Display name
            unit: Unit of measurement
            device_class: HA device class (e.g., 'monetary', 'timestamp')
            state_class: HA state class (e.g., 'measurement', 'total')
            icon: MDI icon (e.g., 'mdi:bitcoin')
            entity_category: Entity category ('config', 'diagnostic')

        Returns:
            True if successful
        """
        if not self._mqtt:
            logger.warning("MQTT client not configured")
            return False

        config = {
            "name": name,
            "unique_id": f"{self.DEVICE_ID}_{object_id}",
            "state_topic": self._get_state_topic(object_id),
            "json_attributes_topic": self._get_attributes_topic(object_id),
            "device": self.device_info,
        }

        if unit:
            config["unit_of_measurement"] = unit
        if device_class:
            config["device_class"] = device_class
        if state_class:
            config["state_class"] = state_class
        if icon:
            config["icon"] = icon
        if entity_category:
            config["entity_category"] = entity_category

        topic = self._get_discovery_topic("sensor", object_id)

        try:
            await self._mqtt.publish(topic, json.dumps(config), retain=True)
            self._registered_entities.add(object_id)
            logger.info(f"Registered MQTT sensor: {name} ({object_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to register MQTT sensor {object_id}: {e}")
            return False

    async def register_binary_sensor(
        self,
        object_id: str,
        name: str,
        device_class: str | None = None,
        icon: str | None = None,
    ) -> bool:
        """Register a binary sensor entity via MQTT Discovery."""
        if not self._mqtt:
            return False

        config = {
            "name": name,
            "unique_id": f"{self.DEVICE_ID}_{object_id}",
            "state_topic": self._get_state_topic(object_id),
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": self.device_info,
        }

        if device_class:
            config["device_class"] = device_class
        if icon:
            config["icon"] = icon

        topic = self._get_discovery_topic("binary_sensor", object_id)

        try:
            await self._mqtt.publish(topic, json.dumps(config), retain=True)
            self._registered_entities.add(object_id)
            logger.info(f"Registered MQTT binary_sensor: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register binary sensor {object_id}: {e}")
            return False

    async def update_state(self, object_id: str, state: str | int | float) -> bool:
        """Update entity state."""
        if not self._mqtt:
            return False

        topic = self._get_state_topic(object_id)
        try:
            await self._mqtt.publish(topic, str(state))
            return True
        except Exception as e:
            logger.error(f"Failed to update state for {object_id}: {e}")
            return False

    async def update_attributes(self, object_id: str, attributes: dict) -> bool:
        """Update entity attributes."""
        if not self._mqtt:
            return False

        topic = self._get_attributes_topic(object_id)
        try:
            await self._mqtt.publish(topic, json.dumps(attributes))
            return True
        except Exception as e:
            logger.error(f"Failed to update attributes for {object_id}: {e}")
            return False

    async def remove_entity(self, component: str, object_id: str) -> bool:
        """Remove an entity by publishing empty config."""
        if not self._mqtt:
            return False

        topic = self._get_discovery_topic(component, object_id)
        try:
            await self._mqtt.publish(topic, "", retain=True)
            self._registered_entities.discard(object_id)
            logger.info(f"Removed MQTT entity: {object_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove entity {object_id}: {e}")
            return False


# Global instances
_supervisor_client: SupervisorAPIClient | None = None
_mqtt_discovery: MQTTDiscoveryClient | None = None


def get_supervisor_client() -> SupervisorAPIClient:
    """Get or create Supervisor API client."""
    global _supervisor_client
    if _supervisor_client is None:
        _supervisor_client = SupervisorAPIClient()
    return _supervisor_client


def get_mqtt_discovery(mqtt_client=None) -> MQTTDiscoveryClient:
    """Get or create MQTT Discovery client."""
    global _mqtt_discovery
    if _mqtt_discovery is None or mqtt_client is not None:
        _mqtt_discovery = MQTTDiscoveryClient(mqtt_client)
    return _mqtt_discovery


# Convenience functions
async def notify(
    message: str,
    title: str = "Crypto Inspect",
    notification_id: str | None = None,
) -> bool:
    """Send a persistent notification to Home Assistant."""
    client = get_supervisor_client()
    return await client.send_persistent_notification(message, title, notification_id)


async def notify_sync_complete(
    success_count: int,
    failure_count: int,
    duration_seconds: float,
) -> bool:
    """Send notification about sync job completion."""
    total = success_count + failure_count
    status = "completed" if failure_count == 0 else "completed with errors"

    message = (
        f"Sync {status}\n"
        f"✓ Success: {success_count}/{total}\n"
        f"✗ Failed: {failure_count}\n"
        f"⏱ Duration: {duration_seconds:.1f}s"
    )

    return await notify(
        message=message,
        title="Crypto Inspect - Sync",
        notification_id="crypto_inspect_sync",
    )


async def notify_error(error_message: str, context: str = "") -> bool:
    """Send error notification."""
    message = f"❌ Error: {error_message}"
    if context:
        message += f"\n📍 Context: {context}"

    return await notify(
        message=message,
        title="Crypto Inspect - Error",
        notification_id="crypto_inspect_error",
    )


async def register_sensors() -> int:
    """
    Register all Crypto Inspect sensors in Home Assistant.

    Creates sensors via Supervisor REST API (auto-discovery).

    Returns:
        Number of sensors registered.
    """
    client = get_supervisor_client()

    if not client.is_available:
        logger.warning("Supervisor API not available, skipping sensor registration")
        return 0

    logger.info("Registering Crypto Inspect sensors...")
    count = 0

    # Основные датчики
    sensors = [
        # Статус
        ("status", "online", "Crypto Inspect Status", "mdi:check-network", None, None),
        # Цены
        ("btc_price", "0", "BTC Price", "mdi:bitcoin", "USDT", None),
        ("eth_price", "0", "ETH Price", "mdi:ethereum", "USDT", None),
        # Рынок
        ("fear_greed", "50", "Fear & Greed Index", "mdi:emoticon-neutral", None, None),
        ("market_pulse", "Нейтрально", "Market Pulse", "mdi:pulse", None, None),
        ("btc_dominance", "0", "BTC Dominance", "mdi:crown", "%", None),
        # Инвестор
        ("do_nothing_ok", "Да", "Do Nothing OK", "mdi:meditation", None, None),
        ("investor_phase", "Накопление", "Investor Phase", "mdi:chart-timeline-variant-shimmer", None, None),
        # Буфер
        ("buffer_size", "0", "Buffer Size", "mdi:database", "candles", None),
        ("candles_total", "0", "Total Candles", "mdi:database-check", "candles", None),
    ]

    for sensor_id, state, name, icon, unit, device_class in sensors:
        success = await client.create_sensor(
            sensor_id=sensor_id,
            state=state,
            friendly_name=name,
            icon=icon,
            unit=unit,
            device_class=device_class,
        )
        if success:
            count += 1

    logger.info(f"Registered {count} sensors")
    return count


async def update_price_sensors(prices: dict[str, float]) -> None:
    """
    Update price sensors.

    Args:
        prices: Dict of {symbol: price}
    """
    client = get_supervisor_client()
    if not client.is_available:
        return

    symbol_map = {
        "BTC/USDT": "btc_price",
        "BTCUSDT": "btc_price",
        "ETH/USDT": "eth_price",
        "ETHUSDT": "eth_price",
    }

    for symbol, price in prices.items():
        sensor_id = symbol_map.get(symbol)
        if sensor_id:
            await client.update_sensor(sensor_id, f"{price:.2f}")


async def update_buffer_stats(buffered: int, flushed: int, current_size: int) -> None:
    """Update buffer statistics sensors."""
    client = get_supervisor_client()
    if not client.is_available:
        return

    await client.update_sensor("buffer_size", str(current_size))
    await client.update_sensor("candles_total", str(flushed))
