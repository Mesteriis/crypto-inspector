"""Crypto sensors for Home Assistant MQTT Discovery.

This module registers crypto-related sensors that Home Assistant
will automatically discover when the add-on starts.
"""

import logging
import os
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


# Sensor definitions for each trading pair
PRICE_SENSORS = [
    {
        "suffix": "price",
        "name_template": "{symbol} Price",
        "unit": "USDT",
        "device_class": "monetary",
        "state_class": "measurement",
        "icon": "mdi:currency-usd",
    },
    {
        "suffix": "change_24h",
        "name_template": "{symbol} 24h Change",
        "unit": "%",
        "state_class": "measurement",
        "icon": "mdi:percent",
    },
    {
        "suffix": "volume_24h",
        "name_template": "{symbol} 24h Volume",
        "unit": "USDT",
        "state_class": "measurement",
        "icon": "mdi:chart-bar",
    },
    {
        "suffix": "high_24h",
        "name_template": "{symbol} 24h High",
        "unit": "USDT",
        "device_class": "monetary",
        "icon": "mdi:arrow-up-bold",
    },
    {
        "suffix": "low_24h",
        "name_template": "{symbol} 24h Low",
        "unit": "USDT",
        "device_class": "monetary",
        "icon": "mdi:arrow-down-bold",
    },
]

# Status sensors
STATUS_SENSORS = [
    {
        "object_id": "sync_status",
        "name": "Sync Status",
        "icon": "mdi:sync",
        "entity_category": "diagnostic",
    },
    {
        "object_id": "last_sync",
        "name": "Last Sync",
        "device_class": "timestamp",
        "entity_category": "diagnostic",
    },
    {
        "object_id": "total_candles",
        "name": "Total Candles Stored",
        "unit": "candles",
        "state_class": "total",
        "icon": "mdi:database",
        "entity_category": "diagnostic",
    },
    {
        "object_id": "sync_success_rate",
        "name": "Sync Success Rate",
        "unit": "%",
        "state_class": "measurement",
        "icon": "mdi:check-circle",
        "entity_category": "diagnostic",
    },
]


def get_symbols() -> list[str]:
    """Get trading symbols from environment."""
    symbols_env = os.environ.get("HA_SYMBOLS", "BTC/USDT,ETH/USDT")
    return [s.strip() for s in symbols_env.split(",") if s.strip()]


def symbol_to_object_id(symbol: str) -> str:
    """Convert symbol to valid object_id (e.g., 'BTC/USDT' -> 'btc_usdt')."""
    return symbol.lower().replace("/", "_").replace("-", "_")


def get_crypto_icon(symbol: str) -> str:
    """Get appropriate icon for a crypto symbol."""
    base = symbol.split("/")[0].upper()
    icons = {
        "BTC": "mdi:bitcoin",
        "ETH": "mdi:ethereum",
        "XRP": "mdi:currency-xrp",
        "LTC": "mdi:litecoin",
        "DOGE": "mdi:dog",
        "SOL": "mdi:sun-wireless",
        "ADA": "mdi:alpha-a-circle",
        "DOT": "mdi:dots-horizontal-circle",
        "MATIC": "mdi:polygon",
        "LINK": "mdi:link-variant",
    }
    return icons.get(base, "mdi:currency-usd")


