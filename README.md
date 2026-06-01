# Royal Caribbean Home Assistant Integration

Custom Home Assistant integration for importing Royal Caribbean account data into
Home Assistant through HACS.

This repository currently implements a token-based first pass. It uses account
API headers captured from a browser session and polls RCCL account, booking,
upgrade, loyalty, and sailing-history endpoints. Automated username/password
login is intentionally left out until the RCCL auth flow can be researched with
complete response bodies and without depending on brittle browser-only behavior.

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

The current config flow asks for:

- `access-token`
- `account-id`
- `appkey`
- optional `vds-id`

These are request headers used by the RCCL web account APIs. Browser developer
tools can show them on calls to `aws-prd.api.rccl.com`, for example the guest
account or profile bookings endpoints. Treat all values as secrets.

## Limitations

- RCCL may expire tokens quickly; reconfigure the integration with fresh header
  values if polling starts returning authentication errors.
- The integration avoids writing raw booking IDs, passenger names, or stateroom
  numbers into sensor attributes.
- The HAR showed the login/authorize sequence, but the saved auth response
  bodies were empty, so this version does not attempt automated login.

## Documentation

Start with [docs/README.md](docs/README.md) for the document map and the current
research/design notes.
