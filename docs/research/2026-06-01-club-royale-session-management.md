# 2026-06-01 Club Royale Session Management

## Symptoms

Home Assistant reported:

`Detected that custom integration 'rccl' closes the Home Assistant aiohttp session`

The Club Royale coordinator also continued to report:

`Club Royale login failed: RCCL did not return a login token`

## Root Cause

`async_create_clientsession()` returns a Home Assistant-managed aiohttp session.
Home Assistant wraps that session's `close()` method and reports custom
integrations that close it directly. The integration did this in the Club Royale
coordinator, config-flow validation, and websocket fallback.

Club Royale polling also created a fresh session and ran the full
username/password login wrapper on every refresh. That made the first poll after
config creation perform another OpenAM login even though config validation had
already obtained Club Royale credentials and a loyalty id.

## Fix

- Do not call `session.close()` on sessions created by Home Assistant helpers.
- Store Club Royale access-token credentials, loyalty id, and Club Royale
  referers in the Club Royale config entry.
- Create one Home Assistant-managed cookie-backed session for the Club Royale
  coordinator.
- Poll offers using stored credentials and the stored loyalty id; reauthenticate
  with the Club Royale referers only when the casino API rejects the request.
