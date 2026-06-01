# 2026-06-01 Club Royale Websocket Data

## Symptom

The Club Royale Lovelace card JavaScript loaded, but the card stayed on
`Loading Club Royale sailings...` and showed no sailing data.

## HAR Evidence

The Home Assistant HAR shows the custom-card resource loading successfully:

`GET /rccl_static/club-royale-calendar-card.js` returned HTTP 200 with
`text/javascript`.

The same HAR contains an outbound Home Assistant websocket frame:

`{"type":"rccl/club_royale_sailings","id":43}`

Nearby websocket frames show normal responses for other request ids, including
`lovelace/info` id 42 and `call_service` id 44. No matching `result` frame for
id 43 appears in the captured websocket traffic.

## Root Cause

The custom websocket command handler is async and awaits RCCL/Club Royale HTTP
work before calling `connection.send_result()`. Home Assistant websocket
commands that respond asynchronously must be marked with
`@websocket_api.async_response`; otherwise the browser-side promise can remain
unanswered and the card can sit in its loading state.

## Fix

- Mark the Club Royale sailing websocket handler with
  `@websocket_api.async_response`.
- Prefer Home Assistant's connection `sendMessagePromise()` in the card and keep
  `callWS()` as fallback.
- Add a browser-side timeout so future no-response failures become visible card
  errors instead of an indefinite loading state.
