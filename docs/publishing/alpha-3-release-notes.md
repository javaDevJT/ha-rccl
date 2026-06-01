# Alpha 3 Release Notes

Tag: `v0.1.0-alpha.3`

This alpha fixes a config-flow hang reported during login testing.

## Fixed

- Added bounded timeouts around RCCL auth and API requests.
- Timeout failures now return a visible Home Assistant config-flow error instead
  of letting the login form spin indefinitely.
- Adjusted `/auth/json/authenticate` to match the captured RCCL HAR more
  closely: OpenAM username/password headers with an empty form-encoded body.
- Added a sanitized live login smoke-test helper:
  `scripts/live_login_check.py`.

## Still Known

- Multifactor and bot-challenge flows are not implemented.
- A live Home Assistant runtime test is still needed.
