# 2026-06-01 Component Design

## Goal

Create a HACS-compatible Home Assistant custom integration that imports Royal
Caribbean account data from the RCCL web APIs observed in the HAR.

## Repository Shape

HACS expects one integration under `custom_components/<domain>/`, plus a root
`README.md` and optional `hacs.json`. The integration domain is `rccl`.

## Authentication Strategy

Use a username/password config flow:

- Royal Caribbean account email
- Royal Caribbean account password

The client follows the RCCL web login flow observed in the HAR and bundled JS:

1. `POST /auth/json/authenticate` with OpenAM username/password headers.
2. `POST /v1/oauth2-authorize/en/royal/web/v1/authorize` with the returned
   `tokenId`.
3. Store derived tokens and account id in the config entry.

Users should never have to paste `access-token`, `account-id`, `appkey`, or
`vds-id` into the configurator.

## Polling Model

Home Assistant creates a single `RCCLClient` and `RCCLDataUpdateCoordinator`.
The coordinator polls every 60 minutes by default and fetches:

- account profile
- enriched profile bookings
- upgrade eligibility
- loyalty info
- loyalty history summary
- loyalty sailing history

Authentication failures should trigger reauthentication so the user can enter
fresh RCCL credentials.

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
