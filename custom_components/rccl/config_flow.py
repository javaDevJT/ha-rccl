"""Config flow for the Royal Caribbean integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import RCCLApiError, RCCLAuthenticationError, RCCLClient, RCCLCredentials
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_APP_KEY,
    CONF_ID_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN_EXPIRES_AT,
    CONF_USERNAME,
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
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
        ),
    }
)


def _reauth_schema(username: str) -> vol.Schema:
    """Return the reauth form schema."""

    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=username): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
            ),
        }
    )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate user input by logging in and calling the RCCL account API."""

    session = async_get_clientsession(hass)

    try:
        credentials = await RCCLClient.async_login(
            session,
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
        )
        client = RCCLClient(session, credentials)
        await client.async_get_account()
    except RCCLAuthenticationError as err:
        raise InvalidAuth from err
    except RCCLApiError as err:
        raise CannotConnect from err

    return {
        "title": "Royal Caribbean",
        "unique_id": credentials.account_id,
        "data": _entry_data(data, credentials),
    }


def _entry_data(data: dict[str, Any], credentials: RCCLCredentials) -> dict[str, Any]:
    """Return config-entry data from login credentials."""

    entry_data = {
        CONF_USERNAME: data[CONF_USERNAME].strip(),
        CONF_PASSWORD: data[CONF_PASSWORD],
        CONF_ACCESS_TOKEN: credentials.access_token,
        CONF_ACCOUNT_ID: credentials.account_id,
        CONF_APP_KEY: credentials.app_key,
        CONF_VDS_ID: credentials.vds_id,
        CONF_SCAN_INTERVAL: data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    }
    if credentials.refresh_token:
        entry_data[CONF_REFRESH_TOKEN] = credentials.refresh_token
    if credentials.id_token:
        entry_data[CONF_ID_TOKEN] = credentials.id_token
    if credentials.expires_at:
        entry_data[CONF_TOKEN_EXPIRES_AT] = credentials.expires_at
    return entry_data


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
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=info["data"])

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> config_entries.ConfigFlowResult:
        """Handle a reauthentication request."""

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Ask the user for fresh RCCL credentials."""

        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            merged_input = {**entry.data, **user_input}
            try:
                info = await validate_input(self.hass, merged_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=info["data"],
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_reauth_schema(entry.data.get(CONF_USERNAME, "")),
            errors=errors,
        )
