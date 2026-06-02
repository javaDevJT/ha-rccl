# Alpha 19 Release Notes

## Fixed

- The Club Royale calendar no longer re-renders the whole card when hovering,
  focusing, or clicking a sailing bar.
- Sailing selection now updates the selected bar styling and details panel in
  place, keeping the active calendar scroll container alive.
- The card stores the calendar scroll position by month so Home Assistant card
  replacement can restore the last scroll offset.
