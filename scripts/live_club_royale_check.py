"""Live Club Royale smoke check.

Set RCCL_USERNAME and RCCL_PASSWORD in the environment before running.
The script prints only sanitized status and never prints credentials, tokens, or
account identifiers.
"""

from __future__ import annotations

import asyncio
from http.cookiejar import CookieJar
import importlib
import json
import os
from pathlib import Path
import sys
import time
import types
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = types.ModuleType("custom_components")
RCCL_PACKAGE = types.ModuleType("custom_components.rccl")
CUSTOM_COMPONENTS.__path__ = [str(ROOT / "custom_components")]
RCCL_PACKAGE.__path__ = [str(ROOT / "custom_components" / "rccl")]
sys.modules.setdefault("custom_components", CUSTOM_COMPONENTS)
sys.modules.setdefault("custom_components.rccl", RCCL_PACKAGE)

api = importlib.import_module("custom_components.rccl.api")


class UrlLibResponse:
    """Minimal aiohttp-style response wrapper."""

    def __init__(
        self,
        session: "CookieSession",
        request_number: int,
        step: str,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
        data: str | bytes | None = None,
    ) -> None:
        self._session = session
        self._request_number = request_number
        self._step = step
        self._method = method
        self._url = url
        self._headers = headers
        self._json_body = json_body
        self._data = data
        self.status = 0
        self._text = ""

    async def __aenter__(self) -> "UrlLibResponse":
        self.status, self._text = await asyncio.to_thread(self._send)
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def text(self) -> str:
        return self._text

    def _send(self) -> tuple[int, str]:
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
            with self._session.opener.open(request, timeout=30) as response:
                text = response.read().decode("utf-8")
                print(
                    f"step={self._request_number}:"
                    f"{self._step}:status={response.status}"
                )
                return response.status, text
        except HTTPError as err:
            text = err.read().decode("utf-8")
            print(
                f"step={self._request_number}:"
                f"{self._step}:status={err.code}"
            )
            return err.code, text
        except URLError as err:
            raise api.RCCLApiError(f"Network error: {err.reason}") from err


class CookieSession:
    """Minimal aiohttp-style session with cookies."""

    def __init__(self) -> None:
        self.request_count = 0
        self.step = "request"
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(self, method: str, url: str, **kwargs: Any) -> UrlLibResponse:
        self.request_count += 1
        request_number = self.request_count
        self.step = _step_name(url)
        print(f"step={request_number}:{self.step}:start")
        return UrlLibResponse(
            self,
            request_number,
            self.step,
            method,
            url,
            headers=kwargs.get("headers", {}),
            json_body=kwargs.get("json"),
            data=kwargs.get("data"),
        )


def _step_name(url: str) -> str:
    if "/auth/json/authenticate" in url:
        return "authenticate"
    if "/oauth2-authorize/" in url:
        return "authorize"
    if "/guestAccounts" in url:
        return "club_guest_account"
    if "/api/casino/v2/offers/merged" in url:
        return "offers_merged"
    if "/api/casino/v1/loyalty-data" in url:
        return "casino_loyalty"
    if "/club-royale/offers" in url:
        return "club_offers_page"
    return "request"


async def main() -> int:
    """Run the live Club Royale check."""

    username = os.environ.get("RCCL_USERNAME")
    password = os.environ.get("RCCL_PASSWORD")
    if not username or not password:
        print("missing_credentials=true")
        return 2

    start = time.monotonic()
    session = CookieSession()
    try:
        credentials = await api.RCCLClient.async_login(
            session,
            username,
            password,
            auth_referer="https://www.royalcaribbean.com/club-royale/signin",
            authorize_referer="https://www.royalcaribbean.com/",
            request_timeout=35,
        )
        client = api.RCCLClient(session, credentials)
        account = await client.async_get_club_royale_account()
        loyalty_id = api.club_royale_loyalty_id({"account": account})
        if not loyalty_id:
            print("club_loyalty_id_present=false")
            return 1
        club_royale = await client.async_get_club_royale_data_for_loyalty_id(loyalty_id)
        sailings = api.club_royale_sailings({"club_royale": club_royale})
    except api.RCCLAuthenticationError as err:
        print(f"elapsed_seconds={time.monotonic() - start:.1f}")
        print(f"result=auth_failed error={err}")
        return 1
    except api.RCCLApiError as err:
        print(f"elapsed_seconds={time.monotonic() - start:.1f}")
        print(f"result=api_failed error={err}")
        return 1

    offers = club_royale.get("offers", {}).get("offers", [])
    details = club_royale.get("offer_details", [])
    print(f"elapsed_seconds={time.monotonic() - start:.1f}")
    print("result=ok")
    print(f"access_token_present={bool(credentials.access_token)}")
    print(f"account_id_present={bool(credentials.account_id)}")
    print(f"club_loyalty_id_present={bool(loyalty_id)}")
    print(f"offer_count={len(offers) if isinstance(offers, list) else 0}")
    print(f"detail_response_count={len(details) if isinstance(details, list) else 0}")
    print(f"sailing_count={len(sailings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
