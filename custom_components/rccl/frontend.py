"""Frontend support for the Royal Caribbean integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import CookieJar
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import RCCLApiError, RCCLAuthenticationError, RCCLClient
from .const import CONF_APP_KEY, CONF_PASSWORD, CONF_USERNAME, DEFAULT_APP_KEY, DOMAIN

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
async def websocket_club_royale_sailings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return normalized Club Royale sailings for Lovelace cards."""

    requested_entry_id = msg.get("entry_id")
    config_entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if not requested_entry_id or entry.entry_id == requested_entry_id
    ]
    if requested_entry_id and not config_entries:
        connection.send_error(msg["id"], "not_found", "RCCL entry not found")
        return

    entries = []
    sailings = []
    errors = []

    for entry in config_entries:
        if not entry.data.get(CONF_USERNAME) or not entry.data.get(CONF_PASSWORD):
            error = "RCCL username/password is required for Club Royale"
            entries.append({"entry_id": entry.entry_id, "sailings": [], "error": error})
            errors.append({"entry_id": entry.entry_id, "message": error})
            continue

        session = async_create_clientsession(hass, cookie_jar=CookieJar())
        try:
            entry_sailings = await RCCLClient.async_fetch_club_royale_sailings(
                session,
                entry.data[CONF_USERNAME],
                entry.data[CONF_PASSWORD],
                app_key=entry.data.get(CONF_APP_KEY, DEFAULT_APP_KEY),
            )
        except RCCLAuthenticationError as err:
            entry_sailings = []
            error = f"Club Royale login failed: {err}"
            errors.append({"entry_id": entry.entry_id, "message": error})
        except RCCLApiError as err:
            entry_sailings = []
            error = f"Club Royale unavailable: {err}"
            errors.append({"entry_id": entry.entry_id, "message": error})
        finally:
            await session.close()

        entry_result = {"entry_id": entry.entry_id, "sailings": entry_sailings}
        matching_error = next(
            (item["message"] for item in errors if item["entry_id"] == entry.entry_id),
            None,
        )
        if matching_error:
            entry_result["error"] = matching_error
        entries.append(entry_result)
        sailings.extend(
            {**sailing, "entry_id": entry.entry_id} for sailing in entry_sailings
        )

    connection.send_result(
        msg["id"],
        {"entries": entries, "sailings": sailings, "errors": errors},
    )
