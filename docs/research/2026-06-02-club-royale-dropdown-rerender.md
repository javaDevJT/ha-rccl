# 2026-06-02 Club Royale Dropdown Re-render

## Symptom

After alpha 20 added dropdown filters, opening a filter dropdown could close it
immediately. The behavior resembled the earlier calendar scroll jump.

## Root Cause

The entity-backed card path still rendered on every Home Assistant `hass` setter
update:

- Home Assistant passed the card a fresh `hass` object.
- The card rebuilt entity sailings from HA states.
- The card called `_render()` even when those sailings were unchanged.
- Replacing `shadowRoot.innerHTML` destroyed the open native `<select>` menu.

Alpha 19 removed hover-triggered calendar renders, but alpha 20 still exposed
the passive HA update render path because native dropdowns are also sensitive to
DOM replacement.

## Fix

- Compute a stable signature for normalized entity sailings.
- Apply entity sailings and render only when the signature changes or the card's
  loading/error state actually transitions.
- Preserve intentional renders for filter changes, month navigation, refresh,
  and real entity data changes.

Alpha 21 reduced passive re-renders, but live behavior could still close an open
dropdown when a legitimate data/config render arrived while a filter was
focused. Alpha 22 adds a focused-filter render deferral:

- If a filter control has focus, passive renders are marked pending instead of
  immediately replacing the shadow DOM.
- The pending render is flushed after the filter loses focus.
- User-driven filter changes still render immediately after the native dropdown
  closes.

## Verification

Local card simulations confirmed:

- Two identical `hass` updates produce one render.
- A changed sailing value produces a second render and updates the stored data.
- A changed sailing value while a filter is focused defers the render, then
  flushes exactly once after focus clears.
