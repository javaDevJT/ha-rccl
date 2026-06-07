"""Sensors for the Royal Caribbean integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import (
    club_royale_offer_summaries,
    crown_anchor_value,
    loyalty_summary,
    next_booking,
    parse_rccl_date,
    safe_booking_attributes,
    upcoming_bookings,
    upgrade_eligible_count,
)
from .const import CONF_ACCOUNT_ID, CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_CLUB_ROYALE
from .coordinator import RCCLClubRoyaleDataUpdateCoordinator, RCCLDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class RCCLSensorEntityDescription(SensorEntityDescription):
    """Describe an RCCL sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSOR_DESCRIPTIONS: tuple[RCCLSensorEntityDescription, ...] = (
    RCCLSensorEntityDescription(
        key="upcoming_cruises",
        name="Upcoming cruises",
        translation_key="upcoming_cruises",
        icon="mdi:ferry",
        value_fn=lambda data: len(upcoming_bookings(data)),
        attributes_fn=lambda data: {
            "next_cruise": safe_booking_attributes(next_booking(data)),
        },
    ),
    RCCLSensorEntityDescription(
        key="next_cruise_date",
        name="Next cruise date",
        translation_key="next_cruise_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda data: (
            next_booking(data).get("sailDate") if next_booking(data) else None
        ),
        attributes_fn=lambda data: safe_booking_attributes(next_booking(data)),
    ),
    RCCLSensorEntityDescription(
        key="upgrade_eligible_cruises",
        name="Upgrade eligible cruises",
        translation_key="upgrade_eligible_cruises",
        icon="mdi:arrow-up-bold-circle",
        value_fn=upgrade_eligible_count,
    ),
    RCCLSensorEntityDescription(
        key="crown_anchor_tier",
        name="Crown & Anchor tier",
        translation_key="crown_anchor_tier",
        icon="mdi:crown",
        value_fn=lambda data: crown_anchor_value(data, "LoyaltyTier"),
    ),
    RCCLSensorEntityDescription(
        key="crown_anchor_points",
        name="Crown & Anchor points",
        translation_key="crown_anchor_points",
        icon="mdi:star-circle",
        value_fn=lambda data: crown_anchor_value(data, "LoyaltyIndividualPoints"),
    ),
    RCCLSensorEntityDescription(
        key="total_cruise_trips",
        name="Total cruise trips",
        translation_key="total_cruise_trips",
        icon="mdi:ship-wheel",
        value_fn=lambda data: loyalty_summary(data).get("totalTrips"),
    ),
    RCCLSensorEntityDescription(
        key="total_cruise_nights",
        name="Total cruise nights",
        translation_key="total_cruise_nights",
        icon="mdi:weather-night",
        value_fn=lambda data: loyalty_summary(data).get("totalNights"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RCCL sensors from a config entry."""

    coordinator: RCCLDataUpdateCoordinator = (
        getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
    )
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_CLUB_ROYALE:
        _async_setup_club_royale_sensors(hass, entry, coordinator, async_add_entities)
        return

    account_id = entry.data[CONF_ACCOUNT_ID]
    async_add_entities(
        RCCLSensor(coordinator, account_id, description)
        for description in SENSOR_DESCRIPTIONS
    )


def _async_setup_club_royale_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RCCLClubRoyaleDataUpdateCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Club Royale offer sensors from a config entry."""

    known_sailing_ids: set[str] = set()
    known_offer_codes: set[str] = set()

    def add_club_royale_entities() -> None:
        data = coordinator.data or {}
        current_sailings = _club_royale_sailings(data)
        current_offers = _club_royale_offers(data)
        current_sailing_ids = {_sailing_id(sailing) for sailing in current_sailings}
        current_offer_codes = {_offer_code(offer) for offer in current_offers}
        if (
            isinstance(coordinator.data, dict)
            and "sailings" in coordinator.data
            and "offers" in coordinator.data
        ):
            _remove_stale_club_royale_entities(
                hass,
                entry,
                current_sailing_ids,
                current_offer_codes,
            )
            known_sailing_ids.intersection_update(current_sailing_ids)
            known_offer_codes.intersection_update(current_offer_codes)

        new_entities: list[ClubRoyaleSailingSensor | ClubRoyaleOfferSensor] = []
        for sailing in current_sailings:
            sailing_id = _sailing_id(sailing)
            if sailing_id in known_sailing_ids:
                continue
            known_sailing_ids.add(sailing_id)
            new_entities.append(ClubRoyaleSailingSensor(coordinator, entry, sailing))
        for offer in current_offers:
            offer_code = _offer_code(offer)
            if offer_code in known_offer_codes:
                continue
            known_offer_codes.add(offer_code)
            new_entities.append(ClubRoyaleOfferSensor(coordinator, entry, offer))
        if new_entities:
            async_add_entities(new_entities)

    async_add_entities([ClubRoyaleSummarySensor(coordinator, entry)])
    add_club_royale_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_club_royale_entities))


