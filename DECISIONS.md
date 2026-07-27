# Architecture Decision Log

This file records significant technical and product decisions for the Pokemon Card Wishlist project.

A recommendation is not a final decision. An ADR may be marked `Accepted` only after explicit confirmation by the project owner.

## Status values

- `Proposed` — under discussion or awaiting validation;
- `Accepted` — approved for implementation;
- `Rejected` — considered but not selected;
- `Superseded` — replaced by a newer ADR.

## Decision template

### ADR-XXX — Decision title

- Status: Proposed / Accepted / Rejected / Superseded
- Date: YYYY-MM-DD
- Owners: Project owner
- Supersedes: ADR-XXX or N/A

#### Context

Describe the problem, constraints, and reason a decision is required.

#### Decision

Describe the selected approach.

#### Alternatives considered

- Alternative A
- Alternative B

#### Consequences

Positive and negative consequences.

#### Validation

Describe how the decision will be evaluated.

#### Follow-up

List implementation, documentation, or migration actions.

---

## ADR-001 — Use a no-code database interface for the MVP

- Status: Proposed
- Date: 2026-07-20
- Owners: Project owner
- Supersedes: N/A

#### Context

The core MVP value is catalogue browsing, wishlist selection, and CSV export. Building a custom frontend before validating the data model and user workflow would increase delivery time and implementation complexity.

#### Decision

Use NocoDB as the initial user interface connected to PostgreSQL.

#### Alternatives considered

- Custom React frontend
- Custom Vue frontend
- Baserow
- Direct spreadsheet workflow

#### Consequences

Positive:

- Faster MVP delivery.
- Built-in table and gallery views.
- Built-in filters, checkboxes, relationships, and CSV export.
- Lower initial frontend complexity.

Negative:

- Limited control over mobile UX.
- Some workflows may depend on NocoDB behaviour.
- A future custom frontend may require migration work.
- Catalogue and wishlist editing permissions must be reviewed carefully.

#### Validation

Test the complete mobile workflow with one full expansion:

- browse;
- search;
- filter;
- preview image;
- mark wanted;
- set quantity and notes;
- open Wishlist view;
- export CSV.

#### Follow-up

- Document NocoDB limitations.
- Confirm that catalogue fields can be protected from unintended editing.
- Accept or reject the ADR after the first mobile workflow test.

---

## ADR-002 — Use PostgreSQL as the primary database

- Status: Proposed
- Date: 2026-07-20
- Owners: Project owner
- Supersedes: N/A

#### Context

The project requires relational data, repeated imports, expansion-to-card relationships, duplicate prevention, import validation, and durable wishlist data.

#### Decision

Use PostgreSQL as the primary database for the MVP deployment.

#### Alternatives considered

- SQLite
- MariaDB
- NocoDB internal database only

#### Consequences

Positive:

- Strong relational integrity.
- Mature backup and restore tools.
- Clear constraints and indexing.
- Good compatibility with NocoDB.
- Easier future API development.
- Better support for staging and import-control tables.

Negative:

- More operational complexity than SQLite.
- Requires a separate container and backup procedure.
- Requires credential and network-access management.

#### Validation

Verify:

- persistence across container and device restarts;
- successful logical backup with `pg_dump`;
- successful restore to a clean database;
- compatibility with NocoDB;
- acceptable performance on the selected Raspberry Pi.

#### Follow-up

- Define backup frequency and retention.
- Define database version and upgrade process.
- Accept or reject the ADR after infrastructure validation.

---

## ADR-003 — Use Tailscale for private remote access

- Status: Proposed
- Date: 2026-07-20
- Owners: Project owner
- Supersedes: N/A

#### Context

The application must be reachable from a phone outside the home network without exposing PostgreSQL or administrative services directly to the public internet.

#### Decision

Use Tailscale for private remote access during the MVP.

#### Alternatives considered

- Cloudflare Tunnel
- Public reverse proxy with port forwarding
- Local-network-only access

#### Consequences

