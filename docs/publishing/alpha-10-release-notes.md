# Alpha 10 Release Notes

## Fixed

- Club Royale sailings now return through Home Assistant's websocket API instead
  of leaving the custom card stuck on `Loading Club Royale sailings...`.
- The card request now has a visible timeout error if Home Assistant does not
  answer the websocket request.
- Added regression coverage for the async websocket response contract and the
  card websocket timeout helper.

## Notes

After upgrading, restart Home Assistant and refresh the browser cache for the
dashboard that uses:

```yaml
url: /rccl_static/club-royale-calendar-card.js
type: module
```
