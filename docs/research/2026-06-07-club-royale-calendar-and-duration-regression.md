# Club Royale Calendar And Duration Regression

## Context

After `v0.1.2`, Home Assistant showed the Club Royale card data but some
multi-night sailings rendered as one-day bars. The same report also showed that
the new offer-code expiration entities were not obvious in the Home Assistant
calendar surface.

## Findings

- The card rendering path depends on each sailing row having a useful
  `return_date`.
- If RCCL or an existing Home Assistant entity provides a missing or collapsed
  `return_date`, the card can only render the sailing on the departure date.
- RCCL sailing labels often include the duration as text, such as `4 Night ...`
  or `5 NIGHT ...`, so duration can be recovered even if a numeric nights field
  is absent or stale.
- A single aggregate calendar entity is easy to miss when the user expects
  offer-code-level calendar entries.

## Fix Contract

- Backend Club Royale normalization now derives `total_nights` from direct
  fields first, then from sailing labels.
- The custom card derives a fallback return date from `total_nights` or `N
  Night` text before computing calendar spans.
- The Club Royale calendar platform now creates one calendar entity per offer
  code, plus the aggregate offer-expiration calendar.
- Stale per-offer calendar entities are removed after successful refreshes.
