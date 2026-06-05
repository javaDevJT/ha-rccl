# Club Royale Offer-Sailing Identity

## Symptom

The Club Royale card could show only a few sailings for an offer that Royal
Caribbean shows with many more sailings. In the Home Assistant screenshot,
August 2026 showed 3 sailings while the active offer filter was
`2026 All-In on August`.

## HAR Evidence

The supplied `www.royalcaribbean.com.har` captured the Royal Caribbean offer
detail page for `26AUG106`. The browser called
`/api/casino/v2/offers/merged` with `offerCode: 26AUG106`,
`playerOfferId: ff935dfb-ca5d-40a5-a148-f506443686d7`, `limit: 1`, and
`page: 1`.

The response contained one offer, `2026 All-In on August`, with 25 sailings, all
in August 2026. Example voyage ids included `JW_FLL_2026-08-10`,
`JW_FLL_2026-08-14`, and `FR_MIA_2026-08-17`.

## Root Cause

RCCL's `sailing.id` is a voyage-level id. The same voyage can appear under more
than one Club Royale offer. The integration used only that voyage id as the
normalized row id, so Home Assistant dynamic sailing entities could collapse
different offer+sailing rows into a single entity.

## Fix

Normalized Club Royale sailing rows now use an offer-scoped id:

`<offerCode>:<source_sailing_id>`

The original RCCL voyage id remains available as `source_sailing_id`.

The card still displays only one bar per voyage by default. Filters are applied
to the full offer+sailing row dataset first, then visible rows are grouped by
`source_sailing_id`. If more than one matching offer remains for a voyage, the
card displays the row with the soonest `reserve_by_date`, falling back to
`sail_by_date` when needed. This keeps the calendar readable while preserving
the ability for an offer filter to surface the matching offer row for a shared
voyage.
