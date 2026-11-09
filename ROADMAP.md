# Release Roadmap

This roadmap describes the planned delivery path for Pokemon Card Wishlist.

It distinguishes planned work from implemented and validated results. Dates are intentionally omitted until delivery capacity and infrastructure availability are confirmed.

## Current status

- Current milestone: `M2 — Infrastructure`
- Completed milestones: `M0 — Discovery`, `M1 — Repository foundation`, `M3 — Data model`, `M4 — First import`
- First planned release: `v0.1.0`
- Application implementation status: Local static gallery prototype implemented and browser-tested for `xy5` and `me55c`; the persistent wishlist application has not started
- Database implementation status: Physical PostgreSQL schema implemented and locally validated
- Infrastructure implementation status: Local development database environment available; Raspberry Pi deployment remains not started
- Import implementation status: Primal Clash full vertical slice completed and validated; `me55c` canonical catalogue import completed and validated (30 cards), without Cardmarket mapping or pricing
- Immediate work: Import `swsh11.json` as the next expansion, then implement a local Wishlist prototype in the gallery; M2 infrastructure remains the formal active milestone and is not complete

`M4 — First import` was completed and validated on 2026-08-03. The Primal Clash vertical slice contains `164` active canonical cards, `173` active Cardmarket products, `165` active canonical-card mappings, `173` append-only market price snapshots, and runtime `From` prices for all `164` canonical cards. Repeated imports create no uncontrolled production duplicates, controlled rollback tests leave no partial accepted state, and all exclusions and unresolved duplicate candidates remain visible. Automatic edition and variant derivation remains deferred through accepted `ADR-013`; `card_editions` and `card_variants` intentionally remain empty without invalidating the card-level import or pricing result.

## Immediate implementation plan

This is the agreed near-term working order. It does not change the formal milestone
completion criteria or the release gates below. Each item remains planned until its
own implementation and validation evidence is recorded.

1. **Import `swsh11.json` (next):** inspect the source file, confirm set identity
   and record count, prepare a controlled canonical-card fixture, validate and
   stage records, review the results, perform a transactional catalogue merge,
   download and validate images, and add the expansion to the local gallery.
   Cardmarket product mapping and prices are separate follow-up work.
2. **Wishlist in the gallery:** add a heart/wanted toggle to cards, a Wishlist-only
   view, and browser `localStorage` persistence; verify selections survive a
   refresh and work across the imported expansions. This is a **prototype**:
   browser-local storage is not the permanent M5 data store.
3. **Persist the Wishlist in PostgreSQL:** design a controlled application access
   path (never expose database credentials in browser code), store wanted state,
   quantity, and notes, and test persistence and data isolation.
4. **Export Wishlist to CSV:** include card identity, expansion, collector number,
   quantity, and notes; test export and encoding.
5. **Complete M2 infrastructure:** prepare Raspberry Pi deployment, SSD-backed
   persistence, private access, backups, restore tests, and restart recovery.
   These are still release blockers even if prototype work happens first.
6. **Expand catalogue and market data:** add Cardmarket mappings and pricing for
   supported new expansions (including `me55c` when data is available), improve
   repeatable batch imports, and retain explicit unresolved-record reporting.

**Current validated catalogue and gallery baseline:** Primal Clash (`xy5`) has
164 canonical cards and 328 downloaded images; 30th Celebration: Classic
Collection (`me55c`) has 30 canonical cards and 60 downloaded images. A local
browser gallery for both expansions has been tested. This does not imply
Wishlist persistence or pricing coverage for `me55c`.

## Release strategy

The project will deliver one complete, validated vertical slice before expanding catalogue coverage.

The first release will focus on:

- one validated expansion;
- a reproducible self-hosted deployment;
- a minimal normalized catalogue;
- a persistent wishlist workflow;
- CSV export;
- documented backup and restore;
- clear validation evidence and known limitations.

## `v0.1.0` — MVP release

**Status:** Planned

**Target milestone:** `M7 — MVP release`

### Required milestone sequence

The release depends on successful completion of:

1. `M1 — Repository foundation`
2. `M2 — Infrastructure`
3. `M3 — Data model`
4. `M4 — First import`
5. `M5 — Wishlist workflow`
6. `M6 — Catalogue expansion`
7. `M7 — MVP release`

Later milestones must not bypass unresolved dependencies from earlier milestones.
The immediate prototype order above is an implementation sequence, not a declaration
that M2 or M5 release gates have been met.

## Milestone roadmap

### `M0 — Discovery`

**Status:** Completed and validated on 2026-07-27

Completed outcomes include:

- source inventory and representative field analysis;
- accepted canonical-card identity boundary;
- accepted source-scoped import keys;
- accepted separation of canonical cards and Cardmarket products;
- accepted edition, language, and finish concepts;
- Primal Clash selected as the first vertical slice;
- direct `idProduct` mapping evidence;
- deterministic canonical-card image metadata;
- validated Primal Clash fixtures and validation scripts.

### `M1 — Repository foundation`

**Status:** Completed and validated on 2026-07-27

Completed outcomes:

- professional repository structure;
- cross-linked core documentation;
- contribution guidance;
- security policy;
- changelog;
- issue templates;
- pull request template;
- initial release roadmap;
- GitHub Project configuration;
- validated Markdown workflow.

Exit condition:

