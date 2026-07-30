# Project Plan

## Project name

Pokemon Card Wishlist

## Purpose

Build a working self-hosted MVP while publicly demonstrating structured planning, data discovery, technical decision-making, data modelling, infrastructure work, security awareness, validation, documentation quality, incremental delivery, and learning progress.

## Current status

- Current milestone: `M4 — First import`
- Completed milestones:
  - `M0 — Discovery` completed and validated on 2026-07-27;
  - `M1 — Repository foundation` completed and validated on 2026-07-27;
  - `M3 — Data model` implemented and locally validated on 2026-07-29.
- Database implementation status: Physical PostgreSQL schema implemented and locally validated
  - `21` project tables are implemented through `17` reversible dbmate migrations;
  - `22` tables exist in `public` together with `schema_migrations`;
  - `dbmate status` reports `Applied: 17` and `Pending: 0`;
  - all migrations have been checked through rollback and reapply;
  - `scripts/database/validate_schema.sql` passes with `schema validation passed`.
- Application implementation status: Not started
- Infrastructure implementation status:
  - the local development environment includes WSL 2, Docker Desktop, PostgreSQL 17, DBeaver Community, dbmate, and Docker Compose;
  - PostgreSQL is reachable locally only through `127.0.0.1`;
  - Raspberry Pi deployment, NocoDB, Tailscale, persistent SSD deployment, backup, and restore remain planned and unvalidated.
- Primary focus: Continue the controlled Primal Clash first import with Cardmarket mappings
- First delivery target: Primal Clash (`xy5`, Cardmarket expansion `1585`) as a validated vertical slice
- Vertical-slice mapping fixture status: Validated
  - `164` canonical cards are covered;
  - `167` Cardmarket listing variants are mapped through direct `idProduct` evidence;
  - `6` unlisted duplicate-like products are preserved as `unmatched_duplicate_candidate`;
  - `4` Online Code Card products are excluded from MVP catalogue scope;
  - no ambiguous, conflicting, or ordinary unmatched mapping rows remain.
- Import implementation status: In progress
  - canonical Primal Clash cards have been imported and repeat-merge idempotency has been validated;
  - the Cardmarket product path from `cardmarket-products.json` through `staging_market_products` to `market_products` is implemented and validated;
  - `177` product records are staged per run, `173` eligible products are active in production, and `4` Online Code Card products are recorded as skipped;
  - repeated Cardmarket product merge produces `173` unchanged and `4` skipped outcomes without duplicates;
  - Cardmarket mappings, editions, variants, prices, runtime `From` pricing, and the complete M4 validation report remain incomplete.
- Image workflow status: Repeatable download workflow implemented separately and recorded in commit `ad3a2d9`; no further image work is required before the mapping import unless database integration exposes a dependency
- Next concrete block: `cardmarket-mappings.json` → `staging_market_mappings` → `card_market_product_mappings`

## Delivery principles

1. Build the smallest useful version first.
2. Make each step reproducible.
3. Record important decisions before or immediately after implementation.
4. Separate raw source data, staging data, normalised catalogue data, and user-generated wishlist data.
5. Prefer simple, free, and self-hosted tools.
6. Complete and validate one vertical slice before expanding catalogue coverage.
7. Treat documentation, validation, and recovery as part of the product.
8. Do not describe planned work as implemented.
9. Do not silently correct ambiguous data.
10. Do not move past a milestone while a blocking dependency remains unresolved.

## Milestones

### M0 — Discovery

**Goal:** Understand all available data sources and define the minimum catalogue concepts.

Deliverables:

- source-file inventory;
- source field inventory;
- expansion-list review;
- image naming and directory review;
- identifier analysis;
- accepted definition of one catalogue record;
- accepted source-scoped import-key strategy;
- accepted edition, language, and finish model;
- mapping risks;
- rejected and unmatched record strategy draft;
- selection of one expansion for the first vertical slice;
- initial ADR backlog.

Exit criteria:

