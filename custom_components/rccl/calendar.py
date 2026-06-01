"""Calendar platform for Royal Caribbean cruises."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import cruise_events
from .const import CONF_ACCOUNT_ID, DOMAIN
from .coordinator import RCCLDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the RCCL calendar entity."""

    coordinator: RCCLDataUpdateCoordinator = (
        getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    )
    async_add_entities([RCCLCruiseCalendar(coordinator, entry.data[CONF_ACCOUNT_ID])])


class RCCLCruiseCalendar(CoordinatorEntity[RCCLDataUpdateCoordinator], CalendarEntity):
    """Read-only RCCL cruise calendar."""

    _attr_has_entity_name = True
    _attr_translation_key = "cruises"

    def __init__(self, coordinator: RCCLDataUpdateCoordinator, account_id: str) -> None:
        super().__init__(coordinator)
        self._account_id = account_id
        self._attr_unique_id = f"{account_id}_cruises"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, account_id)},
            "manufacturer": "Royal Caribbean Group",
            "name": "Royal Caribbean account",
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next cruise event."""

        today = dt_util.now().date()
        for event in self._events():
            if event.end >= today and event.start >= today:
                return event
            if event.start <= today < event.end:
                return event
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events within a date range."""

        start = start_date.date()
        end = end_date.date()
        return [
            event
            for event in self._events()
            if event.end > start and event.start < end
        ]

    def _events(self) -> list[CalendarEvent]:
        """Return RCCL events as Home Assistant calendar events."""

        return [_to_calendar_event(item) for item in cruise_events(self.coordinator.data or {})]


def _to_calendar_event(item: dict[str, Any]) -> CalendarEvent:
    """Convert a normalized RCCL event to a Home Assistant event."""

    return CalendarEvent(
        start=_as_date(item["start"]),
        end=_as_date(item["end"]),
        summary=item["summary"],
        description=item.get("description"),
        location=item.get("location"),
    )


def _as_date(value: Any) -> date:
    """Return a date from normalized event data."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