Positive:

- Minimal public attack surface.
- No router port forwarding.
- Simple private connectivity.
- Suitable for a single-user MVP.

Negative:

- Tailscale must be installed and authenticated on client devices.
- The application is not directly accessible to public demo viewers.
- Access depends on the Tailscale service and account configuration.

#### Validation

From a phone using mobile data:

- connect through Tailscale;
- access NocoDB;
- confirm PostgreSQL is not directly reachable;
- verify the core workflow remains usable.

#### Follow-up

- Document device enrolment and revocation.
- Document the actual exposed ports.
- Decide separately how a future public demo would be presented.

---

## ADR-004 — Store card images on the local SSD for the MVP

- Status: Proposed
- Date: 2026-07-20
- Owners: Project owner
- Supersedes: N/A

#### Context

Card images are available, the application is intended to run on a home server, and the MVP should avoid recurring storage costs.

#### Decision

Store card images on the Raspberry Pi SSD and store file paths or internal URLs in PostgreSQL.

Do not store image binary data inside PostgreSQL.

#### Alternatives considered

- External source URLs
- S3-compatible object storage
- Image binary data in PostgreSQL

#### Consequences

Positive:

- No recurring object-storage cost.
- Full control over availability.
- Simple MVP ownership model.
- Images remain available even if external URLs change.

Negative:

- SSD capacity must be monitored.
- Images must be included in backup and restore planning.
- File-path conventions must remain stable.
- Serving performance must be validated.

#### Validation

With one complete expansion:

- map every expected image;
- load the gallery on a phone;
- record missing-image count;
- measure usability;
- test image backup and restore.

#### Follow-up

- Define deterministic image naming.
- Define the image root directory.
- Add missing-image validation to import reports.

---

## ADR-005 — Separate canonical cards from Cardmarket products

- Status: Accepted
- Date: 2026-07-25
- Owners: Project owner
- Supersedes: N/A

#### Context

The inspected sources describe different levels of identity. Pokémon TCG Data provides one English catalogue record per set and collector number, while Cardmarket may provide multiple market products for the same catalogue card. The Primal Clash evidence includes multiple Cardmarket editions for the same card, such as Vulpix `PRC 20` Version 1 and Version 2.

#### Decision

Define one canonical catalogue card as one set-specific card record identified by the catalogue source card ID, for example `xy5-20`.

Store Cardmarket products as separate market entities. A canonical card may be linked to zero, one, or many Cardmarket products. Do not use `idProduct`, `idMetacard`, card name, or name-plus-attacks as the canonical card identity.

The initial wishlist item references the canonical card. A later version may optionally restrict the wishlist item to a specific edition or variant.

#### Alternatives considered

- Use Cardmarket `idProduct` as the catalogue card key.
- Use Cardmarket `idMetacard` as the catalogue card key.
- Deduplicate all products sharing set, name, and collector number.

#### Consequences

Positive:

- Catalogue identity remains stable and independent from marketplace modelling.
- Multiple Cardmarket editions can be preserved without uncontrolled deduplication.
- Wishlist data is not tied to one market product.
- Future marketplace sources can be added without redefining the catalogue.

Negative:

- A mapping layer between canonical cards and market products is required.
- Some Cardmarket mappings remain ambiguous until collector number, edition, or product-level metadata is available.
- Displaying one price for a canonical card requires an aggregation rule.

#### Validation

Validate with the complete Primal Clash vertical slice:

- 164 canonical `xy5` cards;
- complete collector-number coverage;
- Cardmarket products mapped as one-to-many where required;
- code cards excluded;
- ambiguous mappings reported rather than silently merged.

#### Follow-up

- Add separate canonical-card, market-product, and mapping concepts to the data model.
- Preserve mapping method, status, and confidence.
- Document unresolved market-product mappings.

---

## ADR-006 — Use source-scoped identifiers as stable import keys

- Status: Accepted
- Date: 2026-07-25
- Owners: Project owner
- Supersedes: N/A

