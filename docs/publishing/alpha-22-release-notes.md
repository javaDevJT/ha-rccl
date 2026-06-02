# Alpha 22 Release Notes

## Fixed

- Deferred passive Club Royale card renders while a filter dropdown has focus.
- Fixed remaining cases where a legitimate Home Assistant update could close an
  open filter dropdown.
- Pending renders flush after the filter loses focus, so real data changes still
  appear without replacing controls mid-interaction.
