"""Royal Caribbean integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RCCLClient, RCCLCredentials
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_APP_KEY,
    CONF_SCAN_INTERVAL,
    CONF_VDS_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import RCCLDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Royal Caribbean from a config entry."""

    credentials = RCCLCredentials(
        access_token=entry.data[CONF_ACCESS_TOKEN],
        account_id=entry.data[CONF_ACCOUNT_ID],
        app_key=entry.data[CONF_APP_KEY],
        vds_id=entry.data.get(CONF_VDS_ID) or None,
    )
    client = RCCLClient(async_get_clientsession(hass), credentials)
    interval = timedelta(
        minutes=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    coordinator = RCCLDataUpdateCoordinator(
        hass,
        client,
        update_interval=interval,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        entry.runtime_data = None
    return unload_ok
