"""Config flow for the Royal Caribbean integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RCCLApiError, RCCLAuthenticationError, RCCLClient, RCCLCredentials
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_APP_KEY,
    CONF_SCAN_INTERVAL,
    CONF_VDS_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


class CannotConnect(Exception):
    """Raised when the config flow cannot connect."""


class InvalidAuth(Exception):
    """Raised when configured credentials are rejected."""


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Required(CONF_ACCOUNT_ID): str,
        vol.Required(CONF_APP_KEY): str,
        vol.Optional(CONF_VDS_ID): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate user input by calling the RCCL account API."""

    credentials = RCCLCredentials(
        access_token=data[CONF_ACCESS_TOKEN],
        account_id=data[CONF_ACCOUNT_ID],
        app_key=data[CONF_APP_KEY],
        vds_id=data.get(CONF_VDS_ID) or None,
    )
    client = RCCLClient(async_get_clientsession(hass), credentials)

    try:
        await client.async_get_account()
    except RCCLAuthenticationError as err:
        raise InvalidAuth from err
    except RCCLApiError as err:
        raise CannotConnect from err

    return {"title": "Royal Caribbean"}


class RCCLConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Royal Caribbean config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_ACCOUNT_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
