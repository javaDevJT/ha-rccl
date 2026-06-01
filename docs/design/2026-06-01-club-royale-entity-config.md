# 2026-06-01 Club Royale Entity Config

## Approved Direction

Club Royale offers should be configured through a separate Home Assistant config
path from the normal Royal Caribbean account. The two paths may use the same
username and password, but they should not share a browser session, token, or
coordinator.

## Design

- Add a config-flow menu with two choices: Royal Caribbean account and Club
  Royale offers.
- Store a config entry type in entry data so existing account entries keep their
  current sensors and calendar while Club Royale entries only set up sensors.
- Validate Club Royale by logging in with the HAR-observed Club Royale referer
  and a standalone cookie jar, then fetching the Club Royale guest account.
- Add a Club Royale data coordinator that creates a standalone web session on
  each refresh and returns normalized offer sailings.
- Add a summary sensor plus one date sensor per Club Royale sailing. Sailing
  sensors expose ship, itinerary, cabin guarantee, offer type, occupancy, ports,
  nights, return date, reserve-by date, and offer code as attributes.
- Update the custom card to read Club Royale sailing entities from
  `hass.states` before using the websocket fallback.

## Operational Notes

The entity-backed path makes the data visible in Home Assistant even when the
custom card is not present or fails to load. It also gives diagnostics a clear
split between normal account failures and Club Royale offer-fetch failures.
