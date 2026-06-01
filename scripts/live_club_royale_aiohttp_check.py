"""Live aiohttp Club Royale smoke check.

Set RCCL_USERNAME and RCCL_PASSWORD in the environment before running. The
script prints only sanitized request status and never prints credentials, tokens,
account identifiers, or loyalty identifiers.
"""

from __future__ import annotations

import asyncio
import importlib
import os
from pathlib import Path
import sys
import types
from typing import Any

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = types.ModuleType("custom_components")
RCCL_PACKAGE = types.ModuleType("custom_components.rccl")
CUSTOM_COMPONENTS.__path__ = [str(ROOT / "custom_components")]
RCCL_PACKAGE.__path__ = [str(ROOT / "custom_components" / "rccl")]
sys.modules.setdefault("custom_components", CUSTOM_COMPONENTS)
sys.modules.setdefault("custom_components.rccl", RCCL_PACKAGE)

api = importlib.import_module("custom_components.rccl.api")


def _step_name(url: str) -> str:
    """Return a sanitized request step name."""

    if "/auth/json/authenticate" in url:
        return "authenticate"
    if "/oauth2-authorize/" in url:
        return "authorize"
    if "/guestAccounts" in url:
        return "club_guest_account"
    if "/club-royale/offers" in url:
        return "club_offers_page"
    if "/api/casino/v2/offers/merged" in url:
        return "offers_merged"
    if "/api/casino/v1/loyalty-data" in url:
        return "casino_loyalty"
    return "request"


def _safe_header_summary(headers: dict[str, str]) -> dict[str, object]:
    """Return non-secret request header diagnostics."""

    return {
        "accept": headers.get("accept"),
        "content_type": headers.get("content-type"),
        "origin": headers.get("origin"),
        "referer": headers.get("referer"),
        "authorization_present": bool(headers.get("authorization")),
        "x_account_id_present": bool(headers.get("x-account-id")),
        "x_loyalty_id_present": bool(headers.get("x-loyalty-id")),
        "sec_fetch_site": headers.get("sec-fetch-site"),
        "user_agent_present": bool(headers.get("user-agent")),
    }


class DebugAiohttpResponse:
    """Minimal aiohttp response wrapper that prints sanitized diagnostics."""

    def __init__(
        self,
        session: "DebugAiohttpSession",
        request_number: int,
        step: str,
        headers: dict[str, str],
        context_manager: Any,
    ) -> None:
        self._session = session
        self._request_number = request_number
        self._step = step
        self._headers = headers
        self._context_manager = context_manager
        self._response: Any = None
        self.status = 0

    async def __aenter__(self) -> "DebugAiohttpResponse":
        self._response = await self._context_manager.__aenter__()
        self.status = self._response.status
        cookie_count = sum(1 for _ in self._session.inner.cookie_jar)
        print(
            f"aiohttp_step={self._request_number}:{self._step}:"
            f"status={self.status}:final_url={self._response.url}:"
            f"cookies={cookie_count}:set_cookie_count={len(self._response.cookies)}"
        )
        if self._step in {"club_offers_page", "offers_merged", "casino_loyalty"}:
            print(
                f"aiohttp_headers_{self._request_number}="
                f"{_safe_header_summary(self._headers)}"
            )
            print(
                f"aiohttp_content_type_{self._request_number}="
                f"{self._response.headers.get('content-type')}"
            )
        return self

    async def __aexit__(self, *args: object) -> object:
        return await self._context_manager.__aexit__(*args)

    async def text(self) -> str:
        """Return text while printing a sanitized prefix for relevant calls."""

        text = await self._response.text()
        if self._step in {"club_offers_page", "offers_merged", "casino_loyalty"}:
            prefix = text[:120].replace("\n", " ").replace("\r", " ")
            print(f"aiohttp_text_prefix_{self._request_number}={prefix}")
        return text


class DebugAiohttpSession:
    """Minimal aiohttp session wrapper for RCCLClient tests."""

    def __init__(self, inner: aiohttp.ClientSession) -> None:
        self.inner = inner
        self.request_count = 0

    def request(self, method: str, url: str, **kwargs: Any) -> DebugAiohttpResponse:
        """Return a wrapped request context manager."""

        self.request_count += 1
        request_number = self.request_count
        step = _step_name(str(url))
        headers = kwargs.get("headers", {})
        print(f"aiohttp_step={request_number}:{step}:start")
        return DebugAiohttpResponse(
            self,
            request_number,
            step,
            headers,
            self.inner.request(method, url, **kwargs),
        )


async def _fetch_with_session(
    label: str,
    session: aiohttp.ClientSession,
    credentials: Any,
    loyalty_id: str,
) -> int:
    """Fetch Club Royale data with an existing aiohttp session."""

    client = api.RCCLClient(DebugAiohttpSession(session), credentials)
    try:
        data = await client.async_get_club_royale_data_for_loyalty_id(loyalty_id)
    except Exception as err:  # noqa: BLE001 - live diagnostic script.
        print(f"{label}_result=failed type={type(err).__name__} error={err}")
        return 1

    offers = data.get("offers", {}).get("offers", [])
    sailings = api.club_royale_sailings({"club_royale": data})
    print(f"{label}_result=ok")
    print(f"{label}_offer_count={len(offers) if isinstance(offers, list) else 0}")
    print(f"{label}_sailing_count={len(sailings)}")
    return 0


async def main() -> int:
    """Run the live aiohttp Club Royale check."""

    username = os.environ.get("RCCL_USERNAME")
    password = os.environ.get("RCCL_PASSWORD")
    if not username or not password:
        print("missing_credentials=true")
        return 2

    auth_referer = "https://www.royalcaribbean.com/club-royale/signin"
    authorize_referer = "https://www.royalcaribbean.com/"
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
        debug_session = DebugAiohttpSession(session)
        credentials = await api.RCCLClient.async_login(
            debug_session,
            username,
            password,
            auth_referer=auth_referer,
            authorize_referer=authorize_referer,
            request_timeout=35,
        )
        account = await api.RCCLClient(
            debug_session, credentials
        ).async_get_club_royale_account()
        loyalty_id = api.club_royale_loyalty_id({"account": account})
        print(f"club_loyalty_id_present={bool(loyalty_id)}")
        if not loyalty_id:
            return 1
        same_result = await _fetch_with_session(
            "same_session", session, credentials, loyalty_id
        )

    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as fresh_session:
        fresh_result = await _fetch_with_session(
            "fresh_session", fresh_session, credentials, loyalty_id
        )

    return 0 if same_result == 0 and fresh_result == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

