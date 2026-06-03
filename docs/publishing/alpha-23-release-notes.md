# Alpha 23 Release Notes

## Added

- Added local Home Assistant brand assets in `custom_components/rccl/brand/`.
- Added a reproducible `scripts/generate_brand_assets.py` asset generator.

## Changed

- Replaced Club Royale native select filters with checkbox menus so multiple
  ships, offer types, offers, departures, and night counts can be selected.
- Added per-filter "Select all" and "Deselect all" controls.
- Added a master "Reset filters" button.
- Filter selections now persist while moving month to month.
