"""Frontend support for the Royal Caribbean integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .api import club_royale_sailings
from .const import DOMAIN

STATIC_URL_PATH = "/rccl_static"
CARD_FILENAME = "club-royale-calendar-card.js"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register frontend assets and websocket commands."""

    static_path = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL_PATH, str(static_path), True)]
    )
    websocket_api.async_register_command(hass, websocket_club_royale_sailings)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rccl/club_royale_sailings",
        vol.Optional("entry_id"): str,
    }
)
@callback
def websocket_club_royale_sailings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return normalized Club Royale sailings for Lovelace cards."""

    requested_entry_id = msg.get("entry_id")
    coordinators = hass.data.get(DOMAIN, {})
    entries = []
    sailings = []

    for entry_id, coordinator in coordinators.items():
        if requested_entry_id and entry_id != requested_entry_id:
            continue
        entry_sailings = club_royale_sailings(coordinator.data or {})
        entries.append({"entry_id": entry_id, "sailings": entry_sailings})
        sailings.extend({**sailing, "entry_id": entry_id} for sailing in entry_sailings)

    if requested_entry_id and not entries:
        connection.send_error(msg["id"], "not_found", "RCCL entry not found")
        return

    connection.send_result(msg["id"], {"entries": entries, "sailings": sailings})
