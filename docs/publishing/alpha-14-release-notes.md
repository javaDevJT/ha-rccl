# Alpha 14 Release Notes

## Fixed

- Club Royale offer polling now loads the `/club-royale/offers` page before
  calling the casino offer API, matching the browser sequence observed in live
  testing.
- Casino offer API calls now send the bearer authorization header required by
  RCCL's validation layer.
- A 200 JSON validation response from RCCL is now surfaced as an API error
  instead of silently producing empty Club Royale card data.
- If RCCL rejects an offer request, the coordinator reauthenticates, primes the
  Club Royale offers page again, and retries once.

## Notes

After upgrading, restart Home Assistant. If a stale Club Royale Offers entry from
an earlier alpha still fails after restart, delete and recreate that entry so it
stores the current Club Royale token and referer fields.

