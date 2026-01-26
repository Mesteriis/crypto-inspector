"""Scalar sensor types for single-value measurements.

Provides sensor types for:
- Simple scalar values (int, float, str)
- Percentages with range validation
- Status text values
- Count/counter values
"""

from typing import Any

from service.ha.core.base import BaseSensor


class ScalarSensor(BaseSensor):
    """Sensor for single scalar values.

    Used for simple measurements like:
    - Single numeric values
    - Text status
    - Boolean states
    """

    def validate(self, data: Any) -> Any:
        """Validate scalar value.

        Performs basic type validation from config.

        Args:
            data: Value to validate

        Returns:
            Validated value
        """
        return super().validate(data)

    def format_state(self, value: Any) -> str:
        """Format scalar value as string.

        Args:
            value: Validated value

        Returns:
            String representation
        """
        if value is None:
            return "unknown"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            # Format floats with reasonable precision
            if value == int(value):
                return str(int(value))
            return f"{value:.2f}"
        return str(value)


class PercentSensor(ScalarSensor):
    """Sensor for percentage values (0-100).

    Automatically validates range and adds % formatting.
    """

    def validate(self, data: Any) -> float:
        """Validate percentage value.

        Args:
            data: Value to validate (0-100)

        Returns:
            Validated float percentage

        Raises:
            ValueError: If value out of range
        """
        if data is None:
            return 0.0

        try:
            value = float(data)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid percentage value: {data}") from e

        if not (0 <= value <= 100):
            raise ValueError(f"Percentage must be 0-100, got {value}")

        return value

    def format_state(self, value: float) -> str:
        """Format percentage with proper precision.

        Args:
            value: Validated percentage

        Returns:
            Formatted string (e.g., "45.5")
        """
        if value == int(value):
            return str(int(value))
        return f"{value:.1f}"


class PnlPercentSensor(ScalarSensor):
    """Sensor for P&L percentage values that can be negative.

    Used for portfolio PnL where values can range from -100% to +∞%.
    """

    def validate(self, data: Any) -> float:
        """Validate P&L percentage value.

        Args:
            data: Value to validate

        Returns:
            Validated float percentage

        Raises:
            ValueError: If value is invalid
        """
        if data is None:
            return 0.0

        try:
            value = float(data)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid P&L percentage value: {data}") from e

        # PnL can be negative (losses) or positive (gains)
        # No upper/lower bounds - crypto can have extreme moves
        return value

    def format_state(self, value: float) -> str:
        """Format P&L percentage with sign.

        Args:
            value: Validated percentage

        Returns:
            Formatted string with sign (e.g., "+5.5" or "-3.2")
        """
        if value == int(value):
            return f"{int(value):+d}" if value != 0 else "0"
        return f"{value:+.1f}" if value != 0 else "0.0"


class StatusSensor(ScalarSensor):
    """Sensor for text status values.

    Used for categorical states like:
    - Market phases (accumulation, growth, euphoria, etc.)
    - Risk levels (low, medium, high)
    - Signals (buy, sell, hold)
    """

    # Optional: allowed values for validation
    allowed_values: set[str] | None = None

    def validate(self, data: Any) -> str:
        """Validate status string.

        Args:
            data: Status value

        Returns:
            Validated status string

        Raises:
            ValueError: If value not in allowed_values (when set)
        """
        if data is None:
            return "unknown"

        value = str(data)

        if self.allowed_values and value.lower() not in {v.lower() for v in self.allowed_values}:
            raise ValueError(
                f"Invalid status '{value}'. Allowed: {self.allowed_values}"
            )

        return value

    def format_state(self, value: str) -> str:
        """Return status as-is.

        Args:
            value: Validated status

        Returns:
            Status string
        """
        return value


class CountSensor(ScalarSensor):
    """Sensor for count/counter values.

    Non-negative integers for:
    - Alert counts
    - Event counts
    - Item counts
    """

    def validate(self, data: Any) -> int:
        """Validate count value.

        Args:
            data: Count value

        Returns:
            Validated non-negative integer

        Raises:
            ValueError: If value negative or not integer
        """
        if data is None:
            return 0

        try:
            value = int(data)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid count value: {data}") from e

        if value < 0:
            raise ValueError(f"Count cannot be negative: {value}")

        return value

    def format_state(self, value: int) -> str:
        """Format count as integer string.

        Args:
            value: Validated count

        Returns:
            Integer string
        """
        return str(value)


class BoolSensor(ScalarSensor):
    """Sensor for boolean yes/no values.

    Formats as human-readable text for HA display.
    """

    true_text: str = "Да"
    false_text: str = "Нет"

    def validate(self, data: Any) -> bool:
        """Validate boolean value.

        Args:
            data: Boolean-like value

        Returns:
            Validated boolean
        """
        if data is None:
            return False

        if isinstance(data, bool):
            return data

        if isinstance(data, str):
            return data.lower() in ("true", "yes", "1", "on", "да")

        return bool(data)

    def format_state(self, value: bool) -> str:
        """Format boolean as readable text.

        Args:
            value: Validated boolean

        Returns:
            "Yes"/"No" or custom text
        """
        return self.true_text if value else self.false_text


class EmojiStatusSensor(StatusSensor):
    """Sensor that formats status with emoji prefix.

    Used for Fear & Greed, risk levels, etc.
    """

    # Mapping of value ranges/keys to emoji
    emoji_map: dict[str, str] = {}

    def format_state(self, value: str) -> str:
        """Format status with emoji.

        Args:
            value: Status text

        Returns:
            Emoji + status text
        """
        emoji = self.emoji_map.get(value.lower(), "")
        if emoji:
            return f"{emoji} {value}"
        return value
