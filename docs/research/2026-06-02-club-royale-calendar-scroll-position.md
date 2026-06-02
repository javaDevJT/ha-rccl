# 2026-06-02 Club Royale Calendar Scroll Position

## Symptom

Alpha 17 made the Club Royale calendar internally scrollable, but the card could
jump back to the top while scrolling through dense sailing bars.

## Root Cause

The card rebuilt `shadowRoot.innerHTML` whenever a sailing bar was selected.
Selection happens on `mouseenter`, `focus`, and `click`, so normal scrolling over
overlapping bars could trigger a render. Home Assistant state updates can also
call the `hass` setter and render the card again.

Replacing the shadow DOM creates a fresh `.calendar-shell` element with
`scrollTop` at zero unless the card preserves and restores the previous scroll
offset.

## Fix

- Track the current `.calendar-shell` scroll offset on scroll events.
- Capture the scroll offset before every render and restore it after rebuilding
  the card DOM.
- Skip redundant sailing-selection renders when the same sailing is selected.
- Reset the calendar scroll intentionally only when the visible month changes.

## Verification

A local card simulation scrolled the calendar to `420`, selected another sailing
to force a render, and confirmed the new calendar shell restored `scrollTop` to
`420`. The same simulation set the month-reset flag and confirmed the next render
restored `scrollTop` to `0`.
