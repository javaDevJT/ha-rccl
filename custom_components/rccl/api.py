"""API client and data helpers for Royal Caribbean."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import logging
import re
import time
from typing import Any
from http.cookiejar import CookieJar as UrllibCookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_APP_KEY,
    CONF_AUTH_REFERER,
    CONF_AUTHORIZE_REFERER,
    CONF_ID_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    CONF_USERNAME,
    CONF_VDS_ID,
    DEFAULT_APP_KEY,
    DEFAULT_API_BASE_URL,
    DEFAULT_BRAND,
    DEFAULT_CLUB_ROYALE_API_BASE_URL,
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
_CLUB_ROYALE_APPROVED_AGENCY_IDS = ["109638", "388809"]

JsonObject = dict[str, Any]


class RCCLApiError(Exception):
    """Base error for RCCL API failures."""


class RCCLAuthenticationError(RCCLApiError):
    """Raised when RCCL rejects configured credentials."""


class RCCLUrllibSession:
    """Async-compatible urllib session for Club Royale browser endpoints."""

    def __init__(self, cookie_jar: UrllibCookieJar | None = None) -> None:
        self.cookie_jar = cookie_jar or UrllibCookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

    def request(self, method: str, url: str, **kwargs: Any) -> "RCCLUrllibResponse":
        """Return an aiohttp-like request context manager."""

        return RCCLUrllibResponse(
            self,
            method,
            url,
            headers=kwargs.get("headers", {}),
            json_body=kwargs.get("json"),
            data=kwargs.get("data"),
            params=kwargs.get("params"),
        )


class RCCLUrllibResponse:
    """A small aiohttp-style response wrapper around urllib."""

    def __init__(
        self,
        session: RCCLUrllibSession,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: JsonObject | None = None,
        data: str | bytes | None = None,
        params: dict[str, str] | None = None,
    ) -> None:
        self._session = session
        self._method = method
        self._url = _url_with_params(url, params)
        self._headers = headers
        self._json_body = json_body
        self._data = data
        self.status = 0
        self._text = ""

    async def __aenter__(self) -> "RCCLUrllibResponse":
        self.status, self._text = await asyncio.to_thread(self._send)
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def text(self) -> str:
        """Return the response text."""

        return self._text

    def _send(self) -> tuple[int, str]:
        """Send the request in a worker thread."""

        body: bytes | None = None
        if self._json_body is not None:
            body = json.dumps(self._json_body).encode("utf-8")
        elif isinstance(self._data, str):
            body = self._data.encode("utf-8")
        elif isinstance(self._data, bytes):
            body = self._data

        request = Request(
            self._url,
            data=body,
            headers=self._headers,
            method=self._method,
        )
        try:
            with self._session.opener.open(
                request, timeout=DEFAULT_REQUEST_TIMEOUT
            ) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                return response.status, raw.decode(charset, errors="replace")
        except HTTPError as err:
            raw = err.read()
            charset = err.headers.get_content_charset() or "utf-8"
            return err.code, raw.decode(charset, errors="replace")
        except URLError as err:
            raise RCCLApiError(f"Network error connecting to RCCL: {err.reason}") from err


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
    auth_referer: str | None = None
    authorize_referer: str | None = None


class RCCLClient:
    """Small async client for the RCCL web account APIs."""

    def __init__(self, session: Any, credentials: RCCLCredentials) -> None:
        self._session = session
        self._credentials = credentials
        self._club_royale_primed = False

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
        auth_referer: str | None = None,
        authorize_referer: str | None = None,
        brand: str = DEFAULT_BRAND,
        language: str = DEFAULT_LANGUAGE,
        request_timeout: int | float = DEFAULT_REQUEST_TIMEOUT,
    ) -> RCCLCredentials:
        """Log in to RCCL and return API credentials."""

        auth_referer = auth_referer or f"{web_base_url}/account/signin"
        authorize_referer = authorize_referer or f"{web_base_url}/account/signin"

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
                "referer": auth_referer,
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
                "referer": authorize_referer,
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
            auth_referer=auth_referer,
            authorize_referer=authorize_referer,
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
            auth_referer=self._credentials.auth_referer,
            authorize_referer=self._credentials.authorize_referer,
        )
        self._club_royale_primed = False

    @classmethod
    async def async_fetch_club_royale_sailings(
        cls,
        session: Any,
        username: str,
        password: str,
        *,
        app_key: str = DEFAULT_APP_KEY,
        api_base_url: str = DEFAULT_API_BASE_URL,
        web_base_url: str = DEFAULT_WEB_BASE_URL,
        club_api_base_url: str = DEFAULT_CLUB_ROYALE_API_BASE_URL,
    ) -> list[JsonObject]:
        """Log in with a standalone web session and fetch Club Royale sailings."""

        credentials = await cls.async_login(
            session,
            username,
            password,
            app_key=app_key,
            api_base_url=api_base_url,
            web_base_url=web_base_url,
            auth_referer=f"{web_base_url}/club-royale/signin",
            authorize_referer=f"{web_base_url}/",
        )
        client = cls(session, credentials)
        account = await client.async_get_club_royale_account(
            api_base_url=club_api_base_url
        )
        club_royale = await client.async_get_club_royale_data(account)
        return club_royale_sailings({"club_royale": club_royale})

    async def async_get_account(self) -> JsonObject:
        """Fetch the guest account profile."""

        return await self._request(
            "GET",
            f"/en/royal/web/v3/guestAccounts/{self.account_id}",
        )

    async def async_get_club_royale_account(
        self,
        *,
        api_base_url: str = DEFAULT_CLUB_ROYALE_API_BASE_URL,
    ) -> JsonObject:
        """Fetch the Club Royale web-session guest account profile."""

        return await self._request_absolute(
            "GET",
            f"{api_base_url}/en/royal/web/v3/guestAccounts",
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

    async def async_get_loyalty_history(self, account: JsonObject | None = None) -> JsonObject:
        """Fetch historical sailings."""

        params = None
        if account and (loyalty_number := loyalty_number_from_account(account)):
            params = {"loyaltyNumber": loyalty_number}
        return await self._request(
            "GET",
            f"/en/royal/web/v1/guestAccounts/loyalty/history/{self.account_id}",
            params=params,
        )

    async def async_get_club_royale_data(self, account: JsonObject) -> JsonObject:
        """Fetch Club Royale offers and per-offer sailing details."""

        loyalty_id = club_royale_loyalty_id({"account": account})
        if not loyalty_id:
            raise RCCLApiError("RCCL account did not include a loyalty id")

        return await self.async_get_club_royale_data_for_loyalty_id(loyalty_id)

    async def async_get_club_royale_data_for_loyalty_id(
        self, loyalty_id: str
    ) -> JsonObject:
        """Fetch Club Royale offers and per-offer sailing details by loyalty id."""

        if not self._credentials.access_token and (
            self._credentials.username and self._credentials.password
        ):
            await self.async_reauthenticate()
        await self.async_prime_club_royale_session()

        offers = await self._web_request(
            "POST",
            "/api/casino/v2/offers/merged",
            loyalty_id=loyalty_id,
            json_body={
                "sortBy": "offer.reserveByDate",
                "sortDirection": "asc",
                "limit": 100,
                "approvedAgencyIds": _CLUB_ROYALE_APPROVED_AGENCY_IDS,
                "page": 1,
                "digitalRedemption": True,
            },
        )
        detail_fetches = []
        for offer in _club_royale_offers(offers):
            campaign_offer = offer.get("campaignOffer", {})
            if not isinstance(campaign_offer, dict):
                continue
            offer_code = campaign_offer.get("offerCode")
            player_offer_id = offer.get("playerOfferId")
            if not offer_code or not player_offer_id:
                continue
            detail_fetches.append(
                self._web_request(
                    "POST",
                    "/api/casino/v2/offers/merged",
                    loyalty_id=loyalty_id,
                    json_body={
                        "offerCode": offer_code,
                        "playerOfferId": player_offer_id,
                        "sortBy": "offer.reserveByDate",
                        "sortDirection": "asc",
                        "limit": 1,
                        "page": 1,
                        "approvedAgencyIds": _CLUB_ROYALE_APPROVED_AGENCY_IDS,
                        "digitalRedemption": True,
                    },
                )
            )

        offer_details = await asyncio.gather(*detail_fetches) if detail_fetches else []
        return {"offers": offers, "offer_details": list(offer_details)}

    async def async_prime_club_royale_session(self) -> None:
        """Load the Club Royale offers page before calling same-origin APIs."""

        if self._club_royale_primed:
            return

        await self._request_text(
            self._session,
            "GET",
            f"{self._credentials.web_base_url}/club-royale/offers",
            headers={
                "accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,*/*;q=0.8"
                ),
                "accept-language": "en-US,en;q=0.9",
                "referer": f"{self._credentials.web_base_url}/club-royale/signin",
                "user-agent": _USER_AGENT,
            },
        )
        self._club_royale_primed = True

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
            self._optional(lambda: self.async_get_loyalty_history(account), "loyalty_history"),
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

    async def _request_absolute(
        self,
        method: str,
        url: str,
        *,
        json_body: JsonObject | None = None,
        params: dict[str, str] | None = None,
    ) -> JsonObject:
        """Issue an API request to an absolute URL."""

        try:
            data = await self._request_json(
                self._session,
                method,
                url,
                headers=self._headers(),
                json_body=json_body,
                params=params,
            )
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
        if not auth_request and isinstance(data, dict) and data.get("error"):
            raise RCCLApiError(str(data.get("message") or data.get("code") or data["error"]))
        return data

    @staticmethod
    async def _request_text(
        session: Any,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, str] | None = None,
        timeout: int | float = DEFAULT_REQUEST_TIMEOUT,
    ) -> str:
        """Issue a request and return text."""

        request_kwargs: dict[str, Any] = {"headers": headers}
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
                    return text
        except RCCLApiError:
            raise
        except TimeoutError as err:
            raise RCCLApiError("Timed out connecting to RCCL") from err
        except Exception as err:
            raise RCCLApiError(f"Unable to connect to RCCL: {err}") from err

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

    async def _web_request(
        self,
        method: str,
        path: str,
        *,
        loyalty_id: str,
        json_body: JsonObject | None = None,
        retry_auth: bool = True,
    ) -> JsonObject:
        """Issue an RCCL web API request."""

        url = f"{self._credentials.web_base_url}{path}"
        headers = self._web_headers(loyalty_id)

        try:
            return await self._request_json(
                self._session,
                method,
                url,
                headers=headers,
                json_body=json_body,
            )
        except RCCLAuthenticationError as err:
            if retry_auth and self._credentials.username and self._credentials.password:
                try:
                    await self.async_reauthenticate()
                    await self.async_prime_club_royale_session()
                except RCCLAuthenticationError as reauth_err:
                    raise err from reauth_err
                return await self._web_request(
                    method,
                    path,
                    loyalty_id=loyalty_id,
                    json_body=json_body,
                    retry_auth=False,
                )
            raise
        except RCCLApiError:
            raise
        except TimeoutError as err:
            raise RCCLApiError("Timed out connecting to RCCL") from err
        except Exception as err:
            raise RCCLApiError(f"Unable to connect to RCCL: {err}") from err

    def _web_headers(self, loyalty_id: str) -> dict[str, str]:
        """Build headers expected by RCCL web casino APIs."""

        return {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "authorization": f"Bearer {self._credentials.access_token}",
            "content-type": "application/json",
            "origin": self._credentials.web_base_url,
            "referer": f"{self._credentials.web_base_url}/club-royale/offers",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": _USER_AGENT,
            "x-account-id": self.account_id,
            "x-loyalty-id": loyalty_id,
        }


def credentials_from_oauth_response(
    response: JsonObject,
    *,
    username: str,
    password: str,
    app_key: str = DEFAULT_APP_KEY,
    api_base_url: str = DEFAULT_API_BASE_URL,
    web_base_url: str = DEFAULT_WEB_BASE_URL,
    auth_referer: str | None = None,
    authorize_referer: str | None = None,
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
        auth_referer=auth_referer,
        authorize_referer=authorize_referer,
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
        auth_referer=data.get(CONF_AUTH_REFERER),
        authorize_referer=data.get(CONF_AUTHORIZE_REFERER),
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


def _url_with_params(url: str, params: dict[str, str] | None) -> str:
    """Return a URL with encoded query parameters."""

    if not params:
        return url

    parts = urlsplit(url)
    query = urlencode(params)
    if parts.query:
        query = f"{parts.query}&{query}"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


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


def account_loyalty_information(data: JsonObject) -> JsonObject:
    """Return loyalty information from the account profile response."""

    account_payload = payload(data, "account")
    info = account_payload.get("loyaltyInformation", {})
    return info if isinstance(info, dict) else {}


def club_royale_loyalty_id(data: JsonObject) -> str | None:
    """Return the cruise loyalty id required by Club Royale web APIs."""

    loyalty = account_loyalty_information(data)
    value = _first(
        loyalty,
        "crownAndAnchorId",
        "crownAndAnchorNumber",
        "cruiseLoyaltyId",
    )
    return str(value) if value else None


def loyalty_number_from_account(account: JsonObject) -> str | None:
    """Return the loyalty number required by loyalty-history APIs."""

    return club_royale_loyalty_id({"account": account})


def loyalty_summary(data: JsonObject) -> JsonObject:
    """Return loyalty history summary with history-derived fallbacks."""

    summary = payload(data, "loyalty_summary")
    result = dict(summary) if isinstance(summary, dict) else {}
    history = loyalty_sailings(data)
    derived = _derive_loyalty_summary(history)

    total_trips = _first_int(
        result,
        "totalTrips",
        "totalTripCount",
        "totalCruiseTrips",
        "totalCruises",
        "completedCruises",
    )
    total_nights = _first_int(
        result,
        "totalNights",
        "totalNightCount",
        "totalCruiseNights",
        "totalSailingNights",
        "cruiseNights",
    )

    if (total_trips is None or total_trips == 0) and derived["totalTrips"] > 0:
        total_trips = derived["totalTrips"]
    if (total_nights is None or total_nights == 0) and derived["totalNights"] > 0:
        total_nights = derived["totalNights"]

    if total_trips is not None:
        result["totalTrips"] = total_trips
    if total_nights is not None:
        result["totalNights"] = total_nights
    return result


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
    """Return booking attributes intentionally exposed in Home Assistant."""

    if not booking:
        return {}
    attributes = {
        "booking_id": _first(
            booking,
            "bookingId",
            "bookingID",
            "reservationId",
            "reservationNumber",
            "id",
        ),
        "sail_date": booking.get("sailDate"),
        "ship_code": booking.get("shipCode"),
        "package_code": booking.get("packageCode"),
        "number_of_nights": booking.get("numberOfNights"),
        "booking_status": booking.get("bookingStatus"),
        "stateroom_type": booking.get("stateroomType"),
    }
    passengers = _passenger_attributes(booking)
    if passengers:
        attributes["passengers"] = passengers
    return attributes


def club_royale_sailings(data: JsonObject) -> list[JsonObject]:
    """Return normalized Club Royale offer sailings for the custom card."""

    club_royale = data.get("club_royale", {})
    if not isinstance(club_royale, dict):
        return []

    rows: list[JsonObject] = []
    for detail in club_royale.get("offer_details", []):
        if not isinstance(detail, dict):
            continue
        for offer in _club_royale_offers(detail):
            rows.extend(_normalize_club_royale_offer_sailings(offer))
    return sorted(rows, key=lambda item: (item["sail_date"], item["ship_name"]))


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


def _club_royale_offers(response: JsonObject) -> list[JsonObject]:
    """Return offers from a Club Royale response."""

    offers = response.get("offers", [])
    return [offer for offer in offers if isinstance(offer, dict)]


def _normalize_club_royale_offer_sailings(offer: JsonObject) -> list[JsonObject]:
    """Normalize all sailing rows from one Club Royale offer."""

    campaign_offer = offer.get("campaignOffer", {})
    if not isinstance(campaign_offer, dict):
        return []

    offer_name = campaign_offer.get("name") or offer.get("campaignName")
    offer_type = campaign_offer.get("offerType", {})
    offer_type_name = (
        offer_type.get("name") if isinstance(offer_type, dict) else offer_type
    )
    occupancy_key, occupancy_label = _offer_occupancy(
        campaign_offer.get("description"),
        offer_type_name,
        offer_name,
        offer.get("campaignName"),
    )

    rows = []
    sailings = campaign_offer.get("sailings", [])
    if not isinstance(sailings, list):
        return rows

    for sailing in sailings:
        if not isinstance(sailing, dict):
            continue
        sail_date = parse_rccl_date(sailing.get("sailDate"))
        if not sail_date:
            continue
        nights = _int_or_default(sailing.get("totalNights"), 0)
        return_date = sail_date + timedelta(days=max(nights, 0))
        ship_name = str(sailing.get("shipName") or sailing.get("shipCode") or "")
        itinerary_name = _sailing_name(sailing)
        room_types = _room_types(sailing)
        row = {
            "id": str(
                sailing.get("id")
                or f"{campaign_offer.get('offerCode')}:{sailing.get('shipCode')}:{sail_date}"
            ),
            "sail_date": sail_date.isoformat(),
            "return_date": return_date.isoformat(),
            "total_nights": nights,
            "impacted_days": nights + 1,
            "ship_code": sailing.get("shipCode"),
            "ship_name": ship_name,
            "itinerary_code": sailing.get("itineraryCode"),
            "itinerary_name": itinerary_name,
            "itinerary_description": sailing.get("itineraryDescription"),
            "sailing_type": _nested_name(sailing.get("sailingType")),
            "departure_port": _port(sailing.get("departurePort")),
            "room_types": room_types,
            "is_guarantee": sailing.get("isGTY") is True,
            "cabin_guarantee": _cabin_guarantee(sailing, room_types),
            "offer_name": offer_name,
            "offer_code": campaign_offer.get("offerCode"),
            "offer_type": offer_type_name,
            "offer_occupancy": occupancy_key,
            "offer_occupancy_label": occupancy_label,
            "reserve_by_date": _date_string(campaign_offer.get("reserveByDate")),
            "sail_by_date": _date_string(campaign_offer.get("sailByDate")),
            "calendar_title": _calendar_title(itinerary_name, ship_name),
        }
        rows.append({key: value for key, value in row.items() if value not in (None, "")})
    return rows


def _sailing_name(sailing: JsonObject) -> str:
    """Return the best human sailing name."""

    return str(
        sailing.get("itineraryName")
        or _nested_name(sailing.get("sailingType"))
        or sailing.get("itineraryDescription")
        or "Royal Caribbean sailing"
    )


def _nested_name(value: Any) -> Any:
    """Return a nested object's name field when present."""

    return value.get("name") if isinstance(value, dict) else value