- representative source files have been inspected;
- stable source identifiers are documented;
- the catalogue-record definition is accepted;
- the source-scoped unique-key strategy is accepted;
- image mapping feasibility is understood;
- Primal Clash is selected as the first vertical slice;
- unresolved questions are explicitly recorded.

### M1 — Repository foundation

**Goal:** Create a professional and understandable repository structure.

Deliverables:

- `README.md`;
- `MVP_SCOPE.md`;
- `PROJECT.md`;
- `STACK.md`;
- `DECISIONS.md`;
- `GITHUB_PROJECT.md`;
- `LEARNING_LOG.md`;
- repository structure;
- issue templates;
- pull request template;
- security notes;
- contribution guidance;
- changelog;
- initial release roadmap;
- basic Markdown validation.

Exit criteria:

- repository purpose, scope, status, decisions, and next steps are clear;
- documentation links work;
- planned, implemented, and validated work are distinguishable.

### M2 — Infrastructure

**Goal:** Run the base platform on Raspberry Pi.

Deliverables:

- Raspberry Pi preparation notes;
- SSD configuration;
- Docker and Docker Compose;
- PostgreSQL container;
- NocoDB container;
- persistent volumes;
- private remote access;
- secret handling;
- backup procedure;
- restore procedure;
- operating notes.

Exit criteria:

- NocoDB is reachable from a phone through approved private access;
- PostgreSQL is not publicly exposed;
- data survives container restart;
- data survives Raspberry Pi restart;
- backup and restore are tested;
- infrastructure steps are documented.

### M3 — Data model

**Status:** Completed and locally validated on 2026-07-29

**Goal:** Create the minimum normalised PostgreSQL model.

Completed deliverables:

- approved catalogue-record definition;
- physical PostgreSQL schema with `21` project tables;
- catalogue, edition, variant, market-product, mapping, price-snapshot, wishlist, staging, import-audit, rejection, and mapping-review structures;
- source-scoped uniqueness constraints;
- foreign keys, lifecycle constraints, controlled values, and indexes;
- `17` reversible dbmate migrations;
- data dictionary in `docs/database/data-model.md`;
- executable schema validation in `scripts/database/validate_schema.sql`.

Exit criteria status:

- one expansion can be represented without uncontrolled duplicates at the schema level: satisfied;
- repeated import behaviour is defined through `ADR-008`: satisfied;
- wishlist data remains independent from staging data: satisfied and schema-validated;
- schema assumptions are documented: satisfied;
- first-import and repeat-import runtime validation remain part of `M4 — First import`.

### M4 — First import

**Status:** In progress

**Goal:** Import and validate one complete expansion.

Completed or validated deliverables:

- controlled Primal Clash fixtures;
- canonical-card staging and production merge;
- Cardmarket product source-to-target contract;
- Cardmarket product staging importer, rollback injector, and production merge script;
- repeat staging and repeat production merge validation;
- duplicate prevention and complete per-record audit outcomes;
- explicit Online Code Card exclusion handling.

Remaining deliverables:

- Cardmarket mapping staging and production mappings;
- card editions and variants derived from mappings;
- Cardmarket price staging and snapshots;
- runtime minimum non-null `avg30` validation;
- rejected, unmatched, and missing-image reporting for the complete vertical slice;
- complete M4 import validation report.

Exit criteria:

- the selected expansion is imported completely or discrepancies are documented;
- image mapping is validated;
- repeated import does not create uncontrolled duplicates;
- rejected and unmatched records are visible;
- import evidence is stored.

### M5 — Wishlist workflow

**Goal:** Complete the primary user journey.

Deliverables:

- mobile-friendly catalogue view;
- search;
- expansion and metadata filters;
- image preview;
- wanted control;
- quantity and notes;
- filtered Wishlist view;
- CSV export;
- mobile acceptance test;
- documented NocoDB limitations.

Exit criteria:

- the complete workflow works from a phone;
- catalogue records are not unintentionally editable;
- wishlist data persists;
- exported CSV contains the required fields.

### M6 — Catalogue expansion

**Goal:** Import the remaining supported expansions through a repeatable process.

