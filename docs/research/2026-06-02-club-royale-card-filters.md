# 2026-06-02 Club Royale Card Filters

## Request

Add Lovelace card filters for:

- ship
- offer type
- offer
- departure
- number of nights

## Design

The filters live inside the Club Royale custom card rather than Home Assistant
calendar or entity filtering. Each filter is a compact `select` control populated
from the normalized sailing data already loaded into the card.

Filter values map to the same fields shown in the details panel:

- ship: `ship_name`, falling back to `ship_code`
- offer type: `offer_type` plus `offer_occupancy_label`
- offer: `offer_name` plus `offer_code`
- departure: formatted `departure_port`
- nights: `total_nights`

## Behavior

- Each filter defaults to an `All ...` option.
- Filters combine with AND semantics.
- Changing a filter resets the internal calendar scroll to the top because the
  visible grid may have a different height.
- The selected sailing is moved to the first matching sailing if the previous
  selection is filtered out.
- Reset clears all filters and restores all sailings.

## Verification

A local card simulation confirmed:

- ship options are unique and alphabetized
- nights options are unique and numerically sorted
- ship and nights filters narrow the sailing list as expected
- reset restores the full sailing list
- filter controls render in the card markup
