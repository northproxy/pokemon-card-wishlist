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

- Status: Accepted
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

   - zero inserted catalogue entities;
   - zero updated catalogue entities;
   - no uncontrolled duplicates;
   - unchanged wishlist records.
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

## ADR-009 — Preserve rejected and unresolved import records through controlled review states

- Status: Accepted
- Date: 2026-07-28
- Owners: Project owner
- Supersedes: N/A

#### Context

Imported source records and cross-source mappings do not always contain enough valid evidence to enter the production catalogue or create a confirmed relationship.

The import workflow must distinguish between:

- an invalid source record;
- a valid source entity with no target match;
- a source entity with multiple plausible target matches;
- a possible relationship that requires review;
- a confirmed relationship;
- a valid source record intentionally excluded from MVP catalogue scope;
- the accepted duplicate-like unmatched Cardmarket product case.

These conditions must not be collapsed into one generic error state.

Unknown or ambiguous source data must remain traceable and reviewable. The import process must not invent mappings, silently discard source records, or allow unresolved records to influence canonical-card pricing.

`ADR-008` defines how rejected, unmatched, and ambiguous records interact with staging and transactional production merges. This ADR defines their controlled statuses, required evidence, review lifecycle, and reporting behaviour.

#### Decision

Use controlled source-record and mapping statuses with explicit evidence and review fields.

The controlled statuses are:

- `rejected`;
- `unmatched`;
- `ambiguous`;
- `candidate`;
- `confirmed`;
- `excluded`;
- `unmatched_duplicate_candidate`.

The statuses describe the latest accepted classification of a source record or mapping relationship. Every classification remains traceable to the `import_run` and evidence that produced it.

No unresolved status may be promoted to `confirmed` without deterministic evidence or an explicit reviewed decision.

#### Status definitions

##### `rejected`

Use `rejected` when the source record itself is invalid for the required import contract.

Examples include:

- missing required source-scoped identifier;
- invalid required data type;
- invalid controlled value;
- malformed required relationship;
- duplicate source keys within one authoritative staging scope;
- internally contradictory source fields;
- a record that cannot be parsed without inventing required values.

A rejected record:

- does not create or update its target production entity;
- does not create a mapping;
- does not participate in canonical-card price calculation;
- preserves the raw payload or a durable raw-source reference;
- preserves one or more structured rejection reasons;
- remains linked to the import run;
- may be reprocessed after the source data or validation rule changes.

`rejected` must not be used merely because a valid source entity has no confirmed cross-source mapping.

##### `unmatched`

Use `unmatched` when the source entity is valid, but no plausible target entity can be identified using the available evidence.

An unmatched record:

- may create or update its own independent production entity where applicable;
- does not create a cross-source mapping;
- does not create an edition or variant through inference;
- does not participate in derived values requiring a confirmed mapping;
- remains visible in unresolved-record reports;
- may be reevaluated during a later import or manual review.

For example, a valid Cardmarket product may be preserved in `market_products` while remaining unmatched to a canonical card.

##### `ambiguous`

Use `ambiguous` when two or more target entities are plausible and the available evidence cannot distinguish them safely.

An ambiguous record:

- preserves all plausible candidate targets;
- preserves the evidence supporting each candidate;
- does not create a confirmed mapping;
- does not replace an existing confirmed mapping automatically;
- does not participate in derived values requiring a confirmed mapping;
- requires additional evidence or explicit review before resolution.

The import process must not choose the first, cheapest, closest-name, or otherwise convenient candidate automatically.

##### `candidate`

Use `candidate` when exactly one plausible target relationship has been identified, but the available evidence does not meet the confirmation threshold.

A candidate record:

- preserves the proposed target;
- preserves the mapping method and available evidence;
- does not create an active confirmed production mapping;
- does not participate in canonical-card price calculation;
- remains reviewable;
- may become `confirmed`, `unmatched`, `ambiguous`, `excluded`, or remain `candidate` after further evidence is collected.

`candidate` is not a weaker synonym for `confirmed`.

##### `confirmed`

Use `confirmed` when the mapping is supported by deterministic source evidence or an explicit reviewed decision.

Examples of deterministic evidence include:

