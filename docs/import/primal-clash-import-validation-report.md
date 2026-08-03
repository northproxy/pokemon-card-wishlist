# Primal Clash Import Validation Report

## Document status

* Milestone: `M4 — First import`
* Expansion: `Primal Clash`
* Pokémon TCG Data set: `xy5`
* Cardmarket expansion ID: `1585`
* Validation status: Completed
* Validation date: 2026-08-03

## Purpose

This report consolidates the implementation and validation evidence for the
controlled Primal Clash vertical-slice import completed during
`M4 — First import`.

It verifies the supported import path from prepared source fixtures through:

* source normalization;
* staging;
* staging validation;
* transactional production merges;
* controlled rollback tests;
* repeated imports;
* per-record audit outcomes;
* unresolved-record preservation;
* append-only market price snapshots;
* runtime canonical-card pricing.

The report establishes whether the Primal Clash import satisfies the M4 import
requirements at the currently supported canonical-card scope.

This report does not validate:

* the complete Pokemon card catalogue;
* Raspberry Pi deployment;
* NocoDB;
* the application user interface;
* mobile catalogue browsing;
* wishlist interaction;
* CSV export;
* backup and restore;
* edition-specific catalogue workflows;
* language- or finish-specific catalogue workflows.

## Validation scope

The controlled vertical slice covers:

* `164` canonical Pokémon TCG Data cards;
* `177` Cardmarket product source records;
* `177` Cardmarket mapping source records;
* `177` Cardmarket price source records;
* deterministic canonical-card image metadata;
* locally downloaded small and large card images;
* canonical-card production import;
* Cardmarket product production import;
* Cardmarket mapping review and production import;
* Cardmarket price snapshot production import;
* repeated-import behaviour;
* production transaction rollback behaviour;
* rejected, excluded, unresolved, and duplicate-record reporting;
* runtime canonical-card `From` price calculation.

The validated runtime pricing path is:

```text
canonical card
→ active card-level Cardmarket product mapping
→ active Cardmarket market product
→ latest eligible successful price snapshot
→ MIN(avg30)
```

Automatic population of `card_editions` and `card_variants` is outside the
validated M4 production scope under `ADR-013`.

## Source fixtures and identifiers

The validation uses the controlled Primal Clash fixtures under:

```text
data/fixtures/primal-clash/
```

The fixture set includes:

* canonical-card records;
* Cardmarket product records;
* Cardmarket mapping records;
* Cardmarket price records;
* mapping-review evidence.

External entities use source-scoped stable identifiers.

Canonical cards are identified by:

```text
(source_system, source_card_id)
```

For this report, the canonical source system is `pokemon_tcg_data`, with source
identifiers such as `xy5-20`.

Cardmarket market products are identified by:

```text
(source_system, source_product_id)
```

For this report, the market source system is `cardmarket`, with Cardmarket
`idProduct` preserved as `source_product_id`.

Market price snapshots use the production identity:

```text
(market_product_id, source_snapshot_at)
```

This identity prevents repeated import of the same source snapshot from creating
duplicate historical price rows.

## Accepted rules and decisions

This validation applies the following accepted architecture decisions.

### `ADR-005 — Separate canonical cards from Cardmarket products`

Canonical cards and marketplace products are separate entities. One canonical
card may have zero, one, or multiple mapped Cardmarket products.

### `ADR-006 — Use source-scoped identifiers as stable import keys`

External identifiers are unique only within their source system. Production
uniqueness therefore uses source-scoped keys.

### `ADR-008 — Use staging and validated transactional merges for repeated imports`

Source loading, validation, and production changes are separate stages.
Production merges are transactional and must not leave partially accepted state
after failure.

### `ADR-009 — Preserve rejected and unresolved import records through controlled review states`

Rejected, unmatched, ambiguous, candidate, confirmed, excluded, and
`unmatched_duplicate_candidate` records must remain explicit and reviewable.

### `ADR-011 — Display the minimum 30-day average as the canonical card price`

