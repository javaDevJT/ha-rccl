# Club Royale Filter Panel Scroll Preservation

## Symptom

When a Club Royale filter menu was scrolled down and a checkbox was clicked, the
menu stayed open but jumped back to the top.

## Root Cause

Checkbox changes intentionally re-render the whole card so the calendar and
details update immediately. The card remembered which `<details>` menu was open,
but the scrollable `.filter-panel` inside that menu was rebuilt with
`scrollTop = 0`.

## Fix

- Store filter panel scroll offsets per filter key.
- Capture the active filter panel's scroll position before `shadowRoot.innerHTML`
  is replaced.
- Restore the active panel's scroll position after handlers are reattached.
- Save the panel scroll when a filter menu closes or another filter menu opens.

This preserves the user's position inside long ship, offer, departure, or night
filter lists while still letting the calendar update after each checkbox change.
