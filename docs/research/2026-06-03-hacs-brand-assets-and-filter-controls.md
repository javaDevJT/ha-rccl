# HACS Brand Assets and Club Royale Filter Controls

## HACS and Home Assistant Asset Notes

- HACS integration repositories must keep all runtime files inside
  `custom_components/<domain>/` and require a `manifest.json` with `domain`,
  `documentation`, `issue_tracker`, `codeowners`, `name`, and `version`.
- HACS also checks that integrations conform to Home Assistant brand standards.
- Home Assistant custom integrations can ship local brand assets in
  `custom_components/<domain>/brand/`.
- The supported local brand filenames include `icon.png`, `logo.png`,
  `dark_icon.png`, `dark_logo.png`, and `@2x` variants. Local brand images take
  precedence over the brands CDN in Home Assistant 2026.3 and newer.
- The initial RCCL HAR did not expose a clean first-party logo asset; it mostly
  exposed page art and compiled JavaScript. The user later supplied the
  first-party Royal Caribbean SVG at
  `https://www.royalcaribbean.com/myaccount/assets/images/royal/logo.svg`.
- This repo stores that SVG as `custom_components/rccl/brand/logo.svg` and
  generates local `icon.png` and `logo.png` from it with
  `scripts/generate_brand_assets.py`.

## Filter Control Notes

- Native `<select>` filters were a poor fit for frequent Home Assistant card
  updates because render churn can close platform dropdowns.
- The card now uses custom `<details>` menus with checkbox items. This supports
  multiple selected values for ship, offer type, offer, departure, and nights.
- A missing filter key means unrestricted/all values. This lets "Select all"
  continue to include new values when moving between months.
- An empty filter array means "Deselect all" for that facet and intentionally
  matches no sailings.
- The master "Reset filters" button clears all facets and returns every filter
  to unrestricted mode.

## Sources

- HACS integration publishing documentation:
  https://hacs.xyz/docs/publish/integration/
- HACS general publishing documentation:
  https://hacs.xyz/docs/publish/start/
- Home Assistant custom integration brand image announcement:
  https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api
- Home Assistant brand image documentation:
  https://developers.home-assistant.io/docs/core/integration/brand_images
