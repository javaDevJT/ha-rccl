# 2026-06-01 Club Royale Card

## Goal

Add a custom Lovelace card for Club Royale offer sailings without creating Home
Assistant calendar events.

## Display Contract

- Month-style calendar grid.
- Sailing bars span every impacted day from departure through return day,
  inclusive.
- Bars are labeled with itinerary/sailing name and ship name.
- Hover and keyboard focus show details.
- Offer name, offer code, reserve-by date, and sail-by date appear in details.
- Cabin guarantee/category details appear in details.
- Offer occupancy, such as two-passenger or one-passenger offers, appears in
  details when available.
- Booking ids and passengers are not part of the Club Royale card data model.

## Backend Contract

The integration fetches the Club Royale offer list first, then fetches detail
for each offer with `offerCode` and `playerOfferId`. Detail responses populate
`campaignOffer.sailings`, which are normalized into card rows with:

- `sail_date`
- `return_date`
- `total_nights`
- `ship_code`
- `ship_name`
- `itinerary_code`
- `itinerary_name`
- `itinerary_description`
- `departure_port`
- `room_types`
- `is_guarantee`
- `offer_name`
- `offer_code`
- `offer_type`
- `occupancy`
- `reserve_by_date`
- `sail_by_date`
