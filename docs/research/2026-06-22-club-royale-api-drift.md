# Club Royale API Drift

## HAR Evidence

The supplied `www.royalcaribbean.com.har` from June 2026 shows a newer Club
Royale frontend flow:

- `GET /club-royale/offers` still primes the browser session.
- `GET /api/casino/v1/loyalty-data` returns casino loyalty metadata.
- `GET /api/casino/v1/partners/player` returns a `{data, message}` response.
- `GET /api/casino/v2/offers/list` returns offer cards with empty
  `campaignOffer.sailings` arrays.

The capture does not include any `POST /api/casino/v2/offers/merged` calls and
does not include `approvedAgencyIds` in the casino request shape.

## Frontend Bundle Evidence

The captured Club Royale JavaScript bundle defines:

- a list fetcher for `${baseUrl}/v2/offers/list`
- a detail fetcher for `${baseUrl}/v2/offers/details`

The offer detail modal calls the detail fetcher with `offerCode`,
`playerOfferId`, `sortBy`, `sortDirection`, `limit`, `page`, and
`digitalRedemption`. It reads sailings from the returned offer detail payload.

## Integration Contract

The integration should fetch Club Royale offers with:

- `GET /api/casino/v2/offers/list`
- query params `sortBy=offer.reserveByDate`, `sortDirection=asc`, `limit=100`,
  `page=1`, and `digitalRedemption=true`

For each offer with both `offerCode` and `playerOfferId`, it should fetch detail
data with:

- `GET /api/casino/v2/offers/details`
- query params `offerCode`, `playerOfferId`, `sortBy`, `sortDirection`,
  `limit=1`, `page=1`, and `digitalRedemption=true`
