# Royal Caribbean Home Assistant Integration

Custom Home Assistant integration for importing Royal Caribbean account data into
Home Assistant through HACS.

This repository logs in with Royal Caribbean account credentials, derives the
session headers used by RCCL's web account APIs, and polls account, booking,
upgrade, loyalty, and sailing-history endpoints.

## Features

- UI config flow.
- Cloud polling through Home Assistant's `DataUpdateCoordinator`.
- Account-level sensors for upcoming cruises, next sailing date, upgrade
  eligibility, loyalty tier/points, total trips, and total nights.
- Read-only calendar entity for upcoming and historical sailings.
- Club Royale offer sailing parser and custom Lovelace calendar card.
- Diagnostics with sensitive config values redacted.

## Installation

1. Install `Royal Caribbean` from the HACS integrations catalog. Until this
   repository is included as a HACS default repository, add it as a HACS custom
   repository with category `Integration`.
2. Install `Royal Caribbean`.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and search for
   `Royal Caribbean`.

## Required Values

The config flow asks for:

- Royal Caribbean account email
- Royal Caribbean account password
- optional scan interval

The integration stores credentials in the Home Assistant config entry and uses
them to obtain short-lived RCCL session tokens. Treat your Home Assistant
configuration storage as sensitive.

## Club Royale Card

Add this dashboard resource:

```yaml
url: /rccl_static/club-royale-calendar-card.js
type: module
```

Then add the card:

```yaml
type: custom:rccl-club-royale-calendar-card
```

Optional card settings:

```yaml
type: custom:rccl-club-royale-calendar-card
title: Club Royale Sailings
entry_id: your_config_entry_id
month: "2026-06"
```

The card renders offer sailings as date ranges from departure through return
day. Calendar bars show itinerary/sailing name and ship name; details include
offer name/code, cabin guarantee/category, reserve-by date, sail-by date, and
offer occupancy when RCCL exposes it.

## Limitations

- This project is not affiliated with, endorsed by, or supported by Royal
  Caribbean Group.
- RCCL may change or harden the web login flow. If login starts failing, Home
  Assistant will start a reauthentication flow.
- Booking IDs and passenger fields may be exposed in Home Assistant attributes
  for account booking entities. Treat Home Assistant state history as sensitive.
- Club Royale offer sailings generally do not include booking IDs or passenger
  records, so the custom card does not display those fields.
- Multifactor or bot-challenge flows are not implemented yet.

## Documentation

Start with [docs/README.md](docs/README.md) for the document map and the current
research/design notes.
