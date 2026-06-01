# 2026-06-01 Club Royale Calendar Scroll

## Symptom

Alpha 16 kept dense sailing bars inside their week rows, but Home Assistant still
clipped the lower part of June 2026 and the user could not scroll to the
remaining weeks.

## Root Cause

The card still reported `rows: 8` from `getGridOptions()`. In Home Assistant
grid/sections layouts that allowed the dashboard to allocate a short fixed card
area and clip the taller calendar content before the internal month scroller was
useful.

The calendar scroller also used only `max-height`, so in a clipped dashboard
slot the scrollable viewport was not explicit enough.

## Fix

- Report a dynamic Home Assistant grid size with a minimum of 16 rows.
- Give the calendar shell an explicit pixel height derived from the rendered
  month, capped at 560 pixels.
- Make the calendar shell focusable and scrollable with stable scrollbar gutter.
- Keep the details panel outside the calendar scroller.

## Verification

A local render simulation with 12 overlapping sailings in one June week produced:

- calendar content height: 1,064 pixels
- calendar viewport height: 560 pixels
- `scrollable=true`
- `grid_rows=16`
- no bar spill outside its week row

