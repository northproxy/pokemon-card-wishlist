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
- Controlled Primal Clash canonical-card staging and production import scripts.
- Cardmarket product staging importer in `scripts/import/import_primal_clash_market_products.py`.
- Controlled Cardmarket product rollback injector in `scripts/import/fail_import_primal_clash_market_products.py`.
- Cardmarket product production merge in `scripts/import/merge_primal_clash_market_products.py`.
- Cardmarket product source-to-target contract in `docs/import/primal-clash-source-to-target.md`.
- Cardmarket mapping staging importer and controlled staging rollback utility.
- Cardmarket mapping pre-merge validator and production-merge rollback utility.
- Transactional Cardmarket mapping production merge covering mapping cases, observations, selected candidates, status history, active production mappings, and per-record audit outcomes.
- Cardmarket mapping production merge handoff in `docs/import/m4-cardmarket-mapping-production-merge-handoff.md`.
- Cardmarket price staging importer in `scripts/import/import_primal_clash_market_prices.py`.
- Controlled Cardmarket price staging rollback utility in `scripts/import/fail_import_primal_clash_market_prices.py`.
- Append-only Cardmarket price production merge in `scripts/import/merge_primal_clash_market_prices.py`.
- Controlled Cardmarket price production-merge rollback utility in `scripts/import/fail_merge_primal_clash_market_prices.py`.
- Permanent runtime canonical-card `From` price validator in `scripts/database/validate_primal_clash_from_prices.sql`.
- Consolidated Primal Clash import validation report in `docs/import/primal-clash-import-validation-report.md`.
- Formal M4 milestone exit review in `docs/import/m4-first-import-exit-review.md`.

- Canonical `me55c` fixture containing `30` records for 30th Celebration: Classic Collection, plus dedicated catalogue staging and production merge scripts.
- Updated `scripts/images/download_card_images.py` source directory for the relocated Pokémon TCG Data files; its existing direct-image-URL handling supports ScryDex URLs.

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
- Completed the `M3 — Data model` exit and advanced the active milestone to `M4 — First import`.
- Advanced the M4 implementation focus from canonical cards and Cardmarket products to Cardmarket mappings.
- Advanced the M4 implementation focus from completed Cardmarket mappings to Cardmarket prices and runtime `From` pricing.
- Advanced the M4 focus from completed Cardmarket price implementation to edition and variant scope resolution and the final Primal Clash validation report.
- Accepted `ADR-013`, deferring automatic edition and variant derivation until controlled evidence proves edition identity, language, and finish.
- Advanced the remaining M4 focus to the consolidated Primal Clash import validation report and exit review.
- Completed the `M4 — First import` exit review and returned the active project focus to `M2 — Infrastructure`.
- Updated project status documentation to distinguish the completed Primal Clash import from the still-planned application and Raspberry Pi deployment.
- Extended the Primal Clash source-to-target contract with the validated Cardmarket price staging, append-only snapshot, rollback, repeat-merge, and runtime `MIN(avg30)` rules.
- Documented the source missing-value normalization rule `0000-00-00 00:00:00` → `NULL` for Cardmarket product timestamps.
- Documented explicit skipped-outcome handling for Online Code Card products outside MVP collection scope.

### Validated