Deliverables:

- batch import process;
- import summary for each expansion;
- unmatched-record queue;
- rejected-record queue;
- missing-image report;
- duplicate and data-quality report;
- unsupported-expansion list.

Exit criteria:

- every prepared expansion is imported or explicitly marked unsupported;
- all import runs are traceable;
- unresolved records are reviewable.

### M7 — MVP release

**Goal:** Publish a stable portfolio-ready release.

Deliverables:

- tagged release;
- screenshots;
- architecture diagram;
- demo walkthrough;
- setup and operating guide;
- release notes;
- known limitations;
- validated backup and restore guide;
- lessons learned;
- roadmap for version 2.

Exit criteria:

- all acceptance criteria in `MVP_SCOPE.md` are satisfied;
- major ADRs are recorded;
- repository documentation matches the validated implementation;
- release evidence is complete.

## Work breakdown structure

### Epic: Data discovery

- source inventory;
- source-field analysis;
- expansion mapping;
- image naming conventions;
- catalogue-record validation;
- source-scoped unique-key validation;
- edition, language, and finish modelling;
- canonical-card price aggregation rule;
- data-quality rules.

### Epic: Platform

- Raspberry Pi setup;
- SSD configuration;
- Docker installation;
- PostgreSQL deployment;
- NocoDB deployment;
- persistent storage;
- secure access;
- monitoring;
- backup and restore.

### Epic: Database

- schema design;
- migrations;
- indexes;
- constraints;
- staging tables;
- production tables;
- import-run tracking;
- rejected and unmatched records;
- wishlist model;
- data dictionary.

### Epic: Import pipeline

- parse source files;
- normalise fields;
- map expansions;
- map images;
- detect duplicates;
- upsert records;
- record rejected rows;
- record unmatched rows;
- produce import reports;
- test idempotency.

### Epic: User experience

- catalogue view;
- gallery view;
- expansion filter;
- search;
- image preview;
- wanted state;
- quantity and notes;
- Wishlist view;
- CSV export;
- mobile acceptance test.

### Epic: Documentation and portfolio

- architecture;
- setup guide;
- operating guide;
- data dictionary;
- import guide;
- backup and restore;
- decisions;
- validation reports;
- learning log;
- release notes;
- known limitations;
- case study.

## Definition of Done

A task is done when:

- implementation or analysis is complete;
- acceptance criteria are met;
- relevant tests or validation checks have passed;
- data changes are validated;
- documentation is updated;
- security implications are considered;
- rollback or recovery implications are considered;
- required ADR or Learning Log updates are prepared;
- useful evidence is attached;
- the result is reproducible by another developer where practical.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Source data lacks complete metadata | High | Use additional free sources only after documenting the gap and source confidence |
| Definition of one catalogue record is unclear | High | Inspect representative records and record an ADR before schema finalisation |
| Card variants are ambiguous | High | Preserve source values, avoid silent normalisation, and keep unmatched records |
| Images cannot be mapped reliably | High | Define deterministic naming and produce a missing-image validation report |
| Duplicate records are imported | High | Use a stable source key, database constraints, and repeat-import tests |
| Wishlist data is damaged by catalogue updates | High | Separate wishlist data from staging and define update behaviour |
| Raspberry Pi or SSD failure | High | Use SSD, separate backups, retention, and restore tests |
| NocoDB mobile UX is insufficient | Medium | Validate one full workflow before accepting ADR-001 |
| Remote access is insecure | High | Use Tailscale, document exposure, and avoid public database ports |
| Scope grows too quickly | Medium | Enforce MVP exclusions and milestone gates |
| Documentation diverges from implementation | Medium | Distinguish Proposed, Implemented, and Validated in every major document |

## Portfolio evidence

The repository should visibly demonstrate:

- clear requirements;
- intentional architecture;
- documented trade-offs;
- structured backlog;
- incremental releases;
- data modelling;
- infrastructure setup;
- security awareness;
- testing and validation;
- reproducible procedures;
- honest learning notes;
- retrospective analysis.