async def register_all_sensors(mqtt_discovery) -> int:
    """
    Register all crypto sensors via MQTT Discovery.

    Args:
        mqtt_discovery: MQTTDiscoveryClient instance

    Returns:
        Number of sensors registered
    """
    if mqtt_discovery is None:
        logger.warning("MQTT Discovery not available")
        return 0

    count = 0
    symbols = get_symbols()

    # Register price sensors for each symbol
    for symbol in symbols:
        object_id_base = symbol_to_object_id(symbol)
        base_icon = get_crypto_icon(symbol)

        for sensor_def in PRICE_SENSORS:
            object_id = f"{object_id_base}_{sensor_def['suffix']}"
            name = sensor_def["name_template"].format(symbol=symbol)

            success = await mqtt_discovery.register_sensor(
                object_id=object_id,
                name=name,
                unit=sensor_def.get("unit"),
                device_class=sensor_def.get("device_class"),
                state_class=sensor_def.get("state_class"),
                icon=sensor_def.get("icon", base_icon),
            )
            if success:
                count += 1

    # Register status sensors
    for sensor_def in STATUS_SENSORS:
        success = await mqtt_discovery.register_sensor(
            object_id=sensor_def["object_id"],
            name=sensor_def["name"],
            unit=sensor_def.get("unit"),
            device_class=sensor_def.get("device_class"),
            state_class=sensor_def.get("state_class"),
            icon=sensor_def.get("icon"),
            entity_category=sensor_def.get("entity_category"),
        )
        if success:
            count += 1

    logger.info(f"Registered {count} MQTT sensors for Home Assistant")
    return count


async def update_price_sensor(
    mqtt_discovery,
    symbol: str,
    close_price: Decimal,
    high_24h: Decimal | None = None,
    low_24h: Decimal | None = None,
    volume_24h: Decimal | None = None,
    change_24h: float | None = None,
) -> None:
    """
    Update price sensors for a symbol.

    Args:
        mqtt_discovery: MQTTDiscoveryClient instance
        symbol: Trading pair symbol
        close_price: Current/close price
        high_24h: 24h high price
        low_24h: 24h low price
        volume_24h: 24h trading volume
        change_24h: 24h price change percentage
    """
    if mqtt_discovery is None:
        return

    object_id_base = symbol_to_object_id(symbol)

    # Update main price
    await mqtt_discovery.update_state(f"{object_id_base}_price", str(close_price))

    # Update attributes with additional info
    attributes = {
        "symbol": symbol,
        "last_updated": datetime.utcnow().isoformat(),
    }
    if high_24h:
        attributes["high_24h"] = str(high_24h)
    if low_24h:
        attributes["low_24h"] = str(low_24h)

    await mqtt_discovery.update_attributes(f"{object_id_base}_price", attributes)

    # Update other sensors if data available
    if change_24h is not None:
        await mqtt_discovery.update_state(f"{object_id_base}_change_24h", f"{change_24h:.2f}")

    if volume_24h is not None:
        await mqtt_discovery.update_state(f"{object_id_base}_volume_24h", str(volume_24h))

    if high_24h is not None:
        await mqtt_discovery.update_state(f"{object_id_base}_high_24h", str(high_24h))

    if low_24h is not None:
        await mqtt_discovery.update_state(f"{object_id_base}_low_24h", str(low_24h))


async def update_sync_status(
    mqtt_discovery,
    status: str,
    success_count: int,
    failure_count: int,
    total_candles: int | None = None,
) -> None:
    """
    Update sync status sensors.

    Args:
        mqtt_discovery: MQTTDiscoveryClient instance
        status: Current status ('running', 'completed', 'error')
        success_count: Number of successful fetches
        failure_count: Number of failed fetches
        total_candles: Total candles in database
    """
    if mqtt_discovery is None:
        return

    # Sync status
    await mqtt_discovery.update_state("sync_status", status)

    # Last sync time
    await mqtt_discovery.update_state("last_sync", datetime.utcnow().isoformat())

    # Success rate
    total = success_count + failure_count
    if total > 0:
        rate = (success_count / total) * 100
        await mqtt_discovery.update_state("sync_success_rate", f"{rate:.1f}")

    # Total candles
    if total_candles is not None:
        await mqtt_discovery.update_state("total_candles", str(total_candles))

    # Attributes for sync status
    await mqtt_discovery.update_attributes(
        "sync_status",
        {
            "success_count": success_count,
            "failure_count": failure_count,
            "total_fetches": total,
            "last_run": datetime.utcnow().isoformat(),
        },
    )
