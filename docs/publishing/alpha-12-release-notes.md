# Alpha 12 Release Notes

## Fixed

- The config-flow source picker now uses hardcoded labels for `Royal Caribbean
  account` and `Club Royale offers`, avoiding unlabeled menu options when
  translation loading is stale or incomplete.
- Club Royale config-entry setup no longer blocks on the first offer refresh.
  The summary/entity surface is created first, then the initial Club Royale
  refresh runs in the background.
- Club Royale login-token failures during offer polling are now treated as
  update failures for the Club Royale coordinator instead of setup-breaking
  authentication failures.

## Notes

After upgrading through HACS, restart Home Assistant and create a new entry with
`Club Royale offers`.
