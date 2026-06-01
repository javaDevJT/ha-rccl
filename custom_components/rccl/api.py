"""API client and data helpers for Royal Caribbean."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import logging
import time
from typing import Any

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_APP_KEY,
    CONF_ID_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    CONF_USERNAME,
    CONF_VDS_ID,
    DEFAULT_APP_KEY,
    DEFAULT_API_BASE_URL,
    DEFAULT_BRAND,
    DEFAULT_LANGUAGE,
    DEFAULT_OAUTH_CLIENT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_WEB_BASE_URL,
    HEADER_ACCESS_TOKEN,
    HEADER_ACCOUNT_ID,
    HEADER_APP_KEY,
    HEADER_VDS_ID,
    REQ_APP_ID,
    REQ_APP_VERSION,
)

_LOGGER = logging.getLogger(__name__)
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)

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
    app_key: str = DEFAULT_APP_KEY
    vds_id: str | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    expires_at: int | None = None
    username: str | None = None
    password: str | None = None
    api_base_url: str = DEFAULT_API_BASE_URL
    web_base_url: str = DEFAULT_WEB_BASE_URL


class RCCLClient:
    """Small async client for the RCCL web account APIs."""

    def __init__(self, session: Any, credentials: RCCLCredentials) -> None:
        self._session = session
        self._credentials = credentials

    @property
    def account_id(self) -> str:
        """Return the configured account id."""

        return self._credentials.account_id

    @property
    def credentials(self) -> RCCLCredentials:
        """Return the active credentials."""

        return self._credentials

    @classmethod
    async def async_login(
        cls,
        session: Any,
        username: str,
        password: str,
        *,
        app_key: str = DEFAULT_APP_KEY,
        api_base_url: str = DEFAULT_API_BASE_URL,
        web_base_url: str = DEFAULT_WEB_BASE_URL,
        brand: str = DEFAULT_BRAND,
        language: str = DEFAULT_LANGUAGE,
        request_timeout: int | float = DEFAULT_REQUEST_TIMEOUT,
    ) -> RCCLCredentials:
        """Log in to RCCL and return API credentials."""

        auth_response = await cls._request_json(
            session,
            "POST",
            f"{web_base_url}/auth/json/authenticate",
            headers={
                "accept": "application/json",
                "accept-api-version": "resource=2.0, protocol=1.0",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/x-www-form-urlencoded",
                HEADER_APP_KEY: app_key,
                "origin": web_base_url,
                "referer": f"{web_base_url}/account/signin",
                "user-agent": _USER_AGENT,
                "X-OpenAM-Username": username,
                "X-OpenAM-Password": password,
            },
            data="",
            auth_request=True,
            timeout=request_timeout,
        )
        token_id = auth_response.get("tokenId")
        if not token_id:
            raise RCCLAuthenticationError("RCCL did not return a login token")

        oauth_response = await cls._request_json(
            session,
            "POST",
            f"{api_base_url}/v1/oauth2-authorize/{language}/{brand}/web/v1/authorize",
            headers={
                "accept": "application/json",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/json",
                "AppKey": app_key,
                "origin": web_base_url,
                "referer": f"{web_base_url}/account/signin",
                "user-agent": _USER_AGENT,
            },
            json_body={"client": DEFAULT_OAUTH_CLIENT, "tokenId": token_id},
            auth_request=True,
            timeout=request_timeout,
        )
        return credentials_from_oauth_response(
            oauth_response,
            username=username,
            password=password,
            app_key=app_key,
            api_base_url=api_base_url,
            web_base_url=web_base_url,
        )

    async def async_reauthenticate(self) -> None:
        """Refresh credentials by logging in again."""

        if not self._credentials.username or not self._credentials.password:
            raise RCCLAuthenticationError("No RCCL username/password available")

        self._credentials = await self.async_login(
            self._session,
            self._credentials.username,
            self._credentials.password,
            app_key=self._credentials.app_key,
            api_base_url=self._credentials.api_base_url,
            web_base_url=self._credentials.web_base_url,
        )

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
        retry_auth: bool = True,
    ) -> JsonObject:
        """Issue an API request."""

        url = f"{self._credentials.api_base_url}{path}"
        headers = self._headers()

        try:
            data = await self._request_json(
                self._session,
                method,
                url,
                headers=headers,
                json_body=json_body,
                params=params,
            )
        except RCCLAuthenticationError:
            if retry_auth and self._credentials.username and self._credentials.password:
                await self.async_reauthenticate()
                return await self._request(
                    method,
                    path,
                    json_body=json_body,
                    params=params,
                    retry_auth=False,
                )
            raise
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

    @staticmethod
    async def _request_json(
        session: Any,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: JsonObject | None = None,
        data: str | bytes | None = None,
        params: dict[str, str] | None = None,
        auth_request: bool = False,
        timeout: int | float = DEFAULT_REQUEST_TIMEOUT,
    ) -> JsonObject:
        """Issue a request and parse a JSON response."""

        request_kwargs: dict[str, Any] = {"headers": headers}
        if json_body is not None:
            request_kwargs["json"] = json_body
        if data is not None:
            request_kwargs["data"] = data
        if params is not None:
            request_kwargs["params"] = params

        try:
            async with asyncio.timeout(timeout):
                async with session.request(method, url, **request_kwargs) as response:
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

        if auth_request and isinstance(data, dict) and data.get("error"):
            raise RCCLAuthenticationError(str(data.get("errorDescription") or data["error"]))
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


def credentials_from_oauth_response(
    response: JsonObject,
    *,
    username: str,
    password: str,
    app_key: str = DEFAULT_APP_KEY,
    api_base_url: str = DEFAULT_API_BASE_URL,
    web_base_url: str = DEFAULT_WEB_BASE_URL,
) -> RCCLCredentials:
    """Create credentials from RCCL's authorize response."""

    data = response.get("payload", response)
    if not isinstance(data, dict):
        raise RCCLAuthenticationError("RCCL returned an invalid login response")

    access_token = _first(data, "access_token", "accessToken")
    id_token = _first(data, "id_token", "idToken", "openIdToken")
    refresh_token = _first(data, "refresh_token", "refreshToken")
    expires_in = _first(data, "expires_in", "expiresIn", "tokenExpiration")
    claims = decode_jwt_payload(id_token) if id_token else {}
    account_id = (
        _first(data, "accountId", "account_id", "vdsId", "vds_id")
        or _first(claims, "accountId", "account_id", "vdsId", "vds_id", "vdsid")
    )

    if not access_token:
        raise RCCLAuthenticationError("RCCL did not return an access token")
    if not account_id:
        raise RCCLAuthenticationError("RCCL did not return an account id")

    return RCCLCredentials(
        access_token=str(access_token),
        account_id=str(account_id),
        app_key=app_key,
        vds_id=str(account_id),
        refresh_token=str(refresh_token) if refresh_token else None,
        id_token=str(id_token) if id_token else None,
        expires_at=_expires_at(expires_in),
        username=username,
        password=password,
        api_base_url=api_base_url,
        web_base_url=web_base_url,
    )


