# 2026-06-01 Club Royale Offers 403 Live Test

## Symptom

Home Assistant setup reached the Club Royale coordinator but the first poll failed
with:

`Club Royale login failed: RCCL rejected credentials with HTTP 403`

## Sanitized Live Findings

- The supplied username/password still authenticated successfully against the
  Club Royale login path.
- The OpenAM authenticate request, OAuth authorize request, and Club Royale guest
  account request each returned HTTP 200 in the live probe.
- A direct `POST /api/casino/v2/offers/merged` returned HTTP 403 with an access
  denied HTML response.
- Replaying the same request with account API headers was still HTTP 403.
- Loading `GET /club-royale/offers` before casino API calls changed the API
  response from HTTP 403 to JSON validation errors.
- The validation error reported the missing `authorization` field.
- Loading `/club-royale/offers` first and then sending
  `Authorization: Bearer <access token>` returned HTTP 200 from
  `/api/casino/v2/offers/merged` with 9 offers.
- A separate probe that logged in once, then created a fresh cookie session from
  the stored access token, also succeeded after loading `/club-royale/offers`.
  That fresh-session probe returned 9 offers and 1,270 normalized sailings.

## Fix

The Club Royale client must shape its Home Assistant-managed aiohttp session like
the website does:

- Reuse the Club Royale access token stored on the config entry.
- Load `/club-royale/offers` once before calling the same-origin casino APIs.
- Send `Authorization: Bearer <access token>` on casino API requests.
- If RCCL rejects the casino API call, reauthenticate, prime the offers page
  again, and retry once.