The informational canonical-card price is the minimum eligible non-null
Cardmarket `avg30` across active confirmed market-product mappings.

The value is intended to be labelled:

```text
From
30-day average
```

### `ADR-012 — Preserve unlisted duplicate-like Cardmarket products as unmatched candidates`

Duplicate-like products without sufficient direct mapping evidence remain
preserved as `unmatched_duplicate_candidate`.

They do not create canonical-card mappings and do not participate in canonical
pricing.

### `ADR-013 — Defer automatic edition and variant derivation`

Canonical-card-to-market-product evidence does not automatically prove edition,
language, or finish.

The controlled Primal Clash import therefore does not populate
`card_editions` or `card_variants`.

Empty edition and variant tables are a documented limitation, not an import
failure.

## Validation environment

The validation was executed against the local PostgreSQL development
environment implemented for the project.

The relevant environment includes:

* PostgreSQL 17;
* Docker Desktop;
* Docker Compose;
* WSL 2;
* DBeaver Community;
* `dbmate`;
* `17` applied database migrations;
* `21` project tables;
* permanent schema-wide SQL validation.

Before the M4 import work, the physical schema had already passed:

```text
schema validation passed
```

The M4 result validates the runtime import behaviour against that schema. It
does not validate Raspberry Pi deployment or production infrastructure.

## Canonical-card import validation

### Input

The canonical-card fixture contains:

```text
164 source records
```

Each record represents one Primal Clash canonical card from Pokémon TCG Data set
`xy5`.

### Staging and validation

The canonical-card records were loaded through the controlled staging path.

Validation confirmed:

* all required source identifiers were present;
* all records belonged to the expected set;
* source-scoped identities were unique;
* card relationships were compatible with the production expansion;
* image metadata was present;
* no uncontrolled duplicate canonical-card identity existed.

### First production merge

The first validated merge created the expected canonical-card production state:

```text
164 active canonical cards
```

### Repeated production merge

Repeating the identical canonical-card input produced unchanged-record
behaviour.

The repeat merge did not create duplicate canonical cards or unnecessary new
production identities.

### Result

Canonical-card import validation passed.

The final controlled production state contains:

```text
164 active canonical cards
```

## Cardmarket product import validation

### Input

The Cardmarket product fixture contains:

```text
177 source records
```

The records include:

* eligible individual card products;
* `4` Online Code Card products outside MVP catalogue scope.

### Source normalization

Cardmarket uses the source timestamp value:

```text
0000-00-00 00:00:00
```

as a missing-value sentinel.

The importer normalizes this value to:

```text
NULL
```

before PostgreSQL timestamp parsing while preserving the original source value
inside `raw_payload`.

Validation confirmed per staging run:

* `177` valid staging records;
* `164` missing timestamp sentinels normalized to `NULL`;
* `13` real source timestamps parsed successfully.

Timezone-naive source timestamps are interpreted deterministically by the
importer, but the fixture does not independently prove Cardmarket's original
timezone semantics.

### Controlled staging rollback

A deliberate failure was triggered after a partial staging write.

The transaction was rolled back completely.

Validation confirmed that the failed attempt did not leave a partially accepted
staging result.

### First production merge

The first product production merge produced:

```text
173 inserted
4 skipped
177 total outcomes
```

The `4` skipped records are Online Code Card products explicitly outside MVP
catalogue scope.

They remain represented through audit outcomes but do not create production
`market_products`.

### Repeated production merge

Repeating the identical source produced:

```text
173 unchanged
4 skipped
177 total outcomes
```

The repeated merge produced no uncontrolled inserts or unnecessary updates.

### Final integrity checks

The final product state is:

```text
173 active market products
0 inactive market products
0 duplicate source identities
0 Online Code Card products in production
```

Each controlled production run produced one reconciled
`import_record_outcomes` record for every one of the `177` source rows.

### Result

Cardmarket product import validation passed.

## Cardmarket mapping validation

### Input

The controlled mapping fixture contains:

```text
177 source records
```

