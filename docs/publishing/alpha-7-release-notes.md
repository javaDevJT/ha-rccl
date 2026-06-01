# Alpha 7 Release Notes

## Added

- Added Club Royale offer polling from the web casino API.
- Added per-offer detail polling so available sailings include ship, itinerary,
  sail date, nights, departure port, cabin category, and guarantee flags.
- Added normalized Club Royale sailing rows for frontend use.
- Added `/rccl_static/club-royale-calendar-card.js`, a custom Lovelace card
  that renders offer sailings as impacted-date ranges.
- Added the `rccl/club_royale_sailings` websocket command for the card.

## Fixed

- Backfilled total cruise trips and nights from loyalty-history sailings when
  RCCL's summary payload returns empty or zero totals.
- Account booking attributes now include booking and passenger identity fields.

## Card Notes

The card labels calendar bars with itinerary/sailing name and ship name. Offer
name, offer code, reserve-by date, sail-by date, cabin guarantee/category, and
offer occupancy appear in the detail panel. Club Royale offer rows do not expose
booking ids or passenger rows.
