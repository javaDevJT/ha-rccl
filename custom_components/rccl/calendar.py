"""Calendar platform for Royal Caribbean cruises."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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
        _async_setup_club_royale_calendars(hass, entry, coordinator, async_add_entities)
        return

    async_add_entities([RCCLCruiseCalendar(coordinator, entry.data[CONF_ACCOUNT_ID])])


def _async_setup_club_royale_calendars(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RCCLClubRoyaleDataUpdateCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Club Royale offer expiration calendars."""

    known_offer_codes: set[str] = set()

    def add_offer_calendar_entities() -> None:
        current_offers = _club_royale_offers(coordinator.data or {})
        current_offer_codes = {_offer_code(offer) for offer in current_offers}
        if isinstance(coordinator.data, dict) and "offers" in coordinator.data:
            _remove_stale_club_royale_offer_calendars(
                hass,
                entry,
                current_offer_codes,
            )
            known_offer_codes.intersection_update(current_offer_codes)

        new_entities: list[ClubRoyaleOfferCalendar] = []
        for offer in current_offers:
            offer_code = _offer_code(offer)
            if offer_code in known_offer_codes:
                continue
            known_offer_codes.add(offer_code)
            new_entities.append(ClubRoyaleOfferCalendar(coordinator, entry, offer))
        if new_entities:
            async_add_entities(new_entities)

    async_add_entities([ClubRoyaleOfferExpirationsCalendar(coordinator, entry)])
    add_offer_calendar_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_offer_calendar_entities))


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


class ClubRoyaleOfferExpirationsCalendar(
    CoordinatorEntity[RCCLClubRoyaleDataUpdateCoordinator], CalendarEntity
):
    """Read-only Club Royale aggregate offer expiration calendar."""

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


class ClubRoyaleOfferCalendar(
    CoordinatorEntity[RCCLClubRoyaleDataUpdateCoordinator], CalendarEntity
):
    """Read-only Club Royale calendar for one offer code."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:ticket-percent"

    def __init__(
        self,
        coordinator: RCCLClubRoyaleDataUpdateCoordinator,
        entry: ConfigEntry,
        offer: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._offer_code = _offer_code(offer)
        self._attr_name = f"Club Royale offer {self._offer_code}"
        self._attr_unique_id = _club_royale_offer_calendar_unique_id(
            entry,
            self._offer_code,
        )
        self._attr_device_info = _club_royale_device_info(entry)

    @property
    def event(self) -> CalendarEvent | None:
        """Return this offer's expiration event."""

        offer = self._offer()
        if not offer or not parse_rccl_date(offer.get("expiration_date")):
            return None
        return _offer_to_calendar_event(offer)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return this offer's expiration event within a date range."""

        event = self.event
        if not event:
            return []
        start = start_date.date()
        end = end_date.date()
        return [event] if event.end > start and event.start < end else []

    def _offer(self) -> dict[str, Any] | None:
        """Return the latest matching offer summary."""

        for offer in _club_royale_offers(self.coordinator.data or {}):
            if _offer_code(offer) == self._offer_code:
                return offer
        return None


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


def _club_royale_offers(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized Club Royale offer summaries from coordinator data."""

    return [
        offer
        for offer in club_royale_offer_summaries(data)
        if (
            isinstance(offer, dict)
            and _offer_code(offer)
            and parse_rccl_date(offer.get("expiration_date"))
        )
    ]


def _remove_stale_club_royale_offer_calendars(
    hass: HomeAssistant,
    entry: ConfigEntry,
    current_offer_codes: set[str],
) -> None:
    """Remove dynamic offer calendars no longer in the latest data."""

    registry = er.async_get(hass)
    current_unique_ids = {
        _club_royale_offer_calendar_unique_id(entry, offer_code)
        for offer_code in current_offer_codes
    }
    prefix = f"{entry.entry_id}_club_royale_offer_calendar_"
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            not registry_entry.unique_id
            or not registry_entry.unique_id.startswith(prefix)
        ):
            continue
        if registry_entry.unique_id in current_unique_ids:
            continue
        registry.async_remove(registry_entry.entity_id)


def _offer_code(offer: dict[str, Any]) -> str:
    """Return a stable Club Royale offer code."""

    return str(offer.get("offer_code") or "").strip()


def _club_royale_offer_calendar_unique_id(
    entry: ConfigEntry,
    offer_code: str,
) -> str:
    """Return the Home Assistant unique id for one offer calendar."""

    return f"{entry.entry_id}_club_royale_offer_calendar_{_safe_id(offer_code)}"


def _safe_id(value: str) -> str:
    """Return a Home Assistant unique-id safe suffix."""

    return "".join(char if char.isalnum() else "_" for char in value).strip("_")


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
