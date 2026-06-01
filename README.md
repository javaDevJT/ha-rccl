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
- Diagnostics with sensitive config values redacted.

## Installation

1. Add this repository as a HACS custom repository with category
   `Integration`.
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

## Limitations

- RCCL may change or harden the web login flow. If login starts failing, Home
  Assistant will start a reauthentication flow.
- The integration avoids writing raw booking IDs, passenger names, or stateroom
  numbers into sensor attributes.
- Multifactor or bot-challenge flows are not implemented yet.

## Documentation

Start with [docs/README.md](docs/README.md) for the document map and the current
research/design notes.
