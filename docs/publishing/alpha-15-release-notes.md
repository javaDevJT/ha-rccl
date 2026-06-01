# Alpha 15 Release Notes

## Fixed

- Club Royale config validation and polling now use an async-compatible urllib
  session instead of aiohttp for RCCL's Club Royale browser/casino endpoints.
- The normal Royal Caribbean account integration still uses Home Assistant's
  shared aiohttp client.
- Club Royale offer failures now preserve the original offer-request auth error
  if a retry reauth fails, instead of masking the problem as a missing login
  token.

## Notes

Live testing reproduced the HTTP 403 with aiohttp and confirmed the urllib-backed
Club Royale path returns offers and normalized sailings.

