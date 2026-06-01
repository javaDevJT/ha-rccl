# 2026-06-01 Club Royale Calendar Overflow

## Symptom

Once real Club Royale sailing entities appeared, dense months rendered as a stack
of sailing bars that spilled across later calendar weeks and over the details
panel.

## Root Cause

The card already split multi-day sailings into weekly segments and assigned
non-overlapping lanes inside each week. The calendar rows, however, were fixed at
roughly 108 pixels tall. A week with more than three lanes needed more vertical
space, so later lanes painted outside their week row.

## Fix

- Count the number of lanes needed by each calendar week after segment layout.
- Derive a per-week row height from that lane count.
- Render explicit `grid-template-rows` values for the month instead of a fixed
  repeated row height.
- Put the calendar grid inside an internal scroll region so dense months remain
  navigable without bars overlapping the rest of the card.

## Verification

A local render simulation with 12 overlapping sailings in a single week produced
a 362-pixel week row, kept every bar within its week, and rendered the
`calendar-shell` scroll container.