def _port(value: Any) -> JsonObject | None:
    """Normalize a port mapping."""

    if not isinstance(value, dict):
        return None
    return {key: value.get(key) for key in ("code", "name") if value.get(key)}


def _room_types(sailing: JsonObject) -> list[JsonObject]:
    """Normalize room category data."""

    room_types = sailing.get("roomTypeList", [])
    if not isinstance(room_types, list):
        return []
    return [
        {key: room.get(key) for key in ("code", "name") if room.get(key)}
        for room in room_types
        if isinstance(room, dict)
    ]


def _cabin_guarantee(sailing: JsonObject, room_types: list[JsonObject]) -> str | None:
    """Return a compact cabin category/guarantee label."""

    names = [str(room.get("name")) for room in room_types if room.get("name")]
    if not names:
        return "Guarantee" if sailing.get("isGTY") is True else None
    label = " / ".join(names)
    return f"{label} Guarantee" if sailing.get("isGTY") is True else label


def _offer_occupancy(*values: Any) -> tuple[str | None, str | None]:
    """Infer offer occupancy from RCCL's offer labels."""

    text = " ".join(str(value or "") for value in values).lower()
    if re.search(r"\bfor\s+(?:two|2)\s+(?:guest|passenger)s?\b", text):
        return "two_passengers", "Two passengers"
    if re.search(r"\bfor\s+(?:one|1)\s+(?:guest|passenger)s?\b", text):
        return "one_passenger", "One passenger"
    if re.search(r"\bfor\s+(?:two|2)\b", text):
        return "two_passengers", "Two passengers"
    if re.search(r"\bfor\s+(?:one|1)\b", text):
        return "one_passenger", "One passenger"
    return None, None


