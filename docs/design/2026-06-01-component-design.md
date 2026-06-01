# 2026-06-01 Component Design

## Goal

Create a HACS-compatible Home Assistant custom integration that imports Royal
Caribbean account data from the RCCL web APIs observed in the HAR.

## Repository Shape

HACS expects one integration under `custom_components/<domain>/`, plus a root
`README.md` and optional `hacs.json`. The integration domain is `rccl`.

## Authentication Strategy

Use a token/header based config flow:

- `access-token`
- `account-id`
- `appkey`
- optional `vds-id`

This avoids hard-coding personal values from the HAR and avoids guessing at the
browser login flow while auth response bodies are unavailable.

## Polling Model

Home Assistant creates a single `RCCLClient` and `RCCLDataUpdateCoordinator`.
The coordinator polls every 60 minutes by default and fetches:

- account profile
- enriched profile bookings
- upgrade eligibility
- loyalty info
- loyalty history summary
- loyalty sailing history

Authentication failures should surface as config-entry auth failures so the user
can reconfigure fresh token values.

The coordinator is stored on `ConfigEntry.runtime_data` and mirrored into
`hass.data` for simple fallback access.

## Entities

Sensors:

- upcoming cruises
- next cruise date
- upgrade eligible cruises
- Crown & Anchor tier
- Crown & Anchor points
- total cruise trips
- total cruise nights

Calendar:

- read-only cruise calendar generated from profile bookings and loyalty sailing
  history

Sensor attributes intentionally avoid passenger names, full booking IDs, and
stateroom numbers because Home Assistant state attributes can be stored in
history and diagnostics.

## Future Work

- Implement a robust reauth flow once the complete RCCL authorize response is
  available.
- Add per-booking devices/entities if useful after validating the shape across
  more RCCL accounts.
- Consider exporting full itinerary details when a safe endpoint is identified.