- a direct source product identifier collected from the corresponding marketplace product page;
- a source-provided explicit relationship identifier;
- another documented evidence rule accepted by an ADR or validated import rule.

A confirmed mapping:

- may create or update the production mapping;
- may create the supported edition and variant relationships;
- may participate in canonical-card price calculation when all other pricing requirements are satisfied;
- preserves the mapping method and evidence reference;
- remains traceable to the import run or manual review that confirmed it.

A previously confirmed mapping must not be replaced or removed automatically by weaker new evidence.

##### `excluded`

Use `excluded` when a valid source record is intentionally outside the approved MVP catalogue scope.

Examples include:

- Online Code Card products;
- sealed products;
- unsupported product categories explicitly excluded by project scope.

An excluded record:

- remains preserved as source evidence;
- records a controlled exclusion reason;
- does not create a canonical catalogue entity, edition, variant, or confirmed catalogue mapping;
- does not participate in canonical-card price calculation;
- appears separately from rejected and unresolved records in import reports;
- is not considered a data-quality failure when the exclusion rule is expected and validated.

`excluded` must not be used to hide a record that is difficult to map.

##### `unmatched_duplicate_candidate`

Use `unmatched_duplicate_candidate` only when the conditions accepted in `ADR-012` are satisfied.

The record must:

- be unreferenced by a successfully collected Cardmarket listing URL;
- share `idMetacard` with a directly mapped product;
- have the same normalized product name;
- have the same `idExpansion`, `idCategory`, and category name;
- differ only in `idProduct` and `dateAdded`.

An `unmatched_duplicate_candidate`:

- remains preserved as a valid source product;
- does not create a canonical-card mapping;
- does not create an edition or variant;
- does not participate in canonical-card price calculation;
- remains visible in validation and review reports;
- may be reclassified if richer source evidence becomes available.

This status does not assert that the source record is a confirmed duplicate.

#### Status ownership

Source-record validity and mapping resolution are separate concerns.

Where practical, the physical model should preserve them separately, for example:

- source-record processing status;
- mapping status;
- review status.

A valid market product may therefore be successfully merged as a production entity while its mapping status remains `unmatched`, `candidate`, `ambiguous`, or `unmatched_duplicate_candidate`.

The final physical table design is defined during `M3 — Data model`, but it must not force unrelated concepts into one overloaded status field.

#### Required evidence fields

Every rejected or mapping-review record must preserve, directly or through related evidence tables:

- `import_run_id`;
- `source_system`;
- source entity type;
- source-scoped identifier, when available;
- raw source payload or durable raw-source reference;
- controlled status;
- controlled reason code;
- human-readable reason detail;
- mapping method, where applicable;
- proposed or confirmed target identifier, where applicable;
- candidate target identifiers, where applicable;
- evidence type;
- evidence reference;
- evidence strength or confidence category;
- first observed timestamp;
- latest observed timestamp;
- review state;
- reviewer or review source, where applicable;
- review timestamp, where applicable;
- resolution note, where applicable;
- superseded status reference, where applicable.

Free-text notes may supplement but must not replace controlled status and reason values.

#### Evidence levels

Use controlled evidence levels:

- `direct`;
- `derived`;
- `manual`;
- `insufficient`.

##### `direct`

Evidence explicitly identifies the relationship, such as a collected source product ID from the corresponding product page.

Direct evidence may support automatic `confirmed` status when the validation rule is documented and passes.

##### `derived`

Evidence is produced by a deterministic rule from multiple source fields but does not contain an explicit relationship identifier.

Derived evidence may support `candidate` or, only when separately accepted and validated, `confirmed`.

##### `manual`

A reviewer explicitly confirms or resolves the record using documented evidence.

Manual confirmation must preserve the reviewer, timestamp, evidence, and resolution note.

##### `insufficient`

The available evidence cannot establish a safe relationship.

Insufficient evidence results in `unmatched`, `ambiguous`, or continued `candidate` status.

#### Review lifecycle

The lifecycle must preserve status history rather than overwrite all earlier evidence.

Allowed review transitions include:

