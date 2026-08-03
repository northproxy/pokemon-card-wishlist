# Project Plan

## Project name

Pokemon Card Wishlist

## Purpose

Build a working self-hosted MVP while publicly demonstrating structured planning, data discovery, technical decision-making, data modelling, infrastructure work, security awareness, validation, documentation quality, incremental delivery, and learning progress.

## Current status

- Current milestone: `M2 — Infrastructure`
- Completed milestones:
  - `M0 — Discovery` completed and validated on 2026-07-27;
  - `M1 — Repository foundation` completed and validated on 2026-07-27;
  - `M3 — Data model` implemented and locally validated on 2026-07-29;
  - `M4 — First import` completed and validated on 2026-08-03.
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
- Primary focus: Resume `M2 — Infrastructure` and establish the deployable platform required for the mobile wishlist workflow
- First delivery target: Primal Clash (`xy5`, Cardmarket expansion `1585`) as a validated vertical slice
- Vertical-slice import status: Completed and validated
  - `164` canonical cards are active;
  - `173` Cardmarket market products are active;
  - `165` canonical-card mappings are active;
  - `173` append-only market price snapshots are stored;
  - all `164` canonical cards have a validated runtime `From` price;
  - `2` oversized products are preserved as resolved exclusions;
  - `4` Online Code Card records are preserved as skipped audit outcomes;
  - `6` unlisted duplicate-like products are preserved as `unmatched_duplicate_candidate`;
  - no ambiguous, conflicting, or ordinary unmatched mapping rows remain;
  - `card_editions` and `card_variants` remain empty by design under accepted `ADR-013`.
- Import implementation status: Completed and validated for the Primal Clash canonical-card vertical slice
  - canonical-card, Cardmarket product, mapping, and price imports are implemented;
  - staging, validation, transactional merge, rollback, repeat-import, and per-record audit behaviour are validated;
  - repeated imports create no uncontrolled production duplicates;
  - runtime pricing uses the latest eligible successful snapshot per active market product and calculates `MIN(avg30)`;
  - the consolidated validation report is stored in `docs/import/primal-clash-import-validation-report.md`;
  - the formal exit review is stored in `docs/import/m4-first-import-exit-review.md`.
- Image workflow status: Repeatable download workflow implemented and validated with `328` local PNG files and no missing Primal Clash images
- Next concrete block: Prepare and validate the Raspberry Pi deployment foundation, beginning with the M2 infrastructure issue and its dependencies

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
- first-import and repeat-import runtime validation were completed during `M4 — First import`.

### M4 — First import

**Status:** Completed and validated on 2026-08-03

**Goal:** Import and validate one complete expansion.

Completed deliverables:

- controlled Primal Clash fixtures;
- canonical-card staging and production merge;
- Cardmarket product source-to-target contract;
- Cardmarket product staging importer, rollback injector, and production merge script;
- Cardmarket mapping staging, pre-merge validation, rollback, production merge, repeat merge, and audit reconciliation;
- Cardmarket price staging, staging rollback, append-only production merge, production rollback, and repeat merge;
- duplicate prevention and complete per-record audit outcomes;
- explicit Online Code Card, oversized-product, and unresolved duplicate-candidate handling;
- deterministic image metadata and local image-file validation;
- permanent runtime validator for the minimum non-null `avg30` canonical-card `From` price;
- consolidated validation report in `docs/import/primal-clash-import-validation-report.md`;
- formal exit review in `docs/import/m4-first-import-exit-review.md`.

Validated result:

- `164` active canonical cards;
- `173` active Cardmarket market products;
- `165` active canonical-card mappings;
- `173` append-only market price snapshots;
- `164` canonical cards with runtime `From` prices;
- `0` duplicate market-product source identities;
- `0` duplicate price-snapshot identities;
- `0` `card_editions` and `0` `card_variants` by design under `ADR-013`.

Exit criteria status:

- the selected expansion is imported completely or discrepancies are documented: satisfied;
- image mapping is validated: satisfied;
- repeated import does not create uncontrolled duplicates: satisfied;
- rejected and unmatched records are visible: satisfied;
- import evidence is stored: satisfied.

Known limitations do not block M4 completion. Edition and variant derivation,
the user-facing no-price branch, application workflows, Raspberry Pi deployment,
and broader catalogue coverage remain explicitly deferred to later work.

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