Its accepted classifications are:

```text
165 candidate mappings eligible for confirmation at card scope
6 excluded records
6 unmatched_duplicate_candidate records
```

The six excluded records consist of:

* `4` Online Code Card records;
* `2` oversized product records.

### Mapping evidence

Confirmed mappings use direct Cardmarket `idProduct` evidence collected from
the corresponding product listings.

Collector-number and direct product evidence prove:

```text
canonical card → Cardmarket market product
```

The evidence does not prove complete edition, language, or finish identity.

### Pre-merge validation

Pre-merge reconciliation confirmed:

* all expected source records were present;
* canonical-card references existed;
* eligible market-product references existed;
* active mapping uniqueness could be preserved;
* exclusions remained outside active mapping production;
* duplicate candidates remained unresolved and non-pricing;
* no ordinary `unmatched` rows remained;
* no `ambiguous` rows remained;
* no mapping conflicts remained.

### Controlled production rollback

A deliberate failure was triggered after creating one complete mapping
production chain.

The complete production transaction was rolled back.

Validation confirmed that the failure left no partial accepted:

* mapping case;
* observation;
* candidate;
* status transition;
* active production mapping;
* audit outcome.

### First production merge

The first production mapping merge produced:

```text
165 inserted mappings
12 skipped outcomes
```

The merge created:

```text
173 mapping cases
173 mapping observations
165 selected mapping candidates
173 mapping status-history rows
165 active production mappings
```

The `12` skipped outcomes represent:

* `4` Online Code Card records;
* `2` oversized exclusions;
* `6` unmatched_duplicate_candidate records.

The Online Code Card rows do not create mapping cases because their products are
intentionally absent from production.

The oversized and duplicate-candidate products remain represented through the
controlled mapping-review workflow without active canonical-card mappings.

### Repeated production merge

The repeated production mapping merge produced:

```text
165 unchanged mappings
12 skipped outcomes
0 new mapping cases
0 new active mappings
0 new status transitions
```

The repeated run created new observations and selected-candidate evidence for
eligible source rows while preserving stable current production state.

This is expected behaviour: current mapping state remains idempotent while
append-only or observation evidence may grow.

### Final mapping state

After the first and repeated mapping runs, the cumulative state is:

```text
173 mapping cases
346 mapping observations
330 mapping candidates
173 mapping status-history rows
165 active production mappings
```

### Result

Cardmarket mapping validation passed at canonical-card scope.

## Cardmarket price import validation

### Input

The Cardmarket price fixture contains:

```text
177 source records
```

Validation confirmed:

```text
177 non-null avg30 values
169 non-null avg30_holo values
8 records without avg30_holo
```

The MVP price formula uses `avg30`.

`avg30_holo` is preserved as source data where available but does not
participate in the canonical-card `From` price formula.

### Source snapshot contract

The source fixture provides one controlled file-level snapshot timestamp.

The importer applies the normalized file-level timestamp to every price row in
the fixture.

The importer also assigns:

```text
EUR
```

as the controlled currency for the imported Cardmarket price fixture.

The report does not claim that each source row independently supplied its own
timestamp or currency value.

### Controlled staging rollback

A deliberate failure was triggered after one partial staging insert.

The staging transaction rolled back completely.

No partial accepted staging state remained.

### Controlled production rollback

A deliberate failure was triggered after one price snapshot and one audit
outcome had been written inside the production merge transaction.

The complete transaction rolled back.

Validation confirmed that neither the snapshot nor its audit outcome remained
as accepted production state.

### First production merge

The first price production merge produced:

```text
173 inserted snapshots
4 skipped outcomes
```

The `4` skipped rows are Online Code Card products outside MVP catalogue scope.

### Repeated production merge

Repeating the identical source snapshot produced:

```text
0 inserted snapshots
173 unchanged snapshots
4 skipped outcomes
```

The repeated import did not create duplicate historical snapshot rows and did
not overwrite the original append-only evidence.

### Final snapshot integrity

The final production state contains:

