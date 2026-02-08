"""Sensor registry for centralized sensor management.

Provides automatic registration of sensors via decorator and
centralized access to all registered sensors.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from service.ha.core.base import BaseSensor

logger = logging.getLogger(__name__)


class SensorRegistry:
    """Centralized registry for all HA sensors.

    Sensors are registered via the @register_sensor decorator.
    Provides access by sensor_id or category.
    """

    _sensors: dict[str, type["BaseSensor"]] = {}
    _categories: dict[str, list[str]] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, category: str):
        """Decorator to register a sensor class.

        Args:
            category: Category name for grouping (e.g., 'price', 'market')

        Returns:
            Decorator function

        Example:
            @register_sensor(category="price")
            class PricesSensor(DictSensor):
                config = SensorConfig(sensor_id="prices", ...)
        """

        def decorator(sensor_class: type["BaseSensor"]):
            sensor_id = sensor_class.config.sensor_id

            if sensor_id in cls._sensors:
                raise ValueError(f"Sensor '{sensor_id}' already registered by {cls._sensors[sensor_id].__name__}")

            cls._sensors[sensor_id] = sensor_class
            cls._categories.setdefault(category, []).append(sensor_id)

            logger.debug(f"Registered sensor: {sensor_id} in category '{category}'")
            return sensor_class

        return decorator

    @classmethod
    def get(cls, sensor_id: str) -> type["BaseSensor"]:
        """Get sensor class by ID.

        Args:
            sensor_id: Sensor identifier

        Returns:
            Sensor class

        Raises:
            KeyError: If sensor not found
        """
        if sensor_id not in cls._sensors:
            raise KeyError(f"Sensor '{sensor_id}' not registered")
        return cls._sensors[sensor_id]

    @classmethod
    def get_all(cls) -> dict[str, type["BaseSensor"]]:
        """Get all registered sensors.

        Returns:
            Dictionary mapping sensor_id to sensor class
        """
        return cls._sensors.copy()

    @classmethod
    def get_by_category(cls, category: str) -> list[str]:
        """Get sensor IDs in a category.

        Args:
            category: Category name

        Returns:
            List of sensor IDs in that category
        """
        return cls._categories.get(category, []).copy()

    @classmethod
    def get_categories(cls) -> list[str]:
        """Get all registered categories.

        Returns:
            List of category names
        """
        return list(cls._categories.keys())

    @classmethod
    def count(cls) -> int:
        """Get total number of registered sensors.

        Returns:
            Number of sensors
        """
        return len(cls._sensors)

    @classmethod
    def is_registered(cls, sensor_id: str) -> bool:
        """Check if sensor is registered.

        Args:
            sensor_id: Sensor identifier

        Returns:
            True if registered
        """
        return sensor_id in cls._sensors

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations. Used for testing."""
        cls._sensors.clear()
        cls._categories.clear()
        cls._initialized = False

    @classmethod
    def ensure_initialized(cls) -> None:
        """Ensure all category modules are imported.

        This triggers the @register_sensor decorators to run.
        """
        if cls._initialized:
            return

        # Import all category modules to trigger registration
        try:
            from service.ha import categories  # noqa: F401

            cls._initialized = True
            logger.info(f"Initialized {cls.count()} sensors in {len(cls._categories)} categories")
        except ImportError as e:
            logger.warning(f"Could not import categories: {e}")


# Convenience alias for decorator
register_sensor = SensorRegistry.register
