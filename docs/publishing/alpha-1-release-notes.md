# Alpha 1 Release Notes

Tag: `v0.1.0-alpha.1`

This first alpha packages the Royal Caribbean Home Assistant custom integration
for private HACS testing.

## Included

- HACS-compatible repository structure.
- Home Assistant config flow using RCCL account API header values.
- RCCL API client and shared polling coordinator.
- Sensors for upcoming cruises, next cruise date, RoyalUp eligibility, Crown &
  Anchor tier/points, total trips, and total nights.
- Read-only cruise calendar generated from booking and sailing-history data.
- Diagnostics redaction for credentials and personal booking fields.
- Sanitized HAR research, component design notes, and focused parser tests.

## Known Limits

- Automated username/password login is not implemented yet because the captured
  HAR did not include complete auth response bodies.
- The integration must be tested inside a real Home Assistant runtime before it
  should be considered beta quality.
- Tokens may expire and require reconfiguration with fresh browser-session
  header values.
