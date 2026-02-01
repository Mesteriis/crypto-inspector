"""Dictionary sensor type for multi-value measurements.

Provides sensors that store dict values like:
- {"BTC": 95000, "ETH": 3200}
- {"BTC": 2.5, "ETH": -1.2}

Used for prices, changes, volumes, and other per-symbol data.
"""

import json
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from service.ha.core.base import BaseSensor


class DictSensor(BaseSensor):
    """Sensor for dictionary values (key-value per symbol).

    Stores and publishes dict data like:
    - prices: {"BTC": 95000, "ETH": 3200}
    - changes_24h: {"BTC": 2.5, "ETH": -1.2}

    State is published as JSON string, with individual values
    accessible via HA attributes.
    """

    # Optional: validation function for values
    value_validator: Callable | None = None

    def validate(self, data: Any) -> dict:
        """Validate dictionary data.

        Args:
            data: Dict or dict-like value

        Returns:
            Validated dictionary

        Raises:
            ValueError: If not a valid dict
        """
        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        # Convert Decimal to float for JSON serialization
        result = {}
        for key, value in data.items():
            if isinstance(value, Decimal):
                value = float(value)

            # Apply value validator if defined
            if self.value_validator:
                value = self.value_validator(value)

            result[str(key)] = value

        return result

    def format_state(self, value: dict) -> str:
        """Format dict as JSON string.

        Args:
            value: Validated dict

        Returns:
            JSON string
        """
        return json.dumps(value)

    async def publish(self, value: Any, attributes: dict | None = None) -> bool:
        """Publish dict sensor with symbol count.

        Adds 'count' and 'symbols' to attributes automatically.

        Args:
            value: Dict value to publish
            attributes: Optional additional attributes

        Returns:
            True if published successfully
        """
        validated = self.validate(value)
        self._cached_value = validated

        # Build attributes with symbol info
        attrs = attributes.copy() if attributes else {}
        attrs["count"] = len(validated)
        attrs["symbols"] = list(validated.keys())

        # Include individual values as attributes for HA template access
        for key, val in validated.items():
            attrs[key] = val

        state = self.format_state(validated)
        return await self.publisher.publish_sensor(
            self.config.sensor_id,
            state,
            attrs,
        )

    def get_value(self, key: str) -> Any:
        """Get cached value for specific key.

        Args:
            key: Symbol/key to lookup

        Returns:
            Value or None if not found
        """
        if self._cached_value:
            return self._cached_value.get(key)
        return None


class PriceDictSensor(DictSensor):
    """Specialized dict sensor for price data.

    Validates that all values are positive numbers.
    Formats with appropriate precision.
    """

    def validate(self, data: Any) -> dict:
        """Validate price dictionary.

        Args:
            data: Dict of symbol -> price

        Returns:
            Validated dict with float prices

        Raises:
            ValueError: If any price is invalid
        """
        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        result = {}
        for symbol, price in data.items():
            try:
                if isinstance(price, Decimal):
                    price_float = float(price)
                else:
                    price_float = float(price)

                if price_float < 0:
                    raise ValueError(f"Negative price for {symbol}: {price_float}")

                result[str(symbol)] = price_float

            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid price for {symbol}: {price}") from e

        return result


class PercentDictSensor(DictSensor):
    """Specialized dict sensor for percentage data.

    Used for changes, allocations, etc.
    """

    def validate(self, data: Any) -> dict:
        """Validate percentage dictionary.

        Args:
            data: Dict of symbol -> percentage

        Returns:
            Validated dict with float percentages
        """
        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        result = {}
        for symbol, pct in data.items():
            try:
                if isinstance(pct, Decimal):
                    pct_float = float(pct)
                else:
                    pct_float = float(pct)

                # Format to 2 decimal places
                result[str(symbol)] = round(pct_float, 2)

            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid percentage for {symbol}: {pct}") from e

        return result


class IndicatorDictSensor(DictSensor):
    """Dict sensor for technical indicators per symbol.

    Stores indicator values like RSI, MACD signals, etc.
    """

    # Indicator-specific validation ranges
    min_value: float | None = None
    max_value: float | None = None

    def validate(self, data: Any) -> dict:
        """Validate indicator dictionary.

        Args:
            data: Dict of symbol -> indicator value

        Returns:
            Validated dict
        """
        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        result = {}
        for symbol, value in data.items():
            # Skip None values (they indicate no data available)
            if value is None:
                continue

            # Handle various value types
            if isinstance(value, (int, float, Decimal)):
                float_val = float(value)

                # Range validation
                if self.min_value is not None and float_val < self.min_value:
                    raise ValueError(f"{symbol} indicator {float_val} below min {self.min_value}")
                if self.max_value is not None and float_val > self.max_value:
                    raise ValueError(f"{symbol} indicator {float_val} above max {self.max_value}")

                result[str(symbol)] = float_val

            elif isinstance(value, str):
                # Text indicators (signals, status)
                result[str(symbol)] = value

            elif isinstance(value, dict):
                # Nested indicator data
                result[str(symbol)] = value

            else:
                result[str(symbol)] = str(value)

        return result
