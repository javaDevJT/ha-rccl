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
- Add a timeout regression test.
- Add `scripts/live_login_check.py` to test the Python auth path with
  environment-provided credentials without printing secrets.