```text
173 market price snapshots
0 duplicate (market_product_id, source_snapshot_at) identities
```

### Result

Cardmarket price import validation passed.

## Runtime canonical-card From price validation

The permanent runtime validator is:

```text
scripts/database/validate_primal_clash_from_prices.sql
```

The runtime query first selects the latest eligible snapshot for each active
market product from successful import runs.

It then follows active canonical-card mappings and calculates:

```text
MIN(avg30)
```

for each canonical card.

Validation confirmed:

```text
165 active mapped market products
164 canonical cards with a runtime From price
```

The runtime formula:

* uses active canonical-card mappings;
* uses active market products;
* uses successful import runs;
* uses the latest eligible snapshot for each market product;
* ignores null `avg30` values;
* does not use `avg30_holo`;
* returns the minimum eligible `avg30` per canonical card.

The permanent validator completed with:

```text
Primal Clash runtime From price validation passed
```

All `164` canonical cards in the controlled Primal Clash vertical slice have at
least one eligible non-null runtime `avg30`.

The fixture therefore does not exercise the user-facing no-price branch. The
query semantics allow no result when no eligible non-null price exists, but
that branch is not independently proven by this fixture.

### Result

Runtime canonical-card `From` price validation passed.

## Image coverage validation

### Source metadata coverage

The canonical-card fixture provides deterministic image metadata for all
Primal Clash cards.

Validation confirmed:

```text
164 cards with small image URLs
164 cards with large image URLs
0 missing small image URLs
0 missing large image URLs
164 unique small image URLs
164 unique large image URLs
```

All validated source URLs:

* use HTTPS;
* use the expected `images.pokemontcg.io` host;
* follow the expected set-code and collector-number path pattern.

For example, canonical card `xy5-1` maps to:

```text
/xy5/1.png
/xy5/1_hires.png
```

### Local file coverage

The repeatable local image download workflow processed all `164` canonical
cards.

Validation confirmed:

```text
328 PNG files
0 remaining .part files
```

The `328` files represent:

```text
164 small images
164 large images
```

Repeating the image download produced:

```text
0 downloads
328 existing files
0 failures
0 invalid records
0 missing-image records
```

### Scope limitation

This validates deterministic metadata and local image-file coverage.

It does not yet validate:

* application image serving;
* NocoDB image presentation;
* phone access;
* Raspberry Pi image paths;
* deployed image backup;
* deployed image restore.

### Result

Primal Clash source image coverage and local image-file coverage passed.

## Rejected, excluded, unresolved, and duplicate records

The import report distinguishes invalid source records, expected exclusions,
controlled unresolved records, and duplicate-prevention results.

| Classification                             | Count | Production effect                                           |
| ------------------------------------------ | ----: | ----------------------------------------------------------- |
| Rejected source records                    |   `0` | No rejected production entities                             |
| Online Code Card exclusions                |   `4` | Skipped and absent from catalogue production                |
| Oversized product exclusions               |   `2` | Preserved as resolved mapping cases without active mappings |
| `unmatched_duplicate_candidate`            |   `6` | Market products preserved without canonical-card mappings   |
| Ordinary `unmatched` mappings              |   `0` | None                                                        |
| `ambiguous` mappings                       |   `0` | None                                                        |
| Mapping conflicts                          |   `0` | None                                                        |
| Duplicate canonical-card source identities |   `0` | None                                                        |
| Duplicate market-product source identities |   `0` | None                                                        |
| Duplicate price-snapshot identities        |   `0` | None                                                        |
| Missing canonical-card image metadata      |   `0` | None                                                        |
| Missing local Primal Clash image files     |   `0` | None                                                        |

### Online Code Card records

The four Online Code Card records are structurally valid source records but are
outside the MVP catalogue scope.

They:

* produce controlled skipped outcomes;
* do not create production market products;
* do not create mapping cases;
* do not create active canonical-card mappings;
* do not create price snapshots;
* do not participate in canonical pricing.

### Oversized product records

