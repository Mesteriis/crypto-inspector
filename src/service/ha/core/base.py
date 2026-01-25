"""Base sensor classes for Home Assistant integration.

This module provides the foundational classes for all HA sensors:
- SensorConfig: Declarative configuration dataclass
- BaseSensor: Abstract base class with validation and publishing
"""

import json
import logging
from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from service.ha.core.publisher import SupervisorPublisher

logger = logging.getLogger(__name__)


@dataclass
class SensorConfig:
    """Declarative configuration for a sensor.

    All sensor properties are defined here in a structured way,
    supporting both English and Russian localization.
    """

    sensor_id: str
    name: str
    name_ru: str
    icon: str
    unit: str | None = None
    device_class: str | None = None
    entity_category: str | None = None
    description: str = ""
    description_ru: str = ""
    # Additional metadata for validation
    value_type: str = "any"  # any, int, float, str, dict, bool
    min_value: float | None = None
    max_value: float | None = None


class BaseSensor(ABC):
    """Abstract base class for all Home Assistant sensors.

    Provides:
    - Declarative configuration via SensorConfig
    - Validation before publishing
    - Caching of last published value
    - Standardized publishing interface
    """

    config: SensorConfig

    def __init__(self, publisher: "SupervisorPublisher"):
        """Initialize sensor with publisher.

        Args:
            publisher: SupervisorPublisher instance for HA communication
        """
        self.publisher = publisher
        self._cached_value: Any = None
        self._cached_attributes: dict[str, Any] = {}

    @property
    def sensor_id(self) -> str:
        """Get sensor ID from config."""
        return self.config.sensor_id

    @property
    def cached_value(self) -> Any:
        """Get last cached value."""
        return self._cached_value

    def validate(self, data: Any) -> Any:
        """Validate and transform data before publishing.

        Default implementation performs basic type checking based on config.
        Override in subclasses for custom validation.

        Args:
            data: Raw data to validate

        Returns:
            Validated/transformed data

        Raises:
            ValueError: If validation fails
        """
        if data is None:
            return "unknown"

        # Basic type validation based on config
        if self.config.value_type == "int":
            try:
                data = int(data)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Expected int for {self.sensor_id}: {e}") from e

        elif self.config.value_type == "float":
            try:
                data = float(data)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Expected float for {self.sensor_id}: {e}") from e

        elif self.config.value_type == "bool":
            if not isinstance(data, bool):
                data = bool(data)

        # Range validation
        if self.config.min_value is not None and isinstance(data, (int, float)):
            if data < self.config.min_value:
                raise ValueError(
                    f"{self.sensor_id}: value {data} below minimum {self.config.min_value}"
                )

        if self.config.max_value is not None and isinstance(data, (int, float)):
            if data > self.config.max_value:
                raise ValueError(
                    f"{self.sensor_id}: value {data} above maximum {self.config.max_value}"
                )

        return data

    def format_state(self, value: Any) -> str:
        """Format value for HA state.

        Converts value to string representation suitable for HA.

        Args:
            value: Validated value

        Returns:
            String representation for HA state
        """
        if isinstance(value, dict):
            return json.dumps(value)
        if isinstance(value, bool):
            return "on" if value else "off"
        return str(value)

    async def publish(self, value: Any, attributes: dict | None = None) -> bool:
        """Publish sensor value to Home Assistant.

        Performs validation, caches value, and publishes via publisher.

        Args:
            value: Value to publish
            attributes: Optional additional attributes

        Returns:
            True if published successfully
        """
        try:
            validated = self.validate(value)
            self._cached_value = validated
            if attributes:
                self._cached_attributes.update(attributes)

            state = self.format_state(validated)
            return await self.publisher.publish_sensor(
                self.config.sensor_id,
                state,
                attributes or self._cached_attributes,
            )

        except ValueError as e:
            logger.error(f"Validation failed for {self.sensor_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to publish {self.sensor_id}: {e}")
            return False

    def get_registration_data(self) -> dict:
        """Get data for sensor registration in HA.

        Returns:
            Dictionary with sensor metadata for HA
        """
        # Unique ID for HA entity registry management
        unique_id = f"crypto_inspect_{self.config.sensor_id}"
        
        data = {
            "friendly_name": self.config.name,
            "icon": self.config.icon,
            "description": self.config.description,
            "description_ru": self.config.description_ru,
            "name_ru": self.config.name_ru,
            "unique_id": unique_id,
        }

        if self.config.unit:
            data["unit_of_measurement"] = self.config.unit

        if self.config.device_class:
            data["device_class"] = self.config.device_class

        if self.config.entity_category:
            data["entity_category"] = self.config.entity_category

        return data

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.config.sensor_id})>"
