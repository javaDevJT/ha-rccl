"""Tests for RCCL API data helpers."""

from __future__ import annotations

import base64
import asyncio
import copy
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
                    "sailingDate": "20250501",
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

    def test_parse_rccl_date_supports_loyalty_history_compact_dates(self) -> None:
        """Loyalty history uses YYYYMMDD dates."""

        self.assertEqual(api.parse_rccl_date("20140622"), date(2014, 6, 22))

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
        self.assertEqual(result[0]["id"], "26SUM205:sailing-1")
        self.assertEqual(result[0]["source_sailing_id"], "sailing-1")
        self.assertEqual(result[0]["offer_occupancy"], "two_passengers")
        self.assertEqual(result[0]["offer_occupancy_label"], "Two passengers")
        self.assertEqual(result[0]["offer_type"], "Complimentary")
        self.assertNotIn("booking_id", result[0])
        self.assertNotIn("passengers", result[0])

    def test_club_royale_offer_type_name_sets_guest_count(self) -> None:
        """Cruise Fare For N Guest offer-type names should drive occupancy."""

        data = copy.deepcopy(SAMPLE_CLUB_ROYALE_DATA)
        offers = data["club_royale"]["offer_details"][0]["offers"]
        first_offer = offers[0]
        first_offer["campaignOffer"]["description"] = "Casino offer"
        first_offer["campaignOffer"]["offerType"]["name"] = "Cruise Fare For 1 Guest"
        second_offer = copy.deepcopy(first_offer)
        second_offer["campaignOffer"]["offerCode"] = "26SUM206"
        second_offer["campaignOffer"]["offerType"]["name"] = "Cruise Fare For 2 Guests"
        second_offer["campaignOffer"]["sailings"][0]["id"] = "sailing-2"
        second_offer["campaignOffer"]["sailings"][0]["sailDate"] = "2026-07-03"
        offers.append(second_offer)

        result = api.club_royale_sailings(data)

        by_id = {sailing["id"]: sailing for sailing in result}
        self.assertEqual(by_id["26SUM205:sailing-1"]["offer_occupancy"], "one_passenger")
        self.assertEqual(by_id["26SUM205:sailing-1"]["offer_occupancy_label"], "One passenger")
        self.assertEqual(by_id["26SUM206:sailing-2"]["offer_occupancy"], "two_passengers")
        self.assertEqual(by_id["26SUM206:sailing-2"]["offer_occupancy_label"], "Two passengers")

    def test_club_royale_sailing_level_offer_terms_override_campaign(self) -> None:
        """Per-sailing fare and guest labels should beat campaign defaults."""

        data = copy.deepcopy(SAMPLE_CLUB_ROYALE_DATA)
        campaign_offer = data["club_royale"]["offer_details"][0]["offers"][0]["campaignOffer"]
        campaign_offer["description"] = "Complimentary cruise fare for two guests"
        sailings = campaign_offer["sailings"]
        sailings[0]["offerType"] = {"name": "Cruise Fare For 1 Guest"}
        second_sailing = copy.deepcopy(sailings[0])
        second_sailing["id"] = "sailing-2"
        second_sailing["sailDate"] = "2026-07-03"
        second_sailing["isCOMP"] = False
        second_sailing["fareType"] = {"name": "Cruise Fare For 1 Guest"}
        sailings.append(second_sailing)

        result = api.club_royale_sailings(data)

        by_id = {sailing["id"]: sailing for sailing in result}
        self.assertEqual(by_id["26SUM205:sailing-1"]["offer_type"], "Complimentary")
        self.assertEqual(by_id["26SUM205:sailing-1"]["offer_occupancy"], "one_passenger")
        self.assertEqual(by_id["26SUM205:sailing-1"]["offer_occupancy_label"], "One passenger")
        self.assertEqual(by_id["26SUM205:sailing-2"]["offer_type"], "Reduced fare")
        self.assertEqual(by_id["26SUM205:sailing-2"]["offer_occupancy"], "one_passenger")
        self.assertEqual(by_id["26SUM205:sailing-2"]["offer_occupancy_label"], "One passenger")

    def test_club_royale_sailing_nights_fall_back_to_title_labels(self) -> None:
        """RCCL rows without totalNights should still span every impacted day."""

        data = copy.deepcopy(SAMPLE_CLUB_ROYALE_DATA)
        sailing = data["club_royale"]["offer_details"][0]["offers"][0]["campaignOffer"]["sailings"][0]
        sailing.pop("totalNights")
        sailing["sailDate"] = "2026-06-08"
        sailing["itineraryName"] = "4 Night Key West Bahamas Cruise"
        sailing["itineraryDescription"] = "4 NIGHT KEY WEST BAHAMAS CRUISE"
        sailing["sailingType"] = {"name": "4 Night Key West Bahamas Cruise"}

        result = api.club_royale_sailings(data)

        self.assertEqual(result[0]["total_nights"], 4)
        self.assertEqual(result[0]["impacted_days"], 5)
        self.assertEqual(result[0]["return_date"], "2026-06-12")

    def test_club_royale_shared_voyage_ids_stay_distinct_per_offer(self) -> None:
        """The same RCCL sailing should not collapse across different offers."""

        data = copy.deepcopy(SAMPLE_CLUB_ROYALE_DATA)
        offers = data["club_royale"]["offer_details"][0]["offers"]
        first_offer = offers[0]
        second_offer = copy.deepcopy(first_offer)
        second_offer["campaignName"] = "Second Campaign"
        second_offer["campaignOffer"]["offerCode"] = "26SUM206"
        second_offer["campaignOffer"]["name"] = "Second Offer"
        offers.append(second_offer)

        result = api.club_royale_sailings(data)

        self.assertEqual(len(result), 2)
        self.assertEqual(
            {sailing["id"] for sailing in result},
            {"26SUM205:sailing-1", "26SUM206:sailing-1"},
        )
        self.assertEqual({sailing["source_sailing_id"] for sailing in result}, {"sailing-1"})

    def test_club_royale_offer_summaries_group_sailings_by_offer_code(self) -> None:
        """Offer-code summaries should expose expiration dates and metadata."""

        data = copy.deepcopy(SAMPLE_CLUB_ROYALE_DATA)
        offers = data["club_royale"]["offer_details"][0]["offers"]
        second_offer = copy.deepcopy(offers[0])
        second_offer["campaignName"] = "Second Campaign"
        second_offer["campaignOffer"]["offerCode"] = "26SUM206"
        second_offer["campaignOffer"]["name"] = "Second Offer"
        second_offer["campaignOffer"]["reserveByDate"] = "2026-06-01T03:59:00.000Z"
        second_offer["campaignOffer"]["sailings"][0]["id"] = "sailing-2"
        second_offer["campaignOffer"]["sailings"][0]["sailDate"] = "2026-07-03"
        offers.append(second_offer)
        sailings = api.club_royale_sailings(data)

        result = api.club_royale_offer_summaries({"sailings": sailings})

        by_code = {offer["offer_code"]: offer for offer in result}
        self.assertEqual([offer["offer_code"] for offer in result], ["26SUM206", "26SUM205"])
        self.assertEqual(by_code["26SUM205"]["expiration_date"], "2026-06-11")
        self.assertEqual(by_code["26SUM205"]["sailing_count"], 1)
        self.assertEqual(by_code["26SUM205"]["sailing_ids"], ["26SUM205:sailing-1"])
        self.assertEqual(by_code["26SUM205"]["source_sailing_ids"], ["sailing-1"])
        self.assertEqual(by_code["26SUM205"]["ship_names"], ["Wonder of the Seas"])
        self.assertEqual(by_code["26SUM205"]["offer_type"], "Complimentary")
        self.assertEqual(by_code["26SUM205"]["offer_occupancy_label"], "Two passengers")
        self.assertEqual(by_code["26SUM205"]["sail_by_date"], "2026-10-31")


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
                FakeResponse(200, {"html": "club royale offers page"}),
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
        self.assertEqual(len(session.calls), 3)
        self.assertTrue(session.calls[0]["url"].endswith("/club-royale/offers"))
        self.assertTrue(session.calls[1]["url"].endswith("/api/casino/v2/offers/merged"))
        self.assertEqual(session.calls[1]["headers"]["x-account-id"], "account-123")
        self.assertEqual(session.calls[1]["headers"]["x-loyalty-id"], "364350586")
        self.assertEqual(session.calls[1]["headers"]["authorization"], "Bearer access")
        self.assertEqual(session.calls[1]["json"]["limit"], 100)
        self.assertEqual(session.calls[2]["json"]["offerCode"], "26SUM205")
        self.assertEqual(session.calls[2]["json"]["playerOfferId"], "player-offer-1")
        self.assertEqual(session.calls[2]["json"]["limit"], 1)

    async def test_async_get_data_does_not_fetch_club_royale(self) -> None:
        """Core account setup should not use the separate Club Royale session."""

        session = FakeSession(
            [
                FakeResponse(
                    200,
                    {
                        "payload": {
                            "loyaltyInformation": {
                                "crownAndAnchorId": "364350586",
                            }
                        }
                    },
                ),
                FakeResponse(200, {"payload": {"profileBookings": []}}),
                FakeResponse(200, {"payload": []}),
                FakeResponse(200, {"payload": {"loyaltyInformation": {}}}),
                FakeResponse(200, {"payload": {}}),
                FakeResponse(200, {"payload": {"sailings": []}}),
                FakeResponse(403, {"message": "casino session rejected"}),
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

        result = await client.async_get_data()

        self.assertNotIn("club_royale", result)
        self.assertFalse(
            any("/api/casino/" in str(call["url"]) for call in session.calls)
        )

    async def test_loyalty_history_request_includes_loyalty_number(self) -> None:
        """Past cruise history should pass the account loyalty number."""

        session = FakeSession([FakeResponse(200, {"payload": {"sailings": []}})])
        client = api.RCCLClient(
            session,
            api.RCCLCredentials(
                access_token="access",
                account_id="58acd9a0-a469-4177-8e59-7b535575d979",
                vds_id="58acd9a0-a469-4177-8e59-7b535575d979",
            ),
        )

        await client.async_get_loyalty_history(
            {
                "payload": {
                    "loyaltyInformation": {
                        "crownAndAnchorId": "364350586",
                    }
                }
            }
        )

        self.assertTrue(
            session.calls[0]["url"].endswith(
                "/en/royal/web/v1/guestAccounts/loyalty/history/"
                "58acd9a0-a469-4177-8e59-7b535575d979"
            )
        )
        self.assertEqual(session.calls[0]["params"], {"loyaltyNumber": "364350586"})

    async def test_club_royale_fetch_logs_in_with_separate_session(self) -> None:
        """The card data helper should log in and fetch offers in its own session."""

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
                FakeResponse(
                    200,
                    {
                        "payload": {
                            "loyaltyInformation": {
                                "crownAndAnchorId": "364350586",
                            }
                        }
                    },
                ),
                FakeResponse(200, {"html": "club royale offers page"}),
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
                FakeResponse(200, SAMPLE_CLUB_ROYALE_DATA["club_royale"]["offer_details"][0]),
            ]
        )

        result = await api.RCCLClient.async_fetch_club_royale_sailings(
            session,
            "person@example.com",
            "secret",
        )

        self.assertEqual(result[0]["ship_name"], "Wonder of the Seas")
        self.assertEqual(len(session.calls), 6)
        self.assertTrue(session.calls[0]["url"].endswith("/auth/json/authenticate"))
        self.assertEqual(
            session.calls[0]["headers"]["referer"],
            "https://www.royalcaribbean.com/club-royale/signin",
        )
        self.assertTrue(session.calls[1]["url"].endswith("/en/royal/web/v1/authorize"))
        self.assertEqual(
            session.calls[1]["headers"]["referer"],
            "https://www.royalcaribbean.com/",
        )
        self.assertEqual(
            session.calls[2]["url"],
            "https://api.rccl.com/en/royal/web/v3/guestAccounts",
        )
        self.assertTrue(session.calls[3]["url"].endswith("/club-royale/offers"))
        self.assertTrue(session.calls[4]["url"].endswith("/api/casino/v2/offers/merged"))
        self.assertEqual(session.calls[4]["headers"]["authorization"], "Bearer access")
        self.assertIn("/api/casino/v2/offers/merged", session.calls[5]["url"])


