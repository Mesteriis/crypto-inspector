"""
API routes for Home Assistant sensor data.

Provides a single endpoint that returns all sensor data
for easy REST sensor integration.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from services.candlestick.buffer import get_candle_buffer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.get("")
async def get_all_sensors() -> dict[str, Any]:
    """
    Get all sensor data for Home Assistant.

    This endpoint provides a flat dictionary of all available sensor values
    for easy integration with HA REST sensors.

    Usage in HA configuration.yaml:
    ```yaml
    rest:
      - resource: http://localhost:9999/sensors
        scan_interval: 60
        sensor:
          - name: "Crypto Inspect Status"
            value_template: "{{ value_json.status }}"
          - name: "Crypto Buffer Size"
            value_template: "{{ value_json.buffer_size }}"
    ```
    """
    buffer = get_candle_buffer()
    buffer_stats = buffer.stats if buffer else {"buffered": 0, "flushed": 0, "errors": 0}

    return {
        "status": "online",
        "last_update": datetime.now(UTC).isoformat(),
        # Buffer stats
        "buffer_size": buffer_stats.get("current_buffer_size", 0),
        "buffered_total": buffer_stats.get("buffered", 0),
        "flushed_total": buffer_stats.get("flushed", 0),
        "errors_total": buffer_stats.get("errors", 0),
    }


@router.get("/prices")
async def get_price_sensors() -> dict[str, Any]:
    """
    Get latest prices for all tracked symbols.

    Returns dict with symbol as key, price data as value.
    """
    # TODO: Implement price cache from WebSocket data
    return {
        "status": "available",
        "prices": {},
        "last_update": datetime.now(UTC).isoformat(),
    }


@router.get("/ha-config")
async def get_ha_config_example() -> dict[str, Any]:
    """
    Get example Home Assistant configuration for REST sensors.

    Copy this YAML to your configuration.yaml
    """
    addon_url = "http://localhost:9999"

    return {
        "description": "Add this to your Home Assistant configuration.yaml",
        "yaml": f"""
# Crypto Inspect REST Sensors
rest:
  - resource: {addon_url}/sensors
    scan_interval: 60
    sensor:
      - name: "Crypto Inspect Status"
        value_template: "{{{{ value_json.status }}}}"
        icon: mdi:check-network
      - name: "Crypto Buffer Size"
        value_template: "{{{{ value_json.buffer_size }}}}"
        icon: mdi:database
        unit_of_measurement: "candles"
      - name: "Crypto Candles Flushed"
        value_template: "{{{{ value_json.flushed_total }}}}"
        icon: mdi:database-check
        unit_of_measurement: "candles"

  - resource: {addon_url}/summary/market-pulse
    scan_interval: 300
    sensor:
      - name: "Crypto Market Pulse"
        value_template: "{{{{ value_json.sentiment_ru }}}}"
        icon: mdi:pulse
        json_attributes:
          - confidence
          - reason_ru
          - factors_ru

  - resource: {addon_url}/summary/today-action
    scan_interval: 3600
    sensor:
      - name: "Crypto Today Action"
        value_template: "{{{{ value_json.action_ru }}}}"
        icon: mdi:clipboard-check
        json_attributes:
          - priority_ru
          - details_ru

  - resource: {addon_url}/investor/status
    scan_interval: 300
    sensor:
      - name: "Crypto Do Nothing OK"
        value_template: "{{{{ value_json.do_nothing_ok.state }}}}"
        icon: mdi:meditation
      - name: "Crypto Investor Phase"
        value_template: "{{{{ value_json.phase.name_ru }}}}"
        icon: mdi:chart-timeline-variant-shimmer
""",
    }