Two oversized products are preserved as resolved exclusions in the mapping
review workflow.

They:

* remain represented as source and mapping evidence;
* do not create active canonical-card mappings;
* do not participate in canonical pricing.

### Unmatched duplicate candidates

Six unlisted duplicate-like products are classified as
`unmatched_duplicate_candidate`.

They:

* remain present as valid production market products;
* remain represented in mapping-review evidence;
* do not create active canonical-card mappings;
* do not create editions or variants;
* do not participate in canonical pricing;
* may be reconsidered if richer evidence becomes available.

### Result

All source records are either imported, explicitly skipped, explicitly
excluded, or preserved in a controlled unresolved state.

No source discrepancy is silently discarded.

## Edition and variant scope limitation

The accepted conceptual hierarchy is:

```text
canonical card
→ edition
→ language and finish variant
→ market product
→ price snapshot
```

The physical schema contains:

* `card_editions`;
* `card_variants`.

However, the controlled Primal Clash source evidence proves only card-level
market-product mappings.

The edition-code review covered:

```text
12 mapping rows with non-null edition codes
10 candidate mapping rows
2 excluded oversized rows
```

The review result is:

```text
10 candidate mappings confirmed only at card scope
0 candidate mappings confirmed at edition scope
0 candidate mappings confirmed at variant scope
```

The values `V1` and `V2` do not provide sufficiently consistent evidence for:

* stable edition identity;
* physical edition meaning;
* language;
* finish;
* default edition semantics.

Creating edition or variant records would therefore require guessed project
metadata.

Under `ADR-013`, the controlled production state intentionally contains:

```text
card_editions = 0
card_variants = 0
```

This limitation does not change the validated card-level state:

```text
165 active card-level mappings
173 market price snapshots
164 canonical cards with runtime From prices
```

The project must not claim full production support for English and German
variants, edition filtering, finish filtering, or edition- and variant-specific
CSV values until a controlled classification source or review process is
implemented and validated.

### Result

Edition and variant derivation is correctly deferred and does not block M4
validation at canonical-card scope.

## Repeat-import and idempotency validation

Idempotency was validated separately for mutable current-state records,
review evidence, and append-only snapshot records.

### Canonical cards

Repeating the controlled canonical-card input:

* created no duplicate canonical-card identities;
* preserved stable production records;
* classified the existing records as unchanged.

### Market products

Repeating the controlled product fixture produced:

```text
173 unchanged
4 skipped
0 uncontrolled inserts
0 duplicate source identities
```

### Market mappings

Repeating the controlled mapping fixture produced:

```text
165 unchanged active mappings
12 skipped outcomes
0 new mapping cases
0 new active mappings
0 new status transitions
```

New observations and selected-candidate evidence were recorded as expected for
the repeated source run.

### Market price snapshots

Repeating the same controlled source snapshot produced:

```text
173 unchanged snapshots
0 inserted snapshots
4 skipped outcomes
0 duplicate snapshot identities
```

The original append-only snapshot rows were preserved without updates.

### Audit reconciliation

Every production run records one controlled outcome for every source record in
its declared scope.

Expected exclusions remain visible as skipped outcomes instead of disappearing
from the reconciliation totals.

### Result

Repeated imports create no uncontrolled production duplicates and preserve the
intended current-state, evidence-history, and append-only boundaries.

## Transaction rollback validation

Controlled failure tests were used to prove that staging and production failures
do not leave partially accepted state.

Validated rollback cases include:

* Cardmarket product staging rollback after a partial write;
* Cardmarket mapping production rollback after one complete mapping chain;
* Cardmarket price staging rollback after a partial write;
* Cardmarket price production rollback after one snapshot and audit outcome.

Each controlled failure confirmed:

* the transaction was rolled back;
* previous production state remained unchanged;
* no partial production entity was accepted;
* no partial audit result was accepted;
* subsequent valid execution remained possible.

The product pipeline also exposed an importer lifecycle bug during development:
the implementation attempted to use `merging` while the schema required
`merge_started`.

