# 2026-06-01 Club Royale Session Split

## Symptom

After alpha 7, Home Assistant could surface `invalid_auth` while creating or
setting up the integration. The new Club Royale polling was the risky change.

## Root Cause

Alpha 7 fetched Club Royale offers as part of the normal account coordinator.
That made `/api/casino` responses part of config-entry setup health. If the
casino web API rejected the request with HTTP 401 or 403, the optional fetch
could be treated as an authentication failure for the whole RCCL account.

## Decision

Club Royale must use a different login session entirely. It should not be
fetched by the normal account coordinator.

## Fix

The normal coordinator now fetches account, bookings, upgrades, loyalty, and
history only. The Club Royale Lovelace card calls a websocket command that:

1. creates a fresh cookie-backed client session,
2. logs in with the stored RCCL username/password,
3. fetches the account profile to derive the cruise loyalty id,
4. fetches Club Royale offers and per-offer sailing detail,
5. closes that standalone session.

If Club Royale login or offer polling fails, the card can show an error without
marking the Home Assistant config entry as invalid auth.
