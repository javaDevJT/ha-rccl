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
    safe_booking_attributes,
    upcoming_bookings,
    upgrade_eligible_count,
)
from .const import CONF_ACCOUNT_ID, DOMAIN
from .coordinator import RCCLDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class RCCLSensorEntityDescription(SensorEntityDescription):
    """Describe an RCCL sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSOR_DESCRIPTIONS: tuple[RCCLSensorEntityDescription, ...] = (
    RCCLSensorEntityDescription(
        key="upcoming_cruises",
        translation_key="upcoming_cruises",
        icon="mdi:ferry",
        value_fn=lambda data: len(upcoming_bookings(data)),
        attributes_fn=lambda data: {
            "next_cruise": safe_booking_attributes(next_booking(data)),
        },
    ),
    RCCLSensorEntityDescription(
        key="next_cruise_date",
        translation_key="next_cruise_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda data: (
            next_booking(data).get("sailDate") if next_booking(data) else None
        ),
        attributes_fn=lambda data: safe_booking_attributes(next_booking(data)),
    ),
    RCCLSensorEntityDescription(
        key="upgrade_eligible_cruises",
        translation_key="upgrade_eligible_cruises",
        icon="mdi:arrow-up-bold-circle",
        value_fn=upgrade_eligible_count,
    ),
    RCCLSensorEntityDescription(
        key="crown_anchor_tier",
        translation_key="crown_anchor_tier",
        icon="mdi:crown",
        value_fn=lambda data: crown_anchor_value(data, "LoyaltyTier"),
    ),
    RCCLSensorEntityDescription(
        key="crown_anchor_points",
        translation_key="crown_anchor_points",
        icon="mdi:star-circle",
        value_fn=lambda data: crown_anchor_value(data, "LoyaltyIndividualPoints"),
    ),
    RCCLSensorEntityDescription(
        key="total_cruise_trips",
        translation_key="total_cruise_trips",
        icon="mdi:ship-wheel",
        value_fn=lambda data: loyalty_summary(data).get("totalTrips"),
    ),
    RCCLSensorEntityDescription(
        key="total_cruise_nights",
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
    account_id = entry.data[CONF_ACCOUNT_ID]
    async_add_entities(
        RCCLSensor(coordinator, account_id, description)
        for description in SENSOR_DESCRIPTIONS
    )


class RCCLSensor(CoordinatorEntity[RCCLDataUpdateCoordinator], SensorEntity):
    """RCCL account sensor."""

    entity_description: RCCLSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RCCLDataUpdateCoordinator,
        account_id: str,
        description: RCCLSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
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

    from .api import parse_rccl_date

    return parse_rccl_date(value)
