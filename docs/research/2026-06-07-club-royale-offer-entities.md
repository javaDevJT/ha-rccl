# Club Royale Offer Entities

## Context

Club Royale sailing rows are offer-scoped because the same RCCL voyage can appear
under multiple offer codes. The integration still preserves every offer+sailing
row for filtering and card details, but Home Assistant users also need a direct
entity for each offer code so expiration dates can be tracked outside the custom
card.

## Entity Contract

- `club_royale_offer_summaries(data)` groups normalized Club Royale sailing rows
  by `offer_code`.
- Each summary uses the offer `reserve_by_date` as `expiration_date`.
- Summary attributes include the offer name, offer type, occupancy label,
  sail-by date, sailing ids, source sailing ids, ships, itineraries, departure
  ports, cabin guarantees, available nights, and sail-date span.
- The Club Royale coordinator publishes both `sailings` and `offers` on every
  successful refresh.

## Home Assistant Behavior

- One `SensorDeviceClass.DATE` entity is created per offer code.
- The date sensor state is the offer expiration date.
- Offer sensors use the Club Royale device and `club_royale_offer` entity kind
  so dashboards and automations can distinguish them from sailing sensors.
- Dynamic cleanup removes stale offer-code sensors and stale sailing sensors
  after a successful refresh that includes both `sailings` and `offers`.
- A Club Royale calendar entity exposes one all-day event per offer expiration
  date. This is a separate calendar entity from the normal RCCL cruise calendar.