```text
unmatched → candidate
unmatched → ambiguous
unmatched → confirmed
unmatched → excluded

candidate → confirmed
candidate → ambiguous
candidate → unmatched
candidate → excluded

ambiguous → candidate
ambiguous → confirmed
ambiguous → unmatched
ambiguous → excluded

unmatched_duplicate_candidate → candidate
unmatched_duplicate_candidate → confirmed
unmatched_duplicate_candidate → unmatched
unmatched_duplicate_candidate → excluded

rejected → revalidated
revalidated → rejected
revalidated → unmatched
revalidated → candidate
revalidated → ambiguous
revalidated → confirmed
revalidated → excluded
```

`revalidated` may be represented as an event rather than a persistent final status.

A transition to `confirmed` requires:

- sufficient evidence;
- a recorded confirmation method;
- a target identifier;
- validation that the target is compatible with existing uniqueness and mapping constraints;
- no unresolved conflict with an existing confirmed mapping.

A transition must create a new status-history or resolution record rather than destroying the previous classification evidence.

#### Reprocessing behaviour

Every new import run may reevaluate unresolved records using newly available source data.

Reprocessing must:

- use source-scoped identifiers to reconnect the record with earlier evidence;
- preserve the previous status and evidence;
- create a new observation or classification result;
- avoid duplicating identical unresolved observations unnecessarily;
- never demote or replace a confirmed mapping solely because weaker evidence is observed;
- report status transitions separately from newly observed unresolved records.

Manual resolutions should remain effective across repeated imports unless new direct evidence creates a documented conflict.

Such a conflict must be reported for review rather than silently replacing the manual resolution.

#### Production merge behaviour

The status controls production effects as follows:

| Status                          | Preserve source entity |      Create target entity |    Create mapping | Price contribution |
| ------------------------------- | ---------------------: | ------------------------: | ----------------: | -----------------: |
| `rejected`                      |       Yes, as evidence |                        No |                No |                 No |
| `unmatched`                     |                    Yes | Where independently valid |                No |                 No |
| `ambiguous`                     |                    Yes | Where independently valid |                No |                 No |
| `candidate`                     |                    Yes | Where independently valid | No active mapping |                 No |
| `confirmed`                     |                    Yes |       Yes, where required |               Yes | Yes, when eligible |
| `excluded`                      |       Yes, as evidence |       No catalogue entity |                No |                 No |
| `unmatched_duplicate_candidate` |                    Yes |       Market product only |                No |                 No |

Only `confirmed` mappings may participate in the canonical-card minimum `avg30` calculation defined by `ADR-011`.

#### Import-run failure rules

A row-level `rejected`, `unmatched`, `candidate`, `ambiguous`, `excluded`, or `unmatched_duplicate_candidate` result does not automatically fail the complete import run.

The import run must fail before production merge when a run-level invariant is violated, including:

- duplicate source-scoped identifiers that make deterministic processing impossible;
- staging corruption;
- unsupported schema or file version;
- invalid declared authoritative scope;
- validation totals inconsistent with the declared source input;
- a confirmed mapping conflict that violates uniqueness constraints;
- another configured critical validation rule.

Non-critical unresolved records may be committed as evidence while valid production entities are merged, provided the import summary reports them accurately.

Acceptance thresholds must be explicit and must not be introduced silently in implementation code.

#### Import reporting

Every import summary must report at least:

- total source records;
- valid source records;
- rejected records;
- excluded records;
- confirmed mappings;
- candidate mappings;
- unmatched mappings;
- ambiguous mappings;
- `unmatched_duplicate_candidate` records;
- newly observed unresolved records;
- previously known unresolved records observed again;
- resolved records;
- status transitions;
- unresolved records that could affect catalogue completeness;
- records excluded from canonical-card price calculation;
- run-level validation failures.

The report must distinguish expected exclusions from data-quality failures.

Counts must reconcile with the declared import scope or the run must report why reconciliation is not applicable.

#### Alternatives considered

##### One generic unresolved status

Advantages:

- simpler schema;
- fewer controlled values.

Disadvantages:

- loses the difference between no target, multiple targets, and one unconfirmed target;
- makes review prioritisation difficult;
- obscures production and pricing effects;
- cannot represent the accepted duplicate-candidate rule accurately.

##### Automatically choose the best candidate

Advantages:

