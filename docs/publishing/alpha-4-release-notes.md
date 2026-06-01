# Alpha 4 Release Notes

Tag: `v0.1.0-alpha.4`

This alpha includes the live-tested RCCL login request shape.

## Fixed

- Added browser-like headers to RCCL auth requests:
  `origin`, `referer`, `accept-language`, and `user-agent`.
- Kept the bounded timeout fix from alpha 3.
- Verified the standalone Python login smoke test can complete:
  authenticate, authorize, and guest-account fetch.

## Security Note

The live smoke test prints only sanitized status. It does not print credentials,
tokens, account IDs, or booking data.

## Still Known

- Multifactor and bot-challenge flows are not implemented.
- A live Home Assistant config-flow test is still needed.
