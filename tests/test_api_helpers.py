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
                    "passengers": [
                        {
                            "firstName": "Test",
                            "lastName": "Passenger",
                            "guestId": "guest-1",
                            "crownAndAnchorNumber": "12345",
                        }
                    ],
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


SAMPLE_CLUB_ROYALE_DATA = {
    "club_royale": {
        "offers": {
            "offers": [
                {
                    "playerOfferId": "player-offer-1",
                    "campaignOffer": {
                        "offerCode": "26SUM205",
                        "name": "Fortune Flash",
                    },
                }
            ]
        },
        "offer_details": [
            {
                "offers": [
                    {
                        "campaignName": "Fortune Flash",
                        "playerOfferId": "player-offer-1",
                        "bookingRequest": [
                            {
                                "id": "request-1",
                                "sailings": [{"shipCode": "WN", "sailDate": "2026-06-26"}],
                                "rooms": [{"guests": [{"firstName": "Hidden"}]}],
                            }
                        ],
                        "campaignOffer": {
                            "offerCode": "26SUM205",
                            "offerType": {"code": "COMP", "name": "Complimentary"},
                            "name": "Fortune Flash",
                            "description": "Enjoy an Interior Room for Two",
                            "reserveByDate": "2026-06-11T03:59:00.000Z",
                            "sailByDate": "2026-10-31T00:00:00.000Z",
                            "sailings": [
                                {
                                    "id": "sailing-1",
                                    "isGTY": True,
                                    "isCOMP": True,
                                    "sailDate": "2026-06-26",
                                    "shipCode": "WN",
                                    "shipName": "Wonder of the Seas",
                                    "itineraryCode": "WN03B001",
                                    "itineraryName": "Bahamas & Perfect Day",
                                    "itineraryDescription": "3 NIGHT BAHAMAS & PERFECT DAY CRUISE",
                                    "sailingType": {
                                        "name": "3 Night Bahamas & Perfect Day Cruise"
                                    },
                                    "departurePort": {"code": "MIA", "name": "Miami"},
                                    "totalNights": 3,
                                    "roomTypeList": [
                                        {"code": "INTERIOR", "name": "Interior"}
                                    ],
                                }
                            ],
                        },
                    }
                ]
            }
        ],
    }
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

    def test_loyalty_summary_derives_totals_from_history_when_summary_is_empty(self) -> None:
        """History sailings should backfill zero/empty RCCL summary totals."""

        result = api.loyalty_summary(
            {
                **SAMPLE_DATA,
                "loyalty_summary": {"payload": {"totalTrips": 0, "totalNights": 0}},
                "loyalty_history": {
                    "payload": {
                        "sailings": [
                            {"bookingId": "one", "itineraryNightsQuantity": "4"},
                            {"bookingId": "two", "itineraryNightsQuantity": 7},
                        ]
                    }
                },
            }
        )

        self.assertEqual(result["totalTrips"], 2)
        self.assertEqual(result["totalNights"], 11)

    def test_booking_attributes_include_booking_id_and_passengers(self) -> None:
        """Home Assistant attributes should include booking and passenger details."""

        result = api.safe_booking_attributes(api.next_booking(SAMPLE_DATA, today=date(2026, 6, 1)))

        self.assertEqual(result["booking_id"], "future")
        self.assertEqual(
            result["passengers"],
            [
                {
                    "first_name": "Test",
                    "last_name": "Passenger",
                    "guest_id": "guest-1",
                    "crown_and_anchor_number": "12345",
                }
            ],
        )

    def test_club_royale_sailings_normalize_card_fields(self) -> None:
        """Offer sailings should normalize into card rows without booking guests."""

        result = api.club_royale_sailings(SAMPLE_CLUB_ROYALE_DATA)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["sail_date"], "2026-06-26")
        self.assertEqual(result[0]["return_date"], "2026-06-29")
        self.assertEqual(result[0]["ship_name"], "Wonder of the Seas")
        self.assertEqual(result[0]["itinerary_name"], "Bahamas & Perfect Day")
        self.assertEqual(result[0]["calendar_title"], "Bahamas & Perfect Day - Wonder of the Seas")
        self.assertEqual(result[0]["cabin_guarantee"], "Interior Guarantee")
        self.assertEqual(result[0]["offer_occupancy"], "two_passengers")
        self.assertEqual(result[0]["offer_occupancy_label"], "Two passengers")
        self.assertEqual(result[0]["offer_type"], "Complimentary")
        self.assertNotIn("booking_id", result[0])
        self.assertNotIn("passengers", result[0])


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

    def test_credentials_from_stored_data_preserves_reauth_fields(self) -> None:
        """Setup should use stored tokens while retaining username/password."""

        credentials = api.credentials_from_stored_data(
            {
                "access_token": "stored-access",
                "account_id": "stored-account",
                "app_key": "stored-app-key",
                "username": "person@example.com",
                "password": "secret",
                "refresh_token": "stored-refresh",
                "id_token": "stored-id",
                "token_expires_at": 123,
            }
        )

        self.assertEqual(credentials.access_token, "stored-access")
        self.assertEqual(credentials.account_id, "stored-account")
        self.assertEqual(credentials.vds_id, "stored-account")
        self.assertEqual(credentials.username, "person@example.com")
        self.assertEqual(credentials.password, "secret")

    async def test_async_login_times_out_instead_of_hanging(self) -> None:
        """A stalled RCCL auth request should fail with a bounded error."""

        with self.assertRaisesRegex(api.RCCLApiError, "Timed out"):
            await api.RCCLClient.async_login(
                HangingSession(),
                "person@example.com",
                "secret",
                request_timeout=0.001,
            )

    async def test_async_get_club_royale_data_fetches_offer_details(self) -> None:
        """Club Royale polling should fetch list data and per-offer sailings."""

        session = FakeSession(
            [
                FakeResponse(
                    200,
                    {
                        "offers": [
                            {
                                "playerOfferId": "player-offer-1",
                                "campaignOffer": {"offerCode": "26SUM205"},
                            }
                        ],
                        "totalOffers": 1,
                    },
                ),
                FakeResponse(200, {"offers": [{"campaignOffer": {"sailings": []}}]}),
            ]
        )
        client = api.RCCLClient(
            session,
            api.RCCLCredentials(
                access_token="access",
                account_id="account-123",
                vds_id="account-123",
            ),
        )

        result = await client.async_get_club_royale_data(
            {
                "payload": {
                    "loyaltyInformation": {
                        "crownAndAnchorId": "364350586",
                    }
                }
            }
        )

        self.assertEqual(result["offers"]["totalOffers"], 1)
        self.assertEqual(len(result["offer_details"]), 1)
        self.assertEqual(len(session.calls), 2)
        self.assertTrue(session.calls[0]["url"].endswith("/api/casino/v2/offers/merged"))
        self.assertEqual(session.calls[0]["headers"]["x-account-id"], "account-123")
        self.assertEqual(session.calls[0]["headers"]["x-loyalty-id"], "364350586")
        self.assertEqual(session.calls[0]["json"]["limit"], 100)
        self.assertEqual(session.calls[1]["json"]["offerCode"], "26SUM205")
        self.assertEqual(session.calls[1]["json"]["playerOfferId"], "player-offer-1")
        self.assertEqual(session.calls[1]["json"]["limit"], 1)


if __name__ == "__main__":
    unittest.main()
