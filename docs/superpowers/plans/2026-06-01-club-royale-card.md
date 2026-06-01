# Club Royale Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Club Royale offer parsing plus a custom Lovelace calendar card that shows offer sailings as multi-day impact ranges.

**Architecture:** Extend `RCCLClient` to fetch Club Royale offer list and per-offer sailing details from the web casino API, normalize those rows into a card-safe data contract, and expose them through a Home Assistant websocket command. Serve a plain custom element JavaScript card from the integration's static path; the card calls the websocket command and renders a month grid with range bars.

**Tech Stack:** Home Assistant custom integration, aiohttp-style async client, Home Assistant websocket API, `async_register_static_paths`, vanilla JavaScript custom element, Python `unittest`.

---

### Task 1: Club Royale Data Model

**Files:**
- Modify: `custom_components/rccl/api.py`
- Modify: `tests/test_api_helpers.py`

- [ ] Write failing tests for normalizing offer-detail sailings into rows with `sail_date`, `return_date`, `ship_name`, `itinerary_name`, cabin guarantee, offer occupancy, offer metadata, and no booking/passenger fields.
- [ ] Run the targeted test and verify it fails because the helper does not exist.
- [ ] Implement pure helpers for `club_royale_sailings()`, date-range calculation, room/cabin labels, and occupancy parsing.
- [ ] Run the targeted test and verify it passes.

### Task 2: Club Royale API Fetch

**Files:**
- Modify: `custom_components/rccl/api.py`
- Modify: `tests/test_api_helpers.py`

- [ ] Write failing async client test proving it calls the offer list endpoint and then the per-offer detail endpoint with `offerCode` and `playerOfferId`.
- [ ] Run the targeted test and verify it fails.
- [ ] Add web casino request helpers using `x-account-id` and `x-loyalty-id`, derive loyalty id from account data, and include `club_royale` in coordinator data as an optional fetch.
- [ ] Run the targeted test and verify it passes.

### Task 3: Frontend Serving and Websocket

**Files:**
- Create: `custom_components/rccl/frontend.py`
- Modify: `custom_components/rccl/__init__.py`
- Modify: `custom_components/rccl/manifest.json`
- Modify: `pyproject.toml`

- [ ] Register `/rccl_static` with `hass.http.async_register_static_paths`.
- [ ] Register a websocket command `rccl/club_royale_sailings` that returns normalized sailings for one entry or all entries.
- [ ] Wire `async_setup()` to register the static path and websocket command once.
- [ ] Bump version to alpha 7.

### Task 4: Lovelace Card

**Files:**
- Create: `custom_components/rccl/www/club-royale-calendar-card.js`
- Modify: `README.md`

- [ ] Build `custom:rccl-club-royale-calendar-card`.
- [ ] Fetch data using `hass.connection.sendMessagePromise({ type: "rccl/club_royale_sailings" })`.
- [ ] Render a month grid where each sailing spans `sail_date` through `return_date`, splitting at week boundaries.
- [ ] Label bars with itinerary/sailing and ship, and show offer/cabin/occupancy details in hover/focus/tap details.
- [ ] Document the dashboard resource URL and example card YAML.

### Task 5: Verification and Release

**Files:**
- Create: `docs/publishing/alpha-7-release-notes.md`
- Modify: `docs/README.md`

- [ ] Run `python3 -m compileall -q custom_components tests scripts`.
- [ ] Run `python3 -m unittest discover -s tests -v`.
- [ ] Validate JSON files.
- [ ] Run `git diff --check`.
- [ ] Commit, push, tag `v0.1.0-alpha.7`, and create a prerelease.
