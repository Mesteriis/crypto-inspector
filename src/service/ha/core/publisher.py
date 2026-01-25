"""Publisher for Home Assistant Supervisor API.

Wraps SupervisorAPIClient to provide sensor-specific publishing methods.
"""

import asyncio
import json
import logging

from core.constants import APP_VERSION
from service.ha_integration import SupervisorAPIClient, get_supervisor_client

logger = logging.getLogger(__name__)


class SupervisorPublisher:
    """Publisher for HA sensors via Supervisor REST API.

    Wraps SupervisorAPIClient with sensor-specific methods
    and standardized device info.
    """

    DEVICE_ID = "crypto_inspect"
    DEVICE_NAME = "Crypto Inspect"
    ENTITY_PREFIX = "sensor.crypto_inspect_"
    
    # Store background tasks to prevent garbage collection
    _background_tasks: set = set()

    def __init__(self, client: SupervisorAPIClient | None = None):
        """Initialize publisher.

        Args:
            client: Optional SupervisorAPIClient instance.
                   If not provided, uses global singleton.
        """
        self._client = client or get_supervisor_client()

    @property
    def is_available(self) -> bool:
        """Check if Supervisor API is available."""
        return self._client.is_available

    @property
    def device_info(self) -> dict:
        """Get device info for HA."""
        return {
            "identifiers": [self.DEVICE_ID],
            "name": self.DEVICE_NAME,
            "manufacturer": "Crypto Inspect",
            "model": "Sensor Manager",
            "sw_version": APP_VERSION,
        }

    def _get_entity_id(self, sensor_id: str) -> str:
        """Get full entity ID for sensor.

        Args:
            sensor_id: Sensor identifier (e.g., 'prices')

        Returns:
            Full entity ID (e.g., 'sensor.crypto_inspect_prices')
        """
        return f"{self.ENTITY_PREFIX}{sensor_id}"

    async def create_sensor(
        self,
        sensor_id: str,
        registration_data: dict,
        initial_state: str = "unknown",
    ) -> bool:
        """Create/register sensor in Home Assistant.

        Args:
            sensor_id: Sensor identifier
            registration_data: Sensor metadata from get_registration_data()
            initial_state: Initial state value

        Returns:
            True if created successfully
        """
        if not self.is_available:
            logger.debug("Supervisor API not available, skipping sensor creation")
            return False

        # Add device info to attributes
        attributes = registration_data.copy()
        attributes["device"] = self.device_info

        return await self._client.create_sensor(
            sensor_id=sensor_id,
            state=initial_state,
            friendly_name=registration_data.get("friendly_name", sensor_id),
            icon=registration_data.get("icon", "mdi:help-circle"),
            unit=registration_data.get("unit_of_measurement"),
            device_class=registration_data.get("device_class"),
            attributes=attributes,
        )

    async def publish_sensor(
        self,
        sensor_id: str,
        state: str | dict,
        attributes: dict | None = None,
    ) -> bool:
        """Publish sensor state and attributes.

        Args:
            sensor_id: Sensor identifier
            state: State value (string or dict for JSON)
            attributes: Optional additional attributes

        Returns:
            True if published successfully (or saved to DB when HA not available)
        """
        # Save to database (non-blocking but with task retention)
        task = asyncio.create_task(self._save_sensor_state(sensor_id, state))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        if not self.is_available:
            logger.debug(f"Supervisor API not available, skipping HA publish for {sensor_id}")
            return True  # Return True since we saved to DB

        # Convert dict state to JSON string
        if isinstance(state, dict):
            state_str = json.dumps(state)
        else:
            state_str = str(state)

        return await self._client.update_sensor(
            sensor_id=sensor_id,
            state=state_str,
            attributes=attributes,
        )

    async def _save_sensor_state(self, sensor_id: str, value: str | dict) -> None:
        """Save sensor state to database asynchronously.

        Args:
            sensor_id: Sensor identifier
            value: Sensor value
        """
        try:
            from models.repositories.sensor_state import SensorStateRepository
            from models.session import async_session_maker

            unique_id = f"crypto_inspect_{sensor_id}"
            async with async_session_maker() as session:
                repo = SensorStateRepository(session)
                await repo.upsert(unique_id, sensor_id, value)
        except Exception as e:
            logger.debug(f"Failed to save sensor state {sensor_id}: {e}")

    async def update_attributes(
        self,
        sensor_id: str,
        attributes: dict,
    ) -> bool:
        """Update only sensor attributes without changing state.

        Args:
            sensor_id: Sensor identifier
            attributes: Attributes to update

        Returns:
            True if updated successfully
        """
        if not self.is_available:
            return False

        entity_id = self._get_entity_id(sensor_id)

        # Get current state first
        try:
            client = await self._client._get_client()
            response = await client.get(f"/core/api/states/{entity_id}")

            if response.status_code == 200:
                current = response.json()
                current_state = current.get("state", "unknown")

                # Merge attributes
                current_attrs = current.get("attributes", {})
                current_attrs.update(attributes)

                return await self._client.set_state(
                    entity_id=entity_id,
                    state=current_state,
                    attributes=current_attrs,
                )
            else:
                logger.warning(f"Could not get current state for {entity_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update attributes for {sensor_id}: {e}")
            return False

    async def remove_sensor(self, sensor_id: str) -> bool:
        """Mark sensor as unavailable.

        Args:
            sensor_id: Sensor identifier

        Returns:
            True if updated successfully
        """
        return await self.publish_sensor(
            sensor_id=sensor_id,
            state="unavailable",
            attributes={"available": False},
        )
