# Club Royale Entity Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a separate Club Royale config path that creates Home Assistant entities from retrieved offer sailings.

**Architecture:** Existing Royal Caribbean account entries continue to use the normal account coordinator and `sensor` plus `calendar` platforms. Club Royale entries use a new entry type, a dedicated coordinator with isolated login sessions, and sensor-only entities. The custom card reads those entities first and keeps websocket loading only as fallback.

**Tech Stack:** Home Assistant config entries, DataUpdateCoordinator, SensorEntity, existing RCCL API helpers, Lovelace custom card JavaScript.

---

### Task 1: Source Contract Tests

**Files:**
- Modify: `tests/test_api_helpers.py`

- [ ] Add a failing source-contract test that requires a Club Royale config entry type, `async_step_club_royale`, a dedicated coordinator, entity-backed sensors, and card entity scanning.
- [ ] Run the targeted test and confirm it fails before implementation.

### Task 2: Config Entry Split

**Files:**
- Modify: `custom_components/rccl/const.py`
- Modify: `custom_components/rccl/config_flow.py`
- Modify: `custom_components/rccl/strings.json`

- [ ] Add entry-type constants and a Club Royale loyalty-id key.
- [ ] Convert `async_step_user` to a menu with account and Club Royale choices.
- [ ] Add Club Royale validation using a standalone cookie jar and Club Royale login referer.
- [ ] Keep existing account behavior under `async_step_account`.

### Task 3: Coordinator And Entities

**Files:**
- Modify: `custom_components/rccl/coordinator.py`
- Modify: `custom_components/rccl/__init__.py`
- Modify: `custom_components/rccl/sensor.py`

- [ ] Add a Club Royale coordinator that fetches normalized sailings through isolated sessions.
- [ ] Route Club Royale config entries to sensor-only setup.
- [ ] Create a summary sensor and dynamic per-sailing date sensors with rich attributes.

### Task 4: Entity-Backed Card

**Files:**
- Modify: `custom_components/rccl/www/club-royale-calendar-card.js`

- [ ] Read Club Royale sailing entities from `hass.states`.
- [ ] Use entity data before websocket fallback.
- [ ] Preserve the existing calendar layout and hover/detail behavior.

### Task 5: Verification And Release

**Files:**
- Modify: `custom_components/rccl/manifest.json`
- Modify: `pyproject.toml`
- Create: `docs/publishing/alpha-11-release-notes.md`
- Modify: `docs/README.md`

- [ ] Run compile, unit tests, JS syntax check, JSON parse, diff check, and secret scan.
- [ ] Bump to alpha 11.
- [ ] Commit, push, tag, and create a GitHub prerelease.