PostgreSQL rejected the transaction and rolled back its changes. The importer
was corrected to use:

```text
validated
→ merge_started
→ succeeded
```

No schema change was required.

### Result

No controlled failure left partial accepted production state.

## Final production state

The final current production state is:

| Object or result                           | Final count |
| ------------------------------------------ | ----------: |
| Active canonical cards                     |       `164` |
| Active Cardmarket market products          |       `173` |
| Inactive Cardmarket market products        |         `0` |
| Mapping cases                              |       `173` |
| Active card-level mappings                 |       `165` |
| `card_editions`                            |         `0` |
| `card_variants`                            |         `0` |
| Market price snapshots                     |       `173` |
| Canonical cards with runtime `From` prices |       `164` |
| Duplicate market-product source identities |         `0` |
| Duplicate market-price snapshot identities |         `0` |
| Online Code Card products in production    |         `0` |

The cumulative mapping evidence state after the first and repeated mapping runs
is:

| Evidence object             | Count |
| --------------------------- | ----: |
| Mapping observations        | `346` |
| Mapping candidates          | `330` |
| Mapping status-history rows | `173` |

These cumulative evidence counts are not duplicate current production mappings.
They preserve repeated-import observations while stable production state remains
unchanged.

## M4 exit-criteria assessment

| Exit criterion                                                                | Status | Assessment                                                                                                  |
| ----------------------------------------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------- |
| The selected expansion is imported completely or discrepancies are documented | Pass   | All supported records are imported; exclusions and unresolved records are explicitly classified             |
| Image mapping is validated                                                    | Pass   | `164` small and `164` large source mappings and `328` local PNG files validated                             |
| Repeated import does not create uncontrolled duplicates                       | Pass   | Canonical cards, products, mappings, and snapshots preserve their defined identities                        |
| Rejected and unmatched records remain visible                                 | Pass   | No rejected rows exist; exclusions and six duplicate candidates remain explicitly represented               |
| Import evidence is stored                                                     | Pass   | Import runs, outcomes, staging evidence, mapping observations, candidates, and status history are preserved |
| Production mappings match the accepted fixture                                | Pass   | `165` active card-level mappings validated                                                                  |
| Informational pricing matches the accepted rule                               | Pass   | `164` canonical cards validated through latest eligible snapshots and `MIN(avg30)`                          |
| Controlled failures leave no partial accepted production state                | Pass   | Product, mapping, and price rollback paths validated                                                        |
| Unsupported edition or variant data is not invented                           | Pass   | `card_editions` and `card_variants` intentionally remain empty under `ADR-013`                              |

## Known limitations and deferred work

The following limitations remain after M4 validation.

### Edition and variant data

Production does not yet contain controlled edition, language, or finish records.

Consequences include:

* no edition-specific catalogue filtering;
* no language-specific catalogue filtering;
* no finish-specific catalogue filtering;
* no edition-specific wishlist selection;
* no variant-specific wishlist selection;
* no reliable complete edition, language, or finish values in CSV export.

### Price no-result branch

Every controlled Primal Clash canonical card currently has an eligible non-null
runtime `avg30`.

The fixture does not independently validate a canonical card without an
available price.

### Source timestamp semantics

Timezone-naive Cardmarket source timestamps are normalized deterministically,
but their original timezone semantics are not proven by the fixture.

### Application workflow

The report does not validate:

* NocoDB;
* catalogue browsing;
* search;
* filters;
* image preview in the application;
* wishlist selection;
* quantity and notes;
* Wishlist view;
* CSV export;
* mobile browser access.

These belong to `M5 — Wishlist workflow`.

### Infrastructure

The report does not validate:

* Raspberry Pi deployment;
* SSD-backed production persistence;
* private Tailscale access;
* NocoDB deployment;
* backup scheduling;
* restore testing;
* Raspberry Pi restart recovery.

These remain infrastructure work.

### Broader catalogue coverage

Only Primal Clash is validated as the controlled implementation vertical slice.

