# Alpha 11 Release Notes

## Added

- Added a separate Club Royale Offers config-flow path so Club Royale uses its
  own isolated login session and config entry.
- Added a dedicated Club Royale coordinator that fetches offer sailings through
  standalone browser-style sessions.
- Added real Home Assistant entities for Club Royale data:
  - `Club Royale available sailings` summary sensor.
  - One date sensor per offer sailing with ship, itinerary, cabin guarantee,
    offer type, occupancy, ports, nights, return date, offer code, reserve-by
    date, and sail-by date attributes.
- Updated the Club Royale custom card to read entity-backed sailing data from
  `hass.states` before falling back to the websocket loader.

## Notes

Add a new integration entry and choose `Club Royale offers` to enable the
entity-backed path. Restart Home Assistant after upgrading through HACS.
