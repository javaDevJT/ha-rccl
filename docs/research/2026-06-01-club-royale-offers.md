# 2026-06-01 Club Royale Offers

Source: `/Users/joshuaterk/Downloads/www.royalcaribbean.com.har`

The Club Royale HAR pass focused on offer and sailing data. Personal account
values, tokens, request cookies, passenger details, phone numbers, and exact
account identifiers are intentionally omitted from this note.

## Endpoints

- `GET https://www.royalcaribbean.com/api/casino/v1/loyalty-data`
  returns the casino loyalty profile. Useful fields include casino loyalty id,
  cruise loyalty id, tier, points, and evaluation-period dates.
- `POST https://www.royalcaribbean.com/api/casino/v2/offers/merged`
  with body `sortBy`, `sortDirection`, `limit`, `approvedAgencyIds`, `page`,
  and `digitalRedemption` returns the active offer list.
- The list response includes offer metadata such as campaign code, offer code,
  name, description, offer type, status, reserve-by date, sail-by date, images,
  player offer id, and booking requests.
- The list response does not include available sailings for each offer.
- A second `POST /api/casino/v2/offers/merged` call with `offerCode` and
  `playerOfferId`, plus the same paging and agency fields, returns a single
  offer with populated `campaignOffer.sailings`.

## Request Headers

The casino API requests in the HAR include `x-account-id` and `x-loyalty-id`.
The `x-loyalty-id` value aligns with the cruise loyalty id used by the offer
payload, not the casino loyalty id.

## Sailing Fields

The detail response's `campaignOffer.sailings` rows include:

- `sailDate`
- `shipCode`
- `shipName`
- `itineraryCode`
- `itineraryName`
- `itineraryDescription`
- `departurePort.code`
- `departurePort.name`
- `sailingType.name`
- `totalNights`
- room category data in `roomTypeList`
- offer flags such as `isCOMP`, `isGTY`, `isGOBO`, and `isDOLLARSOFF`

The observed detailed offer contained 34 available sailings. The top-level
offer list contained 9 active offers.

## Integration Implication

The integration should fetch the list first, then fetch detail for each offer
that has an `offerCode` and `playerOfferId`. The normalized data surface should
separate offer metadata from sailing rows so Home Assistant sensors can expose
counts while a Lovelace card can render a month-style browsing view without
creating Home Assistant calendar events.

## Card Display Requirements

- The calendar bar title should prioritize the sailing or itinerary name and
  ship name.
- Offer names belong in the hover/focus detail view, not as the primary
  calendar label.
- Booking identifiers and passenger details are not expected to be available
  for offer sailings and should not be shown in the Club Royale card.
- The details should include the cabin guarantee/category data from
  `roomTypeList` and guarantee flags such as `isGTY`.
- The details should include whether the offer is for two passengers, one
  passenger, or another explicit occupancy/guest-count value when RCCL exposes
  it.
