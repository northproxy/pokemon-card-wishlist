# Changelog

All notable changes to Pokemon Card Wishlist will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project intends to follow Semantic Versioning after the first release.

## [Unreleased]

### Added

- Initial project documentation:

  - `README.md`
  - `MVP_SCOPE.md`
  - `PROJECT.md`
  - `STACK.md`
  - `DECISIONS.md`
  - `GITHUB_PROJECT.md`
  - `LEARNING_LOG.md`
  - `REVIEW_SUMMARY.md`
- Repository contribution guidance in `CONTRIBUTING.md`.
- Initial security policy in `SECURITY.md`.
- Initial release roadmap in `ROADMAP.md`.
- GitHub issue templates for tasks, bugs, research, and decisions.
- Pull request template with validation, security, data-quality, and recovery checks.
- Basic Markdown validation through GitHub Actions.
- Project-specific Markdown lint configuration in `.markdownlint-cli2.yaml`.
- GitHub Project fields and views for milestone, workflow, priority, effort, learning value, risk, documentation, decisions, and data-quality tracking.
- Initial GitHub issue set for completing and validating `M1 — Repository foundation`.
- Discovery documentation for source inventory, source fields, record identity, language and variant modelling, image mapping, data-quality findings, and first-expansion selection.
- Primal Clash vertical-slice fixtures for:

  - canonical cards;
  - Cardmarket products;
  - Cardmarket price records;
  - mapping review.
- Discovery and validation scripts for building, analysing, and validating the Primal Clash fixture.
- Source-scoped external identifier strategy.
- Separate concepts for canonical cards, editions, language and finish variants, Cardmarket products, and price snapshots.
- Informational canonical-card price rule based on the minimum supported non-null Cardmarket `avg30`.
- Explicit `unmatched_duplicate_candidate` handling for duplicate-like Cardmarket source products.
- `ADR-008` defining staging and validated transactional merges for repeated imports.
- `ADR-009` defining controlled rejected and unresolved-record review states.
- `ADR-010` proposing backup scope, retention, and restore validation.

### Changed

- Updated the repository status from `M0 — Discovery` to `M1 — Repository foundation`.
- Updated the current milestone from `M1 — Repository foundation` to `M2 — Infrastructure` after the M1 exit review.
- Replaced inferred Cardmarket product-order matching with direct `idProduct` evidence from individual product pages.
- Clarified the distinction between `Proposed`, `Planned`, `Implemented`, and `Validated`.
- Clarified that the initial wishlist references canonical cards rather than specific market variants.
- Clarified that application, database, infrastructure, authentication, backup, and deployment implementation have not started.
- Accepted `ADR-008` after project-owner review.
- Accepted `ADR-009` after project-owner review.
- Recorded `ADR-010` as `Proposed` pending M2 implementation and restore-test evidence.

### Validated

- Completed and validated `M0 — Discovery` on 2026-07-27.
- Validated the Primal Clash vertical slice with:

  - `164` canonical cards covered;
  - `167` Cardmarket listing variants mapped through direct `idProduct` evidence;
  - `4` Online Code Card products excluded from MVP catalogue scope;
  - `6` unlisted products preserved as `unmatched_duplicate_candidate`;
  - no ambiguous, conflicting, or ordinary unmatched mapping rows.
- Validated deterministic image metadata for all `164` canonical Primal Clash cards.
- Validated unique small and large image URLs using the expected Pokémon TCG image path pattern.
- Validated the permanent Primal Clash fixture checks for structure, counts, mapping coverage, controlled statuses, exclusions, unresolved-status handling, and image metadata.
- Validated the `Markdown validation` GitHub Actions workflow against the current repository documentation.
- Confirmed that all tracked Markdown files pass the configured lint rules.
- Completed and validated `M1 — Repository foundation` on 2026-07-27.
- Validated the GitHub Project fields, views, filters, sorting, and initial M1 issue set.
- Verified all public README documentation links, the Markdown workflow badge, and the issue-template contact links.
- Confirmed that the required M1 repository files are present and the working tree is clean.

### Security

- Documented the initial security baseline.
- Documented that secrets must remain outside the repository.
- Documented that PostgreSQL must not be exposed directly to the public internet.
- Documented planned security controls for private access, backups, dependency review, imported data, and restore testing.

### Documentation

- Standardised the project name as `Pokemon Card Wishlist`.
- Standardised milestone names from `M0` through `M7`.
- Updated the public project status to reflect completion of discovery and the start of repository-foundation work.
- Updated the public project status to reflect completion of the repository foundation and the start of infrastructure work.
- Added contribution workflow, commit guidance, pull request expectations, validation evidence requirements, and scope-control rules.

### Planned

The following remain planned and are not yet implemented or validated:

- Docker and Docker Compose infrastructure;
- PostgreSQL deployment;
- NocoDB deployment;
- Tailscale private access;
- persistent SSD storage;
- database schema and migrations;
- import pipeline;
- wishlist workflow;
- CSV export;
- backup scheduling;
- restore testing;
- Raspberry Pi restart recovery;
- release `v0.1.0`.

## Release history

No versioned release has been published yet.
