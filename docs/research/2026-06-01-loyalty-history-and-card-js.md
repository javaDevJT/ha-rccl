# 2026-06-01 Loyalty History and Card JS

## Symptoms

- Past cruises were still wrong after the earlier history work.
- The Club Royale custom card JavaScript did not load.

## HAR Evidence

The updated HAR shows loyalty history using:

`GET https://aws-prd.api.rccl.com/en/royal/web/v1/guestAccounts/loyalty/history/<account_id>?loyaltyNumber=<crown_anchor_id>`

The response contains historical `payload.sailings` rows with fields such as
`bookingId`, `passengerId`, `itineraryNightsQuantity`, `itineraryDescription`,
`originPortDescription`, `destinationPortDescription`, `sailingDate`,
`shipCode`, `shipName`, and `status`.

The `sailingDate` value can use compact `YYYYMMDD` form, for example
`20140622`.

## Root Causes

- The integration called the loyalty-history endpoint without the
  `loyaltyNumber` query parameter.
- Frontend static registration only happened from integration-level setup. To
  make the custom card resource robust for config-entry loading, frontend
  registration should also happen from config-entry setup and be idempotent.

## Fix

- Derive the loyalty number from `account.payload.loyaltyInformation.crownAndAnchorId`.
- Pass `loyaltyNumber` when fetching loyalty history.
- Keep compact `YYYYMMDD` date parsing covered by regression tests.
- Register frontend static paths and the websocket command from both
  `async_setup()` and `async_setup_entry()`, with a domain-data guard to avoid
  duplicate registration.
