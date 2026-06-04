# Club Royale Offer Guest Count Detection

## Symptom

Club Royale sailings were not reliably distinguishing one-guest offers from
two-guest offers when RCCL labeled the offer as `Cruise Fare For 1 Guest` or
`Cruise Fare For 2 Guests`.

## Root Cause

The normalized sailing rows only inferred `offer_occupancy` from
`campaignOffer.description`. RCCL can carry the guest-count label in
`campaignOffer.offerType.name`, such as `Cruise Fare For 1 Guest`, while the
description remains a generic casino-offer string.

## Fix

`_offer_occupancy()` now inspects multiple offer labels:

- `campaignOffer.description`
- `campaignOffer.offerType.name`
- `campaignOffer.name`
- `campaignName`

It explicitly matches `for 1/one guest`, `for 2/two guests`, and passenger
variants before falling back to the older broad `for one` / `for two`
description behavior.

The normalized fields remain:

- `offer_occupancy`: `one_passenger` or `two_passengers`
- `offer_occupancy_label`: `One passenger` or `Two passengers`
