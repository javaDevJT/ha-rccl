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
- [research/2026-06-01-entity-names.md](research/2026-06-01-entity-names.md)
  records the device-page entity naming fix.
- [research/2026-06-01-club-royale-offers.md](research/2026-06-01-club-royale-offers.md)
  records the Club Royale offer and sailing endpoint shape.
- [research/2026-06-01-loyalty-totals-and-booking-attributes.md](research/2026-06-01-loyalty-totals-and-booking-attributes.md)
  records the inaccurate total trip/night diagnosis and the decision to expose
  booking/passenger attributes in Home Assistant.
- [design/2026-06-01-component-design.md](design/2026-06-01-component-design.md)
  explains the login-based component design and the Home Assistant entities.
- [design/2026-06-01-club-royale-card.md](design/2026-06-01-club-royale-card.md)
  captures the Club Royale custom card display and backend data contract.
- [superpowers/plans/2026-06-01-club-royale-card.md](superpowers/plans/2026-06-01-club-royale-card.md)
  is the implementation plan for the Club Royale offer parser and Lovelace card.
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
- [publishing/alpha-6-release-notes.md](publishing/alpha-6-release-notes.md)
  describes the entity display-name fix.
- [publishing/alpha-7-release-notes.md](publishing/alpha-7-release-notes.md)
  describes the Club Royale offer card and totals fix.