class RCCLSensor(CoordinatorEntity[RCCLDataUpdateCoordinator], SensorEntity):
    """RCCL account sensor."""

    entity_description: RCCLSensorEntityDescription
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: RCCLDataUpdateCoordinator,
        account_id: str,
        description: RCCLSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{account_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, account_id)},
            "manufacturer": "Royal Caribbean Group",
            "name": "Royal Caribbean account",
        }

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""

        value = self.entity_description.value_fn(self.coordinator.data or {})
        if self.entity_description.device_class is SensorDeviceClass.DATE:
            return _as_date(value)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return safe sensor attributes."""

        if not self.entity_description.attributes_fn:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data or {})


def _as_date(value: Any) -> date | None:
    """Coerce Home Assistant date sensor values to date objects."""

    return parse_rccl_date(value)


class ClubRoyaleSummarySensor(
    CoordinatorEntity[RCCLClubRoyaleDataUpdateCoordinator], SensorEntity
):
    """Club Royale offer summary sensor."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:cards"
    _attr_translation_key = "club_royale_available_sailings"

    def __init__(
        self, coordinator: RCCLClubRoyaleDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Club Royale available sailings"
        self._attr_unique_id = f"{entry.entry_id}_club_royale_available_sailings"
        self._attr_device_info = _club_royale_device_info(entry)

    @property
    def native_value(self) -> int:
        """Return the current offer-sailing count."""

        return len(_club_royale_sailings(self.coordinator.data or {}))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return card-discovery metadata."""

        return {
            "integration": DOMAIN,
            "entity_kind": "club_royale_summary",
        }


class ClubRoyaleSailingSensor(
    CoordinatorEntity[RCCLClubRoyaleDataUpdateCoordinator], SensorEntity
):
    """Club Royale sailing date sensor."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:ship-wheel"

    def __init__(
        self,
        coordinator: RCCLClubRoyaleDataUpdateCoordinator,
        entry: ConfigEntry,
        sailing: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._sailing_id = _sailing_id(sailing)
        self._attr_name = sailing.get("calendar_title") or "Club Royale sailing"
        self._attr_unique_id = _club_royale_sailing_unique_id(entry, self._sailing_id)
        self._attr_device_info = _club_royale_device_info(entry)

    @property
    def native_value(self) -> date | None:
        """Return the sailing start date."""

        return parse_rccl_date(self._sailing().get("sail_date"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sailing details for Home Assistant and custom cards."""

        sailing = self._sailing()
        return {
            **sailing,
            "integration": DOMAIN,
            "entity_kind": "club_royale_sailing",
            "sailing_id": self._sailing_id,
        }

    def _sailing(self) -> dict[str, Any]:
        """Return the latest matching sailing row."""

        for sailing in _club_royale_sailings(self.coordinator.data or {}):
            if _sailing_id(sailing) == self._sailing_id:
                return sailing
        return {"id": self._sailing_id}


class ClubRoyaleOfferSensor(
    CoordinatorEntity[RCCLClubRoyaleDataUpdateCoordinator], SensorEntity
):
    """Club Royale offer expiration sensor."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:ticket-percent"

    def __init__(
        self,
        coordinator: RCCLClubRoyaleDataUpdateCoordinator,
        entry: ConfigEntry,
        offer: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._offer_code = _offer_code(offer)
        self._attr_name = f"Club Royale offer {self._offer_code}"
        self._attr_unique_id = _club_royale_offer_unique_id(entry, self._offer_code)
        self._attr_device_info = _club_royale_device_info(entry)

    @property
    def native_value(self) -> date | None:
        """Return the offer expiration date."""

        return parse_rccl_date(self._offer().get("expiration_date"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return offer details for Home Assistant."""

        offer = self._offer()
        return {
            **offer,
            "integration": DOMAIN,
            "entity_kind": "club_royale_offer",
            "offer_code": self._offer_code,
        }

    def _offer(self) -> dict[str, Any]:
        """Return the latest matching offer summary."""

        for offer in _club_royale_offers(self.coordinator.data or {}):
            if _offer_code(offer) == self._offer_code:
                return offer
        return {"offer_code": self._offer_code}


def _club_royale_sailings(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized Club Royale sailings from coordinator data."""

    sailings = data.get("sailings", [])
    return [sailing for sailing in sailings if isinstance(sailing, dict)]


def _club_royale_offers(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized Club Royale offer summaries from coordinator data."""

    offers = data.get("offers", [])
    if isinstance(offers, list):
        filtered = [
            offer
            for offer in offers
            if isinstance(offer, dict) and str(offer.get("offer_code") or "").strip()
        ]
        if filtered:
            return filtered
    return club_royale_offer_summaries(data)


def _remove_stale_club_royale_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    current_sailing_ids: set[str],
    current_offer_codes: set[str],
) -> None:
    """Remove dynamic Club Royale sensors no longer in the latest data."""

    registry = er.async_get(hass)
    current_unique_ids = {
        _club_royale_sailing_unique_id(entry, sailing_id)
        for sailing_id in current_sailing_ids
    }
    current_unique_ids.update(
        _club_royale_offer_unique_id(entry, offer_code)
        for offer_code in current_offer_codes
    )
    prefixes = (
        f"{entry.entry_id}_club_royale_sailing_",
        f"{entry.entry_id}_club_royale_offer_",
    )
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            not registry_entry.unique_id
            or not registry_entry.unique_id.startswith(prefixes)
        ):
            continue
        if registry_entry.unique_id in current_unique_ids:
            continue
        registry.async_remove(registry_entry.entity_id)


def _sailing_id(sailing: dict[str, Any]) -> str:
    """Return a stable id for a Club Royale sailing."""

    return str(
        sailing.get("id")
        or f"{sailing.get('offer_code')}:{sailing.get('ship_code')}:{sailing.get('sail_date')}"
    )


def _offer_code(offer: dict[str, Any]) -> str:
    """Return a stable Club Royale offer code."""

    return str(offer.get("offer_code") or "").strip()


def _club_royale_sailing_unique_id(entry: ConfigEntry, sailing_id: str) -> str:
    """Return the Home Assistant unique id for one sailing sensor."""

    return f"{entry.entry_id}_club_royale_sailing_{_safe_id(sailing_id)}"


def _club_royale_offer_unique_id(entry: ConfigEntry, offer_code: str) -> str:
    """Return the Home Assistant unique id for one offer sensor."""

    return f"{entry.entry_id}_club_royale_offer_{_safe_id(offer_code)}"


def _safe_id(value: str) -> str:
    """Return a Home Assistant unique-id safe suffix."""

    return "".join(char if char.isalnum() else "_" for char in value).strip("_")


def _club_royale_device_info(entry: ConfigEntry) -> dict[str, Any]:
    """Return device info for Club Royale offer entities."""

    return {
        "identifiers": {(DOMAIN, f"club_royale_{entry.entry_id}")},
        "manufacturer": "Royal Caribbean Group",
        "name": "Club Royale offers",
    }
