# Alpha 2 Release Notes

Tag: `v0.1.0-alpha.2`

This alpha replaces the manual RCCL header-entry setup with a normal
Royal Caribbean login flow.

## Changed

- Config flow now asks for Royal Caribbean email and password instead of
  `access-token`, `account-id`, `appkey`, and `vds-id`.
- Client performs the RCCL two-step web auth flow:
  `POST /auth/json/authenticate`, then
  `POST /v1/oauth2-authorize/en/royal/web/v1/authorize`.
- Account id is derived from the authorize payload or OpenID token claims.
- Tokens are refreshed by logging in again when stored credentials are present.
- Reauthentication flow now asks for fresh RCCL credentials.
- Diagnostics redact username, password, access token, refresh token, id token,
  and booking identifiers.

## Still Known

- Multifactor and bot-challenge flows are not implemented.
- This still needs validation inside a real Home Assistant runtime.