#### Context

The inspected source files contain unique identifiers, but identifiers from different systems must not share one global namespace. Pokémon TCG Data card IDs are unique within that catalogue, and Cardmarket `idProduct` values are unique within the Cardmarket product snapshot.

#### Decision

Use source-scoped natural keys for imported external entities:

- canonical card: `(source_system, source_card_id)`, for example `('pokemon_tcg_data', 'xy5-20')`;
- Cardmarket market product: `(source_system, source_product_id)`, for example `('cardmarket', '273532')`;
- Cardmarket expansion mapping: preserve `idExpansion` as a source identifier, not as the internal primary key.

Internal database surrogate keys may be added for relationships and implementation convenience, but they do not replace source-scoped uniqueness constraints.

#### Alternatives considered

- Use unscoped source IDs directly as primary keys.
- Use card name and collector number as the only import key.
- Generate new internal IDs without preserving unique source constraints.

#### Consequences

Positive:

- Repeat imports can use deterministic conflict targets.
- Multiple sources can coexist safely.
- Source traceability is preserved.
- External identifier changes and mapping errors remain reviewable.

Negative:

- Import logic must consistently identify the source system.
- Cross-source equivalence requires explicit mapping tables.

#### Validation

- Reimport the Primal Clash fixture twice without creating duplicate canonical cards or market products.
- Verify uniqueness constraints reject duplicate source identifiers within the same source.
- Verify identical literal IDs from different sources do not collide.

#### Follow-up

- Define exact database constraints during `M3 — Data model`.
- Preserve raw source identifiers in staging and validation reports.

---

## ADR-007 — Model edition, language, and finish as separate concepts

- Status: Accepted
- Date: 2026-07-25
- Owners: Project owner
- Supersedes: N/A

#### Context

A canonical card may have multiple Cardmarket editions, and each edition may be available in different languages and finishes. The Primal Clash Vulpix example demonstrates that the same set and collector number can have a standard edition and a special Build-A-Bear Workshop edition. Normal, reverse holo, holo, and other finishes are distinct variants rather than synonyms for edition.

#### Decision

Model the hierarchy as:

`canonical card → edition → variant → market product`

Where:

- `edition` distinguishes releases such as Cardmarket Version 1 and Version 2;
- `variant` distinguishes language and finish combinations;
- initial supported languages are English and German;
- finish values include normal, reverse holo, holo, and an extensible `other` category;
- Cardmarket edition codes such as `V1` and `V2` are preserved;
- a human-readable edition name is stored when known, such as `Standard` or `Build-A-Bear Workshop`; otherwise the display name falls back to `Version 1`, `Version 2`, and so on.

The MVP wishlist references the canonical card only. Selecting a specific edition or variant is planned for a later version.

#### Alternatives considered

- Treat every edition and finish as a separate canonical card.
- Store edition, language, and finish in one free-text variant field.
- Ignore editions and variants until after the MVP.

#### Consequences

Positive:

- Distinct physical and market variants are preserved.
- English and German variants can coexist without duplicating the canonical catalogue.
- Future edition-specific wishlist selection is supported.
- Price records can remain attached to the correct market product or variant.

Negative:

- The model contains more entities and mappings than a flat catalogue.
- Source data may not always identify edition or finish explicitly.
- Unknown values require unresolved mapping states.

#### Validation

- Represent both Vulpix `PRC 20` editions without merging them.
- Represent normal and reverse-holo variants independently.
- Store English and German variants for the same canonical card.
- Confirm that the initial wishlist can reference `xy5-20` without selecting an edition.

#### Follow-up

- Define controlled language and finish values in `M3 — Data model`.
- Add edition and variant mapping evidence to import reports.
- Keep edition and variant selection out of the initial wishlist UI.

---

## ADR-008 — Use staging and validated transactional merges for repeated imports

- Status: Proposed
- Date: 2026-07-27
- Owners: Project owner
- Supersedes: N/A

#### Context

Catalogue and market data will be imported repeatedly from external source files.

