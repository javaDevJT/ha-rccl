# Alpha 5 Release Notes

Tag: `v0.1.0-alpha.5`

This alpha fixes setup failing immediately after a successful config-flow login.

## Fixed

- Home Assistant setup now uses the fresh `access_token` and `account_id` stored
  by the config flow.
- Setup no longer performs a second immediate RCCL login just because
  username/password are present.
- Runtime credentials still keep username/password so later auth failures can
  trigger automatic reauthentication.

## Still Known

- Multifactor and bot-challenge flows are not implemented.
- Live Home Assistant setup should be retested with this alpha.
