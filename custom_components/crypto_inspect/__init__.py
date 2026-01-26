"""Crypto Inspect integration for Home Assistant.

Unified sensor management for cryptocurrency market intelligence.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import CryptoInspectCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Crypto Inspect from YAML configuration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Crypto Inspect from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    session = async_get_clientsession(hass)

    coordinator = CryptoInspectCoordinator(
        hass=hass,
        session=session,
        host=host,
        port=port,
        update_interval=update_interval,
        entry_id=entry.entry_id,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to connect to Crypto Inspect: %s", err)
        raise ConfigEntryNotReady(f"Failed to connect: {err}") from err

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info(
        "Crypto Inspect integration set up successfully: %s:%s",
        host,
        port,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Crypto Inspect integration unloaded")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