def credentials_from_stored_data(data: JsonObject) -> RCCLCredentials:
    """Create runtime credentials from stored Home Assistant entry data."""

    return RCCLCredentials(
        access_token=str(data[CONF_ACCESS_TOKEN]),
        account_id=str(data[CONF_ACCOUNT_ID]),
        app_key=str(data.get(CONF_APP_KEY, DEFAULT_APP_KEY)),
        vds_id=data.get(CONF_VDS_ID) or data.get(CONF_ACCOUNT_ID),
        refresh_token=data.get(CONF_REFRESH_TOKEN),
        id_token=data.get(CONF_ID_TOKEN),
        expires_at=data.get(CONF_TOKEN_EXPIRES_AT),
        username=data.get(CONF_USERNAME),
        password=data.get(CONF_PASSWORD),
    )


def decode_jwt_payload(token: str) -> JsonObject:
    """Decode an unsigned JWT payload without validating it."""

    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload_part = parts[1]
    padded = payload_part + "=" * (-len(payload_part) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload_data = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}
    return payload_data if isinstance(payload_data, dict) else {}


def _first(source: JsonObject, *keys: str) -> Any:
    """Return the first present value from a mapping."""

    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return None


def _expires_at(expires_in: Any) -> int | None:
    """Return an epoch timestamp from an expires-in value."""

    try:
        return int(time.time()) + int(expires_in)
    except (TypeError, ValueError):
        return None


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
