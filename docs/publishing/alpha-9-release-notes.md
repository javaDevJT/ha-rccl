# Alpha 9 Release Notes

## Fixed

- Past cruise history now calls the HAR-observed loyalty-history endpoint shape
  with `loyaltyNumber=<crown_anchor_id>`.
- Added regression coverage for compact loyalty-history dates such as
  `YYYYMMDD`.
- The Club Royale custom card frontend is now registered from config-entry
  setup as well as integration setup, with an idempotent guard.

## Notes

After upgrading, restart Home Assistant and keep the dashboard resource:

```yaml
url: /rccl_static/club-royale-calendar-card.js
type: module
```
