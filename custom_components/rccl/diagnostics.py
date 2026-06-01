"""Diagnostics support for the Royal Caribbean integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_APP_KEY,
    CONF_ID_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_USERNAME,
    CONF_VDS_ID,
    DOMAIN,
)

TO_REDACT = {
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_APP_KEY,
    CONF_ID_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_USERNAME,
    CONF_VDS_ID,
    "id_token",
    "refresh_token",
    "username",
    "password",
    "access-token",
    "account-id",
    "appkey",
    "vds-id",
    "bookingId",
    "masterBookingId",
    "passengerId",
    "firstName",
    "lastName",
    "email",
    "birthdate",
    "stateroomNumber",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = getattr(entry, "runtime_data", None) or hass.data[DOMAIN].get(
        entry.entry_id
    )
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "data": async_redact_data(coordinator.data if coordinator else {}, TO_REDACT),
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return device diagnostics."""

    return await async_get_config_entry_diagnostics(hass, entry)
