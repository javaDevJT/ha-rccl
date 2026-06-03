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
that reads credentials from environment variables. `scripts/live_club_royale_check.py`
does the same for Club Royale offers. `scripts/live_club_royale_aiohttp_check.py`
reproduces the Home Assistant aiohttp request stack for Club Royale debugging.

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
- [research/2026-06-01-club-royale-session-split.md](research/2026-06-01-club-royale-session-split.md)
  records why Club Royale uses a standalone login session.
- [research/2026-06-01-loyalty-history-and-card-js.md](research/2026-06-01-loyalty-history-and-card-js.md)
  records the loyalty-history query parameter and frontend registration fixes.
- [research/2026-06-01-club-royale-websocket-data.md](research/2026-06-01-club-royale-websocket-data.md)
  records the Home Assistant HAR evidence for the Club Royale websocket request
  hanging without a result frame.
- [research/2026-06-01-club-royale-alpha-12-regressions.md](research/2026-06-01-club-royale-alpha-12-regressions.md)
  records the unlabeled menu and Club Royale setup-failure diagnosis.
- [research/2026-06-01-club-royale-session-management.md](research/2026-06-01-club-royale-session-management.md)
  records the Home Assistant-managed aiohttp session and Club Royale credential
  reuse fixes.
- [research/2026-06-01-club-royale-offers-403-live-test.md](research/2026-06-01-club-royale-offers-403-live-test.md)
  records the live 403 diagnosis for the Club Royale offers API.
- [research/2026-06-01-club-royale-aiohttp-403.md](research/2026-06-01-club-royale-aiohttp-403.md)
  records the live aiohttp-vs-urllib Club Royale 403 diagnosis.
- [research/2026-06-01-club-royale-calendar-overflow.md](research/2026-06-01-club-royale-calendar-overflow.md)
  records the custom-card dense-month overflow diagnosis and fix.
- [research/2026-06-01-club-royale-calendar-scroll.md](research/2026-06-01-club-royale-calendar-scroll.md)
  records the Home Assistant card-size clipping and internal-scroll fix.
- [research/2026-06-02-club-royale-calendar-scroll-position.md](research/2026-06-02-club-royale-calendar-scroll-position.md)
  records the scroll-position preservation fix for card re-renders.
- [research/2026-06-02-club-royale-card-filters.md](research/2026-06-02-club-royale-card-filters.md)
  records the Club Royale card filter controls and field mappings.
- [research/2026-06-02-club-royale-dropdown-rerender.md](research/2026-06-02-club-royale-dropdown-rerender.md)
  records the fix for dropdowns closing on unchanged Home Assistant updates.
- [research/2026-06-03-hacs-brand-assets-and-filter-controls.md](research/2026-06-03-hacs-brand-assets-and-filter-controls.md)
  records HACS/Home Assistant brand asset requirements and the multi-select
  Club Royale filter behavior.
- [design/2026-06-01-component-design.md](design/2026-06-01-component-design.md)
  explains the login-based component design and the Home Assistant entities.
- [design/2026-06-01-club-royale-card.md](design/2026-06-01-club-royale-card.md)
  captures the Club Royale custom card display and backend data contract.
- [design/2026-06-01-club-royale-entity-config.md](design/2026-06-01-club-royale-entity-config.md)
  captures the separate Club Royale config-entry and entity-backed card design.
- [superpowers/plans/2026-06-01-club-royale-card.md](superpowers/plans/2026-06-01-club-royale-card.md)
  is the implementation plan for the Club Royale offer parser and Lovelace card.
- [superpowers/plans/2026-06-01-club-royale-entity-config.md](superpowers/plans/2026-06-01-club-royale-entity-config.md)
  is the implementation plan for separate Club Royale config and entities.
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
- [publishing/alpha-8-release-notes.md](publishing/alpha-8-release-notes.md)
  describes the Club Royale standalone-session fix.
- [publishing/alpha-9-release-notes.md](publishing/alpha-9-release-notes.md)
  describes the past-cruise history and custom-card loading fixes.
- [publishing/alpha-10-release-notes.md](publishing/alpha-10-release-notes.md)
  describes the Club Royale websocket data-loading fix.
- [publishing/alpha-11-release-notes.md](publishing/alpha-11-release-notes.md)
  describes the separate Club Royale config path and entity-backed card data.
- [publishing/alpha-12-release-notes.md](publishing/alpha-12-release-notes.md)
  describes the Club Royale config menu label and nonblocking setup fixes.
- [publishing/alpha-13-release-notes.md](publishing/alpha-13-release-notes.md)
  describes the Home Assistant aiohttp session and Club Royale credential reuse
  fixes.
- [publishing/alpha-14-release-notes.md](publishing/alpha-14-release-notes.md)
  describes the Club Royale offers page priming and authorization-header fixes.
- [publishing/alpha-15-release-notes.md](publishing/alpha-15-release-notes.md)
  describes the urllib-backed Club Royale session fix for Home Assistant.
- [publishing/alpha-16-release-notes.md](publishing/alpha-16-release-notes.md)
  describes the Club Royale calendar dense-month layout fix.
- [publishing/alpha-17-release-notes.md](publishing/alpha-17-release-notes.md)
  describes the Club Royale calendar grid-size and scroll fix.
- [publishing/alpha-18-release-notes.md](publishing/alpha-18-release-notes.md)
  describes the Club Royale calendar scroll-position fix.
- [publishing/alpha-19-release-notes.md](publishing/alpha-19-release-notes.md)
  describes the in-place Club Royale sailing selection fix.
- [publishing/alpha-20-release-notes.md](publishing/alpha-20-release-notes.md)
  describes the Club Royale card filter controls.
- [publishing/alpha-21-release-notes.md](publishing/alpha-21-release-notes.md)
  describes the Club Royale dropdown re-render fix.
- [publishing/alpha-22-release-notes.md](publishing/alpha-22-release-notes.md)
  describes the focused-filter render deferral fix.
- [publishing/alpha-23-release-notes.md](publishing/alpha-23-release-notes.md)
  describes local brand assets and multi-select Club Royale filters.
- [publishing/alpha-24-release-notes.md](publishing/alpha-24-release-notes.md)
  describes replacing the brand assets with the supplied Royal Caribbean SVG.
