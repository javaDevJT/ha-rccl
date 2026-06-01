"""Royal Caribbean integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    DEFAULT_APP_KEY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import RCCLDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Royal Caribbean from a config entry."""

    session = async_get_clientsession(hass)
    try:
        credentials = await _credentials_from_entry(hass, session, entry)
    except RCCLAuthenticationError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except RCCLApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    client = RCCLClient(session, credentials)
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


async def _credentials_from_entry(
    hass: HomeAssistant,
    session: object,
    entry: ConfigEntry,
) -> RCCLCredentials:
    """Build fresh RCCL credentials from a config entry."""

    if entry.data.get(CONF_USERNAME) and entry.data.get(CONF_PASSWORD):
        credentials = await RCCLClient.async_login(
            session,
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            app_key=entry.data.get(CONF_APP_KEY, DEFAULT_APP_KEY),
        )
        data = {**entry.data, **_credential_updates(credentials)}
        hass.config_entries.async_update_entry(entry, data=data)
        return credentials

    return RCCLCredentials(
        access_token=entry.data[CONF_ACCESS_TOKEN],
        account_id=entry.data[CONF_ACCOUNT_ID],
        app_key=entry.data.get(CONF_APP_KEY, DEFAULT_APP_KEY),
        vds_id=entry.data.get(CONF_VDS_ID) or None,
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        id_token=entry.data.get(CONF_ID_TOKEN),
        expires_at=entry.data.get(CONF_TOKEN_EXPIRES_AT),
    )


def _credential_updates(credentials: RCCLCredentials) -> dict[str, object]:
    """Return config-entry updates from credentials."""

    updates: dict[str, object] = {
        CONF_ACCESS_TOKEN: credentials.access_token,
        CONF_ACCOUNT_ID: credentials.account_id,
        CONF_APP_KEY: credentials.app_key,
        CONF_VDS_ID: credentials.vds_id,
    }
    if credentials.refresh_token:
        updates[CONF_REFRESH_TOKEN] = credentials.refresh_token
    if credentials.id_token:
        updates[CONF_ID_TOKEN] = credentials.id_token
    if credentials.expires_at:
        updates[CONF_TOKEN_EXPIRES_AT] = credentials.expires_at
    return updates
