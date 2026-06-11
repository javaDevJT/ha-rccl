# Club Royale Offer Entity Deduplication

## Context

`v0.1.3` created a date sensor and a calendar entity for every Club Royale offer
code. In Home Assistant's entity list, that produced duplicate-looking rows for
each offer: one date sensor with the expiration date and one calendar entity
with an `Off` state.

## Decision

- Keep the per-offer date sensors as the primary offer-code entities.
- Keep one aggregate Club Royale offer-expiration calendar.
- Remove per-offer calendar entities to avoid duplicating every offer in the
  entity list.
- During Club Royale calendar setup, remove legacy per-offer calendar registry
  entries whose unique ids use the old `club_royale_offer_calendar_` prefix.
- Name offer date sensors with the friendly offer name plus offer code when both
  are available.

## Naming

Offer sensors now use:

- `Club Royale <offer name> (<offer code>)` when both values are present.
- `Club Royale <offer name>` when only the name is present.
- `Club Royale offer <offer code>` as a fallback.
