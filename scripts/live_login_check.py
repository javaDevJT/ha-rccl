"""Live RCCL login check.

Set RCCL_USERNAME and RCCL_PASSWORD in the environment before running.
The script prints only sanitized status and never prints tokens or account IDs.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
from pathlib import Path
import sys
import types
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import time

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
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
        data: str | bytes | None = None,
    ) -> None:
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
            with urlopen(request, timeout=25) as response:
                return response.status, response.read().decode("utf-8")
        except HTTPError as err:
            return err.code, err.read().decode("utf-8")
        except URLError as err:
            raise api.RCCLApiError(f"Network error: {err.reason}") from err


class UrlLibSession:
    """Minimal aiohttp-style session wrapper."""

    def __init__(self) -> None:
        self.request_count = 0

    def request(self, method: str, url: str, **kwargs: Any) -> UrlLibResponse:
        self.request_count += 1
        parsed_step = "authenticate" if "authenticate" in url else "authorize"
        if "guestAccounts" in url:
            parsed_step = "guest_account"
        print(f"step={self.request_count}:{parsed_step}:start")
        return UrlLibResponse(
            method,
            url,
            headers=kwargs.get("headers", {}),
            json_body=kwargs.get("json"),
            data=kwargs.get("data"),
        )


async def main() -> int:
    """Run the live login smoke test."""

    username = os.environ.get("RCCL_USERNAME")
    password = os.environ.get("RCCL_PASSWORD")
    if not username or not password:
        print("Missing RCCL_USERNAME or RCCL_PASSWORD")
        return 2

    start = time.monotonic()
    session = UrlLibSession()
    try:
        credentials = await api.RCCLClient.async_login(
            session,
            username,
            password,
            request_timeout=30,
        )
        print(f"login_elapsed_seconds={time.monotonic() - start:.1f}")
        client = api.RCCLClient(session, credentials)
        account = await client.async_get_account()
    except api.RCCLAuthenticationError as err:
        print(f"elapsed_seconds={time.monotonic() - start:.1f}")
        print(f"login=auth_failed error={err}")
        return 1
    except api.RCCLApiError as err:
        print(f"elapsed_seconds={time.monotonic() - start:.1f}")
        print(f"login=api_failed error={err}")
        return 1

    payload = account.get("payload", {}) if isinstance(account, dict) else {}
    print("login=ok")
    print(f"account_id_present={bool(credentials.account_id)}")
    print(f"access_token_present={bool(credentials.access_token)}")
    print(f"profile_payload_present={bool(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
