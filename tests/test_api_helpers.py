"""Tests for RCCL API data helpers."""

from __future__ import annotations

from datetime import date
import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = types.ModuleType("custom_components")
RCCL_PACKAGE = types.ModuleType("custom_components.rccl")
CUSTOM_COMPONENTS.__path__ = [str(ROOT / "custom_components")]
RCCL_PACKAGE.__path__ = [str(ROOT / "custom_components" / "rccl")]
sys.modules.setdefault("custom_components", CUSTOM_COMPONENTS)
sys.modules.setdefault("custom_components.rccl", RCCL_PACKAGE)

api = importlib.import_module("custom_components.rccl.api")


SAMPLE_DATA = {
    "bookings": {
        "payload": {
            "profileBookings": [
                {
                    "bookingId": "past",
                    "bookingStatus": "BOOKED",
                    "numberOfNights": 3,
                    "packageCode": "PAST",
                    "sailDate": "2026-01-10",
                    "shipCode": "OA",
                    "stateroomNumber": "1234",
                },
                {
                    "bookingId": "future",
                    "bookingStatus": "BOOKED",
                    "numberOfNights": 7,
                    "packageCode": "CARIB",
                    "sailDate": "2026-07-04",
                    "shipCode": "UT",
                    "stateroomNumber": "5678",
                },
            ]
        }
    },
    "upgrades": {
        "payload": [
            {"bookingId": "future", "upgradeEligible": True},
            {"bookingId": "past", "upgradeEligible": False},
        ]
    },
    "loyalty": {
        "payload": {
            "loyaltyInformation": {
                "crownAndAnchorSocietyLoyaltyTier": "Diamond",
                "crownAndAnchorSocietyLoyaltyIndividualPoints": 90,
            }
        }
    },
    "loyalty_history": {
        "payload": {
            "sailings": [
                {
                    "bookingId": "history",
                    "itineraryCode": "HIST",
                    "itineraryNightsQuantity": "4",
                    "originPortDescription": "Miami",
                    "sailingDate": "2025-05-01",
                    "shipName": "Example of the Seas",
                    "status": "COMPLETED",
                }
            ]
        }
    },
}


class ApiHelperTest(unittest.TestCase):
    """Exercise pure API helper behavior."""

    def test_upcoming_bookings_are_filtered_and_sorted(self) -> None:
        """Only future bookings should be returned."""

        result = api.upcoming_bookings(SAMPLE_DATA, today=date(2026, 6, 1))

        self.assertEqual([item["bookingId"] for item in result], ["future"])
        self.assertEqual(api.next_booking(SAMPLE_DATA, today=date(2026, 6, 1))["shipCode"], "UT")

    def test_upgrade_eligible_count(self) -> None:
        """Only true upgrade eligibility counts."""

        self.assertEqual(api.upgrade_eligible_count(SAMPLE_DATA), 1)

    def test_crown_anchor_values(self) -> None:
        """Loyalty values are extracted by suffix."""

        self.assertEqual(api.crown_anchor_value(SAMPLE_DATA, "LoyaltyTier"), "Diamond")
        self.assertEqual(api.crown_anchor_value(SAMPLE_DATA, "LoyaltyIndividualPoints"), 90)

    def test_cruise_events_include_bookings_and_history(self) -> None:
        """Calendar events should normalize future bookings and history."""

        events = api.cruise_events(SAMPLE_DATA)

        self.assertEqual([event["start"] for event in events], [date(2025, 5, 1), date(2026, 1, 10), date(2026, 7, 4)])
        self.assertEqual(events[-1]["end"], date(2026, 7, 12))
        self.assertIn("7 night cruise", events[-1]["description"])


if __name__ == "__main__":
    unittest.main()
