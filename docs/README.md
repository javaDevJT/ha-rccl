# Documentation Map

This folder stores project knowledge that should survive beyond a single coding
session. Add new information here whenever research, runtime inspection, or
implementation work discovers something useful.

## Structure

- `research/`: externally gathered facts and sanitized evidence, including HAR
  analysis and links to upstream Home Assistant or HACS documentation.
- `design/`: architecture decisions, implementation plans, and known tradeoffs.
- `publishing/`: release, repository, and distribution notes.

Repository scripts live in `scripts/` and are intentionally small operational
helpers. `scripts/live_login_check.py` is a sanitized live RCCL login smoke test
that reads credentials from environment variables.

## Current Notes

- [research/2026-06-01-har-analysis.md](research/2026-06-01-har-analysis.md)
  summarizes the RCCL HAR without exposing account tokens or passenger details.
- [research/2026-06-01-login-hang.md](research/2026-06-01-login-hang.md)
  records the config-flow hang diagnosis and timeout fix.
- [design/2026-06-01-component-design.md](design/2026-06-01-component-design.md)
  explains the login-based component design and the Home Assistant entities.
- [publishing/2026-06-01-alpha-1.md](publishing/2026-06-01-alpha-1.md)
  tracks the alpha 1 GitHub publishing flow.
- [publishing/alpha-2-release-notes.md](publishing/alpha-2-release-notes.md)
  describes the login-flow fix after alpha 1.
- [publishing/alpha-3-release-notes.md](publishing/alpha-3-release-notes.md)
  describes the config-flow timeout fix.
- [publishing/alpha-4-release-notes.md](publishing/alpha-4-release-notes.md)
  describes the live-tested login request shape.
- [publishing/alpha-5-release-notes.md](publishing/alpha-5-release-notes.md)
  describes the setup fix after successful config creation.