- Validated the `me55c` canonical fixture: `30` cards and SHA-256 `b8b20bb7ee8bfb72ea00953be7cdad0b2d17a555866d9f39b2f19c31929cc121`.
- Confirmed `me55c` staging import run `16` with `30` validated records and its production merge into expansion ID `3`: `30` inserted, `0` updated, `0` unchanged, `0` reactivated.
- Confirmed the `me55c` production expansion contains `30` cards and downloaded `60` local images with `0` failures, `0` invalid records and `0` missing-image records.
- `me55c` market-product, mapping, and price imports remain out of scope of this validation; repeat-import and rollback behaviour for `me55c` are not yet validated.

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
- Validated the controlled Primal Clash canonical-card production import and repeated unchanged merge.
- Validated Cardmarket product staging with `177` valid rows, `164` normalized missing timestamps, and `13` parsed timestamps per run.
- Validated complete transaction rollback after an intentional failure following `10` partial Cardmarket product staging inserts.
- Validated the first Cardmarket product production merge with `173` inserted and `4` skipped Online Code Card outcomes.
- Validated the repeated Cardmarket product production merge with `173` unchanged and `4` skipped outcomes.
- Confirmed `173` active production market products, `0` inactive products, `0` duplicate source identities, and `0` Online Code Card products in production.
- Confirmed `177` reconciled `import_record_outcomes` for each Cardmarket product production run.
- Validated the current mapping fixture with `165` candidate mappings, `6` exclusions, and `6` unmatched duplicate candidates.
- Reviewed `12` rows containing edition codes: `10` candidate mappings supported only at card scope and `2` excluded oversized products.
- Confirmed `0` candidate mappings at edition scope and `0` at variant scope.
- Confirmed `card_editions = 0` and `card_variants = 0` as the controlled M4 production state.
- Confirmed the deferral leaves `165` active mappings, `173` price snapshots, and runtime `From` prices for `164` canonical cards unchanged.
- Validated complete rollback after an intentional failure following one complete production mapping chain.
- Validated the first Cardmarket mapping production merge with `165` inserted mappings, `12` skipped outcomes, `173` mapping cases, `173` observations, `165` selected candidates, and `173` status transitions.
- Validated the repeated Cardmarket mapping production merge with `165` unchanged mappings, `12` skipped outcomes, `0` new cases, `0` new active mappings, and `0` new status transitions.
- Confirmed final cumulative mapping state of `173` cases, `346` observations, `330` candidates, `173` status-history rows, and `165` active production mappings.
- Validated Cardmarket price staging with `177` normalized and valid records, `177` non-null `avg30` values, `169` non-null `avg30-holo` values, and `8` records without `avg30-holo`.
- Validated complete staging rollback after an intentional failure following one partial Cardmarket price staging insert.
- Validated complete production rollback after an intentional failure following one price snapshot and one audit outcome.
- Validated the first Cardmarket price production merge with `173` inserted snapshots and `4` skipped Online Code Card outcomes.
- Validated the repeated Cardmarket price production merge with `0` inserted snapshots, `173` unchanged snapshots, and `4` skipped outcomes.
- Confirmed final `market_price_snapshots` count of `173` with `0` duplicate `(market_product_id, source_snapshot_at)` identities.
- Validated runtime canonical-card pricing across `165` active mapped market products and `164` canonical cards.
- Confirmed the runtime price rule uses the latest eligible successful snapshot per market product and calculates `MIN(avg30)` without using `avg30_holo`.
- Confirmed the runtime result can be labelled `From` and `30-day average`.

- Completed and validated `M4 — First import` on 2026-08-03.
- Confirmed the final Primal Clash production state of `164` active canonical cards, `173` active Cardmarket products, `165` active canonical-card mappings, `173` append-only price snapshots, and `164` canonical cards with runtime `From` prices.
- Confirmed that all M4 exit criteria pass: complete or explicitly reconciled source scope, image coverage, repeat-import safety, visible rejected and unmatched states, and stored import evidence.
- Confirmed that controlled product, mapping, and price failures leave no partial accepted production state.
- Confirmed that `0` `card_editions` and `0` `card_variants` are an accepted non-blocking limitation under `ADR-013` rather than an import failure.

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
- Added README links to the consolidated Primal Clash validation report and M4 exit review.
- Updated `PROJECT.md`, `ROADMAP.md`, and `README.md` to mark M4 completed and validated.

### Planned

The following remain planned and are not yet implemented or validated:

- Raspberry Pi Docker and Docker Compose deployment;
- Raspberry Pi PostgreSQL deployment and persistent SSD storage;
- NocoDB deployment;
- Tailscale private access;
- controlled edition and variant classification and backfill;
- wishlist workflow;
- CSV export;
- backup scheduling;
- restore testing;
- Raspberry Pi restart recovery;
- release `v0.1.0`.

## Release history

No versioned release has been published yet.