def _date_string(value: Any) -> str | None:
    """Return an ISO date string from an RCCL date value."""

    parsed = parse_rccl_date(value)
    return parsed.isoformat() if parsed else None


def _calendar_title(itinerary_name: str, ship_name: str) -> str:
    """Return the card range-bar title."""

    return f"{itinerary_name} - {ship_name}" if ship_name else itinerary_name


def _first_int(source: JsonObject, *keys: str) -> int | None:
    """Return the first integer-like value from a mapping."""

    for key in keys:
        if key not in source:
            continue
        try:
            return int(source[key])
        except (TypeError, ValueError):
            continue
    return None


def _derive_loyalty_summary(sailings: list[JsonObject]) -> JsonObject:
    """Derive total trips and nights from loyalty-history sailings."""

    total_nights = 0
    for sailing in sailings:
        total_nights += _int_or_default(
            _first(
                sailing,
                "itineraryNightsQuantity",
                "numberOfNights",
                "totalNights",
                "nights",
            ),
            0,
        )
    return {"totalTrips": len(sailings), "totalNights": total_nights}


def _passenger_attributes(booking: JsonObject) -> list[JsonObject]:
    """Return normalized passenger identity attributes from a booking."""

    for key in (
        "passengers",
        "passengerDetails",
        "guests",
        "guestDetails",
        "bookingGuests",
        "reservationGuests",
    ):
        passengers = booking.get(key)
        if not isinstance(passengers, list):
            continue
        normalized = [
            _normalize_passenger(passenger)
            for passenger in passengers
            if isinstance(passenger, dict)
        ]
        return [passenger for passenger in normalized if passenger]
    return []


def _normalize_passenger(passenger: JsonObject) -> JsonObject:
    """Normalize passenger fields to stable Home Assistant attribute names."""

    fields = {
        "first_name": _first(passenger, "firstName", "first_name", "givenName"),
        "last_name": _first(passenger, "lastName", "last_name", "surname"),
        "guest_id": _first(passenger, "guestId", "guestID", "id", "passengerId"),
        "crown_and_anchor_number": _first(
            passenger,
            "crownAndAnchorNumber",
            "crownAndAnchorId",
            "cruiseLoyaltyId",
            "loyaltyNumber",
        ),
    }
    return {key: value for key, value in fields.items() if value not in (None, "")}
