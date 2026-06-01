"""Sensors for the Royal Caribbean integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import (
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

    def add_sailing_entities() -> None:
        new_entities: list[ClubRoyaleSailingSensor] = []
        for sailing in _club_royale_sailings(coordinator.data or {}):
            sailing_id = _sailing_id(sailing)
            if sailing_id in known_sailing_ids:
                continue
            known_sailing_ids.add(sailing_id)
            new_entities.append(ClubRoyaleSailingSensor(coordinator, entry, sailing))
        if new_entities:
            async_add_entities(new_entities)

    async_add_entities([ClubRoyaleSummarySensor(coordinator, entry)])
    add_sailing_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_sailing_entities))


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
        self._attr_unique_id = (
            f"{entry.entry_id}_club_royale_sailing_{_safe_id(self._sailing_id)}"
        )
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


def _club_royale_sailings(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized Club Royale sailings from coordinator data."""

    sailings = data.get("sailings", [])
    return [sailing for sailing in sailings if isinstance(sailing, dict)]


def _sailing_id(sailing: dict[str, Any]) -> str:
    """Return a stable id for a Club Royale sailing."""

    return str(
        sailing.get("id")
        or f"{sailing.get('offer_code')}:{sailing.get('ship_code')}:{sailing.get('sail_date')}"
    )


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
