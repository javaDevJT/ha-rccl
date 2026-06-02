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

## Verification

Local card simulations confirmed:

- Two identical `hass` updates produce one render.
- A changed sailing value produces a second render and updates the stored data.