Repeated imports must:

- create new source entities without uncontrolled duplicates;
- update changed source-derived values;
- avoid unnecessary updates for unchanged records;
- preserve records that disappear temporarily from a source snapshot;
- keep rejected, unmatched, and ambiguous records reviewable;
- preserve source traceability;
- support rollback after a failed merge;
- avoid modifying user-generated wishlist data.

The accepted source-scoped conflict targets are:

- canonical card: `(source_system, source_card_id)`;
- market product: `(source_system, source_product_id)`.

Direct upserts into production tables would be simple, but would mix parsing, validation, and production changes in one operation. This would make partial failures, unresolved mappings, validation reporting, and rollback more difficult to control.

Append-only source snapshots provide strong historical traceability, but using append-only storage as the only production model would add unnecessary complexity to catalogue queries and current-state management.

A separate staging and merge process is therefore required before the physical schema and first import workflow are finalised.

#### Decision

Use staging tables followed by a validated transactional merge for catalogue and market-product imports.

The import process must separate:

1. source loading;
2. staging validation;
3. production merge;
4. unresolved-record reporting;
5. import-run validation.

No production catalogue record may be inserted or updated directly from unvalidated source data.

Use append-only storage where historical traceability is required, including:

- `import_runs`;
- `market_price_snapshots`;
- validation evidence;
- rejected and unresolved source-record evidence.

Production catalogue entities represent the current accepted state. Source snapshots and import evidence remain separately traceable.

`wishlist_items` and other user-generated fields remain outside the catalogue import update boundary. Catalogue imports must not insert, update, replace, or delete wishlist records.

#### Merge outcomes

Each validated staging record must receive a controlled merge outcome.

##### `inserted`

Use `inserted` when a validated staging record has no production record with the same source-scoped conflict target.

The merge must:

- create one production record;
- preserve the source identifiers;
- assign or retain the internal surrogate identifier required by the schema;
- record the result against the current `import_run`.

Dependent records may be inserted only after their required parent records have been merged successfully.

##### `updated`

Use `updated` when a production record exists and one or more import-owned values differ from the validated staging values.

The merge must:

- update only source-derived fields owned by the import process;
- preserve the production primary key;
- preserve relationships from user-generated data;
- record the update against the current `import_run`;
- update the production modification timestamp.

Comparison must use normalised target values rather than raw source formatting where normalisation rules have been defined.

##### `unchanged`

Use `unchanged` when the production record exists and all compared import-owned values equal the validated staging values.

The merge must:

- perform no production `UPDATE`;
- preserve the existing modification timestamp;
- record the record as `unchanged` in the import summary.

Repeating the same validated import must therefore produce no new production rows and no unnecessary production updates.

##### `missing`

Use `missing` when a production record that was previously observed is absent from the current validated authoritative import scope.

A record must not be classified as `missing` when the import contains only a partial or non-authoritative subset of the source.

A `missing` result must:

- preserve the production record;
- preserve all source identifiers and relationships;
- preserve any related wishlist data;
- record evidence of absence against the current `import_run`;
- remain reviewable.

One missing observation must not automatically retire or delete the production record.

##### `retired`

Use `retired` only when retirement is supported by an explicit source signal or by a separately approved and validated retirement rule.

Retirement must:

- use a controlled inactive state such as `is_active = false` or `retired_at`;
- preserve the production record and its source identifiers;
- preserve existing relationships, including wishlist references;
- exclude the record from ordinary active catalogue views where appropriate;
- preserve the record for audit and historical review.

Imported entities must not be physically deleted as part of a normal repeated import.

Until sequential source snapshots provide enough evidence for an automatic retirement threshold, missing records remain active and reviewable. Retirement requires explicit confirmation or an explicit source status.

##### `rejected`

Use `rejected` when a source record cannot pass structural or domain validation and therefore cannot participate in the production merge.

Examples include:

- missing required source identifiers;
- invalid required field types;
- invalid controlled values;
- invalid source relationships;
- unresolved duplicate conflicts within staging.

