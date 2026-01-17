"""Crypto sensors for Home Assistant MQTT Discovery.

This module registers crypto-related sensors that Home Assistant
will automatically discover when the add-on starts.

Sensors use dictionary format to support multiple trading pairs:
- sensor.crypto_inspect_prices: {"BTC/USDT": 100000, "ETH/USDT": 3500}
- sensor.crypto_inspect_changes: {"BTC/USDT": 2.5, "ETH/USDT": -1.2}
"""

import json
import logging
import os
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


def get_symbols() -> list[str]:
    """Get trading symbols from environment."""
    symbols_env = os.environ.get("HA_SYMBOLS", "BTC/USDT,ETH/USDT")
    return [s.strip() for s in symbols_env.split(",") if s.strip()]


class CryptoSensorsManager:
    """
    Manages crypto sensors for Home Assistant.

    Creates aggregated sensors that contain data for all trading pairs
    in dictionary format, making it easy to use in HA templates.
    """

    DEVICE_ID = "crypto_inspect"
    DEVICE_NAME = "Crypto Inspect"

    # Sensor definitions
    SENSORS = {
        "prices": {
            "name": "Crypto Prices",
            "icon": "mdi:currency-usd",
            "unit": "USDT",
        },
        "changes_24h": {
            "name": "Crypto 24h Changes",
            "icon": "mdi:percent",
            "unit": "%",
        },
        "volumes_24h": {
            "name": "Crypto 24h Volumes",
            "icon": "mdi:chart-bar",
            "unit": "USDT",
        },
        "highs_24h": {
            "name": "Crypto 24h Highs",
            "icon": "mdi:arrow-up-bold",
            "unit": "USDT",
        },
        "lows_24h": {
            "name": "Crypto 24h Lows",
            "icon": "mdi:arrow-down-bold",
            "unit": "USDT",
        },
        "sync_status": {
            "name": "Sync Status",
            "icon": "mdi:sync",
            "entity_category": "diagnostic",
        },
        "last_sync": {
            "name": "Last Sync",
            "icon": "mdi:clock-outline",
            "device_class": "timestamp",
            "entity_category": "diagnostic",
        },
        "candles_count": {
            "name": "Total Candles",
            "icon": "mdi:database",
            "unit": "candles",
            "entity_category": "diagnostic",
        },
    }

    def __init__(self, mqtt_client=None):
        self._mqtt = mqtt_client
        self._prices: dict[str, str] = {}
        self._changes: dict[str, str] = {}
        self._volumes: dict[str, str] = {}
        self._highs: dict[str, str] = {}
        self._lows: dict[str, str] = {}

    @property
    def device_info(self) -> dict:
        """Device info for MQTT Discovery."""
        return {
            "identifiers": [self.DEVICE_ID],
            "name": self.DEVICE_NAME,
            "model": "Crypto Data Collector",
            "manufacturer": "Crypto Inspect Add-on",
            "sw_version": "0.1.0",
        }

    def _get_discovery_topic(self, sensor_id: str) -> str:
        """Get MQTT discovery config topic."""
        return f"homeassistant/sensor/{self.DEVICE_ID}/{sensor_id}/config"

    def _get_state_topic(self, sensor_id: str) -> str:
        """Get MQTT state topic."""
        return f"{self.DEVICE_ID}/{sensor_id}/state"

    def _get_attributes_topic(self, sensor_id: str) -> str:
        """Get MQTT attributes topic."""
        return f"{self.DEVICE_ID}/{sensor_id}/attributes"

    async def register_sensors(self) -> int:
        """
        Register all sensors via MQTT Discovery.

        Returns:
            Number of sensors registered.
        """
        if not self._mqtt:
            logger.warning("MQTT client not configured, skipping sensor registration")
            return 0

        count = 0
        symbols = get_symbols()

        for sensor_id, sensor_def in self.SENSORS.items():
            config = {
                "name": sensor_def["name"],
                "unique_id": f"{self.DEVICE_ID}_{sensor_id}",
                "state_topic": self._get_state_topic(sensor_id),
                "json_attributes_topic": self._get_attributes_topic(sensor_id),
                "device": self.device_info,
            }

            if "icon" in sensor_def:
                config["icon"] = sensor_def["icon"]
            if "unit" in sensor_def:
                config["unit_of_measurement"] = sensor_def["unit"]
            if "device_class" in sensor_def:
                config["device_class"] = sensor_def["device_class"]
            if "entity_category" in sensor_def:
                config["entity_category"] = sensor_def["entity_category"]

            topic = self._get_discovery_topic(sensor_id)

            try:
                await self._mqtt.publish(topic, json.dumps(config), retain=True)
                count += 1
                logger.info(f"Registered sensor: {sensor_def['name']}")
            except Exception as e:
                logger.error(f"Failed to register sensor {sensor_id}: {e}")

        # Publish initial attributes with symbol list
        await self._publish_attributes("prices", {"symbols": symbols, "count": len(symbols)})

        logger.info(f"Registered {count} MQTT sensors, tracking {len(symbols)} symbols")
        return count

    async def _publish_state(self, sensor_id: str, state: str | dict) -> bool:
        """Publish sensor state."""
        if not self._mqtt:
            return False

        topic = self._get_state_topic(sensor_id)
        payload = json.dumps(state) if isinstance(state, dict) else str(state)

        try:
            await self._mqtt.publish(topic, payload)
            return True
        except Exception as e:
            logger.error(f"Failed to publish state for {sensor_id}: {e}")
            return False

    async def _publish_attributes(self, sensor_id: str, attributes: dict) -> bool:
        """Publish sensor attributes."""
        if not self._mqtt:
            return False

        topic = self._get_attributes_topic(sensor_id)
        try:
            await self._mqtt.publish(topic, json.dumps(attributes))
            return True
        except Exception as e:
            logger.error(f"Failed to publish attributes for {sensor_id}: {e}")
            return False

    async def update_price(
        self,
        symbol: str,
        price: Decimal | float,
        change_24h: float | None = None,
        volume_24h: Decimal | float | None = None,
        high_24h: Decimal | float | None = None,
        low_24h: Decimal | float | None = None,
    ) -> None:
        """
        Update price data for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            price: Current price
            change_24h: 24h price change percentage
            volume_24h: 24h trading volume
            high_24h: 24h high price
            low_24h: 24h low price
        """
        # Update internal state
        self._prices[symbol] = str(price)

        if change_24h is not None:
            self._changes[symbol] = f"{change_24h:.2f}"
        if volume_24h is not None:
            self._volumes[symbol] = str(volume_24h)
        if high_24h is not None:
            self._highs[symbol] = str(high_24h)
        if low_24h is not None:
            self._lows[symbol] = str(low_24h)

        # Publish all price data
        await self._publish_state("prices", self._prices)
        await self._publish_attributes(
            "prices",
            {
                "symbols": list(self._prices.keys()),
                "count": len(self._prices),
                "last_updated": datetime.utcnow().isoformat(),
            },
        )

        # Publish other metrics if we have data
        if self._changes:
            await self._publish_state("changes_24h", self._changes)
        if self._volumes:
            await self._publish_state("volumes_24h", self._volumes)
        if self._highs:
            await self._publish_state("highs_24h", self._highs)
        if self._lows:
            await self._publish_state("lows_24h", self._lows)

    async def update_all_prices(self, prices_data: dict[str, dict]) -> None:
        """
        Update prices for all symbols at once.

        Args:
            prices_data: Dict of {symbol: {price, change_24h, volume_24h, high_24h, low_24h}}
        """
        for symbol, data in prices_data.items():
            self._prices[symbol] = str(data.get("price", 0))
            if "change_24h" in data:
                self._changes[symbol] = f"{data['change_24h']:.2f}"
            if "volume_24h" in data:
                self._volumes[symbol] = str(data["volume_24h"])
            if "high_24h" in data:
                self._highs[symbol] = str(data["high_24h"])
            if "low_24h" in data:
                self._lows[symbol] = str(data["low_24h"])

        # Publish all states
        await self._publish_state("prices", self._prices)
        await self._publish_state("changes_24h", self._changes)
        await self._publish_state("volumes_24h", self._volumes)
        await self._publish_state("highs_24h", self._highs)
        await self._publish_state("lows_24h", self._lows)

        await self._publish_attributes(
            "prices",
            {
                "symbols": list(self._prices.keys()),
                "count": len(self._prices),
                "last_updated": datetime.utcnow().isoformat(),
            },
        )

    async def update_sync_status(
        self,
        status: str,
        success_count: int = 0,
        failure_count: int = 0,
        total_candles: int | None = None,
    ) -> None:
        """
        Update sync status sensors.

        Args:
            status: Current status ('running', 'completed', 'error')
            success_count: Number of successful operations
            failure_count: Number of failed operations
            total_candles: Total candles in database
        """
        # Sync status
        await self._publish_state("sync_status", status)
        await self._publish_attributes(
            "sync_status",
            {
                "success_count": success_count,
                "failure_count": failure_count,
                "total_operations": success_count + failure_count,
                "success_rate": (
                    f"{(success_count / (success_count + failure_count) * 100):.1f}%"
                    if (success_count + failure_count) > 0
                    else "N/A"
                ),
            },
        )

        # Last sync timestamp
        await self._publish_state("last_sync", datetime.utcnow().isoformat())

        # Total candles
        if total_candles is not None:
            await self._publish_state("candles_count", str(total_candles))

    async def remove_sensors(self) -> None:
        """Remove all sensors by publishing empty configs."""
        if not self._mqtt:
            return

        for sensor_id in self.SENSORS:
            topic = self._get_discovery_topic(sensor_id)
            try:
                await self._mqtt.publish(topic, "", retain=True)
            except Exception as e:
                logger.error(f"Failed to remove sensor {sensor_id}: {e}")

        logger.info("Removed all MQTT sensors")


# Global instance
_sensors_manager: CryptoSensorsManager | None = None


def get_sensors_manager(mqtt_client=None) -> CryptoSensorsManager:
    """Get or create sensors manager."""
    global _sensors_manager
    if _sensors_manager is None or mqtt_client is not None:
        _sensors_manager = CryptoSensorsManager(mqtt_client)
    return _sensors_manager
