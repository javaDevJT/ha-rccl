# Account Reload Auth And Offer Attributes

## Symptoms

- Reloading the Royal Caribbean account config entry can fail with
  `RCCL did not return a login token`.
- Home Assistant Recorder warns when a Club Royale offer sensor has more than
  16,384 bytes of attributes, especially large offer-code entities such as
  `sensor.club_royale_offers_club_royale_offer_26tier3`.

## Findings

- The account setup path treated every `RCCLAuthenticationError` as a fatal
  `ConfigEntryAuthFailed`, including the intermittent OpenAM response where
  RCCL returns HTTP success without a `tokenId`.
- The normal account coordinator can also hit the same missing-token error
  during `async_config_entry_first_refresh` when an existing token needs
  reauthentication during a reload.
- Club Royale offer sensors were exposing full offer summary dictionaries,
  including hundreds of sailing ids, source sailing ids, and sail dates.

## Contract

- HTTP 401/403 and other credential rejections still fail authentication.
- The exact missing-token message is treated as transient only when the config
  entry already contains stored account context.
- Account setup may continue with stored credentials and schedule a background
  refresh after entity setup.
- Offer-code sensors expose compact Recorder-safe attributes: useful offer
  metadata, capped display lists, and counts for omitted raw arrays.