- fewer unresolved records;
- more complete-looking catalogue and price coverage.

Disadvantages:

- introduces unsupported mappings;
- can attach prices to the wrong canonical card;
- hides source-data limitations;
- makes future correction and audit more difficult.

##### Discard rejected and excluded records

Advantages:

- less stored evidence;
- simpler reporting.

Disadvantages:

- loses source traceability;
- prevents later reprocessing;
- hides catalogue-scope and data-quality decisions;
- makes source count reconciliation unreliable.

##### Controlled statuses with preserved evidence

Advantages:

- preserves uncertainty explicitly;
- supports repeatable review and reprocessing;
- prevents unresolved records from affecting derived prices;
- separates expected exclusions from invalid records;
- supports audit and portfolio evidence.

Disadvantages:

- requires controlled values and status-history structures;
- requires more detailed import reports;
- requires clear review procedures;
- unresolved queues require ongoing maintenance.

#### Consequences

Positive:

- invalid source records and unresolved mappings remain distinguishable;
- ambiguous mappings cannot be silently promoted;
- confirmed mappings have a documented evidence threshold;
- expected MVP exclusions do not appear as import failures;
- unresolved records cannot distort canonical-card pricing;
- later evidence can resolve records without reconstructing discarded source data;
- import reports can reconcile source coverage and review workload.

Negative:

- the data model requires several controlled statuses and evidence fields;
- status transitions and manual decisions must be preserved;
- review queues add operational work;
- physical separation of source validity, mapping status, and review status increases schema complexity;
- confirmation rules must be validated per source and mapping method.

#### Validation

Validate the decision with the Primal Clash fixture and controlled synthetic test cases.

The validation must confirm:

1. All `167` directly evidenced listing variants are classified as `confirmed`.
2. All `4` Online Code Card products are classified as `excluded`.
3. All `6` accepted duplicate-like records are classified as `unmatched_duplicate_candidate`.
4. No ordinary `unmatched`, `ambiguous`, or conflict records remain in the validated Primal Clash result.
5. No excluded or unresolved record contributes to canonical-card price calculation.
6. A structurally invalid test record becomes `rejected` and does not enter production.
7. A valid record with no plausible target becomes `unmatched`.
8. A record with one plausible but insufficiently evidenced target becomes `candidate`.
9. A record with multiple plausible targets becomes `ambiguous`.
10. No `candidate` or `ambiguous` record becomes `confirmed` without new evidence or explicit review.
11. Reprocessing preserves previous evidence and records the status transition.
12. Import summary counts reconcile with the declared test scope.
13. A row-level unresolved result does not fail an otherwise valid import run.
14. A run-level invariant violation prevents the production merge.
15. Repeated import does not create duplicate unresolved records or duplicate confirmed mappings.

#### Follow-up

- Define controlled reason codes for every status.
- Define the physical source-record, mapping, evidence, review, and status-history tables.
- Define evidence references for automated and manual decisions.
- Define uniqueness constraints for active confirmed mappings.
- Define how manual review is performed through NocoDB or administrative SQL.
- Add unresolved-record and status-transition validation queries.
- Add import-report reconciliation checks.
- Add synthetic rejected, unmatched, candidate, and ambiguous fixtures.
- Reference `ADR-009` from the data dictionary and import operating guide.

---

## ADR-010 — Define backup scope, retention, and restore validation

- Status: Proposed
- Date: 2026-07-28
- Owners: Project owner
- Supersedes: N/A

#### Context

The MVP will store several types of persistent data:

- PostgreSQL catalogue, import-control, price, and wishlist data;
- locally stored card images;
- Docker Compose and application configuration;
- operational documentation and recovery procedures;
- secrets and credentials that must remain outside the repository.

A backup stored only on the Raspberry Pi or on the same SSD does not protect
against device loss, SSD failure, filesystem corruption, accidental deletion,
or destructive maintenance.

Database backup creation alone is not sufficient. The application must also be
recoverable with its image files and required configuration.

A backup process must therefore define:

- what is backed up;
- where backups are stored;
- how often they are created;
- how long they are retained;
- how secrets are handled;
- how backup integrity is checked;
- how restoration is tested;
- what evidence is retained.

