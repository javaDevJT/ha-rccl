# 2026-06-01 Login Hang

## Symptom

Home Assistant's Royal Caribbean config form hangs after submitting credentials.

## Root Cause Found In Code

The alpha 2 login path did not set a bounded timeout around the RCCL/OpenAM
network calls. If RCCL stalls, challenges, or never completes an auth response,
the Home Assistant config flow can keep spinning instead of returning a visible
form error.

The first auth request also presented itself as JSON, while the HAR showed
`application/x-www-form-urlencoded` with OpenAM username/password headers and no
meaningful body.

## Fix

- Wrap RCCL HTTP requests in `asyncio.timeout()`.
- Surface timeout as `RCCLApiError`, which the config flow maps to
  `cannot_connect`.
- Send `/auth/json/authenticate` with
  `application/x-www-form-urlencoded` and an empty body.
- Include browser-like `origin`, `referer`, `accept-language`, and `user-agent`
  headers on auth requests.
- Add a timeout regression test.
- Add `scripts/live_login_check.py` to test the Python auth path with
  environment-provided credentials without printing secrets.

## Live Evidence

The sanitized live smoke test completed the full Python auth path:

- `authenticate` step started and returned.
- `authorize` step started and returned.
- login elapsed time was under 6 seconds.
- `guest_account` step started and returned.
- access token, account id, and profile payload were present.

The test did not print token values, account IDs, or credentials.

## Setup Failure After Successful Config Creation

After the config flow could be created, Home Assistant setup immediately failed
with `RCCL did not return a login token`.

Root cause: `async_setup_entry` performed a second login whenever
username/password were stored, even though the config flow had already stored a
fresh access token and account id. The second immediate login could return a
different auth shape or no `tokenId`, causing setup to fail.

Fix: setup now prefers stored `access_token` and `account_id` and only logs in
from username/password when no stored session exists. Username/password are
still attached to runtime credentials so later 401/403 responses can trigger
automatic reauth.
