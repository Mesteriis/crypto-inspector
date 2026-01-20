"""Composite sensor type for complex grouped data.

Provides sensors that combine multiple related values
into a single sensor with rich attributes.

Used for:
- Smart summaries (pulse, health, action, outlook)
- Investor status (multiple metrics in one)
- Market data (fear_greed, dominance, derivatives)
"""

from typing import Any

from service.ha.core.base import BaseSensor


class CompositeSensor(BaseSensor):
    """Sensor for composite/grouped data.

    Stores primary state value with multiple related attributes.
    Used for complex data that doesn't fit simple scalar or dict patterns.

    Example:
        state: "Bullish"
        attributes:
            confidence: 85
            reason: "Strong buying pressure"
            sentiment_ru: "Бычий"
    """

    # Define which attribute is the primary state
    primary_attribute: str = "state"

    # Define required attributes (for validation)
    required_attributes: list[str] = []

    def validate(self, data: Any) -> dict:
        """Validate composite data.

        Args:
            data: Dict with state and attributes

        Returns:
            Validated data dict

        Raises:
            ValueError: If required attributes missing
        """
        if data is None:
            return {self.primary_attribute: "unknown"}

        if not isinstance(data, dict):
            # If single value, treat as primary state
            return {self.primary_attribute: data}

        # Check required attributes
        for attr in self.required_attributes:
            if attr not in data:
                raise ValueError(f"Missing required attribute: {attr}")

        return data

    def format_state(self, value: dict) -> str:
        """Extract primary state from composite data.

        Args:
            value: Validated composite dict

        Returns:
            Primary state as string
        """
        state = value.get(self.primary_attribute, "unknown")
        return str(state)

    async def publish(self, value: Any, attributes: dict | None = None) -> bool:
        """Publish composite sensor.

        State is the primary value, all other data goes to attributes.

        Args:
            value: Composite data dict
            attributes: Optional additional attributes

        Returns:
            True if published successfully
        """
        validated = self.validate(value)
        self._cached_value = validated

        # Extract state
        state = self.format_state(validated)

        # Build attributes from remaining data
        attrs = {k: v for k, v in validated.items() if k != self.primary_attribute}

        # Merge with additional attributes
        if attributes:
            attrs.update(attributes)

        return await self.publisher.publish_sensor(
            self.config.sensor_id,
            state,
            attrs,
        )


class BilingualCompositeSensor(CompositeSensor):
    """Composite sensor with English/Russian state variants.

    Stores both language versions in attributes.
    State is the language-appropriate version.
    """

    # Attribute names for each language
    state_en_attr: str = "state_en"
    state_ru_attr: str = "state_ru"

    async def publish(
        self,
        value: Any,
        attributes: dict | None = None,
        language: str = "ru",
    ) -> bool:
        """Publish with language selection.

        Args:
            value: Composite data with state_en and state_ru
            attributes: Optional additional attributes
            language: 'en' or 'ru' for primary state

        Returns:
            True if published successfully
        """
        validated = self.validate(value)
        self._cached_value = validated

        # Get language-appropriate state
        if language == "ru" and self.state_ru_attr in validated:
            state = validated[self.state_ru_attr]
        elif self.state_en_attr in validated:
            state = validated[self.state_en_attr]
        else:
            state = validated.get(self.primary_attribute, "unknown")

        # Include both language versions in attributes
        attrs = validated.copy()
        if attributes:
            attrs.update(attributes)

        return await self.publisher.publish_sensor(
            self.config.sensor_id,
            str(state),
            attrs,
        )


class MarketPulseSensor(CompositeSensor):
    """Specialized composite for market pulse/summary.

    Includes confidence score and reasoning.
    """

    primary_attribute: str = "pulse"
    required_attributes: list[str] = ["pulse"]

    def format_state(self, value: dict) -> str:
        """Format pulse with optional confidence.

        Args:
            value: Pulse data

        Returns:
            Formatted state like "Bullish (85%)"
        """
        pulse = value.get("pulse", "unknown")
        confidence = value.get("confidence")

        if confidence is not None:
            return f"{pulse} ({confidence}%)"
        return str(pulse)


class InvestorStatusSensor(CompositeSensor):
    """Specialized composite for investor status.

    Groups all investor-related metrics.
    """

    primary_attribute: str = "do_nothing_ok"

    def format_state(self, value: dict) -> str:
        """Format investor status.

        Args:
            value: Investor status data

        Returns:
            Yes/No based on do_nothing_ok
        """
        ok = value.get("do_nothing_ok", False)
        return "Yes" if ok else "No"


class SmartSummarySensor(CompositeSensor):
    """Specialized composite for smart summary data.

    Combines multiple summary aspects into one sensor.
    """

    primary_attribute: str = "summary"

    async def publish(self, value: Any, attributes: dict | None = None) -> bool:
        """Publish smart summary with all components.

        Args:
            value: Summary data with pulse, health, action, outlook
            attributes: Optional additional attributes

        Returns:
            True if published successfully
        """
        validated = self.validate(value)
        self._cached_value = validated

        # Create concise summary state
        parts = []
        if "pulse" in validated:
            parts.append(f"Pulse: {validated['pulse']}")
        if "action" in validated:
            parts.append(f"Action: {validated['action']}")

        state = " | ".join(parts) if parts else "No data"

        attrs = validated.copy()
        if attributes:
            attrs.update(attributes)

        return await self.publisher.publish_sensor(
            self.config.sensor_id,
            state,
            attrs,
        )