The MVP should use a simple, reproducible process without introducing an
unnecessary backup platform or paid service.

#### Decision

Use separate backup mechanisms for PostgreSQL and file-based data.

Use:

- `pg_dump` for PostgreSQL logical backups;
- file-level archive or copy for card images and required configuration;
- at least one backup copy stored outside the Raspberry Pi and its primary SSD;
- documented retention rules;
- documented restore procedures;
- periodic restore validation to a clean test location.

A backup is not considered validated merely because the backup command
completed successfully.

The backup process is considered validated only after the protected data has
been restored and the restored result has passed the required integrity checks.

#### Backup scope

The backup scope must include the following categories.

##### PostgreSQL data

Back up the PostgreSQL database containing:

- catalogue data;
- canonical cards;
- editions and variants;
- Cardmarket products and mappings;
- market price snapshots;
- import runs and validation evidence;
- rejected and unresolved record evidence;
- wishlist items;
- user-entered quantity and notes;
- schema objects required by the application.

Use a logical PostgreSQL backup produced by `pg_dump`.

The backup must include enough database structure and data to restore the
application database into a clean PostgreSQL instance.

##### Card images

Back up all locally managed card images required by the application.

The backup must preserve:

- relative file paths;
- file names;
- directory structure;
- file contents;
- enough metadata to reconnect database image references after restoration.

Temporary download files, caches, and reproducible intermediate files do not
need to be included unless they are required for recovery.

##### Configuration

Back up the configuration required to recreate the deployment, including where
applicable:

- `compose.yaml` or `docker-compose.yml`;
- Docker environment-file templates without secret values;
- service configuration files;
- storage path definitions;
- image-serving configuration;
- backup and restore scripts;
- documented version information;
- operational notes required for recovery.

Files already version-controlled in GitHub do not need to be duplicated for
source-history purposes, but the recovery procedure must identify the required
repository revision or release tag.

##### Secrets

Secrets must not be committed to the repository or stored in plaintext backup
evidence.

Secrets may be backed up only through an explicitly protected mechanism, such
as:

- an encrypted password manager;
- an encrypted archive;
- another documented secure secret-storage method.

The restore guide must identify which secrets must be recreated or retrieved.

The backup process must not copy plaintext secret files to an unprotected
off-device location.

##### Excluded data

The following may be excluded when they are reproducible and not required for
recovery:

- container images available from their registries;
- disposable container layers;
- caches;
- temporary import files;
- generated reports that can be reproduced from retained source and database
  data;
- development-only files not used by the deployed MVP.

Exclusions must be documented rather than assumed.

#### Backup locations

Maintain at least two storage locations:

1. the primary live storage on the Raspberry Pi SSD;
2. at least one backup copy outside the Raspberry Pi and outside the primary
   SSD.

The external copy may use:

- another computer;
- an external drive that is not permanently attached;
- a network storage location;
- an encrypted remote storage service;
- another separately approved location.

A backup stored on another directory or partition of the same SSD does not
satisfy the off-device requirement.

The selected external location must be documented during infrastructure
implementation.

#### Backup schedule

Use a simple MVP schedule.

Recommended baseline:

- PostgreSQL logical backup: daily;
- images and configuration backup: daily when changes are expected, otherwise
  at least weekly;
- immediate manual backup before destructive maintenance, database migration,
  restore testing, or major import changes.

The exact execution time may be selected during deployment.

A failed scheduled backup must be visible through logs or another documented
check. Silent failure is not acceptable.

#### Retention

Use a rolling retention policy suitable for a single-user MVP.

Recommended baseline:

- retain the most recent `7` daily backups;
- retain the most recent `4` weekly backups;
- retain one manual pre-change backup for each significant migration or recovery
  test until the related change is validated.

Retention applies to complete recovery sets, not only to database files.

A recovery set should make it possible to identify the matching:

- database backup;
- image backup;
- configuration revision;
- backup timestamp;
- application or repository version.

Old backups may be deleted only after:

- the required newer backups exist;
- backup creation completed successfully;
- the retention policy remains satisfied.

The implementation may simplify the physical storage layout, but it must not
silently reduce the accepted recovery coverage.

#### Backup naming and metadata