- repository purpose, scope, status, decisions, and next actions are clear;
- documentation links work;
- planned, implemented, and validated work are distinguishable.

### `M2 — Infrastructure`

**Status:** Ready to start

Planned outcomes:

- Raspberry Pi preparation;
- SSD-backed persistent storage;
- Docker and Docker Compose;
- PostgreSQL deployment;
- NocoDB deployment;
- private access through Tailscale;
- secret handling;
- database and file backups;
- tested restore procedure;
- restart recovery documentation.

Exit condition:

- the platform is reachable privately from a phone;
- PostgreSQL is not publicly exposed;
- persistent data survives container and device restarts;
- backup and restore are validated.

### `M3 — Data model`

**Status:** Completed and locally validated on 2026-07-29

Completed outcomes:

- physical PostgreSQL schema with `21` project tables;
- `17` reversible dbmate migrations with no pending migrations;
- source-scoped uniqueness constraints;
- canonical-card, edition, variant, market-product, mapping, and price-snapshot separation;
- wishlist data isolated from staging and market-price ownership;
- import-run tracking and staging structures;
- rejected-record and mapping-review workflows;
- data dictionary and executable schema-wide validation;
- successful rollback and reapply checks for all migrations.

Exit condition status:

- one expansion can be represented without uncontrolled duplicates at the schema level: satisfied;
- repeated import behaviour is defined: satisfied;
- wishlist data remains independent from staging data: satisfied;
- runtime first-import and repeat-import validation were completed during `M4 — First import`.

### `M4 — First import`

**Status:** Completed and validated on 2026-08-03

Completed outcomes:

- controlled Primal Clash canonical-card import and repeated unchanged merge;
- validated Cardmarket product staging, rollback, first merge, and repeat merge;
- `173` active Cardmarket products with `4` explicit Online Code Card skipped outcomes;
- controlled mapping staging, rollback, first merge, and repeat merge;
- `173` mapping cases and `165` active canonical-card mappings;
- preserved oversized exclusions and `unmatched_duplicate_candidate` review states;
- controlled Cardmarket price staging and production rollback validation;
- `173` append-only market price snapshots with no duplicate snapshot identities;
- runtime minimum non-null `avg30` validation for all `164` canonical cards;
- deterministic image metadata and `328` validated local PNG files;
- accepted `ADR-013` deferral with `0` production editions and `0` production variants;
- consolidated validation report and formal milestone exit review.

Exit condition status:

- Primal Clash is imported completely or discrepancies are explicitly documented: satisfied;
- repeat imports do not create uncontrolled duplicates: satisfied;
- unresolved records remain visible: satisfied;
- production mappings and informational pricing are validated against the accepted fixture: satisfied.

Known limitations are published and assigned to later milestones. None blocks formal M4 completion.

### `M5 — Wishlist workflow`

**Status:** Planned

Planned outcomes:

- mobile-friendly catalogue view;
- search and filters;
- card-image preview;
- wanted state;
- quantity and notes;
- filtered Wishlist view;
- CSV export;
- mobile workflow validation;
- documented NocoDB limitations.

Exit condition:

- the complete primary user journey works from a phone;
- wishlist data persists;
- catalogue data is protected from unintended editing;
- CSV export contains the required fields.

### `M6 — Catalogue expansion`

**Status:** Planned

Planned outcomes:

- repeatable batch-import process;
- supported expansion imports;
- import summaries;
- rejected and unmatched queues;
- missing-image reports;
- duplicate and data-quality reports;
- explicit unsupported-expansion records.

Exit condition:

- every prepared expansion is imported or explicitly marked unsupported;
- all import runs are traceable;
- unresolved records are reviewable.

### `M7 — MVP release`

**Status:** Planned

Planned outcomes:

- complete MVP acceptance test;
- validated backup and restore documentation;
- architecture diagram;
- setup and operating guide;
- screenshots;
- demo walkthrough;
- release notes;
- known limitations;
- lessons learned;
- Git tag `v0.1.0`.

Exit condition:

- all acceptance criteria in `MVP_SCOPE.md` are satisfied;
- documentation matches the validated implementation;
- major decisions and known limitations are published;
- release evidence is complete.

## Release gates

The `v0.1.0` release must not be published until:

- Primal Clash is imported and validated;
- catalogue images are accessible;
- search and filtering work;
- wishlist selections persist;
- quantity and notes persist;
- CSV export works;
- informational `From` pricing follows the accepted `avg30` rule;
- repeated import behaviour is validated;
- rejected and unmatched records are reported;
- the application recovers after restart;
- backup and restore are tested;
- security exposure is documented;
- major ADRs are recorded;
- known limitations are published.

## Deferred work

The following are not part of `v0.1.0` unless a separate scope decision is accepted:

- real-time market-price synchronization;
- price-history analytics;
- automated purchasing;
- Cardmarket account integration;
- native mobile applications;
- multi-user permissions;
- public registration;
- collection-value analytics;
- image recognition;
- AI matching;
- recommendation features;
- full offline mode;
- public internet access for the MVP application.

## Future releases

Potential post-MVP releases may address:

- edition- and variant-specific wishlist preferences;
- broader catalogue coverage;
- improved mobile user experience;
- a custom frontend if NocoDB proves insufficient;
- additional marketplace sources;
- stronger automation and monitoring.

These items are exploratory and are not approved commitments.
