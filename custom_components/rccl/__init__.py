"""Royal Caribbean integration for Home Assistant."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    RCCLApiError,
    RCCLAuthenticationError,
    RCCLClient,
    RCCLCredentials,
    RCCLUrllibSession,
    credentials_from_stored_data,
)
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_APP_KEY,
    CONF_AUTH_REFERER,
    CONF_AUTHORIZE_REFERER,
    CONF_CLUB_ROYALE_LOYALTY_ID,
    CONF_ENTRY_TYPE,
    CONF_ID_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN_EXPIRES_AT,
    CONF_USERNAME,
    CONF_VDS_ID,
    CLUB_ROYALE_PLATFORMS,
    DEFAULT_APP_KEY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WEB_BASE_URL,
    DOMAIN,
    ENTRY_TYPE_CLUB_ROYALE,
    PLATFORMS,
)
from .coordinator import RCCLClubRoyaleDataUpdateCoordinator, RCCLDataUpdateCoordinator
from .frontend import async_setup_frontend

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, object]) -> bool:
    """Set up integration-level RCCL frontend resources."""

    await async_setup_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Royal Caribbean from a config entry."""

    await async_setup_frontend(hass)

    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_CLUB_ROYALE:
        return await _async_setup_club_royale_entry(hass, entry)

    session = async_get_clientsession(hass)
    transient_login_failure = False
    try:
        credentials = await _credentials_from_entry(hass, session, entry)
    except RCCLAuthenticationError as err:
        if _is_transient_login_token_error(err) and entry.data.get(CONF_ACCOUNT_ID):
            _LOGGER.warning(
                "RCCL did not return a login token during setup; using stored "
                "entry credentials and retrying after setup"
            )
            credentials = _fallback_credentials_from_entry(entry)
            transient_login_failure = True
        else:
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

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed as err:
        if not _is_transient_login_token_error(err):
            hass.data[DOMAIN].pop(entry.entry_id, None)
            entry.runtime_data = None
            raise
        _LOGGER.warning(
            "RCCL did not return a login token during initial refresh; setup "
            "will continue and retry in background"
        )
        transient_login_failure = True
    except Exception:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        entry.runtime_data = None
        raise

    await hass.config_entries.async_forward_entry_setups(entry, _platforms_for_entry(entry))
    if transient_login_failure:
        refresh_task = hass.async_create_task(_async_refresh_account_later(coordinator))
        entry.async_on_unload(refresh_task.cancel)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, _platforms_for_entry(entry)
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        entry.runtime_data = None
    return unload_ok


async def _async_setup_club_royale_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up a standalone Club Royale offers config entry."""

    if not entry.data.get(CONF_USERNAME) or not entry.data.get(CONF_PASSWORD):
        raise ConfigEntryAuthFailed("Club Royale username/password is required")
    if not entry.data.get(CONF_CLUB_ROYALE_LOYALTY_ID):
        raise ConfigEntryNotReady("Club Royale loyalty id is required")

    interval = timedelta(
        minutes=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    session = RCCLUrllibSession()
    credentials = _club_royale_credentials_from_entry(entry)
    client = RCCLClient(session, credentials)
    coordinator = RCCLClubRoyaleDataUpdateCoordinator(
        hass,
        client,
        str(entry.data[CONF_CLUB_ROYALE_LOYALTY_ID]),
        update_interval=interval,
    )

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, _platforms_for_entry(entry))
    refresh_task = hass.async_create_task(_async_refresh_club_royale_later(coordinator))
    entry.async_on_unload(refresh_task.cancel)
    return True


async def _async_refresh_club_royale_later(
    coordinator: RCCLClubRoyaleDataUpdateCoordinator,
) -> None:
    """Refresh Club Royale data without blocking config-entry setup."""

    try:
        await coordinator.async_request_refresh()
    except Exception as err:  # noqa: BLE001 - keep setup alive for visible entities.
        _LOGGER.debug("Initial Club Royale refresh failed: %s", err)


async def _async_refresh_account_later(coordinator: RCCLDataUpdateCoordinator) -> None:
    """Refresh RCCL account data without blocking config-entry reload."""

    try:
        await coordinator.async_request_refresh()
    except Exception as err:  # noqa: BLE001 - keep setup alive for visible entities.
        _LOGGER.debug("Deferred RCCL account refresh failed: %s", err)


def _platforms_for_entry(entry: ConfigEntry) -> list[str]:
    """Return Home Assistant platforms for this RCCL entry type."""

    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_CLUB_ROYALE:
        return CLUB_ROYALE_PLATFORMS
    return PLATFORMS


def _club_royale_credentials_from_entry(entry: ConfigEntry) -> RCCLCredentials:
    """Build Club Royale credentials while supporting alpha 11/12 entries."""

    if entry.data.get(CONF_ACCESS_TOKEN) and entry.data.get(CONF_ACCOUNT_ID):
        credentials = credentials_from_stored_data(dict(entry.data))
        if credentials.auth_referer and credentials.authorize_referer:
            return credentials
        return replace(
            credentials,
            auth_referer=f"{DEFAULT_WEB_BASE_URL}/club-royale/signin",
            authorize_referer=f"{DEFAULT_WEB_BASE_URL}/",
        )

    return RCCLCredentials(
        access_token="",
        account_id=str(entry.data.get(CONF_ACCOUNT_ID) or entry.entry_id),
        app_key=entry.data.get(CONF_APP_KEY, DEFAULT_APP_KEY),
        vds_id=entry.data.get(CONF_VDS_ID) or entry.data.get(CONF_ACCOUNT_ID),
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        auth_referer=entry.data.get(CONF_AUTH_REFERER)
        or f"{DEFAULT_WEB_BASE_URL}/club-royale/signin",
        authorize_referer=entry.data.get(CONF_AUTHORIZE_REFERER)
        or f"{DEFAULT_WEB_BASE_URL}/",
    )


def _is_transient_login_token_error(err: BaseException) -> bool:
    """Return true for RCCL's intermittent empty OpenAM login response."""

    return "did not return a login token" in str(err)


def _fallback_credentials_from_entry(entry: ConfigEntry) -> RCCLCredentials:
    """Build best-effort credentials from a stored account config entry."""

    return RCCLCredentials(
        access_token=str(entry.data.get(CONF_ACCESS_TOKEN) or ""),
        account_id=str(entry.data[CONF_ACCOUNT_ID]),
        app_key=entry.data.get(CONF_APP_KEY, DEFAULT_APP_KEY),
        vds_id=entry.data.get(CONF_VDS_ID) or entry.data.get(CONF_ACCOUNT_ID),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        id_token=entry.data.get(CONF_ID_TOKEN),
        expires_at=entry.data.get(CONF_TOKEN_EXPIRES_AT),
        username=entry.data.get(CONF_USERNAME),
        password=entry.data.get(CONF_PASSWORD),
    )


async def _credentials_from_entry(
    hass: HomeAssistant,
    session: object,
    entry: ConfigEntry,
) -> RCCLCredentials:
    """Build fresh RCCL credentials from a config entry."""

    if entry.data.get(CONF_ACCESS_TOKEN) and entry.data.get(CONF_ACCOUNT_ID):
        return credentials_from_stored_data(dict(entry.data))

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
