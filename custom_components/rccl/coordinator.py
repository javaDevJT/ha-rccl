"""Data coordinator for the Royal Caribbean integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from aiohttp import CookieJar
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RCCLApiError, RCCLAuthenticationError, RCCLClient
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class RCCLDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate RCCL account polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: RCCLClient,
        *,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            always_update=False,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch fresh RCCL account data."""

        try:
            return await self.client.async_get_data()
        except RCCLAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RCCLApiError as err:
            raise UpdateFailed(str(err)) from err


class RCCLClubRoyaleDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Club Royale offer polling with an isolated web session."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        *,
        app_key: str,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_club_royale",
            update_interval=update_interval,
            always_update=False,
        )
        self._hass = hass
        self._username = username
        self._password = password
        self._app_key = app_key

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch fresh Club Royale offer sailings."""

        session = async_create_clientsession(self._hass, cookie_jar=CookieJar())
        try:
            sailings = await RCCLClient.async_fetch_club_royale_sailings(
                session,
                self._username,
                self._password,
                app_key=self._app_key,
            )
        except RCCLAuthenticationError as err:
            raise UpdateFailed(f"Club Royale login failed: {err}") from err
        except RCCLApiError as err:
            raise UpdateFailed(str(err)) from err
        finally:
            await session.close()

        return {"sailings": sailings}
