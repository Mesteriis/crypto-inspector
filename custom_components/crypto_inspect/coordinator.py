"""Data coordinator for Crypto Inspect integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_HEALTH,
    API_SENSORS_ALL,
    API_SENSORS_REGISTRY,
    DOMAIN,
)

if TYPE_CHECKING:
    from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)


class CryptoInspectCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching sensor data from Crypto Inspect API."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        host: str,
        port: int,
        update_interval: int,
        entry_id: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self._session = session
        self._host = host
        self._port = port
        self._entry_id = entry_id
        self._base_url = f"http://{host}:{port}"

        # Cached sensor registry (metadata)
        self._sensor_registry: dict[str, dict] = {}
        self._registry_loaded = False

    @property
    def base_url(self) -> str:
        """Return the base URL for the API."""
        return self._base_url

    @property
    def sensor_registry(self) -> dict[str, dict]:
        """Return cached sensor registry."""
        return self._sensor_registry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch sensor data from Crypto Inspect API."""
        # Load registry on first update
        if not self._registry_loaded:
            await self._load_sensor_registry()

        try:
            async with self._session.get(
                f"{self._base_url}{API_SENSORS_ALL}",
                timeout=30,
            ) as response:
                if response.status != 200:
                    raise UpdateFailed(
                        f"API returned status {response.status}"
                    )

                data = await response.json()

                _LOGGER.debug(
                    "Fetched %d sensors from Crypto Inspect",
                    len(data.get("sensors", {})),
                )

                return data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _load_sensor_registry(self) -> None:
        """Load sensor registry (metadata) from API."""
        try:
            async with self._session.get(
                f"{self._base_url}{API_SENSORS_REGISTRY}",
                timeout=30,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._sensor_registry = data.get("sensors", {})
                    self._registry_loaded = True
                    _LOGGER.info(
                        "Loaded sensor registry with %d sensors",
                        len(self._sensor_registry),
                    )
                else:
                    _LOGGER.warning(
                        "Failed to load sensor registry: status %s",
                        response.status,
                    )
        except Exception as err:
            _LOGGER.warning("Failed to load sensor registry: %s", err)

    async def async_check_connection(self) -> bool:
        """Check connection to Crypto Inspect API."""
        try:
            async with self._session.get(
                f"{self._base_url}{API_HEALTH}",
                timeout=10,
            ) as response:
                return response.status == 200
        except Exception:
            return False

    def get_sensor_value(self, sensor_id: str) -> Any:
        """Get value for a specific sensor from cached data."""
        if not self.data:
            return None

        sensors = self.data.get("sensors", {})
        sensor_data = sensors.get(sensor_id)

        if sensor_data is None:
            return None

        # Handle both simple values and dicts with 'value' key
        if isinstance(sensor_data, dict):
            return sensor_data.get("value", sensor_data)
        return sensor_data

    def get_sensor_attributes(self, sensor_id: str) -> dict[str, Any]:
        """Get attributes for a specific sensor."""
        if not self.data:
            return {}

        sensors = self.data.get("sensors", {})
        sensor_data = sensors.get(sensor_id)

        if not isinstance(sensor_data, dict):
            return {}

        # Extract attributes, excluding 'value' key
        return {k: v for k, v in sensor_data.items() if k != "value"}

    def get_sensor_metadata(self, sensor_id: str) -> dict[str, Any]:
        """Get metadata for a specific sensor from registry."""
        return self._sensor_registry.get(sensor_id, {})

    def get_available_sensors(self) -> list[str]:
        """Get list of available sensor IDs."""
        if self.data:
            return list(self.data.get("sensors", {}).keys())
        return list(self._sensor_registry.keys())