A rejected record must:

- not create or update a production entity;
- preserve the raw source payload or a durable reference to it;
- preserve the validation rule and rejection reason;
- remain linked to the `import_run`;
- appear in the import validation summary.

A rejected row does not automatically fail the complete import run. The complete run must fail only when a run-level invariant or configured acceptance threshold is violated.

The detailed rejected-record taxonomy is defined by `ADR-009`.

##### `unmatched`

Use `unmatched` when a valid imported entity cannot be linked to a required target entity using the available evidence.

For example, a valid Cardmarket source product may be stored as a market product while remaining unmatched to a canonical card.

An unmatched record must:

- remain preserved as a valid source-derived entity where applicable;
- not create an unsupported mapping;
- preserve the missing relationship and available evidence;
- remain linked to the `import_run`;
- remain visible in unresolved-record reports;
- not contribute to derived values that require a confirmed mapping.

The accepted `unmatched_duplicate_candidate` classification remains a controlled subtype of unmatched handling. Such products remain preserved, do not create catalogue mappings, and do not contribute to the canonical-card price.

The detailed unmatched workflow and controlled statuses are defined by `ADR-009`.

##### `ambiguous`

Use `ambiguous` when more than one target mapping is plausible and the available evidence is insufficient to select one safely.

An ambiguous record must:

- not receive an automatically selected mapping;
- preserve all candidate targets and available evidence;
- not replace an existing confirmed mapping without explicit validation;
- remain linked to the `import_run`;
- remain visible in unresolved-record reports;
- not contribute to dependent derived values.

When a required parent relationship is ambiguous, dependent production records must not be created until the ambiguity is resolved.

The detailed ambiguous-mapping workflow is defined by `ADR-009`.

#### Transaction boundary

The validated production merge must execute in a database transaction.

The logical import sequence is:

1. create an `import_run`;
2. load source records into staging;
3. validate staging records and run-level invariants;
4. stop before production changes if pre-merge validation fails;
5. merge parent production entities;
6. merge dependent production entities;
7. merge confirmed mappings;
8. append price snapshots;
9. record rejected, unmatched, and ambiguous outcomes;
10. calculate the import validation summary;
11. commit the production merge;
12. mark the `import_run` as successful.

If any production merge operation fails, the transaction must be rolled back.

After rollback:

- production catalogue data remains in its previous consistent state;
- wishlist data remains unchanged;
- no partial production merge is accepted;
- the `import_run` is marked as failed;
- available staging and validation evidence is retained for investigation.

The implementation may use separate short transactions for creation of the import run, staging ingestion, and post-rollback failure recording, provided the production merge itself remains atomic.

#### Import ownership boundary

The import process may update only fields explicitly classified as source-derived and import-owned.

The import process must not update:

- wishlist selection state;
- wanted quantity;
- user notes;
- future user-selected edition or variant preferences;
- other user-generated metadata.

Foreign-key relationships from wishlist data to canonical cards must remain valid when catalogue records are updated, marked missing, or retired.

#### Required invariants

The implementation must enforce the following invariants:

- no production entity is merged from unvalidated staging data;
- one source-scoped conflict target resolves to at most one production entity;
- repeating the same validated import produces zero inserts and zero updates;
- a missing record is not treated as deleted;
- retirement does not physically delete imported entities;
- catalogue imports do not modify wishlist data;
- rejected, unmatched, and ambiguous records do not receive invented mappings;
- market price snapshots are append-only;
- a failed production merge leaves the previous production state unchanged;
- every import outcome is traceable to an `import_run`.

#### Alternatives considered

##### Direct upsert into production tables

Advantages:

- fewer tables and processing stages;
- simpler initial implementation;
- direct use of database conflict handling.

Disadvantages:

- validation and production changes become tightly coupled;
- partial failures are harder to investigate;
- rejected and unresolved rows are harder to preserve consistently;
- dry-run validation is limited;
- production may be changed before full run-level validation is complete.

