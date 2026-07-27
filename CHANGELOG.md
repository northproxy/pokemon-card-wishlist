# Changelog

All notable changes to Pokemon Card Wishlist will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project intends to follow Semantic Versioning after the first release.

## [Unreleased]

### Added

* Initial project documentation:

  * `README.md`
  * `MVP_SCOPE.md`
  * `PROJECT.md`
  * `STACK.md`
  * `DECISIONS.md`
  * `GITHUB_PROJECT.md`
  * `LEARNING_LOG.md`
  * `REVIEW_SUMMARY.md`
* Repository contribution guidance in `CONTRIBUTING.md`.
* Initial security policy in `SECURITY.md`.
* Discovery documentation for source inventory, source fields, record identity, language and variant modelling, image mapping, data-quality findings, and first-expansion selection.
* Primal Clash vertical-slice fixtures for:

  * canonical cards;
  * Cardmarket products;
  * Cardmarket price records;
  * mapping review.
* Discovery and validation scripts for building, analysing, and validating the Primal Clash fixture.
* Source-scoped external identifier strategy.
* Separate concepts for canonical cards, editions, language and finish variants, Cardmarket products, and price snapshots.
* Informational canonical-card price rule based on the minimum supported non-null Cardmarket `avg30`.
* Explicit `unmatched_duplicate_candidate` handling for duplicate-like Cardmarket source products.

### Changed

* Updated the repository status from `M0 — Discovery` to `M1 — Repository foundation`.
* Replaced inferred Cardmarket product-order matching with direct `idProduct` evidence from individual product pages.
* Clarified the distinction between `Proposed`, `Planned`, `Implemented`, and `Validated`.
* Clarified that the initial wishlist references canonical cards rather than specific market variants.
* Clarified that application, database, infrastructure, authentication, backup, and deployment implementation have not started.

### Validated

* Completed and validated `M0 — Discovery` on 2026-07-27.
* Validated the Primal Clash vertical slice with:

  * `164` canonical cards covered;
  * `167` Cardmarket listing variants mapped through direct `idProduct` evidence;
  * `4` Online Code Card products excluded from MVP catalogue scope;
  * `6` unlisted products preserved as `unmatched_duplicate_candidate`;
  * no ambiguous, conflicting, or ordinary unmatched mapping rows.
* Validated deterministic image metadata for all `164` canonical Primal Clash cards.
* Validated unique small and large image URLs using the expected Pokémon TCG image path pattern.
* Validated the permanent Primal Clash fixture checks for structure, counts, mapping coverage, controlled statuses, exclusions, unresolved-status handling, and image metadata.

### Security

* Documented the initial security baseline.
* Documented that secrets must remain outside the repository.
* Documented that PostgreSQL must not be exposed directly to the public internet.
* Documented planned security controls for private access, backups, dependency review, imported data, and restore testing.

### Documentation

* Standardised the project name as `Pokemon Card Wishlist`.
* Standardised milestone names from `M0` through `M7`.
* Updated the public project status to reflect completion of discovery and the start of repository-foundation work.
* Added contribution workflow, commit guidance, pull request expectations, validation evidence requirements, and scope-control rules.

### Planned

The following remain planned and are not yet implemented or validated:

* issue templates;
* pull request template;
* Markdown validation through GitHub Actions;
* initial release roadmap;
* GitHub Project views and fields;
* Docker and Docker Compose infrastructure;
* PostgreSQL deployment;
* NocoDB deployment;
* Tailscale private access;
* persistent SSD storage;
* database schema and migrations;
* import pipeline;
* wishlist workflow;
* CSV export;
* backup scheduling;
* restore testing;
* Raspberry Pi restart recovery;
* release `v0.1.0`.

## Release history

No versioned release has been published yet.
