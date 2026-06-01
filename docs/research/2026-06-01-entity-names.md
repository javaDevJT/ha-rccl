# 2026-06-01 Entity Names

## Symptom

The Home Assistant device page showed nonsensical entity labels:

- `Date`
- repeated `Royal Caribbean account`
- unlabeled cruise calendar row shown as `Royal Caribbean account`

## Root Cause

The entities relied on `translation_key` and `strings.json` for display names,
but the runtime UI fell back to device and device-class names. With
`has_entity_name` enabled and no explicit entity `name`, Home Assistant had no
stable local name to display for each sensor.

## Fix

- Add explicit `name` values to every sensor entity description.
- Set `_attr_name` from the description in each sensor.
- Disable device-name prefixing for these account-summary entities by setting
  `_attr_has_entity_name = False`.
- Give the calendar entity an explicit `Cruises` name.

Existing entity unique IDs are unchanged.
