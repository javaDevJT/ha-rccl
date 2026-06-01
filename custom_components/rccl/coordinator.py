"""Data coordinator for the Royal Caribbean integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
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