Additional expansions remain part of `M6 — Catalogue expansion`.

## Evidence index

### Architecture decisions

* `ADR-005 — Separate canonical cards from Cardmarket products`
* `ADR-006 — Use source-scoped identifiers as stable import keys`
* `ADR-008 — Use staging and validated transactional merges for repeated imports`
* `ADR-009 — Preserve rejected and unresolved import records through controlled review states`
* `ADR-011 — Display the minimum 30-day average as the canonical card price`
* `ADR-012 — Preserve unlisted duplicate-like Cardmarket products as unmatched candidates`
* `ADR-013 — Defer automatic edition and variant derivation`

### Permanent import and validation scripts

* `scripts/import/import_primal_clash_catalogue.py`
* `scripts/import/merge_primal_clash_catalogue.py`
* `scripts/import/import_primal_clash_market_products.py`
* `scripts/import/fail_import_primal_clash_market_products.py`
* `scripts/import/merge_primal_clash_market_products.py`
* `scripts/import/import_primal_clash_market_mappings.py`
* `scripts/import/validate_primal_clash_market_mapping_merge.py`
* `scripts/import/fail_merge_primal_clash_market_mappings.py`
* `scripts/import/merge_primal_clash_market_mappings.py`
* `scripts/import/import_primal_clash_market_prices.py`
* `scripts/import/fail_import_primal_clash_market_prices.py`
* `scripts/import/merge_primal_clash_market_prices.py`
* `scripts/import/fail_merge_primal_clash_market_prices.py`
* `scripts/database/validate_schema.sql`
* `scripts/database/validate_primal_clash_from_prices.sql`
* `scripts/images/download_card_images.py`

### Documentation

* `docs/database/data-model.md`
* `docs/import/primal-clash-source-to-target.md`
* `docs/import/m4-cardmarket-mapping-production-merge-handoff.md`
* `scripts/images/README.md`
* `DECISIONS.md`
* `PROJECT.md`
* `ROADMAP.md`
* `CHANGELOG.md`
* `LEARNING_LOG.md`

### Import-run evidence

Relevant controlled run evidence includes:

* Cardmarket product staging and production runs `4` and `6`;
* first Cardmarket mapping production merge run `10`;
* repeated Cardmarket mapping production merge run `12`;
* first Cardmarket price staging and production run `13`;
* repeated Cardmarket price staging and production run `15`.

Controlled rollback attempts may consume sequence values without producing
successful import runs. Gaps in run identifiers are therefore not evidence of
missing accepted production imports.

### Relevant commits

* `ad3a2d9` — Add repeatable card image download workflow
* `5b49bda` — Implement Cardmarket price import pipeline
* `e3d2a53` — Document Cardmarket price import validation
* `b19b0b0` — Document edition and variant derivation deferral

## Validation conclusion

The controlled Primal Clash import satisfies the `M4 — First import`
requirements at canonical-card scope.

The validated vertical slice contains:

```text
164 active canonical cards
173 active Cardmarket market products
165 active canonical-card mappings
173 append-only market price snapshots
164 canonical cards with runtime From prices
```

All expected source records are either:

* imported;
* recorded as explicit skipped outcomes;
* preserved as resolved exclusions;
* preserved as controlled unresolved duplicate candidates.

The import does not silently discard discrepancies or create unsupported
mappings.

Repeated imports create no uncontrolled production duplicates. Stable
current-state entities remain unchanged, repeated mapping evidence remains
auditable, and repeated identical market-price snapshots do not create duplicate
historical rows.

Controlled transaction failures leave no partial accepted production state.

The runtime informational price is validated as the minimum eligible non-null
Cardmarket `avg30` from the latest successful snapshot for each active mapped
market product.

Automatic edition and variant derivation remains explicitly deferred under
`ADR-013`. The empty `card_editions` and `card_variants` tables are a documented
source-evidence limitation and do not invalidate the confirmed card-level
mappings or runtime pricing result.

The consolidated import result is ready for the separate M4 exit review.
