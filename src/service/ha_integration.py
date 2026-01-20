"""Home Assistant integration services.

This module provides:
1. Supervisor API client for notifications and sensor management
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

# Supervisor API token is automatically available in add-ons
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
SUPERVISOR_URL = "http://supervisor"

# Retry configuration
HA_CONNECTION_RETRIES = 5
HA_RETRY_DELAY_SECONDS = 3


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
        self._connection_checked = False
        self._connection_available = False

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

    async def check_connection(self, retries: int = HA_CONNECTION_RETRIES) -> bool:
        """
        Check connection to Supervisor API with retries.
        
        Args:
            retries: Number of retry attempts
            
        Returns:
            True if connection successful
        """
        if not self.is_available:
            logger.info("Supervisor token not found, running in standalone mode")
            return False
        
        for attempt in range(1, retries + 1):
            try:
                client = await self._get_client()
                response = await client.get("/core/api/")
                if response.status_code == 200:
                    self._connection_checked = True
                    self._connection_available = True
                    logger.info("Successfully connected to Home Assistant Supervisor API")
                    return True
            except httpx.HTTPError as e:
                logger.warning(
                    f"HA Supervisor connection attempt {attempt}/{retries} failed: {e}"
                )
            except Exception as e:
                logger.warning(
                    f"HA Supervisor connection attempt {attempt}/{retries} error: {e}"
                )
            
            if attempt < retries:
                logger.info(f"Retrying in {HA_RETRY_DELAY_SECONDS} seconds...")
                await asyncio.sleep(HA_RETRY_DELAY_SECONDS)
        
        self._connection_checked = True
        self._connection_available = False
        logger.warning(
            f"Could not connect to HA Supervisor after {retries} attempts. "
            "Continuing without HA integration."
        )
        return False

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


# Global instances
_supervisor_client: SupervisorAPIClient | None = None


def get_supervisor_client() -> SupervisorAPIClient:
    """Get or create Supervisor API client."""
    global _supervisor_client
    if _supervisor_client is None:
        _supervisor_client = SupervisorAPIClient()
    return _supervisor_client


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
