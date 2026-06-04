# HACS Default Readiness

## Current HACS Requirements

The HACS default-repository documentation requires a repository to be public on
GitHub, installable as a custom repository, and backed by passing HACS Action
and Hassfest workflows before opening a `hacs/default` pull request. A full
GitHub release, not just a tag, must be created after those actions pass.

The same checklist also verifies that the repository has a description, issues
enabled, topics defined, a valid manifest, a valid `hacs.json`, at least one
release, sorted JSON in the default-list PR, and Home Assistant Brands coverage
for integrations.

## Repository State

`javaDevJT/ha-rccl` is public, not archived, has issues enabled, and has the
description `Royal Caribbean custom integration for Home Assistant`.

The `hacs/default` `integration` list is a sorted JSON array. The alphabetical
position for this repository is after `javaDevJT/DTE-Rates-for-Home-Assistant`
and before `JayBlackedOut/hass-nhlapi`.

## Changes For Readiness

- Added HACS, Hassfest, and unit/syntax GitHub workflows.
- Added repository and manifest codeowner metadata.
- Added an MIT license.
- Promoted package metadata from alpha prerelease numbering to `0.1.0` so the
  next release can be a normal release for default-repository review.