class SourceContractTest(unittest.TestCase):
    """Check Home Assistant wiring that is hard to import without HA installed."""

    def test_frontend_registration_is_idempotent_and_entry_backed(self) -> None:
        """The card JS should be registered when a config entry is set up."""

        init_source = (ROOT / "custom_components" / "rccl" / "__init__.py").read_text()
        frontend_source = (
            ROOT / "custom_components" / "rccl" / "frontend.py"
        ).read_text()

        self.assertGreaterEqual(init_source.count("await async_setup_frontend(hass)"), 2)
        self.assertIn("_FRONTEND_REGISTERED", frontend_source)
        self.assertIn("async_register_static_paths", frontend_source)
        self.assertIn("@websocket_api.async_response", frontend_source)
        self.assertIn("_entryIdFromEntities", card_source := (
            ROOT / "custom_components" / "rccl" / "www" / "club-royale-calendar-card.js"
        ).read_text())
        self.assertIn("config_entry_id", card_source)
        self.assertIn("WEBSOCKET_TIMEOUT_MS", card_source)
        self.assertIn("_sendWebsocket", card_source)

    def test_club_royale_has_separate_config_entry_and_entities(self) -> None:
        """Club Royale should be configured and exposed independently."""

        const_source = (ROOT / "custom_components" / "rccl" / "const.py").read_text()
        config_flow_source = (
            ROOT / "custom_components" / "rccl" / "config_flow.py"
        ).read_text()
        init_source = (ROOT / "custom_components" / "rccl" / "__init__.py").read_text()
        coordinator_source = (
            ROOT / "custom_components" / "rccl" / "coordinator.py"
        ).read_text()
        sensor_source = (ROOT / "custom_components" / "rccl" / "sensor.py").read_text()
        card_source = (
            ROOT / "custom_components" / "rccl" / "www" / "club-royale-calendar-card.js"
        ).read_text()

        self.assertIn("CONF_ENTRY_TYPE", const_source)
        self.assertIn("ENTRY_TYPE_CLUB_ROYALE", const_source)
        self.assertIn("CONF_CLUB_ROYALE_LOYALTY_ID", const_source)
        self.assertIn("CLUB_ROYALE_PLATFORMS", const_source)
        self.assertIn("async_show_menu", config_flow_source)
        self.assertIn("async_step_account", config_flow_source)
        self.assertIn("async_step_club_royale", config_flow_source)
        self.assertIn("validate_club_royale_input", config_flow_source)
        self.assertIn("RCCLUrllibSession", config_flow_source)
        self.assertIn("RCCLClubRoyaleDataUpdateCoordinator", coordinator_source)
        self.assertIn("async_get_club_royale_data_for_loyalty_id", coordinator_source)
        self.assertIn("ENTRY_TYPE_CLUB_ROYALE", init_source)
        self.assertIn("CLUB_ROYALE_PLATFORMS", init_source)
        self.assertIn("ClubRoyaleSummarySensor", sensor_source)
        self.assertIn("ClubRoyaleSailingSensor", sensor_source)
        self.assertIn("club_royale_sailing", sensor_source)
        self.assertIn("_sailingsFromEntities", card_source)
        self.assertIn("club_royale_sailing", card_source)
        self.assertIn("_weekLaneCounts", card_source)
        self.assertIn("_weekRowHeight", card_source)
        self.assertIn("_calendarViewportHeight", card_source)
        self.assertIn("_estimatedGridRows", card_source)
        self.assertIn("_displaySailings", card_source)
        self.assertIn("_sailingGroupKey", card_source)
        self.assertIn("_preferredSailing", card_source)
        self.assertIn("source_sailing_id", card_source)
        self.assertIn("offerExpiryTime", card_source)
        self.assertIn("reserve_by_date", card_source)
        self.assertIn("sail_by_date", card_source)
        self.assertIn("_calendarScrollTop", card_source)
        self.assertIn("_currentCalendarScrollTop", card_source)
        self.assertIn("_restoreCalendarScroll", card_source)
        self.assertIn("_resetCalendarScrollOnRender", card_source)
        self.assertIn("_calendarScrollStorageKey", card_source)
        self.assertIn("sessionStorage", card_source)
        self.assertIn("_syncSelectedSailing", card_source)
        self.assertIn("_detailsContent", card_source)
        self.assertIn("data-sailing-details", card_source)
        self.assertIn("calendar-shell", card_source)
        self.assertIn("tabindex=\"0\"", card_source)
        self.assertIn("scrollbar-gutter", card_source)
        self.assertIn("grid-template-rows:${weekRows}", card_source)
        select_body = card_source.split("  _selectSailing", 1)[1].split(
            "\n  _setFilter", 1
        )[0]
        self.assertNotIn("this._render()", select_body)
        self.assertIn("this._syncSelectedSailing()", select_body)

    def test_club_royale_card_has_filter_controls(self) -> None:
        """The Club Royale card should filter sailings by useful offer facets."""

        card_source = (
            ROOT / "custom_components" / "rccl" / "www" / "club-royale-calendar-card.js"
        ).read_text()

        self.assertIn("_filters", card_source)
        self.assertIn("_filteredSailings", card_source)
        self.assertIn("_filterOptions", card_source)
        self.assertIn("_filterBar", card_source)
        self.assertIn("_filterMenu", card_source)
        self.assertIn("_filterValue", card_source)
        self.assertIn("_setFilter", card_source)
        self.assertIn("_setFilterItem", card_source)
        self.assertIn("_selectAllFilterOptions", card_source)
        self.assertIn("_deselectAllFilterOptions", card_source)
        self.assertIn("_resetFilters", card_source)
        self.assertIn("_filterSummary", card_source)
        self.assertIn("_filterSelection", card_source)
        self.assertIn("_normalizeFilterState", card_source)
        self.assertIn("_filterPanelScrollTop", card_source)
        self.assertIn("_currentFilterPanelScrollTop", card_source)
        self.assertIn("_restoreFilterPanelScroll", card_source)
        self.assertIn("_applyEntitySailings", card_source)
        self.assertIn("_sailingsSignature", card_source)
        self.assertIn("_renderOrDefer", card_source)
        self.assertIn("_hasFocusedFilterControl", card_source)
        self.assertIn("_flushDeferredRender", card_source)
        self.assertIn("_pendingRender", card_source)
        self.assertIn("data-filter-key", card_source)
        self.assertIn("data-filter-value", card_source)
        self.assertIn("data-filter-bulk", card_source)
        self.assertIn("data-filter-open", card_source)
        self.assertIn("data-filter-panel", card_source)
        self.assertIn('type="checkbox"', card_source)
        self.assertIn("Select all", card_source)
        self.assertIn("Deselect all", card_source)
        self.assertIn("Reset filters", card_source)
        self.assertIn("details", card_source)
        self.assertIn("summary", card_source)
        self.assertIn("Ship", card_source)
        self.assertIn("Offer type", card_source)
        self.assertIn("Offer", card_source)
        self.assertIn("Departure", card_source)
        self.assertIn("Nights", card_source)
        self.assertIn("ship", card_source)
        self.assertIn("offer_type", card_source)
        self.assertIn("offer", card_source)
        self.assertIn("departure", card_source)
        self.assertIn("nights", card_source)

    def test_hacs_brand_assets_are_packaged(self) -> None:
        """HACS and Home Assistant should have local brand assets to display."""

        brand_dir = ROOT / "custom_components" / "rccl" / "brand"
        manifest_source = (ROOT / "custom_components" / "rccl" / "manifest.json").read_text()
        pyproject_source = (ROOT / "pyproject.toml").read_text()
        generator_source = (ROOT / "scripts" / "generate_brand_assets.py").read_text()

        self.assertTrue((brand_dir / "logo.svg").is_file())
        self.assertTrue((brand_dir / "icon.png").is_file())
        self.assertTrue((brand_dir / "logo.png").is_file())
        self.assertIn('"@javaDevJT"', manifest_source)
        self.assertIn('"http"', manifest_source)
        self.assertIn('"version": "0.1.3"', manifest_source)
        self.assertIn('version = "0.1.3"', pyproject_source)
        self.assertIn(
            "https://www.royalcaribbean.com/myaccount/assets/images/royal/logo.svg",
            generator_source,
        )

    def test_hacs_default_submission_files_are_present(self) -> None:
        """Default HACS repositories expect validation workflows and metadata."""

        init_source = (ROOT / "custom_components" / "rccl" / "__init__.py").read_text()
        workflows = ROOT / ".github" / "workflows"
        license_source = (ROOT / "LICENSE").read_text()
        codeowners_source = (ROOT / ".github" / "CODEOWNERS").read_text()
        hacs_workflow = (workflows / "hacs.yml").read_text()
        hassfest_workflow = (workflows / "hassfest.yml").read_text()
        tests_workflow = (workflows / "tests.yml").read_text()

        self.assertIn("MIT License", license_source)
        self.assertIn("@javaDevJT", codeowners_source)
        self.assertIn("hacs/action@main", hacs_workflow)
        self.assertIn("category: integration", hacs_workflow)
        self.assertIn("home-assistant/actions/hassfest@master", hassfest_workflow)
        self.assertIn("python -m unittest discover -s tests -q", tests_workflow)
        self.assertIn("CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)", init_source)

    def test_club_royale_menu_labels_and_setup_are_nonblocking(self) -> None:
        """Club Royale setup should show labels and not fail on initial refresh."""

        config_flow_source = (
            ROOT / "custom_components" / "rccl" / "config_flow.py"
        ).read_text()
        init_source = (ROOT / "custom_components" / "rccl" / "__init__.py").read_text()
        coordinator_source = (
            ROOT / "custom_components" / "rccl" / "coordinator.py"
        ).read_text()

        self.assertIn('"account": "Royal Caribbean account"', config_flow_source)
        self.assertIn('"club_royale": "Club Royale offers"', config_flow_source)
        club_setup = init_source.split("async def _async_setup_club_royale_entry", 1)[1]
        club_setup = club_setup.split("async def _credentials_from_entry", 1)[0]
        self.assertNotIn("async_config_entry_first_refresh", club_setup)
        self.assertIn("_async_refresh_club_royale_later", init_source)
        club_coordinator = coordinator_source.split(
            "class RCCLClubRoyaleDataUpdateCoordinator", 1
        )[1]
        self.assertIn("except RCCLAuthenticationError as err:", club_coordinator)
        self.assertIn('UpdateFailed(f"Club Royale login failed: {err}")', club_coordinator)

    def test_club_royale_sessions_are_ha_managed_and_reuse_entry_credentials(self) -> None:
        """Club Royale should not close HA sessions or immediately relogin every poll."""

        component_sources = "\n".join(
            path.read_text()
            for path in (ROOT / "custom_components" / "rccl").glob("*.py")
        )
        api_source = (ROOT / "custom_components" / "rccl" / "api.py").read_text()
        config_flow_source = (
            ROOT / "custom_components" / "rccl" / "config_flow.py"
        ).read_text()
        coordinator_source = (
            ROOT / "custom_components" / "rccl" / "coordinator.py"
        ).read_text()
        init_source = (ROOT / "custom_components" / "rccl" / "__init__.py").read_text()

        self.assertNotIn("await session.close()", component_sources)
        self.assertIn("CONF_AUTH_REFERER", config_flow_source)
        self.assertIn("CONF_ACCESS_TOKEN", config_flow_source)
        self.assertIn("auth_referer: str | None = None", api_source)
        self.assertIn("async_get_club_royale_data_for_loyalty_id", api_source)
        self.assertIn("class RCCLUrllibSession", api_source)
        self.assertIn("HTTPCookieProcessor", api_source)
        self.assertIn("asyncio.to_thread", api_source)
        self.assertIn("async_prime_club_royale_session", api_source)
        self.assertIn("_request_text", api_source)
        self.assertIn("/club-royale/offers", api_source)
        self.assertIn(
            '"authorization": f"Bearer {self._credentials.access_token}"',
            api_source,
        )
        self.assertIn("raise err from reauth_err", api_source)
        self.assertIn("credentials_from_stored_data", init_source)
        self.assertIn("RCCLUrllibSession()", init_source)
        club_coordinator = coordinator_source.split(
            "class RCCLClubRoyaleDataUpdateCoordinator", 1
        )[1]
        self.assertIn("client: RCCLClient", club_coordinator)
        self.assertNotIn("async_fetch_club_royale_sailings", club_coordinator)

    def test_club_royale_sailing_entities_are_cleaned_up(self) -> None:
        """Stale Club Royale sailing entities should be removed automatically."""

        const_source = (ROOT / "custom_components" / "rccl" / "const.py").read_text()
        calendar_source = (
            ROOT / "custom_components" / "rccl" / "calendar.py"
        ).read_text()
        card_source = (
            ROOT / "custom_components" / "rccl" / "www" / "club-royale-calendar-card.js"
        ).read_text()
        sensor_source = (ROOT / "custom_components" / "rccl" / "sensor.py").read_text()

        self.assertIn("entity_registry", sensor_source)
        self.assertIn("_remove_stale_club_royale_entities", sensor_source)
        self.assertIn("async_entries_for_config_entry", sensor_source)
        self.assertIn("registry.async_remove", sensor_source)
        self.assertIn("known_sailing_ids.intersection_update", sensor_source)
        self.assertIn("ClubRoyaleOfferSensor", sensor_source)
        self.assertIn("club_royale_offer", sensor_source)
        self.assertIn("_club_royale_offer_unique_id", sensor_source)
        self.assertIn("known_offer_codes.intersection_update", sensor_source)
        self.assertIn("club_royale_offer_summaries", sensor_source)
        self.assertIn('CLUB_ROYALE_PLATFORMS = ["sensor", "calendar"]', const_source)
        self.assertIn("ENTRY_TYPE_CLUB_ROYALE", calendar_source)
        self.assertIn("ClubRoyaleOfferCalendar", calendar_source)
        self.assertIn("known_offer_codes.intersection_update", calendar_source)
        self.assertIn("_club_royale_offer_calendar_unique_id", calendar_source)
        self.assertIn("club_royale_offer_summaries", calendar_source)
        self.assertIn("club_royale_offer_expirations", calendar_source)
        self.assertIn("returnDateForSailing", card_source)
        self.assertIn("nightsFromText", card_source)


if __name__ == "__main__":
    unittest.main()
