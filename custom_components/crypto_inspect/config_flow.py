"""Config flow for Crypto Inspect integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_HEALTH,
    CONF_HOST,
    CONF_LANGUAGE,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_LANGUAGE,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(["ru", "en"]),
    }
)


async def validate_connection(
    hass: HomeAssistant,
    host: str,
    port: int,
) -> dict[str, Any]:
    """Validate the connection to Crypto Inspect API."""
    session = async_get_clientsession(hass)
    url = f"http://{host}:{port}{API_HEALTH}"

    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                raise ConnectionError(f"API returned status {response.status}")

            data = await response.json()
            return {
                "title": f"Crypto Inspect ({host}:{port})",
                "version": data.get("version", "unknown"),
            }
    except aiohttp.ClientError as err:
        raise ConnectionError(f"Cannot connect to {url}: {err}") from err
    except Exception as err:
        raise ConnectionError(f"Unexpected error: {err}") from err


class CryptoInspectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Crypto Inspect."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            # Check for existing entry with same host:port
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            try:
                info = await validate_connection(self.hass, host, port)
            except ConnectionError as err:
                _LOGGER.error("Connection validation failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during validation")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_LANGUAGE: user_input[CONF_LANGUAGE],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CryptoInspectOptionsFlow:
        """Get the options flow for this handler."""
        return CryptoInspectOptionsFlow(config_entry)


class CryptoInspectOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Crypto Inspect."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                    vol.Required(
                        CONF_LANGUAGE,
                        default=self.config_entry.data.get(
                            CONF_LANGUAGE, DEFAULT_LANGUAGE
                        ),
                    ): vol.In(["ru", "en"]),
                }
            ),
        )
