# 2026-06-01 Club Royale Aiohttp 403

## Symptom

After alpha 14, Home Assistant still logged:

`Club Royale login failed: RCCL rejected credentials with HTTP 403`

Deleting and recreating the Club Royale config entry did not help.

## Sanitized Live Findings

- A live `urllib` probe using the supplied credentials succeeded against Club
  Royale offers.
- A live `aiohttp` probe using the same credentials reproduced Home Assistant's
  failure.
- With `aiohttp`, authenticate, authorize, and Club Royale guest account lookup
  returned HTTP 200.
- The `GET /club-royale/offers` page-prime request also returned HTTP 200, but
  landed on `/club-royale/signin?country=USA&returnTo=offers`.
- The following `POST /api/casino/v2/offers/merged` returned HTTP 403 with an
  access-denied HTML body even though the bearer authorization, account id, and
  loyalty id headers were present.
- `aiohttp.CookieJar(quote_cookie=False)` still returned the same HTTP 403.
- The production `RCCLUrllibSession` path returned 9 offers and 1,272 normalized
  sailings in the live probe.

## Decision

Use Home Assistant's shared aiohttp session for the normal RCCL account entry,
but use an async-compatible threaded `urllib` session for the Club Royale entry.
RCCL's Club Royale casino API currently accepts the urllib request stack and
rejects the aiohttp request stack at the access-control layer.

If RCCL rejects a Club Royale offer request and a retry reauth fails, preserve
the original offer-request error so Home Assistant does not mask it as a
misleading login-token failure.