##### Append-only source snapshots with derived current state

Advantages:

- complete source history;
- strong auditability;
- flexible reconstruction of past states.

Disadvantages:

- more complex current-state queries;
- more storage and retention requirements;
- increased implementation complexity for the MVP;
- derived-state refresh and consistency rules would require additional infrastructure.

##### Staging followed by validated transactional merge

Advantages:

- validation occurs before production changes;
- dry-run and import summaries are practical;
- unresolved records remain explicit;
- production updates can be atomic;
- repeated imports can be tested deterministically;
- wishlist data can remain outside the merge boundary.

Disadvantages:

- requires staging and import-control tables;
- requires explicit merge logic;
- requires clear ownership rules for production fields;
- requires cleanup or retention rules for staging data.

#### Consequences

Positive:

- repeated catalogue imports can be idempotent;
- source-scoped uniqueness remains enforceable;
- failed imports cannot leave a partially merged catalogue;
- rejected and unresolved records remain traceable;
- wishlist data remains independent from source updates;
- validation can occur before production changes;
- append-only price history remains compatible with current-state catalogue tables.

Negative:

- the schema and import pipeline contain additional tables and states;
- merge logic must distinguish import-owned and user-owned fields;
- authoritative import scope must be declared before missing records can be detected;
- retirement requires a separate evidence-based policy;
- staging retention and cleanup rules must be documented.

#### Validation

Validate the decision with the Primal Clash vertical slice.

The validation must include:

1. Import the complete validated fixture into an empty database.
2. Confirm the expected production and unresolved-record counts.
3. Repeat the identical import.
4. Confirm that the second import produces:

   * zero inserted catalogue entities;
   * zero updated catalogue entities;
   * no uncontrolled duplicates;
   * unchanged wishlist records.
5. Change one import-owned field in staging and confirm that exactly one expected production record is updated.
6. Remove one record from a declared complete authoritative scope and confirm that it is reported as `missing` without deletion or automatic retirement.
7. Import a rejected record and confirm that it does not reach production.
8. Import unmatched and ambiguous mapping examples and confirm that no unsupported mapping or canonical price contribution is created.
9. Force a merge failure and confirm that all production changes are rolled back.
10. Confirm that price snapshots remain append-only.
11. Confirm that existing wishlist quantity and notes remain unchanged through insert, update, missing, retirement, and rollback tests.

#### Follow-up

- Define the rejected, unmatched, and ambiguous record taxonomy in `ADR-009`.
- Define staging, import-run, validation-evidence, and merge-result tables.
- Define import-owned fields for every production table.
- Define how an import declares its authoritative source scope.
- Define staging retention and cleanup rules.
- Define the physical inactive-state fields used for retirement.
- Add database constraints for the accepted source-scoped conflict targets.
- Write repeat-import, rollback, unresolved-record, and wishlist-preservation tests.
- Revisit automatic retirement only after sequential source snapshots provide sufficient evidence.

---

## ADR-011 — Display the minimum 30-day average as the canonical card price

- Status: Accepted
- Date: 2026-07-25
- Owners: Project owner
- Supersedes: N/A

#### Context

The MVP wishlist references a canonical card, while Cardmarket prices belong to market products and may differ by edition, language, and finish. A single canonical card therefore may have several valid `avg30` values.

#### Decision

Display the minimum available non-null Cardmarket 30-day average price across all supported English and German editions and variants linked to the canonical card.

Present this value as a starting price, for example `From €0.15`, and label it as a 30-day average.

When edition- or variant-specific wishlist selection is added later, display that selected market variant's own 30-day average instead.

#### Alternatives considered

- Arithmetic mean across all linked variants.
- Price from the first or default market product.
- No price in the MVP.
- Current low or trend price instead of the 30-day average.

#### Consequences

Positive:

- The displayed value has a clear marketplace meaning.
- Expensive special editions do not inflate the entry price.
- The rule is deterministic and easy to validate.

