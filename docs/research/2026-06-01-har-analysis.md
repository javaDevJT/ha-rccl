# 2026-06-01 HAR Analysis

Source: `/Users/joshuaterk/Downloads/www.royalcaribbean.com.har`

The HAR contains 263 requests. The useful account traffic is concentrated on
`aws-prd.api.rccl.com` and a smaller set of `www.royalcaribbean.com` auth and
GraphQL calls. Telemetry, fonts, images, cookie banners, and anti-bot resources
were ignored.

## Relevant Hosts

- `www.royalcaribbean.com`: page shell, login resources, GraphQL calls, and the
  initial auth endpoint.
- `aws-prd.api.rccl.com`: account, bookings, upgrades, loyalty, and history
  endpoints used after authentication.

## Auth Observations

- The RCCL account bundle calls `POST /auth/json/authenticate` with
  `X-OpenAM-Username`, `X-OpenAM-Password`, `accept-api-version:
  resource=2.0, protocol=1.0`, and the public web `appkey`.
- The successful OpenAM response returns a `tokenId`.
- The bundle then calls
  `POST /v1/oauth2-authorize/en/royal/web/v1/authorize` with the public web
  app key and body `{ "client": "login-component", "tokenId": "..." }`.
- The authorize response is expected to include `access_token`,
  `refresh_token`, `id_token`, and `expires_in`; account-web wrapper payloads
  may spell these as `accessToken`, `refreshToken`, `openIdToken`, and
  `tokenExpiration`.
- The account id used by guest-account endpoints is available as
  `payload.accountId` in wrapper responses or as a `vdsid`/`vdsId`-style claim
  in the OpenID token.
- Subsequent API requests use headers named `access-token`, `account-id`, and
  `appkey`. Some also include `vds-id`, `req-app-id`, and `req-app-vers`.

The integration should therefore collect username/password, log in through the
same OpenAM/OAuth sequence, and derive the access token and account id
automatically.

## Account API Endpoints

- `GET /en/royal/web/v3/guestAccounts/{account_id}`
  returns contact, legacy account, cruising history, and loyalty account data.
- `GET /v1/profileBookings/enriched/{account_id}`
  returns profile bookings. Booking fields include `bookingStatus`, `brand`,
  `numberOfNights`, `packageCode`, `sailDate`, `shipCode`, `stateroomType`, and
  related passenger/booking fields.
- `POST /v1/profileBookings/searchAddGetProfileBookings`
  returns similar profile bookings, but the request body includes personal data.
  The integration avoids this endpoint for the MVP.
- `GET /en/R/web/v1/guestAccounts/upgrades`
  returns upgrade eligibility per booking.
- `GET /en/royal/web/v1/guestAccounts/loyalty/info`
  returns Crown & Anchor and related loyalty tier/points fields.
- `GET /en/royal/web/v1/guestAccounts/loyalty/history/summary`
  returns total nights and total trips.
- `GET /en/royal/web/v1/guestAccounts/loyalty/history/{account_id}`
  returns historical sailings with itinerary, ship, date, points, and status
  fields.

## Upstream Documentation Checked

- Home Assistant config flows:
  https://developers.home-assistant.io/docs/core/integration/config_flow
  - `manifest.json` needs `config_flow: true`; the flow lives in
    `config_flow.py`; account IDs are acceptable unique IDs for cloud services
    when they do not collide.
- Home Assistant integration manifests:
  https://developers.home-assistant.io/docs/creating_integration_manifest
  - Custom integrations require a valid `version` in `manifest.json`; setting
    `integration_type` explicitly is recommended.
- Home Assistant fetching data and `DataUpdateCoordinator`:
  https://developers.home-assistant.io/docs/integration_fetching_data
  - Use a single coordinated poll for shared API data and
    `async_config_entry_first_refresh()` during setup.
- Home Assistant sensor entities:
  https://developers.home-assistant.io/docs/core/entity/sensor
- Home Assistant calendar entities:
  https://developers.home-assistant.io/docs/core/entity/calendar/
  - All-day calendar events should use `datetime.date` values, and
    `async_get_events()` returns events in a requested date range.
- Home Assistant diagnostics:
  https://developers.home-assistant.io/docs/core/integration_diagnostics
- HACS integration repository structure:
  https://hacs.xyz/docs/publish/integration/
  - HACS expects a single directory under `custom_components/`; the integration
    `manifest.json` must include `domain`, `documentation`, `issue_tracker`,
    `codeowners`, `name`, and `version`.
