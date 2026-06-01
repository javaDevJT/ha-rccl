# Alpha 8 Release Notes

## Fixed

- Removed Club Royale polling from the normal RCCL account coordinator.
- Club Royale card data now logs in through a standalone web session on demand.
- Club Royale account lookup now uses the HAR-observed `api.rccl.com` guest
  account endpoint rather than the normal account coordinator endpoint.
- Club Royale auth/API failures are returned to the card instead of invalidating
  the Home Assistant config entry.

## Why

Club Royale behaves like a separate web session. A casino API 401/403 should not
make the core Royal Caribbean account integration fail with `invalid_auth`.
