# Club Royale Sailing-Level Offers And Cleanup

## Symptom

Club Royale sailings could still display as `Complimentary - Two passengers`
even when RCCL exposed a sailing-level `Cruise Fare For 1 Guest` label or a
reduced-fare sailing.

Old dynamic sailing entities also remained in Home Assistant after RCCL stopped
returning the matching sailing rows.

## Root Cause

The normalizer inferred `offer_type`, `offer_occupancy`, and
`offer_occupancy_label` once from `campaignOffer` and applied those values to
every sailing in the campaign. RCCL can attach different terms to individual
sailing rows using fields such as `offerType`, `fareType`, and `isCOMP`.

The sensor platform tracked Club Royale sailing ids as an append-only set. It
added newly discovered sailing sensors but never removed entity-registry entries
for sailing ids that disappeared from the latest successful coordinator data.

## Fix

Sailing rows now inspect their own offer/fare labels first. If a sailing has a
one-guest or two-guest label, that value overrides the campaign fallback.
`isCOMP: false` is treated as `Reduced fare`, while `isCOMP: true` remains
`Complimentary`.

When the coordinator has a current `sailings` snapshot, the sensor platform
removes stale dynamic sailing entities for the config entry from Home
Assistant's entity registry, then trims its in-memory known-id set to the same
current snapshot.