Backup files must use deterministic names containing at least:

- project identifier;
- backup type;
- UTC or clearly documented local timestamp;
- database or component name where applicable.

Example naming pattern:

```text
pokemon-card-wishlist_postgresql_2026-07-28T010000Z.dump
pokemon-card-wishlist_files_2026-07-28T010000Z.tar.gz
pokemon-card-wishlist_manifest_2026-07-28T010000Z.json
```

Each recovery set should preserve a manifest containing where practical:

- creation timestamp;
- host identifier;
- PostgreSQL version;
- backup command or script version;
- repository commit or release identifier;
- included components;
- excluded components;
- backup file sizes;
- checksum values;
- success or failure status.

The manifest must not contain secret values.

#### Integrity checks

Every created backup must receive basic validation.

Database backup validation must include where practical:

- successful `pg_dump` exit status;
- non-zero backup file size;
- expected backup format;
- recorded checksum;
- ability to inspect or restore the dump.

File backup validation must include:

- successful archive or copy operation;
- expected directories present;
- non-zero file count where images are expected;
- recorded checksum or archive integrity check;
- no accidental inclusion of plaintext secrets.

Checksums help detect file corruption but do not replace restore testing.

#### Restore procedure

The restore procedure must support recovery into a clean environment.

The documented sequence must include:

1. identify the required recovery set;
2. obtain the matching repository revision or release;
3. prepare a clean PostgreSQL instance;
4. restore the database;
5. restore card images to the documented path;
6. restore or recreate configuration;
7. retrieve or recreate required secrets securely;
8. start the services;
9. run database and application validation;
10. record the restore result.

Restore testing must not overwrite the only working production environment
unless an explicit recovery exercise has been planned and a rollback path is
available.

Prefer restore validation in an isolated database, temporary Docker Compose
project, or other clean test environment.

#### Restore validation

A successful restore test must verify at least:

- PostgreSQL restore completes without unresolved errors;
- expected schema objects exist;
- expected catalogue row counts are present;
- wishlist items are present;
- wanted quantity and notes are preserved;
- import-run and unresolved-record evidence is present;
- image files are present;
- database image references resolve to restored files;
- the application can connect to the restored database;
- catalogue records can be read;
- the Wishlist view or equivalent validation query returns expected data;
- no secrets were exposed through logs, repository files, or backup evidence.

Where practical, the restore test should also verify:

- the canonical-card minimum `avg30` query;
- source-scoped uniqueness constraints;
- foreign-key integrity;
- backup checksum consistency;
- service restart after restoration.

A restore test is unsuccessful if data is present but the documented application
workflow cannot use it.

#### Restore-test frequency

Perform restore validation:

- before accepting the infrastructure milestone;
- after material changes to database version, storage layout, backup scripts, or
  restore scripts;
- before the MVP release;
- periodically during operation, with a recommended minimum of once every three
  months.

A restore test may be performed more frequently during implementation.

The project must not claim that backup and restore are validated until at least
one complete restore test has passed.

#### Recovery objectives

The MVP does not require formal enterprise service-level guarantees.

Use the following practical targets:

- recovery point objective: loss of no more than one day of database changes
  under the normal daily backup schedule;
- recovery time objective: restore the MVP within one planned maintenance
  session using the documented procedure.

These are recovery targets, not validated guarantees, until measured through a
restore exercise.

Any measured restore duration and observed data-loss window should be recorded
in the restore evidence.

#### Backup and restore evidence

Each validation exercise must record:

- date and time;
- backup set used;
- source environment;
- target restore environment;
- commands or scripts executed;
- backup file sizes;
- checksum results;
- database restore result;
- file restore result;
- validation queries or checks;
- observed issues;
- recovery duration;
- final success or failure status.

Evidence must not include:

- passwords;
- tokens;
- private keys;
- plaintext environment files containing secrets;
- sensitive network credentials.

Operational logs may be retained if they are reviewed for secret exposure.

#### Failure handling

If a backup fails:

- do not delete the last known valid backup;
- record the failure;
- preserve relevant logs without secrets;
- investigate the failure;
- rerun the backup after correction;
- verify that retention still contains a usable recovery set.

If restore validation fails:

