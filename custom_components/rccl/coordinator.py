"""Data coordinator for the Royal Caribbean integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RCCLApiError, RCCLAuthenticationError, RCCLClient, club_royale_sailings
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
        client: RCCLClient,
        loyalty_id: str,
        *,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_club_royale",
            update_interval=update_interval,
            always_update=False,
        )
        self.client = client
        self._loyalty_id = loyalty_id

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch fresh Club Royale offer sailings."""

        try:
            club_royale = await self.client.async_get_club_royale_data_for_loyalty_id(
                self._loyalty_id
            )
            sailings = club_royale_sailings({"club_royale": club_royale})
        except RCCLAuthenticationError as err:
            raise UpdateFailed(f"Club Royale login failed: {err}") from err
        except RCCLApiError as err:
            raise UpdateFailed(str(err)) from err

        return {"sailings": sailings}
