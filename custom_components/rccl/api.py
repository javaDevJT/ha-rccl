"""API client and data helpers for Royal Caribbean."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import logging
from typing import Any

from .const import (
    DEFAULT_API_BASE_URL,
    HEADER_ACCESS_TOKEN,
    HEADER_ACCOUNT_ID,
    HEADER_APP_KEY,
    HEADER_VDS_ID,
    REQ_APP_ID,
    REQ_APP_VERSION,
)

_LOGGER = logging.getLogger(__name__)

JsonObject = dict[str, Any]


class RCCLApiError(Exception):
    """Base error for RCCL API failures."""


class RCCLAuthenticationError(RCCLApiError):
    """Raised when RCCL rejects configured credentials."""


@dataclass(frozen=True)
class RCCLCredentials:
    """Headers required by RCCL account APIs."""

    access_token: str
    account_id: str
    app_key: str
    vds_id: str | None = None
    api_base_url: str = DEFAULT_API_BASE_URL


class RCCLClient:
    """Small async client for the RCCL web account APIs."""

    def __init__(self, session: Any, credentials: RCCLCredentials) -> None:
        self._session = session
        self._credentials = credentials

    @property
    def account_id(self) -> str:
        """Return the configured account id."""

        return self._credentials.account_id

    async def async_get_account(self) -> JsonObject:
        """Fetch the guest account profile."""

        return await self._request(
            "GET",
            f"/en/royal/web/v3/guestAccounts/{self.account_id}",
        )

    async def async_get_profile_bookings(self) -> JsonObject:
        """Fetch enriched profile bookings."""

        return await self._request(
            "GET",
            f"/v1/profileBookings/enriched/{self.account_id}",
        )

    async def async_get_upgrades(self) -> JsonObject:
        """Fetch RoyalUp eligibility data."""

        return await self._request("GET", "/en/R/web/v1/guestAccounts/upgrades")

    async def async_get_loyalty_info(self) -> JsonObject:
        """Fetch loyalty tier and points."""

        return await self._request("GET", "/en/royal/web/v1/guestAccounts/loyalty/info")

    async def async_get_loyalty_history_summary(self) -> JsonObject:
        """Fetch total cruise nights and trips."""

        return await self._request(
            "GET",
            "/en/royal/web/v1/guestAccounts/loyalty/history/summary",
        )

    async def async_get_loyalty_history(self) -> JsonObject:
        """Fetch historical sailings."""

        return await self._request(
            "GET",
            f"/en/royal/web/v1/guestAccounts/loyalty/history/{self.account_id}",
        )

    async def async_get_data(self) -> JsonObject:
        """Fetch all data used by the Home Assistant entities."""

        account, bookings = await asyncio.gather(
            self.async_get_account(),
            self.async_get_profile_bookings(),
        )
        optional = await asyncio.gather(
            self._optional(self.async_get_upgrades, "upgrades"),
            self._optional(self.async_get_loyalty_info, "loyalty"),
            self._optional(self.async_get_loyalty_history_summary, "loyalty_summary"),
            self._optional(self.async_get_loyalty_history, "loyalty_history"),
        )

        return {
            "account": account,
            "bookings": bookings,
            "upgrades": optional[0],
            "loyalty": optional[1],
            "loyalty_summary": optional[2],
            "loyalty_history": optional[3],
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }

    async def _optional(self, fetcher: Any, label: str) -> JsonObject:
        """Fetch optional data and keep core booking polling alive."""

        try:
            return await fetcher()
        except RCCLAuthenticationError:
            raise
        except RCCLApiError as err:
            _LOGGER.warning("Unable to fetch optional RCCL %s data: %s", label, err)
            return {"status": "unavailable", "errors": [{"message": str(err)}]}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: JsonObject | None = None,
        params: dict[str, str] | None = None,
    ) -> JsonObject:
        """Issue an API request."""

        url = f"{self._credentials.api_base_url}{path}"
        headers = self._headers()

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
            ) as response:
                text = await response.text()
                if response.status in (401, 403):
                    raise RCCLAuthenticationError(
                        f"RCCL rejected credentials with HTTP {response.status}"
                    )
                if response.status < 200 or response.status >= 300:
                    raise RCCLApiError(f"RCCL API returned HTTP {response.status}")
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError as err:
                    raise RCCLApiError("RCCL API returned invalid JSON") from err
        except RCCLApiError:
            raise
        except TimeoutError as err:
            raise RCCLApiError("Timed out connecting to RCCL") from err
        except Exception as err:
            raise RCCLApiError(f"Unable to connect to RCCL: {err}") from err

        errors = data.get("errors") if isinstance(data, dict) else None
        if errors:
            raise RCCLApiError(f"RCCL API returned {len(errors)} error(s)")
        return data

    def _headers(self) -> dict[str, str]:
        """Build headers expected by RCCL account APIs."""

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            HEADER_ACCESS_TOKEN: self._credentials.access_token,
            HEADER_ACCOUNT_ID: self._credentials.account_id,
            HEADER_APP_KEY: self._credentials.app_key,
            "req-app-id": REQ_APP_ID,
            "req-app-vers": REQ_APP_VERSION,
        }
        if self._credentials.vds_id:
            headers[HEADER_VDS_ID] = self._credentials.vds_id
        return headers


def payload(data: JsonObject, key: str) -> Any:
    """Return the payload from a stored API response."""

    value = data.get(key, {})
    return value.get("payload", {}) if isinstance(value, dict) else {}


def profile_bookings(data: JsonObject) -> list[JsonObject]:
    """Return profile bookings from coordinator data."""

    bookings_payload = payload(data, "bookings")
    bookings = bookings_payload.get("profileBookings", [])
    return [item for item in bookings if isinstance(item, dict)]


def loyalty_sailings(data: JsonObject) -> list[JsonObject]:
    """Return loyalty-history sailings from coordinator data."""

    history_payload = payload(data, "loyalty_history")
    sailings = history_payload.get("sailings", [])
    return [item for item in sailings if isinstance(item, dict)]


def upgrade_items(data: JsonObject) -> list[JsonObject]:
    """Return upgrade eligibility rows from coordinator data."""

    upgrades = payload(data, "upgrades")
    if isinstance(upgrades, list):
        return [item for item in upgrades if isinstance(item, dict)]
    return []


def loyalty_information(data: JsonObject) -> JsonObject:
    """Return loyalty information."""

    info = payload(data, "loyalty").get("loyaltyInformation", {})
    return info if isinstance(info, dict) else {}


def loyalty_summary(data: JsonObject) -> JsonObject:
    """Return loyalty history summary."""

    summary = payload(data, "loyalty_summary")
    return summary if isinstance(summary, dict) else {}


def parse_rccl_date(value: Any) -> date | None:
    """Parse date values observed in RCCL payloads."""

    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def booking_sail_date(booking: JsonObject) -> date | None:
    """Return a booking's sail date."""

    return parse_rccl_date(booking.get("sailDate") or booking.get("sailingDate"))