- mark the recovery set or procedure as unvalidated;
- record the failure reason;
- preserve the failed-test evidence;
- correct the backup or restore procedure;
- repeat the restore test from a clean target;
- do not claim backup readiness until the repeated test passes.

A backup process with repeated unreviewed failures must be treated as an active
operational risk.

#### Security requirements

The backup process must:

- use least-privilege access where practical;
- protect external backup storage from unauthorised access;
- avoid public exposure of database dumps;
- avoid plaintext secret storage;
- protect backup encryption keys separately from encrypted backup files;
- restrict file permissions;
- avoid including unnecessary personal or system data;
- document who or what can access the backups.

Encrypted backups are required when the selected external storage is not fully
trusted or is accessible outside the private environment.

Encryption must not create a single unrecoverable dependency. The decryption
method and key-recovery process must be documented securely.

#### Alternatives considered

##### Database backup only

Advantages:

- simplest process;
- small backup size;
- easy automation with `pg_dump`.

Disadvantages:

- does not protect locally stored images;
- does not preserve required deployment configuration;
- cannot recover the complete application state.

##### Full disk image only

Advantages:

- captures the complete device state;
- potentially simple full-device replacement.

Disadvantages:

- large backup size;
- slower creation and restoration;
- less portable across hardware and software versions;
- difficult to validate individual database contents;
- may capture unnecessary or sensitive system data.

##### Filesystem copy of the live PostgreSQL data directory

Advantages:

- potentially fast;
- preserves physical database files.

Disadvantages:

- unsafe without correct PostgreSQL consistency controls;
- tied to PostgreSQL version and platform;
- less portable than logical backups;
- easier to misuse during a live copy.

##### Logical database backup plus file-level backup

Advantages:

- portable PostgreSQL recovery;
- explicit coverage of images and configuration;
- simple enough for the MVP;
- easy to validate in a clean environment;
- compatible with Docker-based deployment.

Disadvantages:

- requires coordination between multiple backup components;
- requires manifests or timestamps to identify matching recovery sets;
- restore procedure is longer than a single-file device image;
- secret recovery remains a separate responsibility.

#### Consequences

Positive:

- the complete MVP state can be recovered;
- wishlist and imported catalogue data receive explicit protection;
- image storage is included in recovery planning;
- same-device backups are not mistaken for disaster recovery;
- backup success and restore success remain separate validation states;
- the process remains compatible with the proposed Docker and PostgreSQL stack;
- recovery evidence supports milestone and portfolio validation.

Negative:

- external backup storage is required;
- multiple backup components must be coordinated;
- retention consumes additional storage;
- restore exercises require time and a clean test environment;
- secret recovery requires a separate secure process;
- backup monitoring and failure review add operational work.

#### Validation

Validate this decision during `M2 — Infrastructure`.

The validation must include:

1. Create a PostgreSQL backup with `pg_dump`.
2. Create a file backup containing the required images and configuration.
3. Copy or write the recovery set to a location outside the Raspberry Pi SSD.
4. Generate or record checksums.
5. Prepare a clean restore environment.
6. Restore PostgreSQL.
7. Restore images and configuration.
8. Recreate or retrieve secrets through the documented secure process.
9. Start the restored services.
10. Confirm expected catalogue and wishlist data.
11. Confirm wishlist quantity and notes are preserved.
12. Confirm image references resolve.
13. Confirm the application can use the restored database.
14. Confirm PostgreSQL remains unexposed to the public internet.
15. Record restore duration and observed problems.
16. Confirm retention cleanup does not delete the latest valid recovery set.
17. Confirm backup evidence contains no secrets.

#### Follow-up

- Select and document the external backup location.
- Define the exact backup schedule on the Raspberry Pi.
- Define the physical directory layout for backup files.
- Implement reusable backup and restore scripts.
- Add backup manifests and checksums.
- Define log review and failure-notification behaviour.
- Document the secret recovery method.
- Perform and record the first clean restore test.
- Update `PROJECT.md`, `ROADMAP.md`, `STACK.md`, and `CHANGELOG.md` after
  implementation and validation.
- Accept or revise this ADR after the first complete restore test.

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

No additional ADRs are currently scheduled.
