# 2026-06-01 Club Royale Alpha 12 Regressions

## Symptoms

- The config-flow source-selection step showed two options, but both were
  unlabeled in Home Assistant.
- A Club Royale entry could fail setup with
  `RCCL did not return a login token`.

## Evidence

Home Assistant's current data-entry-flow documentation says menu labels can be
provided directly by passing a `{step_id: label}` dictionary to
`async_show_menu()`. Alpha 11 used a list and relied on `strings.json`
translation loading, which is brittle for this custom integration menu.

The setup failure is consistent with alpha 11 validating Club Royale credentials
in the config flow, creating the entry, then immediately doing another
standalone Club Royale login during `async_config_entry_first_refresh()`. If the
second login returns no OpenAM `tokenId`, Home Assistant marks the new config
entry as failed before the summary/entity surface exists.

## Fix

- Hardcode the two source-selection labels in the `async_show_menu()` result.
- Let Club Royale config-entry setup finish after creating the coordinator and
  sensor platform.
- Trigger the first Club Royale refresh in the background so transient login
  failures show up as coordinator/entity update failures rather than setup
  failures.
- Treat Club Royale login failures in the Club Royale coordinator as
  `UpdateFailed`, not account reauthentication failures.
