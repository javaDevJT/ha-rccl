# Alpha 6 Release Notes

Tag: `v0.1.0-alpha.6`

This alpha fixes nonsensical Home Assistant entity labels on the device page.

## Fixed

- Sensors now have explicit display names in code instead of relying only on
  translation fallback.
- Device page rows should show names such as `Upcoming cruises`, `Next cruise
  date`, `Upgrade eligible cruises`, `Crown & Anchor tier`, and `Total cruise
  nights`.
- Calendar entity now has the explicit name `Cruises`.

## Note

Entity unique IDs did not change. If Home Assistant has cached old display names
for existing entities, reload the integration or remove/re-add the config entry.
