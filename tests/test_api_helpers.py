"""Tests for RCCL API data helpers."""

from __future__ import annotations

import base64
import asyncio
from datetime import date
import importlib
import json
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


class FakeResponse:
    """Minimal async response for client tests."""

    def __init__(self, status: int, payload: dict[str, object]) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def text(self) -> str:
        return json.dumps(self._payload)


class FakeSession:
    """Minimal aiohttp-like session for client tests."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self._responses.pop(0)


class HangingResponse:
    """Response that never enters, for timeout tests."""

    async def __aenter__(self) -> "HangingResponse":
        await asyncio.sleep(60)
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class HangingSession:
    """Session that returns a hanging response."""

    def request(self, method: str, url: str, **kwargs: object) -> HangingResponse:
        return HangingResponse()


def fake_jwt(payload: dict[str, object]) -> str:
    """Return an unsigned JWT for tests."""

    def encode(value: dict[str, object]) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode(payload)}."


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


class LoginTest(unittest.IsolatedAsyncioTestCase):
    """Exercise login parsing without Home Assistant."""

    async def test_async_login_uses_username_password_and_derives_account_id(self) -> None:
        """The client should perform the RCCL two-step login flow."""

        session = FakeSession(
            [
                FakeResponse(200, {"tokenId": "openam-token"}),
                FakeResponse(
                    200,
                    {
                        "access_token": "access",
                        "refresh_token": "refresh",
                        "id_token": fake_jwt({"vdsid": "account-123"}),
                        "expires_in": 3600,
                    },
                ),
            ]
        )

        credentials = await api.RCCLClient.async_login(
            session,
            "person@example.com",
            "secret",
        )

        self.assertEqual(credentials.account_id, "account-123")
        self.assertEqual(credentials.access_token, "access")
        self.assertEqual(credentials.refresh_token, "refresh")
        self.assertEqual(credentials.username, "person@example.com")
        self.assertEqual(credentials.password, "secret")
        self.assertEqual(len(session.calls), 2)
        self.assertTrue(session.calls[0]["url"].endswith("/auth/json/authenticate"))
        self.assertEqual(
            session.calls[0]["headers"]["X-OpenAM-Username"],
            "person@example.com",
        )
        self.assertEqual(session.calls[0]["headers"]["X-OpenAM-Password"], "secret")
        self.assertEqual(
            session.calls[0]["headers"]["content-type"],
            "application/x-www-form-urlencoded",
        )
        self.assertEqual(session.calls[0]["data"], "")
        self.assertTrue(session.calls[1]["url"].endswith("/en/royal/web/v1/authorize"))
        self.assertEqual(
            session.calls[1]["json"],
            {"client": "login-component", "tokenId": "openam-token"},
        )

    def test_credentials_from_wrapped_oauth_response(self) -> None:
        """The parser should also support RCCL's account-web payload spelling."""

        credentials = api.credentials_from_oauth_response(
            {
                "payload": {
                    "accessToken": "access",
                    "refreshToken": "refresh",
                    "accountId": "account-456",
                    "openIdToken": fake_jwt({"ignored": True}),
                    "tokenExpiration": 3600,
                }
            },
            username="person@example.com",
            password="secret",
        )

        self.assertEqual(credentials.account_id, "account-456")
        self.assertEqual(credentials.vds_id, "account-456")
        self.assertEqual(credentials.id_token, fake_jwt({"ignored": True}))

    async def test_async_login_times_out_instead_of_hanging(self) -> None:
        """A stalled RCCL auth request should fail with a bounded error."""

        with self.assertRaisesRegex(api.RCCLApiError, "Timed out"):
            await api.RCCLClient.async_login(
                HangingSession(),
                "person@example.com",
                "secret",
                request_timeout=0.001,
            )


if __name__ == "__main__":
    unittest.main()