def upcoming_bookings(data: JsonObject, today: date | None = None) -> list[JsonObject]:
    """Return bookings with sail dates today or later."""

    today = today or date.today()
    bookings = [
        booking
        for booking in profile_bookings(data)
        if (booking_date := booking_sail_date(booking)) and booking_date >= today
    ]
    return sorted(bookings, key=lambda item: booking_sail_date(item) or date.max)


def next_booking(data: JsonObject, today: date | None = None) -> JsonObject | None:
    """Return the next upcoming cruise booking."""

    bookings = upcoming_bookings(data, today)
    return bookings[0] if bookings else None


def crown_anchor_value(data: JsonObject, suffix: str) -> Any:
    """Return a Crown & Anchor loyalty value by suffix."""

    loyalty = loyalty_information(data)
    direct_key = f"crownAndAnchorSociety{suffix}"
    if direct_key in loyalty:
        return loyalty[direct_key]

    for key, value in loyalty.items():
        if key.lower().endswith(suffix.lower()) and "crown" in key.lower():
            return value
    return None


def upgrade_eligible_count(data: JsonObject) -> int:
    """Return the number of bookings eligible for RoyalUp."""

    return sum(1 for item in upgrade_items(data) if item.get("upgradeEligible") is True)


def safe_booking_attributes(booking: JsonObject | None) -> JsonObject:
    """Return booking attributes safe for Home Assistant state history."""

    if not booking:
        return {}
    return {
        "sail_date": booking.get("sailDate"),
        "ship_code": booking.get("shipCode"),
        "package_code": booking.get("packageCode"),
        "number_of_nights": booking.get("numberOfNights"),
        "booking_status": booking.get("bookingStatus"),
        "stateroom_type": booking.get("stateroomType"),
    }


def cruise_events(data: JsonObject) -> list[JsonObject]:
    """Build normalized all-day cruise events from booking/history data."""

    events: dict[str, JsonObject] = {}
    for booking in profile_bookings(data):
        start = booking_sail_date(booking)
        if not start:
            continue
        nights = _int_or_default(booking.get("numberOfNights"), 1)
        key = _event_key(booking.get("bookingId"), start, booking.get("shipCode"))
        events[key] = {
            "start": start,
            "end": start + timedelta(days=max(nights, 1) + 1),
            "summary": _summary(booking.get("shipCode")),
            "description": _description(
                nights=nights,
                status=booking.get("bookingStatus"),
                package=booking.get("packageCode"),
                ship=booking.get("shipCode"),
            ),
            "location": None,
        }

    for sailing in loyalty_sailings(data):
        start = parse_rccl_date(sailing.get("sailingDate"))
        if not start:
            continue
        nights = _int_or_default(sailing.get("itineraryNightsQuantity"), 1)
        key = _event_key(sailing.get("bookingId"), start, sailing.get("shipCode"))
        events.setdefault(
            key,
            {
                "start": start,
                "end": start + timedelta(days=max(nights, 1) + 1),
                "summary": _summary(sailing.get("shipName") or sailing.get("shipCode")),
                "description": _description(
                    nights=nights,
                    status=sailing.get("status"),
                    package=sailing.get("itineraryCode"),
                    ship=sailing.get("shipName") or sailing.get("shipCode"),
                ),
                "location": sailing.get("originPortDescription"),
            },
        )

    return sorted(events.values(), key=lambda item: item["start"])


def _event_key(booking_id: Any, start: date, ship: Any) -> str:
    """Return a stable event key without exposing it outside this module."""

    return f"{booking_id or 'unknown'}:{start.isoformat()}:{ship or 'ship'}"


def _summary(ship: Any) -> str:
    """Return a calendar summary."""

    return f"Royal Caribbean cruise ({ship})" if ship else "Royal Caribbean cruise"


def _description(*, nights: int, status: Any, package: Any, ship: Any) -> str:
    """Return a compact event description."""

    parts = [f"{nights} night cruise"]
    if ship:
        parts.append(f"Ship: {ship}")
    if package:
        parts.append(f"Itinerary/package: {package}")
    if status:
        parts.append(f"Status: {status}")
    return "\n".join(parts)


def _int_or_default(value: Any, default: int) -> int:
    """Coerce a value to int."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default
