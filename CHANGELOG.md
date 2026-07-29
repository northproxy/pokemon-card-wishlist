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
- Permanent image download utility in
  `scripts/images/download_card_images.py` for downloading small and large
  Pokemon TCG Data card images into set-specific local directories.
- Usage and validation documentation in `scripts/images/README.md`.
- Reproducible local PostgreSQL development environment using Docker Compose.
- Local environment template in `.env.example` with secrets kept outside Git.
- Docker-based `dbmate` service and tracked migration directory under `db/`.
- Local PostgreSQL development and troubleshooting guide in
  `docs/database/local-postgresql-development-setup.md`.
- Seventeen incremental `dbmate` migrations implementing the complete physical
  PostgreSQL schema across `21` project tables.
- Permanent executable schema validation in
  `scripts/database/validate_schema.sql`.

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
- Advanced the current project focus to `M3 — Data model` after preparing the
  local database development environment.
- Clarified that local PostgreSQL development is implemented and validated while
  Raspberry Pi deployment, backup, restore, NocoDB, and private access remain
  planned.
- Updated the data-model status from conceptual and not started to implemented
  and locally validated.
- Advanced the M3 focus from schema creation to the controlled Primal Clash
  bootstrap and first import path.

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
- Validated the complete `xy5` image download workflow:
  - processed `164` card records;
  - confirmed `328` PNG files under `images/raw/xy5/`;
  - confirmed that no `.part` files remained;
  - repeated the run with `0` downloads, `328` existing files, `0` failures,
    `0` invalid records, and `0` missing-image records.
- Validated WSL 2 and Docker Desktop integration from both Windows and Ubuntu
  24.04.
- Validated PostgreSQL 17 container health, local-only port binding, and DBeaver
  connectivity.
- Validated `dbmate` through Docker for migration creation, status checks,
  application, schema generation, and rollback.
- Confirmed that `.env` is ignored by Git and that tracked SQL migrations and
  `db/schema.sql` are exempted from the general `*.sql` ignore rule.
- Applied and rollback-validated all `17` schema migrations with `dbmate`.
- Confirmed `21` project tables and `22` total public tables including
  `schema_migrations`.
- Validated source-scoped uniqueness, catalogue hierarchy constraints, import
  lifecycle rules, staging-state rules, mapping review consistency, active
  production mappings, price snapshot integrity, and wishlist isolation.
- Passed the permanent schema-wide executable validation with
  `schema validation passed`.

### Security

- Documented the initial security baseline.
- Documented that secrets must remain outside the repository.
- Documented that PostgreSQL must not be exposed directly to the public internet.
- Documented planned security controls for private access, backups, dependency review, imported data, and restore testing.
- Bound the local PostgreSQL port to `127.0.0.1` rather than all network
  interfaces.
- Disabled automatic startup of the unrelated Windows PostgreSQL 18 service to
  prevent local port conflicts without deleting its data.

### Documentation

- Standardised the project name as `Pokemon Card Wishlist`.
- Standardised milestone names from `M0` through `M7`.
- Updated the public project status to reflect completion of discovery and the start of repository-foundation work.
- Updated the public project status to reflect completion of the repository foundation and the start of infrastructure work.
- Added contribution workflow, commit guidance, pull request expectations, validation evidence requirements, and scope-control rules.
- Added local PostgreSQL setup and troubleshooting documentation.
- Added a README link to the local PostgreSQL development guide.
- Added a README link to the image download utilities documentation.

### Planned

The following remain planned and are not yet implemented or validated:

- Raspberry Pi Docker and Docker Compose deployment;
- Raspberry Pi PostgreSQL deployment and persistent SSD storage;
- NocoDB deployment;
- Tailscale private access;
- import pipeline;
- wishlist workflow;
- CSV export;
- backup scheduling;
- restore testing;
- Raspberry Pi restart recovery;
- release `v0.1.0`.

## Release history

No versioned release has been published yet.
