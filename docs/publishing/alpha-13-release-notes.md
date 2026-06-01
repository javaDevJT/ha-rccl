# Alpha 13 Release Notes

## Fixed

- Removed direct closing of Home Assistant-managed aiohttp sessions from Club
  Royale config validation, polling, and websocket fallback paths.
- Club Royale config entries now store the validated access token, loyalty id,
  and Club Royale login referers.
- Club Royale polling now reuses config-entry credentials and only reauthenticates
  when RCCL rejects the offer request.

## Notes

After upgrading, restart Home Assistant. Recreate the Club Royale Offers entry
if it was created on alpha 11 or alpha 12 and continues to have stale stored
credentials.