Negative:

- The displayed price may refer to a different language, finish, or edition than the image shown.
- Missing mappings or null `avg30` values can prevent price display.
- The value is not a quote or guarantee of current availability.

#### Validation

For the Primal Clash fixture:

- collect all linked English and German non-null `avg30` values;
- verify the displayed value equals their minimum;
- verify null values are ignored;
- verify cards without an available value display no fabricated price;
- verify the UI labels the value as `From` and `30-day average`.

#### Follow-up

- Add price-source timestamp and currency to the data model.
- Add the aggregation rule to import and UI validation tests.
- Document that the price is informational and may be stale.

---

## ADR-012 — Preserve unlisted duplicate-like Cardmarket products as unmatched candidates

- Status: Accepted
- Date: 2026-07-27
- Owners: Project owner
- Supersedes: N/A

#### Context

The Primal Clash Cardmarket product fixture contains six products that are not referenced by any current Cardmarket listing URL:

- `295269` — Escape Rope;
- `295286` — Dive Ball;
- `295292` — Rough Seas;
- `312211` — Wonder Energy;
- `312239` — Teammates;
- `312267` — Rough Seas.

Each record shares the same name, `idMetacard`, `idExpansion`, `idCategory`, and category name with one or more directly mapped products. The inspected records differ only by `idProduct` and `dateAdded`.

The available source data does not explain why these additional products were created. It therefore does not provide enough evidence to classify them as confirmed editions, variants, reprints, or duplicates.

#### Decision

Classify an unlisted Cardmarket product as `unmatched_duplicate_candidate` when all of the following conditions are true:

- it is not referenced by a successfully collected Cardmarket listing URL;
- it shares `idMetacard` with a directly mapped product;
- its normalized product name matches the directly mapped product;
- `idExpansion`, `idCategory`, and category name match;
- the inspected differences are limited to `idProduct` and `dateAdded`.

An `unmatched_duplicate_candidate`:

- remains preserved as a source product record;
- is not mapped to a canonical card;
- does not create a catalogue edition or variant;
- does not participate in the canonical MVP price calculation;
- remains visible in import validation and review reports;
- may be reclassified later when richer source evidence becomes available.

This classification is evidence-based but intentionally does not claim that the source products are confirmed duplicates.

#### Alternatives considered

- Map each additional product to the canonical card using its shared `idMetacard`.
- Merge the additional records into the directly mapped product.
- Exclude the additional records entirely.
- Treat each additional product as a confirmed edition or variant.

#### Consequences

Positive:

- Source records are preserved without inventing unsupported mappings.
- Duplicate-like products cannot distort canonical price aggregation.
- The import process remains explicit about unresolved Cardmarket data.
- Future evidence can reclassify the records without reconstructing discarded source data.

Negative:

- Some imported Cardmarket products remain intentionally unmapped.
- The classification requires validation against directly mapped sibling records.
- A future source snapshot may require re-evaluation of the candidates.

#### Validation

For the Primal Clash vertical slice:

- verify that all six identified products receive the
  `unmatched_duplicate_candidate` classification;
- verify that they remain present in source and validation records;
- verify that none creates a canonical-card mapping;
- verify that none contributes to the canonical card price;
- verify that directly mapped products remain unchanged;
- report any future record whose differences exceed `idProduct` and
  `dateAdded` as a separate unresolved case.

#### Follow-up

- Add `unmatched_duplicate_candidate` to the controlled mapping-status values.
- Update the Primal Clash mapping builder to emit this status when the
  documented conditions are satisfied.
- Add permanent validation for candidate classification and price exclusion.
- Reference this rule from `ADR-009 — Define rejected and unmatched record
  handling`.

---

## Planned ADRs

The following decisions are expected before or during `M0 — Discovery` and `M3 — Data model`:

- `ADR-009 — Define rejected and unmatched record handling`
- `ADR-010 — Define backup scope, retention, and restore validation`

These ADRs must not be finalised without evidence from real source files.
