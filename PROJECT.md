# Project Plan

## Project name

Pokemon Card Wishlist

## Purpose

Build a working self-hosted MVP while publicly demonstrating structured planning, data discovery, technical decision-making, data modelling, infrastructure work, security awareness, validation, documentation quality, incremental delivery, and learning progress.

## Current status

- Current milestone: `M2 — Infrastructure`
- Completed milestones:
  - `M0 — Discovery` completed and validated on 2026-07-27;
  - `M1 — Repository foundation` completed and validated on 2026-07-27.
- Implementation status: Discovery tooling, the Primal Clash vertical-slice fixtures, the repository foundation, the GitHub Project workflow, and Markdown validation are validated; application, database, and infrastructure implementation have not started
- Primary focus: Select and execute the first reproducible M2 infrastructure task while preserving the approved security, storage, backup, and recovery boundaries
- Repository status:
  - the public GitHub repository has been created;
  - contribution, security, changelog, issue-template, pull-request-template, and roadmap files have been added;
  - GitHub Actions Markdown validation is implemented and passing;
  - GitHub Project fields, views, and the initial M1 issue set are configured and validated;
  - published README and issue-template contact links have been checked.
- First delivery target: Primal Clash (`xy5`, Cardmarket expansion `1585`) as a validated vertical slice
- Vertical-slice mapping status: Validated
  - `164` canonical cards are covered;
  - `167` Cardmarket listing variants are mapped through direct `idProduct` evidence;
  - `6` unlisted duplicate-like products are preserved as `unmatched_duplicate_candidate`;
  - `4` Online Code Card products are excluded from MVP catalogue scope;
  - no ambiguous, conflicting, or ordinary unmatched mapping rows remain.
- Validation status: `validate_primal_clash_fixture.py` passes for fixture structure, record counts, mapping coverage, controlled statuses, unresolved-status checks, and deterministic canonical-card image metadata
- Image mapping status: Validated at the metadata level
  - all `164` canonical cards have unique small and large image URLs;
  - no image metadata is missing;
  - all URLs use HTTPS and the expected `images.pokemontcg.io` host;
  - all URL paths match the deterministic set-code and collector-number pattern;
  - remote availability, downloading, local storage, and backup remain future implementation and validation work.
- Current milestone focus: Begin `M2 — Infrastructure` with one documented, reversible, and validated action at a time

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

**Goal:** Create the minimum normalised PostgreSQL model.

Deliverables:

- approved catalogue-record definition;
- `expansions` table;
- catalogue or `cards` table;
- `wishlist_items` table;
- import-run metadata;
- rejected and unmatched record structures;
- relationships and constraints;
- indexes;
- migrations;
- sample dataset;
- data dictionary;
- validation queries.

Exit criteria:

- one expansion and its records can be stored without uncontrolled duplicates;
- repeated import behaviour is defined;
- wishlist data remains independent from staging data;
- schema assumptions are documented.

### M4 — First import

**Goal:** Import and validate one complete expansion.

Deliverables:

- one-expansion fixture or dataset;
- documented source-to-target mapping;
- import command or script;
- linked images;
- duplicate checks;
- rejected and unmatched record report;
- missing-image report;
- import validation report;
- repeat-import test.

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
