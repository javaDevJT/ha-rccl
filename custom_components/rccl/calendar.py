"""Calendar platform for Royal Caribbean cruises."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import club_royale_offer_summaries, cruise_events, parse_rccl_date
from .const import CONF_ACCOUNT_ID, CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_CLUB_ROYALE
from .coordinator import RCCLClubRoyaleDataUpdateCoordinator, RCCLDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the RCCL calendar entity."""

    coordinator: RCCLDataUpdateCoordinator = (
        getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    )
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_CLUB_ROYALE:
        async_add_entities([ClubRoyaleOfferCalendar(coordinator, entry)])
        return

    async_add_entities([RCCLCruiseCalendar(coordinator, entry.data[CONF_ACCOUNT_ID])])


class RCCLCruiseCalendar(CoordinatorEntity[RCCLDataUpdateCoordinator], CalendarEntity):
    """Read-only RCCL cruise calendar."""

    _attr_has_entity_name = False
    _attr_name = "Cruises"
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


class ClubRoyaleOfferCalendar(
    CoordinatorEntity[RCCLClubRoyaleDataUpdateCoordinator], CalendarEntity
):
    """Read-only Club Royale offer expiration calendar."""

    _attr_has_entity_name = False
    _attr_name = "Club Royale offer expirations"
    _attr_icon = "mdi:calendar-star"

    def __init__(
        self,
        coordinator: RCCLClubRoyaleDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_club_royale_offer_expirations"
        self._attr_device_info = _club_royale_device_info(entry)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next offer expiration event."""

        today = dt_util.now().date()
        for event in self._events():
            if event.start <= today < event.end:
                return event
            if event.start >= today:
                return event
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return offer expiration events within a date range."""

        start = start_date.date()
        end = end_date.date()
        return [
            event
            for event in self._events()
            if event.end > start and event.start < end
        ]

    def _events(self) -> list[CalendarEvent]:
        """Return Club Royale offers as Home Assistant calendar events."""

        return [
            _offer_to_calendar_event(offer)
            for offer in club_royale_offer_summaries(self.coordinator.data or {})
            if parse_rccl_date(offer.get("expiration_date"))
        ]


def _to_calendar_event(item: dict[str, Any]) -> CalendarEvent:
    """Convert a normalized RCCL event to a Home Assistant event."""

    return CalendarEvent(
        start=_as_date(item["start"]),
        end=_as_date(item["end"]),
        summary=item["summary"],
        description=item.get("description"),
        location=item.get("location"),
    )


def _offer_to_calendar_event(offer: dict[str, Any]) -> CalendarEvent:
    """Convert a Club Royale offer summary to a calendar event."""

    expiration = parse_rccl_date(offer.get("expiration_date"))
    if expiration is None:
        raise ValueError("Club Royale offer missing expiration date")
    return CalendarEvent(
        start=expiration,
        end=expiration + timedelta(days=1),
        summary=_offer_summary(offer),
        description=_offer_description(offer),
        location=", ".join(offer.get("departure_ports", [])) or None,
    )


def _offer_summary(offer: dict[str, Any]) -> str:
    """Return a compact Club Royale offer calendar summary."""

    label = offer.get("offer_name") or offer.get("offer_code") or "offer"
    return f"Club Royale offer expires: {label}"


def _offer_description(offer: dict[str, Any]) -> str:
    """Return Club Royale offer details for the calendar event."""

    lines = []
    if offer.get("offer_code"):
        lines.append(f"Offer code: {offer['offer_code']}")
    if offer.get("offer_type"):
        lines.append(f"Offer type: {offer['offer_type']}")
    if offer.get("offer_occupancy_label"):
        lines.append(f"Guests: {offer['offer_occupancy_label']}")
    if offer.get("sailing_count") is not None:
        lines.append(f"Sailings: {offer['sailing_count']}")
    if offer.get("sail_by_date"):
        lines.append(f"Sail by: {offer['sail_by_date']}")
    if offer.get("ship_names"):
        lines.append(f"Ships: {', '.join(offer['ship_names'])}")
    if offer.get("itinerary_names"):
        lines.append(f"Itineraries: {', '.join(offer['itinerary_names'])}")
    if offer.get("cabin_guarantees"):
        lines.append(f"Cabins: {', '.join(offer['cabin_guarantees'])}")
    return "\n".join(lines)


def _club_royale_device_info(entry: ConfigEntry) -> dict[str, Any]:
    """Return device info for Club Royale calendar entities."""

    return {
        "identifiers": {(DOMAIN, f"club_royale_{entry.entry_id}")},
        "manufacturer": "Royal Caribbean Group",
        "name": "Club Royale offers",
    }


def _as_date(value: Any) -> date:
    """Return a date from normalized event data."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
