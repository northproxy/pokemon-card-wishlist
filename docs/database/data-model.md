# PostgreSQL Data Model

## Status

- Document status: Implemented and locally validated
- Milestone: `M3 — Data model`
- Implementation status: Physical PostgreSQL schema implemented locally
- Migration status: `17` dbmate migrations applied and rollback-validated locally
- Detailed data dictionary coverage: `21` of `21` initial tables
- First implementation target: Primal Clash
- Catalogue source set: `xy5`
- Cardmarket expansion: `1585`

This document defines the implemented physical table responsibilities, ownership boundaries, relationships, uniqueness rules, and lifecycle expectations for the MVP PostgreSQL data model.

It includes the implemented columns, PostgreSQL data types, constraints, indexes, and lifecycle rules for all `21` initial tables.

The physical PostgreSQL schema described by this document has been implemented through `17` incremental dbmate migrations. All `21` project tables have been created in the local PostgreSQL environment, and implementation-specific constraints, foreign keys, indexes, rollback paths, and schema-wide validation have been exercised locally.

This status does not mean that production data import, Primal Clash fixture loading, repeat-import behaviour, runtime pricing, or the wishlist application workflow have been validated. Those remain later milestone work.

## Purpose

The data model must support:

- canonical Pokemon card catalogue records;
- separate editions and language or finish variants;
- independent Cardmarket market products;
- confirmed mappings at the most specific evidence-supported target level;
- append-only market price snapshots;
- an informational canonical-card `From` price;
- a persistent single-user wishlist;
- repeatable and reviewable imports;
- validated transactional production merges;
- rejected and unresolved source-record handling;
- preservation of source evidence;
- prevention of uncontrolled duplicates;
- preservation of wishlist data during catalogue imports.

## Scope

The first implemented and validated vertical slice is Primal Clash.

The initial data model must support:

- `164` canonical cards;
- `167` directly evidenced Cardmarket listing mappings;
- `4` excluded Online Code Card products;
- `6` `unmatched_duplicate_candidate` Cardmarket products;
- English and German market scope;
- edition and finish concepts where supported by evidence;
- imported Cardmarket price snapshots;
- a canonical-card wishlist;
- repeat-import and rollback validation.

The physical model must remain usable for later supported expansions without redefining canonical card or market-product identity.

The validated Primal Clash fixture confirms direct canonical-card-to-market-product relationships and preserves edition codes where available. It does not by itself prove that every confirmed mapping identifies a complete language and finish variant. The physical model must therefore represent the most specific target level supported by the available evidence without inventing missing edition, language, or finish values.

## Accepted decision basis

The model implements the following accepted boundaries:

- a canonical card is separate from a Cardmarket product;
- imported external entities use source-scoped identifiers;
- the conceptual hierarchy is `canonical card → edition → variant → market product`;
- edition, language, and finish are separate concepts;
- the initial wishlist references the canonical card;
- repeated imports use staging followed by a validated transactional merge;
- rejected and unresolved records remain explicit and reviewable;
- unresolved mappings do not participate in canonical-card pricing;
- market price snapshots remain attached to market products;
- the canonical-card price is derived from eligible linked Cardmarket prices;
- duplicate-like unlisted Cardmarket products remain preserved as `unmatched_duplicate_candidate`.

## Design principles

- Keep source data, normalized production data, staging data, and user-generated data separate.
- Preserve source-scoped identifiers for every imported external entity.
- Use internal surrogate identifiers for relationships where practical.
- Do not use market-product identifiers as canonical card identifiers.
- Do not silently create editions, variants, or mappings from insufficient evidence.
- Represent a confirmed market-product relationship at the most specific target level supported by evidence.
- Do not require variant-level confirmation when only card-level or edition-level evidence exists.
- Do not physically delete imported entities during normal repeated imports.
- Keep market price history append-only.
- Keep wishlist data outside the catalogue import ownership boundary.
- Preserve import and mapping evidence after production changes.
- Distinguish current accepted state from per-import observations and historical transitions.
- Use the smallest physical structure that still satisfies the accepted ADRs.
- Do not describe proposed structures as implemented or validated.

## Ownership boundaries

### Import-owned production data

The import process owns source-derived fields in:

- `expansions`;
- `expansion_source_identifiers`;
- `cards`;
- `market_products`.

The mapping process owns evidence-derived fields in:

- `card_editions`;
- `card_variants`;
- `card_market_product_mappings`;
- `card_market_mapping_cases`.

The import and mapping processes may update only explicitly defined owned fields.

They must not update user-generated wishlist fields.

### Append-only market and audit data

The following data is immutable after insertion and remains append-only across completed runs:

- `market_price_snapshots`;
- `import_record_outcomes`;
- `mapping_case_observations`;
- `mapping_status_history`;
- `rejected_source_records`;
- `rejected_source_record_reasons`.

An `import_runs` row remains mutable while its run is active. After the run reaches a terminal state, it must not be changed except through an explicitly documented administrative correction.

Corrections must be represented by new observations, outcomes, or status-history records rather than destructive rewriting of completed evidence.

### User-owned data

The user owns:

- wishlist membership;
- wanted quantity;
- wishlist notes;
- future edition or variant preferences.

For the MVP, these values are stored only in `wishlist_items`.

### Temporary staging data

Staging tables contain normalized source records that have not yet been accepted into production.

Staging tables:

- are not used as the catalogue source of truth;
- are not used by the wishlist;
- are not used directly by the canonical-card price query;
- may be cleaned according to a documented retention policy;
- must remain available long enough to investigate failed imports.

### Review data

Review structures preserve:

- rejected source records;
- mapping classifications;
- candidate targets;
- repeated observations;
- accepted status transitions;
- manual resolutions.

Review data must not be replaced by free-text notes alone.

## Entity overview

```text
expansions
    |
    |-- expansion_source_identifiers
    |
    |-- cards
            |
            |-- card_editions
                    |
                    |-- card_variants

market_products
    |
    |-- market_price_snapshots
    |
    |-- card_market_mapping_cases
            |
            |-- mapping_case_observations
            |
            |-- mapping_candidates
            |
            |-- mapping_status_history
            |
            |-- card_market_product_mappings

cards
    |
    |-- wishlist_items

import_runs
    |
    |-- staging_cards
    |
    |-- staging_market_products
    |
    |-- staging_market_prices
    |
    |-- staging_market_mappings
    |
    |-- import_record_outcomes
    |
    |-- rejected_source_records
            |
            |-- rejected_source_record_reasons
```

## Physical table inventory

### Production catalogue

- `expansions`
- `expansion_source_identifiers`
- `cards`
- `card_editions`
- `card_variants`

### Market data

- `market_products`
- `card_market_product_mappings`
- `market_price_snapshots`

### User-owned data

- `wishlist_items`

### Import control

- `import_runs`
- `staging_cards`
- `staging_market_products`
- `staging_market_prices`
- `staging_market_mappings`
- `import_record_outcomes`

### Review and unresolved records

- `rejected_source_records`
- `rejected_source_record_reasons`
- `card_market_mapping_cases`
- `mapping_case_observations`
- `mapping_candidates`
- `mapping_status_history`

The proposed initial model contains `21` physical tables.

## Production catalogue tables

### `expansions`

#### Purpose

Store one internal normalized card expansion.

An expansion represents one catalogue release or set independent from any identifier assigned by an external source system.

For Primal Clash, one internal expansion is associated with at least:

- Pokemon TCG Data set ID `xy5`;
- Cardmarket expansion ID `1585`.

An expansion is not:

- a source-specific expansion record;
- a canonical card;
- a market product;
- an import run;
- a wishlist item.

External source identities belong to `expansion_source_identifiers`.

#### Ownership

- Data owner: catalogue import process.
- User editing: not allowed through the wishlist workflow.
- Source-derived display fields: import-owned.
- Normal import deletion: not allowed.
- Retirement: allowed only through explicit source evidence or an approved reviewed decision.
- Source identifiers: not stored directly in this table.
- Mapping and market-price data: not stored in this table.

#### Columns

| Column          | PostgreSQL type                | Nullable | Default                    | Ownership                 | Description                                                                     |
| --------------- | ------------------------------ | -------: | -------------------------- | ------------------------- | ------------------------------------------------------------------------------- |
| `expansion_id`  | `bigint` generated as identity |       No | Generated                  | Database                  | Internal surrogate primary key for the normalized expansion.                    |
| `expansion_key` | `text`                         |       No | None                       | Import-owned identity     | Project-controlled stable technical key for the internal expansion.             |
| `name`          | `text`                         |       No | None                       | Import-owned display      | Preferred human-readable expansion name.                                        |
| `series_name`   | `text`                         |      Yes | `null`                     | Import-owned display      | Human-readable series or era name when available, for example `XY`.             |
| `printed_total` | `integer`                      |      Yes | `null`                     | Import-owned source value | Printed set size when explicitly supplied by the accepted catalogue source.     |
| `total`         | `integer`                      |      Yes | `null`                     | Import-owned source value | Total known set size when explicitly supplied by the accepted catalogue source. |
| `release_date`  | `date`                         |      Yes | `null`                     | Import-owned source value | Expansion release date when provided by accepted source evidence.               |
| `symbol_url`    | `text`                         |      Yes | `null`                     | Import-owned source value | Source reference or URL for the expansion symbol image when available.          |
| `logo_url`      | `text`                         |      Yes | `null`                     | Import-owned source value | Source reference or URL for the expansion logo image when available.            |
| `is_active`     | `boolean`                      |       No | `true`                     | Import-owned lifecycle    | Indicates whether the expansion is included in ordinary active catalogue views. |
| `retired_at`    | `timestamp with time zone`     |      Yes | `null`                     | Import-owned lifecycle    | Timestamp when the expansion was explicitly retired. Null while active.         |
| `created_at`    | `timestamp with time zone`     |       No | Current database timestamp | Database                  | Timestamp when the production expansion row was created.                        |
| `updated_at`    | `timestamp with time zone`     |       No | Current database timestamp | Database                  | Timestamp of the latest actual change to an import-owned or lifecycle field.    |

#### Primary key

```text
expansion_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- Pokemon TCG Data set ID;
- Cardmarket expansion ID;
- expansion display name;
- import-run ID.

#### Internal expansion key

`expansion_key` provides a stable project-controlled identifier.

Example:

```text
primal_clash
```

Required uniqueness:

```text
UNIQUE (expansion_key)
```

The key must:

- remain stable after creation;
- contain non-whitespace text;
- use lowercase controlled formatting;
- use a deterministic separator convention;
- not depend on one external source;
- not be changed by an ordinary repeated import.

A display-name correction must not change `expansion_key`.

#### Why an internal key is required

External identifiers remain source-scoped.

For example:

```text
pokemon_tcg_data / xy5
```

and:

```text
cardmarket / 1585
```

identify the same internal expansion but are not interchangeable identifiers.

Using one external ID as the internal identity would make the model dependent on that source and complicate later source integration.

#### Required constraints

##### Non-empty expansion key

Conceptual rule:

```text
trim(expansion_key) <> ''
```

##### Non-empty name

Conceptual rule:

```text
trim(name) <> ''
```

##### Optional text consistency

When present, the following values must contain non-whitespace text:

- `series_name`;
- `symbol_url`;
- `logo_url`.

Empty source values should normally be normalized to null.

##### Printed total

When present:

```text
printed_total >= 0
```

##### Total

When present:

```text
total >= 0
```

##### Set-size consistency

When both values are present, the proposed rule is:

```text
printed_total <= total
```

This assumes `total` includes the printed set plus any additional officially represented cards.

The rule must be validated against representative source data before becoming a physical database constraint.

##### Lifecycle consistency

When:

```text
is_active = true
```

then:

```text
retired_at is null
```

When:

```text
is_active = false
```

then:

```text
retired_at is not null
```

#### Source-identifier boundary

External identifiers do not belong directly in `expansions`.

The following values belong to `expansion_source_identifiers`:

- source system;
- source expansion ID;
- source-specific display name;
- source-specific URL;
- source-specific metadata required for identity resolution.

The internal expansion remains valid even when:

- one source identifier is unavailable;
- a new source is added;
- one source changes its display name;
- one source no longer publishes the expansion.

#### Expansion-name semantics

`name` is the preferred project display name.

For the Primal Clash expansion:

```text
name = Primal Clash
```

The value should come from accepted catalogue evidence or an approved reviewed correction.

The import process must not use `name` as the only matching key between sources.

Matching names such as:

```text
Primal Clash
```

do not by themselves prove that two source records identify the same expansion.

Cross-source relationships must be established explicitly through `expansion_source_identifiers` and validated source evidence.

#### Series name

`series_name` stores a human-readable broader series or era when the source provides it.

Example:

```text
series_name = XY
```

It is descriptive and must not be used as expansion identity.

Several expansions may share the same series name.

A generic `series` table is deferred until application requirements establish a need for:

- series-level navigation;
- series metadata;
- ordering;
- source identifiers;
- lifecycle management.

#### Set-size fields

##### `printed_total`

Stores the source-provided printed set size.

For example, it may represent the official numbered card count.

It must not be calculated by counting imported production cards unless the source contract explicitly defines it that way.

##### `total`

Stores the source-provided total set size when available.

It may include cards beyond the printed numbered range according to source semantics.

The importer must preserve source meaning and must not silently redefine either value.

##### Card-count reconciliation

Production card count and source set-size fields are related but not identical concepts.

For example:

```text
count(cards in expansion)
```

may differ from:

```text
printed_total
```

or:

```text
total
```

because of:

- secret cards;
- source omissions;
- source scope;
- future corrections;
- deliberately excluded records.

Run-level validation must document which count is expected for the accepted fixture.

For Primal Clash, the accepted canonical fixture contains:

```text
164 canonical cards
```

This does not automatically establish that either stored set-size field must equal `164`.

#### Release date

`release_date` stores the accepted source release date when available.

Normalization rules:

- parse only supported source date formats;
- store the calendar date without an invented time;
- preserve null when unavailable;
- do not infer from import time;
- do not infer from Cardmarket product creation timestamps.

A corrected source release date may update the field through a validated import.

#### Image references

`symbol_url` and `logo_url` may initially store source image references.

They must not contain:

- credentials;
- expiring authenticated URLs when a durable source exists;
- local temporary staging paths.

The first schema does not require separate managed expansion-image records.

A separate image structure may be introduced later if implementation requires:

- local file ownership;
- checksums;
- download status;
- multiple resolutions;
- replacement history.

#### Relationships

```text
expansions
    1 → many expansion_source_identifiers
```

```text
expansions
    1 → many cards
```

```text
expansions
    1 → zero or many market_products
```

The `market_products.expansion_id` relationship is optional because a market product may be preserved before its cross-source expansion relationship is confirmed.

#### Foreign-key behavior

From `expansion_source_identifiers`:

```text
expansion_source_identifiers.expansion_id
→ expansions.expansion_id
```

Recommended behavior:

```text
ON DELETE RESTRICT
```

From `cards`:

```text
cards.expansion_id
→ expansions.expansion_id
```

Recommended behavior:

```text
ON DELETE RESTRICT
```

From `market_products`:

```text
market_products.expansion_id
→ expansions.expansion_id
```

Recommended behavior:

```text
ON DELETE RESTRICT
```

Normal lifecycle management must use `is_active` and `retired_at` rather than physical deletion.

#### Import comparison fields

Repeated expansion imports compare normalized values for:

- `name`;
- `series_name`;
- `printed_total`;
- `total`;
- `release_date`;
- `symbol_url`;
- `logo_url`;
- `is_active`;
- `retired_at`.

The following are not ordinary update fields:

- `expansion_id`;
- `expansion_key`;
- `created_at`;
- `updated_at`.

Changing `expansion_key` would change internal identity and is not permitted through an ordinary import update.

#### Production resolution

A source expansion resolves the internal expansion through:

```text
(source_system, source_expansion_id)
```

in:

```text
expansion_source_identifiers
```

The importer must not resolve an existing expansion through:

- display name alone;
- series name;
- release date alone;
- card overlap alone;
- numeric similarity between source identifiers;
- first available expansion.

When a source identifier does not exist:

- create a new internal expansion only when the source record represents a genuinely new expansion;
- or attach the identifier to an existing expansion only when cross-source equivalence is confirmed.

#### Merge behavior

##### Bootstrapped

For the first Primal Clash implementation, create the expansion through controlled bootstrap or seed logic when:

- the accepted internal expansion identity is defined;
- a deterministic `expansion_key` is assigned;
- no conflicting internal key exists;
- the accepted source identifiers are available;
- the bootstrap validation has passed.

Create the expansion and its accepted `expansion_source_identifiers` rows atomically.

A general staged expansion-import path is deferred until multi-expansion ingestion requires it.

##### Updated

Update an existing expansion only when accepted import-owned values differ.

The update must preserve:

- `expansion_id`;
- `expansion_key`;
- cards;
- market-product relationships;
- source identifiers;
- wishlist relationships through cards;
- `created_at`.

An actual update changes `updated_at`.

##### Unchanged

When compared values are equivalent:

- do not execute an unnecessary update;
- preserve `updated_at`;
- record `unchanged` through `import_record_outcomes` when expansion outcomes are reported.

##### Missing

When an expansion is absent from a later authoritative source scope:

- record missing evidence where the scope supports it;
- preserve the expansion;
- preserve source identifiers;
- preserve cards;
- preserve market products;
- preserve wishlist data;
- preserve lifecycle state.

One missing observation must not retire the expansion.

##### Retired

Retire an expansion only through:

- an explicit source lifecycle signal; or
- an approved reviewed decision.

Retirement sets:

```text
is_active = false
```

and:

```text
retired_at = retirement timestamp
```

Retirement must not physically delete dependent catalogue or market data.

##### Reactivated

A retired expansion may be reactivated through sufficient source evidence or an approved reviewed decision.

Reactivation sets:

```text
is_active = true
```

and:

```text
retired_at = null
```

The transition must remain traceable through import outcomes or later lifecycle history if introduced.

##### Conflict

A conflict exists when:

- one source-scoped identifier already belongs to another expansion;
- the proposed `expansion_key` is already used by an incompatible expansion;
- a normal import attempts to merge two existing expansions;
- source evidence for one identity points to incompatible internal expansions;
- an expansion would need to be reassigned through weak name-based evidence.

A conflict must:

- prevent automatic merge;
- preserve existing production state;
- preserve source and staging evidence;
- produce a conflict outcome or rejection according to the processing boundary;
- not silently combine expansions.

#### Cross-source expansion matching

Cross-source equivalence must be based on explicit accepted evidence.

For Primal Clash, the model accepts:

```text
pokemon_tcg_data / xy5
```

and:

```text
cardmarket / 1585
```

as identifiers of the same internal expansion.

The evidence establishing that relationship must remain documented in:

- project fixtures;
- discovery output;
- import configuration;
- or another durable review source.

The `expansions` row itself does not need to duplicate that evidence.

#### Primal Clash example

A conceptual production row may contain:

| Column          | Example value                                |
| --------------- | -------------------------------------------- |
| `expansion_id`  | Database-generated value                     |
| `expansion_key` | `primal_clash`                               |
| `name`          | `Primal Clash`                               |
| `series_name`   | `XY` or `null` according to accepted fixture |
| `printed_total` | Accepted source value or `null`              |
| `total`         | Accepted source value or `null`              |
| `release_date`  | Accepted source date or `null`               |
| `symbol_url`    | Accepted source reference or `null`          |
| `logo_url`      | Accepted source reference or `null`          |
| `is_active`     | `true`                                       |
| `retired_at`    | `null`                                       |
| `created_at`    | Database-generated timestamp                 |
| `updated_at`    | Database-generated timestamp                 |

Its source identities are stored separately:

```text
pokemon_tcg_data / xy5
cardmarket / 1585
```

#### Index candidates

Likely access paths include:

- lookup by `expansion_key`;
- active expansion listing;
- sorting by release date;
- joining source identifiers;
- joining cards;
- joining market products.

Potential supporting indexes include:

```text
(release_date)
```

and:

```text
(is_active, release_date)
```

The unique constraint on `expansion_key` provides direct internal-key lookup.

Final indexes must be selected after catalogue and NocoDB query patterns are reviewed.

#### Validation requirements

The first schema validation must confirm:

- one internal Primal Clash expansion can be created;
- `expansion_key` is unique;
- blank expansion keys are rejected;
- blank names are rejected;
- one expansion can have multiple source identifiers;
- `pokemon_tcg_data / xy5` resolves to Primal Clash;
- `cardmarket / 1585` resolves to the same expansion;
- source identifiers are not stored directly in the expansion row;
- multiple cards can reference one expansion;
- market products may reference the expansion when cross-source resolution is confirmed;
- an unresolved market expansion relationship does not require creation of a duplicate expansion;
- repeated identical imports create no duplicate expansion;
- unchanged imports preserve `updated_at`;
- a corrected display field updates the existing expansion rather than creating a new one;
- one missing observation does not retire or delete the expansion;
- retirement preserves cards, source identifiers, market products, and wishlist data;
- deleting a referenced expansion is restricted;
- conflicting source identity does not merge expansions automatically;
- a failed production transaction leaves the existing expansion unchanged.

#### Deferred fields

The following fields are not included in the first version:

- source-specific expansion IDs;
- source-specific names;
- source-specific URLs;
- expansion description;
- abbreviation;
- series foreign key;
- release region;
- rotation or legality metadata;
- display ordering;
- card-count cache;
- canonical-price summary;
- first observed import run;
- latest observed import run;
- last missing import run;
- retirement reason;
- lifecycle history;
- administrative notes;
- local symbol path;
- local logo path;
- image checksums.

Source-specific identity belongs to `expansion_source_identifiers`.

#### Open questions

- What exact normalization rule should create `expansion_key`?
- Should `expansion_key` be manually assigned or derived once from an accepted name?
- Are `printed_total` and `total` both required for the first Primal Clash fixture?
- Does the accepted source define `total` consistently enough for the constraint `printed_total <= total`?
- Should `series_name` remain plain text or be deferred until a series model exists?
- Should symbol and logo references remain URLs or later become locally managed image records?
- Should the first schema restrict expansion lifecycle changes to manual review?
- Should `updated_at` be maintained by explicit merge logic or a narrowly defined database trigger?

### `expansion_source_identifiers`

#### Purpose

Store one source-scoped external identifier for one internal normalized expansion.

The table separates internal expansion identity from identifiers assigned by individual source systems.

For Primal Clash, the same internal expansion is associated with at least:

- `pokemon_tcg_data / xy5`;
- `cardmarket / 1585`.

A source identifier row is not:

- the internal expansion itself;
- a canonical card;
- a market product;
- an import run;
- a generic source-system registry.

#### Ownership

- Data owner: catalogue and source-integration import process.
- User editing: not allowed through the wishlist workflow.
- Normal import deletion: not allowed.
- Source-identity reassignment: not allowed through an ordinary import.
- Source metadata updates: allowed only when supported by accepted source evidence.
- Cross-source equivalence: represented by several rows pointing to the same `expansion_id`.

#### Columns

| Column                           | PostgreSQL type                | Nullable | Default                    | Ownership                    | Description                                                                            |
| -------------------------------- | ------------------------------ | -------: | -------------------------- | ---------------------------- | -------------------------------------------------------------------------------------- |
| `expansion_source_identifier_id` | `bigint` generated as identity |       No | Generated                  | Database                     | Internal surrogate primary key for the source identifier row.                          |
| `expansion_id`                   | `bigint`                       |       No | None                       | Import-owned relationship    | References the internal normalized expansion represented by this source identity.      |
| `source_system`                  | `text`                         |       No | None                       | Import-owned identity        | Controlled external source identifier, for example `pokemon_tcg_data` or `cardmarket`. |
| `source_expansion_id`            | `text`                         |       No | None                       | Import-owned identity        | Stable expansion identifier within the source system, for example `xy5` or `1585`.     |
| `source_name`                    | `text`                         |      Yes | `null`                     | Import-owned source metadata | Source-specific expansion display name when available.                                 |
| `source_url`                     | `text`                         |      Yes | `null`                     | Import-owned source metadata | Durable source-specific expansion URL or reference when available.                     |
| `source_payload`                 | `jsonb`                        |      Yes | `null`                     | Import-owned evidence        | Optional structured source metadata required for source reconciliation or review.      |
| `is_active`                      | `boolean`                      |       No | `true`                     | Import-owned lifecycle       | Indicates whether the source identifier remains active for normal source resolution.   |
| `retired_at`                     | `timestamp with time zone`     |      Yes | `null`                     | Import-owned lifecycle       | Timestamp when the source identifier was explicitly retired. Null while active.        |
| `created_at`                     | `timestamp with time zone`     |       No | Current database timestamp | Database                     | Timestamp when the source identifier row was created.                                  |
| `updated_at`                     | `timestamp with time zone`     |       No | Current database timestamp | Database                     | Timestamp of the latest actual change to source metadata or lifecycle state.           |

#### Primary key

```text
expansion_source_identifier_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- source expansion ID;
- internal expansion ID;
- source-system name;
- import-run ID.

#### Foreign key

```text
expansion_id
→ expansions.expansion_id
```

Required behavior:

- the referenced expansion must already exist;
- deleting an expansion with source identifiers must be restricted;
- deletion must not cascade from `expansions`;
- retiring an expansion must preserve all source identifiers.

Recommended behavior:

```text
ON DELETE RESTRICT
```

#### Required business identity

```text
UNIQUE (
    source_system,
    source_expansion_id
)
```

One source-scoped expansion identifier must resolve to at most one internal expansion.

Examples:

```text
pokemon_tcg_data / xy5
```

and:

```text
cardmarket / 1585
```

may both point to the same `expansion_id`.

The same literal identifier may exist in different source systems.

For example:

```text
source_a / 1585
```

and:

```text
source_b / 1585
```

are not considered the same source identity.

#### Required constraints

##### Non-empty source system

```text
trim(source_system) <> ''
```

##### Non-empty source expansion ID

```text
trim(source_expansion_id) <> ''
```

##### Optional text consistency

When present, the following values must contain non-whitespace text:

- `source_name`;
- `source_url`.

Empty source values should normally be normalized to null.

##### Lifecycle consistency

When:

```text
is_active = true
```

then:

```text
retired_at is null
```

When:

```text
is_active = false
```

then:

```text
retired_at is not null
```

#### Source-system values

Initial controlled values include:

- `pokemon_tcg_data`;
- `cardmarket`.

The exact list should remain aligned with:

- import-run source systems;
- staging source-system values;
- market-product source identities;
- mapping evidence.

A source-system value must be:

- stable;
- lowercase;
- technical rather than human-readable;
- reused consistently across all tables.

For example:

```text
pokemon_tcg_data
```

must not also appear elsewhere as:

```text
Pokemon TCG Data
```

or:

```text
pokemontcg
```

unless an explicit aliasing mechanism is introduced.

#### Source expansion ID

`source_expansion_id` is stored as `text`.

Reasons:

- external identifiers are opaque source values;
- numeric-looking IDs are not used for arithmetic;
- one source may use alphanumeric identifiers;
- text avoids source-specific type assumptions.

Examples:

```text
xy5
```

```text
1585
```

The importer must:

- trim surrounding whitespace;
- preserve source-significant case and punctuation;
- not convert numeric-looking identifiers to integers;
- not derive missing IDs from source names;
- not replace the value with `expansion_id`.

#### Source name

`source_name` preserves the source-specific display name.

Examples may include:

```text
Primal Clash
```

or a source-localized or differently formatted equivalent.

The value is descriptive.

It must not be used as the source identity or as the only basis for cross-source matching.

A source-name correction may update the row without changing:

- `source_system`;
- `source_expansion_id`;
- `expansion_id`.

#### Source URL

`source_url` may store a durable source-specific expansion location.

It must not contain:

- credentials;
- session tokens;
- short-lived signed parameters when a stable URL exists;
- temporary local paths.

The URL is supporting metadata and not part of the business identity.

#### Source payload

`source_payload` may preserve structured source-specific expansion metadata that does not belong in the normalized `expansions` row.

Possible examples include:

- source-specific release metadata;
- source-specific category values;
- source labels;
- source ordering;
- reconciliation evidence;
- source relationship details.

The payload should be included only when a real import or review requirement exists.

It must not become an undocumented substitute for normalized columns.

The importer must not depend on arbitrary JSON keys without a documented schema or rule.

#### Cross-source equivalence

Several source identifier rows may reference one internal expansion.

For Primal Clash:

```text
expansion_id = internal Primal Clash ID
source_system = pokemon_tcg_data
source_expansion_id = xy5
```

and:

```text
expansion_id = internal Primal Clash ID
source_system = cardmarket
source_expansion_id = 1585
```

This relationship establishes that both source identities resolve to the same normalized expansion.

The table does not explain why the equivalence was accepted.

Supporting evidence remains in:

- validated discovery fixtures;
- source configuration;
- import evidence;
- reviewed project documentation.

#### Identity immutability

The following fields form the external identity and must not be changed through an ordinary update:

- `source_system`;
- `source_expansion_id`.

Changing either field creates a different source identity.

If a source corrects an identifier:

- preserve the old identifier;
- retire it if appropriate;
- insert the corrected identifier as a new row;
- attach both to the same expansion only when equivalence is confirmed.

`expansion_id` must also not be reassigned through a normal import.

Reassignment would mean one source identity changed its internal meaning and must be treated as a conflict or explicit administrative correction.

#### Production resolution

Source expansion resolution uses:

```text
(source_system, source_expansion_id)
```

to find:

```text
expansion_id
```

This path is used by:

- catalogue-card imports;
- market-product imports;
- mapping imports;
- validation logic;
- expansion reconciliation.

Example:

```text
pokemon_tcg_data / xy5
→ internal Primal Clash expansion
```

Example:

```text
cardmarket / 1585
→ internal Primal Clash expansion
```

The importer must not fall back silently to:

- source name matching;
- release-date matching;
- card-name overlap;
- numeric proximity;
- first available expansion.

#### Insert behavior

Create a source identifier when:

- the source system is supported;
- the source expansion ID is valid;
- the target internal expansion exists or is created atomically;
- the source identity does not already exist;
- cross-source equivalence has been validated where applicable.

For a new internal expansion, recommended transaction order:

1. insert `expansions`;
2. insert its first `expansion_source_identifiers` row;
3. insert additional confirmed source identifiers;
4. commit.

The expansion must not remain permanently without any source identity unless an explicit manually managed expansion workflow is approved.

#### Update behavior

Mutable fields may include:

- `source_name`;
- `source_url`;
- `source_payload`;
- `is_active`;
- `retired_at`.

An update must preserve:

- `expansion_source_identifier_id`;
- `expansion_id`;
- `source_system`;
- `source_expansion_id`;
- `created_at`.

An actual value change updates `updated_at`.

An unchanged repeated import must preserve `updated_at`.

#### Repeated import behavior

When the same source identity appears again:

- resolve the existing row through `(source_system, source_expansion_id)`;
- confirm that it still points to the expected expansion;
- update only changed source metadata;
- do not insert a duplicate;
- do not reassign the source identity.

If the repeated source identity resolves to another proposed expansion, the importer must report a conflict.

#### Missing behavior

If a source identifier is absent from a later authoritative source scope:

- preserve the row;
- preserve its relationship to the internal expansion;
- preserve lifecycle state;
- record missing evidence through import outcomes when applicable.

One missing observation must not automatically retire the source identifier.

#### Retirement

Retire a source identifier only through:

- an explicit source signal;
- a validated source migration;
- an approved reviewed decision.

Retirement sets:

```text
is_active = false
```

and:

```text
retired_at = retirement timestamp
```

A retired source identifier:

- remains resolvable for historical evidence;
- remains linked to its expansion;
- must not be reused for another expansion;
- may be excluded from ordinary active source-resolution paths.

#### Reactivation

A retired source identifier may be reactivated when sufficient evidence confirms that it is active again.

Reactivation sets:

```text
is_active = true
```

and:

```text
retired_at = null
```

The identity remains unchanged.

#### Conflict behavior

A conflict exists when:

- the same `(source_system, source_expansion_id)` already belongs to another expansion;
- an import attempts to reassign an existing source identity;
- two source records in one run claim the same source identity for different expansions;
- weak display-name evidence conflicts with an established source mapping;
- a retired identifier is proposed for reuse by another expansion.

A conflict must:

- prevent automatic reassignment;
- preserve the existing relationship;
- preserve staging and source evidence;
- create a conflict outcome or fail validation;
- require explicit reviewed correction.

#### Source name and internal name boundary

The following values may differ:

```text
expansions.name
```

and:

```text
expansion_source_identifiers.source_name
```

`expansions.name` is the preferred normalized project display value.

`source_name` preserves how one source represents the expansion.

A source-specific name update must not automatically overwrite the normalized internal name unless the import rule explicitly identifies that source as authoritative for the normalized field.

#### Relationships

```text
expansions
    1 → many expansion_source_identifiers
```

Each source identifier belongs to exactly one expansion.

One expansion may have:

- one catalogue-source identifier;
- one market-source identifier;
- several future source identifiers;
- retired historical identifiers.

#### Primal Clash example

First row:

| Column                           | Example value                       |
| -------------------------------- | ----------------------------------- |
| `expansion_source_identifier_id` | Database-generated value            |
| `expansion_id`                   | Internal Primal Clash expansion ID  |
| `source_system`                  | `pokemon_tcg_data`                  |
| `source_expansion_id`            | `xy5`                               |
| `source_name`                    | `Primal Clash`                      |
| `source_url`                     | Accepted source reference or `null` |
| `source_payload`                 | Source metadata or `null`           |
| `is_active`                      | `true`                              |
| `retired_at`                     | `null`                              |

Second row:

| Column                           | Example value                           |
| -------------------------------- | --------------------------------------- |
| `expansion_source_identifier_id` | Database-generated value                |
| `expansion_id`                   | Same internal Primal Clash expansion ID |
| `source_system`                  | `cardmarket`                            |
| `source_expansion_id`            | `1585`                                  |
| `source_name`                    | Source display value or `null`          |
| `source_url`                     | Accepted source reference or `null`     |
| `source_payload`                 | Source metadata or `null`               |
| `is_active`                      | `true`                                  |
| `retired_at`                     | `null`                                  |

#### Import comparison fields

Repeated imports compare normalized values for:

- `source_name`;
- `source_url`;
- `source_payload`;
- `is_active`;
- `retired_at`.

The following are not ordinary update fields:

- `expansion_source_identifier_id`;
- `expansion_id`;
- `source_system`;
- `source_expansion_id`;
- `created_at`;
- `updated_at`.

#### Index candidates

Likely access paths include:

- resolution by `(source_system, source_expansion_id)`;
- listing all identifiers for one expansion;
- active identifiers by source system;
- lookup by source name for review only;
- finding retired identifiers.

Potential supporting indexes include:

```text
(expansion_id)
```

```text
(source_system, is_active)
```

The required uniqueness constraint provides the primary source-resolution path.

Final indexes must be selected during migration and import-query design.

#### Validation requirements

The first schema validation must confirm:

- one expansion can have several source identifiers;
- `pokemon_tcg_data / xy5` can be stored;
- `cardmarket / 1585` can be stored;
- both resolve to the same internal Primal Clash expansion;
- `(source_system, source_expansion_id)` is unique;
- the same literal source ID may exist in another source system;
- blank source systems are rejected;
- blank source expansion IDs are rejected;
- numeric-looking source IDs remain text;
- source names are not used as identity;
- repeated identical imports create no duplicate rows;
- unchanged imports preserve `updated_at`;
- source metadata corrections update the existing row;
- one source identity cannot be reassigned automatically;
- missing observations do not delete or retire the row;
- retired identifiers remain preserved;
- retired identifiers cannot be reused for another expansion;
- deleting a referenced expansion is restricted;
- unresolved source identifiers prevent dependent production resolution;
- a failed production transaction leaves existing source relationships unchanged.

#### Deferred fields

The following fields are not included in the first version:

- source-system foreign key;
- source locale;
- source region;
- source release date;
- source series name;
- source ordering;
- source checksum;
- first observed import run;
- latest observed import run;
- last missing import run;
- retirement reason;
- identity-correction history;
- reviewed-by identifier;
- administrative notes;
- source evidence reference as a dedicated field.

These fields may be added only when import or review workflows establish a clear responsibility.

#### Open questions

- Should `source_payload` be included in the first schema or remain only in staging and import evidence?
- Should `source_name` be required for catalogue sources but optional for market sources?
- Should `source_url` be stored here or derived from source configuration?
- Should inactive source identifiers remain available for ordinary resolution or only historical resolution?
- Should `source_system` eventually reference a dedicated source registry?
- Should source-identity corrections require a dedicated history table?
- Should `updated_at` be maintained by explicit merge logic or a narrowly defined database trigger?

### `cards`

#### Purpose

Store one canonical set-specific card imported from an accepted catalogue source.

A canonical card represents one card identity within one normalized expansion.

Example source-scoped identity:

```text
pokemon_tcg_data / xy5-20
```

A canonical card is not:

- an abstract Pokemon character;
- an expansion;
- a card edition;
- a language or finish variant;
- a Cardmarket product;
- a market-price snapshot;
- a wishlist item.

Edition, language, finish, market-product, price, and wishlist concerns remain in separate tables.

#### Ownership

- Data owner: catalogue import process.
- User editing through the wishlist workflow: not allowed.
- Source-derived catalogue fields: import-owned.
- Wishlist fields: not stored in this table.
- Mapping fields: not stored in this table.
- Normal import deletion: not allowed.
- Retirement: allowed only through explicit source evidence or an approved reviewed decision.
- Identity reassignment: not allowed through an ordinary import.

#### Columns

| Column             | PostgreSQL type                | Nullable | Default                    | Ownership                 | Description                                                                  |
| ------------------ | ------------------------------ | -------: | -------------------------- | ------------------------- | ---------------------------------------------------------------------------- |
| `card_id`          | `bigint` generated as identity |       No | Generated                  | Database                  | Internal surrogate primary key for the canonical card.                       |
| `expansion_id`     | `bigint`                       |       No | None                       | Import-owned relationship | References the normalized expansion containing the card.                     |
| `source_system`    | `text`                         |       No | None                       | Import-owned identity     | Controlled catalogue source identifier, initially `pokemon_tcg_data`.        |
| `source_card_id`   | `text`                         |       No | None                       | Import-owned identity     | Stable card identifier within the source system, for example `xy5-20`.       |
| `collector_number` | `text`                         |       No | None                       | Import-owned source value | Collector number preserved as text.                                          |
| `name`             | `text`                         |       No | None                       | Import-owned display      | Preferred canonical card display name from the accepted catalogue source.    |
| `rarity`           | `text`                         |      Yes | `null`                     | Import-owned source value | Source-provided rarity when available.                                       |
| `image_small_url`  | `text`                         |      Yes | `null`                     | Import-owned source value | Small canonical-card image reference when available.                         |
| `image_large_url`  | `text`                         |      Yes | `null`                     | Import-owned source value | Large canonical-card image reference when available.                         |
| `is_active`        | `boolean`                      |       No | `true`                     | Import-owned lifecycle    | Indicates whether the card appears in ordinary active catalogue views.       |
| `retired_at`       | `timestamp with time zone`     |      Yes | `null`                     | Import-owned lifecycle    | Timestamp when the card was explicitly retired. Null while active.           |
| `created_at`       | `timestamp with time zone`     |       No | Current database timestamp | Database                  | Timestamp when the production card row was created.                          |
| `updated_at`       | `timestamp with time zone`     |       No | Current database timestamp | Database                  | Timestamp of the latest actual change to an import-owned or lifecycle field. |

#### Primary key

```text
card_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- source card ID;
- collector number;
- expansion ID;
- Cardmarket product ID;
- wishlist item ID.

#### Foreign key

```text
expansion_id
→ expansions.expansion_id
```

Required behavior:

- the referenced expansion must already exist;
- deleting an expansion with cards must be restricted;
- deletion must not cascade from `expansions` to `cards`;
- retiring an expansion must preserve all cards.

Recommended behavior:

```text
ON DELETE RESTRICT
```

#### Required business identity

```text
UNIQUE (
    source_system,
    source_card_id
)
```

One source-scoped card identifier must resolve to at most one canonical card.

For Primal Clash:

```text
pokemon_tcg_data / xy5-20
```

identifies one canonical card.

The same literal source card ID may exist in another source system without collision.

#### Required constraints

##### Non-empty source system

```text
trim(source_system) <> ''
```

##### Non-empty source card ID

```text
trim(source_card_id) <> ''
```

##### Non-empty collector number

```text
trim(collector_number) <> ''
```

##### Non-empty card name

```text
trim(name) <> ''
```

##### Optional text consistency

When present, the following values must contain non-whitespace text:

- `rarity`;
- `image_small_url`;
- `image_large_url`.

Empty source values should normally be normalized to null.

##### Lifecycle consistency

When:

```text
is_active = true
```

then:

```text
retired_at is null
```

When:

```text
is_active = false
```

then:

```text
retired_at is not null
```

#### Source system

Initial expected value:

```text
pokemon_tcg_data
```

The value must be:

- lowercase;
- stable;
- technical rather than human-readable;
- consistent with staging and import-run source-system values.

The same source must not appear under several uncontrolled aliases.

#### Source card ID

`source_card_id` is stored as `text`.

Reasons:

- source identifiers are opaque external values;
- alphanumeric IDs are supported;
- numeric interpretation is not required;
- text preserves the original source identity.

Example:

```text
xy5-20
```

The importer must:

- trim surrounding whitespace;
- preserve source-significant case and punctuation;
- not derive the value from collector number;
- not replace it with internal `card_id`;
- not reconstruct it from expansion and row order.

#### Collector number

`collector_number` remains text.

Examples may include:

```text
20
```

```text
20a
```

```text
XY123
```

Text storage avoids assumptions that all collector numbers are plain integers.

The collector number:

- supports display and filtering;
- may support future validation;
- is not the canonical business identity;
- must not replace `(source_system, source_card_id)`.

#### Collector-number uniqueness

A universal uniqueness constraint on:

```text
(expansion_id, collector_number)
```

is not approved yet.

Reasons:

- representative expansions have not yet been validated;
- alternate numbering formats may exist;
- source corrections may create temporary conflicts;
- suffixes and promotional numbering may require special treatment.

The first migration should not enforce this constraint unless the cross-table review and representative fixture validation approve it.

A non-unique index may still be useful for lookup and review.

#### Card name

`name` stores the preferred canonical display name.

For the Primal Clash example:

```text
name = Vulpix
```

The value may be updated when the accepted source corrects spelling or display formatting.

The card name must not be used as:

- source identity;
- cross-source mapping identity;
- edition identity;
- market-product identity.

Several cards may share the same name within or across expansions.

#### Rarity

`rarity` preserves the accepted source value when available.

It is descriptive and not part of card identity.

The importer should:

- trim surrounding whitespace;
- preserve source spelling and capitalization where practical;
- store null when unavailable;
- not invent a default rarity;
- not normalize into an uncontrolled project taxonomy without an approved rule.

A separate rarity lookup table is not required for the first schema version.

#### Image references

`image_small_url` and `image_large_url` may initially store canonical-card source image references.

The values must not contain:

- credentials;
- expiring authenticated parameters when durable URLs exist;
- temporary staging paths.

The image fields are descriptive and do not participate in card identity.

A separate `card_images` table remains deferred until local image management demonstrates a need for:

- several files per card;
- local file paths;
- checksums;
- download status;
- replacement history;
- multiple resolutions beyond the current pair.

#### Expansion consistency

The card's `expansion_id` must correspond to its accepted source expansion identity.

For Primal Clash:

```text
source_card_id = xy5-20
```

must resolve through the catalogue import scope to the internal expansion identified by:

```text
pokemon_tcg_data / xy5
```

in `expansion_source_identifiers`.

The importer must not assign the card to an expansion through:

- matching expansion names alone;
- collector-number range;
- source card ID prefix unless the source contract explicitly defines it;
- first available expansion;
- Cardmarket product data.

#### Production resolution

A staged card resolves production identity through:

```text
(source_system, source_card_id)
```

The source expansion resolves independently through:

```text
(source_system, source_expansion_id)
→ expansion_source_identifiers
→ expansions.expansion_id
```

Both resolutions must be valid before production merge.

A source card identity must not be reassigned to another expansion through an ordinary import.

Such a change is an identity conflict requiring explicit review.

#### Relationships

```text
expansions
    1 → many cards
```

```text
cards
    1 → zero or many card_editions
```

```text
cards
    1 → zero or one wishlist_items
```

```text
cards
    1 → zero or many card_market_product_mappings
```

A canonical card may be referenced by many historical or active market-product mappings.

#### Edition boundary

Edition data does not belong directly in `cards`.

The card row must not contain:

- source edition code;
- edition key;
- edition display name;
- language;
- finish.

Confirmed edition-level structures belong to `card_editions`.

A card-level confirmed mapping does not require an edition row.

#### Variant boundary

Language and finish do not belong directly in `cards`.

The card row must not contain:

- language code;
- finish code;
- finish detail;
- variant identity.

Confirmed variant-level structures belong to `card_variants`.

#### Market-product boundary

The card row must not contain:

- Cardmarket product ID;
- Cardmarket metaproduct ID;
- mapping status;
- confirmation scope;
- mapping method;
- market price.

These values belong to market, mapping, and price tables.

#### Wishlist boundary

The card row must not contain:

- wanted state;
- quantity;
- user notes;
- edition preference;
- variant preference.

The MVP wishlist relationship belongs to `wishlist_items`.

Catalogue imports must not mutate wishlist-owned data.

#### Import comparison fields

Repeated card imports compare normalized values for:

- resolved `expansion_id`;
- `collector_number`;
- `name`;
- `rarity`;
- `image_small_url`;
- `image_large_url`;
- `is_active`;
- `retired_at`.

The following are not ordinary update fields:

- `card_id`;
- `source_system`;
- `source_card_id`;
- `created_at`;
- `updated_at`.

Changing `source_system` or `source_card_id` would change source identity.

Changing `expansion_id` for an existing source identity normally indicates a conflict rather than a routine update.

#### Merge behavior

##### Inserted

Create a card when:

- the staging row is valid;
- the source-scoped card identity does not exist;
- the source expansion resolves uniquely;
- all required card values are present;
- run-level validation has passed.

The card must reference an existing normalized expansion.

##### Updated

Update an existing card only when one or more accepted import-owned values differ.

A valid update may change:

- collector number, if the source corrects it;
- name;
- rarity;
- image references;
- lifecycle fields under an approved rule.

The update must preserve:

- `card_id`;
- source identity;
- expansion relationship unless an explicit correction is approved;
- editions;
- variants;
- mappings;
- wishlist relationship;
- `created_at`.

An actual update changes `updated_at`.

##### Unchanged

When all compared values are equivalent:

- do not execute an unnecessary update;
- preserve `updated_at`;
- record `unchanged` through `import_record_outcomes`.

##### Missing

When a production card is absent from a later authoritative source scope:

- record a `missing` outcome;
- preserve the card row;
- preserve lifecycle state;
- preserve editions and variants;
- preserve mappings;
- preserve wishlist data.

One missing observation must not retire the card.

##### Retired

Retire a card only through:

- an explicit source lifecycle signal; or
- an approved reviewed decision.

Retirement sets:

```text
is_active = false
```

and:

```text
retired_at = retirement timestamp
```

Retirement must not physically delete:

- the card;
- editions;
- variants;
- mappings;
- wishlist items;
- historical evidence.

##### Reactivated

A retired card may be reactivated through sufficient source evidence or an approved reviewed decision.

Reactivation sets:

```text
is_active = true
```

and:

```text
retired_at = null
```

The transition must remain traceable through import outcomes or later lifecycle history.

##### Conflict

A conflict exists when:

- the same source-scoped card identity is proposed for another expansion;
- two staging rows claim the same source identity with incompatible values;
- an ordinary import attempts to change identity fields;
- weaker or ambiguous evidence attempts to replace established source identity;
- the source expansion cannot resolve uniquely.

A conflict must:

- prevent automatic merge;
- preserve existing production state;
- preserve staging and source evidence;
- create a conflict outcome or fail run-level validation;
- not silently reassign the card.

#### Duplicate handling

Two cards must not be merged solely because they share:

- the same name;
- the same collector number;
- similar image;
- similar market-product name;
- the same Pokemon character.

Production identity remains source-scoped.

Potential duplicate investigation belongs to review or validation workflows, not silent production merging.

#### Missing and retirement distinction

`missing` is an import observation.

`retired` is an explicit lifecycle state.

A card may be missing in one authoritative run while remaining active.

Therefore:

```text
missing outcome
≠ retired card
```

Automatic retirement after one missing observation is not allowed.

#### User-data preservation

All card merge paths must preserve `wishlist_items`.

The following must not delete or modify wishlist quantity or notes:

- card insert;
- card update;
- unchanged import;
- missing outcome;
- retirement;
- reactivation;
- mapping changes;
- price imports;
- failed merge rollback.

Physical deletion of a card referenced by a wishlist item must be restricted.

#### Primal Clash example

A conceptual Vulpix row may contain:

| Column             | Example value                                   |
| ------------------ | ----------------------------------------------- |
| `card_id`          | Database-generated value                        |
| `expansion_id`     | Internal Primal Clash expansion ID              |
| `source_system`    | `pokemon_tcg_data`                              |
| `source_card_id`   | `xy5-20`                                        |
| `collector_number` | `20`                                            |
| `name`             | `Vulpix`                                        |
| `rarity`           | Accepted source value or `null`                 |
| `image_small_url`  | `https://images.pokemontcg.io/xy5/20.png`       |
| `image_large_url`  | `https://images.pokemontcg.io/xy5/20_hires.png` |
| `is_active`        | `true`                                          |
| `retired_at`       | `null`                                          |
| `created_at`       | Database-generated timestamp                    |
| `updated_at`       | Database-generated timestamp                    |

Edition, language, finish, Cardmarket product identity, market price, and wishlist data are stored elsewhere.

#### Expected foreign-key behavior

From `card_editions`:

```text
card_editions.card_id
→ cards.card_id
```

Recommended behavior:

```text
ON DELETE RESTRICT
```

From `wishlist_items`:

```text
wishlist_items.card_id
→ cards.card_id
```

Recommended behavior:

```text
ON DELETE RESTRICT
```

From `card_market_product_mappings`:

```text
card_market_product_mappings.card_id
→ cards.card_id
```

Recommended behavior:

```text
ON DELETE RESTRICT
```

From mapping review structures that reference card targets:

```text
ON DELETE RESTRICT
```

Historical and user relationships must survive ordinary lifecycle changes.

#### Index candidates

Likely access paths include:

- lookup by `(source_system, source_card_id)`;
- listing cards by `expansion_id`;
- lookup by collector number within an expansion;
- filtering by active state;
- sorting by collector number;
- searching by card name;
- joining wishlist items;
- joining mappings.

Potential supporting indexes include:

```text
(expansion_id, collector_number)
```

```text
(expansion_id, is_active)
```

```text
(name)
```

The name index type should be selected only after search behavior is defined.

Final indexes must be approved during migration design.

#### Validation requirements

The first schema validation must confirm:

- all `164` accepted Primal Clash canonical cards can be stored;
- every card references the internal Primal Clash expansion;
- `pokemon_tcg_data / xy5-20` resolves to one card;
- source-scoped identity is unique;
- source card IDs remain text;
- collector numbers remain text;
- blank required fields are rejected;
- null rarity is accepted;
- image URLs may be null when the source contract permits it;
- two cards may share the same name;
- collector number is not used as the sole identity;
- repeated identical imports create no duplicate cards;
- unchanged imports preserve `updated_at`;
- one corrected descriptive value updates exactly one card;
- a missing observation does not delete or retire the card;
- retirement preserves editions, variants, mappings, and wishlist data;
- a card-level mapping creates no edition or variant automatically;
- unresolved market products do not modify the card;
- deleting a referenced card is restricted;
- a forced merge failure leaves cards and wishlist data unchanged.

#### Deferred fields

The following fields are not included in the first version:

- abstract Pokemon or character identity;
- national Pokedex number;
- supertype;
- subtypes;
- energy types;
- HP;
- attacks;
- abilities;
- weaknesses;
- resistances;
- retreat cost;
- artist;
- flavor text;
- regulation mark;
- legality metadata;
- source update timestamp;
- local image paths;
- image checksums;
- edition information;
- variant information;
- mapping status;
- market-product ID;
- current market price;
- cached canonical `From` price;
- wishlist quantity;
- wishlist notes;
- first observed import run;
- latest observed import run;
- last missing import run;
- retirement reason;
- lifecycle history;
- administrative notes.

These fields may be added only when an approved application or import requirement establishes a clear responsibility.

#### Open questions

- Should `(expansion_id, collector_number)` eventually become unique?
- Should `source_system` be constrained to `pokemon_tcg_data` in the first schema version?
- Are both image URLs required for the accepted Primal Clash fixture?
- Should image references remain external URLs or move to locally managed files before MVP completion?
- Should rarity remain source text or later use a controlled lookup?
- Can an accepted source ever move an existing card identity to another expansion?
- Should card lifecycle changes require dedicated history beyond import outcomes?
- Should `updated_at` be maintained by explicit merge logic or a narrowly defined database trigger?

### `card_editions`

#### Purpose

Store one confirmed edition-level release of a canonical card.

An edition distinguishes releases of the same canonical set-specific card when the source evidence shows that the marketplace treats them as different editions.

Examples include:

- Version 1;
- Version 2;
- Standard;
- Build-A-Bear Workshop.

An edition is not:

- a canonical card;
- a language;
- a finish;
- a Cardmarket product;
- a wishlist preference.

Language and finish combinations belong to `card_variants`.

#### Ownership

- Data owner: confirmed mapping process.
- User editing: not allowed through the wishlist workflow.
- Normal import deletion: not allowed.
- Creation from unresolved evidence: not allowed.
- Retirement: allowed only through explicit source evidence or an approved reviewed decision.
- Display-name updates: allowed only when the value is mapping-owned and supported by accepted evidence.

#### Columns

| Column                | PostgreSQL type                | Nullable | Default                    | Ownership                  | Description                                                                                                          |
| --------------------- | ------------------------------ | -------: | -------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `card_edition_id`     | `bigint` generated as identity |       No | Generated                  | Database                   | Internal surrogate primary key for the edition.                                                                      |
| `card_id`             | `bigint`                       |       No | None                       | Mapping-owned relationship | References the canonical card represented by this edition.                                                           |
| `edition_key`         | `text`                         |       No | None                       | Mapping-owned identity     | Project-controlled stable key for the edition within one canonical card.                                             |
| `source_system`       | `text`                         |      Yes | `null`                     | Mapping-owned evidence     | Source system that provided the edition code, initially expected to be `cardmarket` when available.                  |
| `source_edition_code` | `text`                         |      Yes | `null`                     | Mapping-owned evidence     | Source-provided edition code, for example `V1` or `V2`.                                                              |
| `display_name`        | `text`                         |       No | None                       | Mapping-owned display      | Human-readable edition name, for example `Standard`, `Version 2`, or `Build-A-Bear Workshop`.                        |
| `is_active`           | `boolean`                      |       No | `true`                     | Mapping-owned lifecycle    | Indicates whether the edition is available in ordinary active catalogue views.                                       |
| `retired_at`          | `timestamp with time zone`     |      Yes | `null`                     | Mapping-owned lifecycle    | Timestamp when the edition was explicitly retired. Null while active.                                                |
| `created_at`          | `timestamp with time zone`     |       No | Current database timestamp | Database                   | Timestamp when the production edition row was created.                                                               |
| `updated_at`          | `timestamp with time zone`     |       No | Current database timestamp | Database                   | Timestamp of the latest actual change to a mapping-owned or lifecycle field. An unchanged import must not modify it. |

#### Primary key

```text
card_edition_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- Cardmarket `idProduct`;
- Cardmarket `idMetacard`;
- source edition code;
- canonical card ID.

#### Foreign key

```text
card_id
→ cards.card_id
```

Required behavior:

- the referenced canonical card must already exist;
- deleting a card with editions must be restricted;
- deletion must not cascade from `cards` to `card_editions`.

#### Required constraints

##### Edition identity within one card

```text
UNIQUE (card_id, edition_key)
```

##### Hierarchy compatibility key

Add the supporting uniqueness required by composite foreign keys:

```text
UNIQUE (card_edition_id, card_id)
```

The same project-controlled edition key may be reused for another canonical card.

Example:

```text
xy5-20 / standard
```

and:

```text
xy5-21 / standard
```

represent different edition rows because they belong to different cards.

##### Non-empty edition key

Conceptual rule:

```text
trim(edition_key) <> ''
```

##### Non-empty display name

Conceptual rule:

```text
trim(display_name) <> ''
```

##### Source-code consistency

`source_system` and `source_edition_code` must either both be present or both be null.

Conceptual rule:

```text
source_system is null
and source_edition_code is null
```

or:

```text
source_system is not null
and source_edition_code is not null
```

When present, both values must contain non-whitespace text.

##### Source edition uniqueness

When a source edition code is available, the proposed uniqueness rule is:

```text
UNIQUE (card_id, source_system, source_edition_code)
```

This uniqueness applies only to rows where source edition evidence exists.

The same source edition code, such as `V1`, may occur for different canonical cards.

##### Lifecycle consistency

```text
is_active = true
→ retired_at is null
```

```text
is_active = false
→ retired_at is not null
```

#### `edition_key`

`edition_key` is an internal project-controlled identity within one card.

Examples may include:

- `standard`;
- `version_1`;
- `version_2`;
- `build_a_bear_workshop`.

The exact normalization rule must be deterministic.

`edition_key` must not be derived from display text without a documented rule.

The import process must not create an edition key merely because:

- one Cardmarket product exists;
- a product has the same name as another product;
- a product has a different `idProduct`;
- a product has a different price;
- a product order suggests a version;
- semantic similarity suggests a special edition.

Creation requires confirmed edition-level evidence or an explicit reviewed decision.

#### `source_edition_code`

The source edition code preserves a value explicitly supplied or deterministically evidenced from the source.

Examples:

- `V1`;
- `V2`.

It must not be reconstructed from:

- product order;
- product ID order;
- price order;
- display-name assumptions;
- candidate ranking.

If no source edition code exists, the column remains null.

#### `display_name`

`display_name` is intended for catalogue and administrative presentation.

Preferred value order:

1. confirmed human-readable source or reviewed edition name;
2. controlled fallback derived from a confirmed source edition code;
3. reviewed project display name.

Examples:

```text
source_edition_code = V1
display_name = Version 1
```

```text
source_edition_code = V2
display_name = Build-A-Bear Workshop
```

The fallback name must not claim knowledge that the evidence does not support.

For example, `V1` may safely display as `Version 1`, but it must not automatically display as `Standard` unless that meaning has been confirmed.

#### Creation rule

A production edition may be created only when the accepted mapping has:

```text
confirmation_scope = edition
```

or:

```text
confirmation_scope = variant
```

A mapping confirmed only at card level must not create an edition.

The following mapping classifications must not create an edition:

- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`.

A `confirmed` mapping with:

```text
confirmation_scope = card
```

also must not create an edition.

#### Relationships

```text
cards
    1 → many card_editions
```

```text
card_editions
    1 → many card_variants
```

A confirmed market-product mapping may reference an edition directly when:

- the canonical card is confirmed;
- the edition is confirmed;
- language or finish is not yet sufficiently confirmed.

#### Import comparison fields

The repeated mapping merge compares normalized values for:

- `edition_key`;
- `source_system`;
- `source_edition_code`;
- `display_name`;
- `is_active`;
- `retired_at`.

The following are not ordinary update fields:

- `card_edition_id`;
- `card_id`;
- `created_at`;
- `updated_at`.

Changing `card_id` would change the edition identity and is not permitted through a normal import update.

#### Merge behavior

##### Inserted

Create an edition when:

- the canonical card exists;
- the mapping status is `confirmed`;
- confirmation scope is `edition` or `variant`;
- the edition identity is deterministic;
- no conflicting edition key exists;
- no conflicting source edition code exists.

##### Updated

Update only when a mapping-owned display or lifecycle value has changed.

The update must preserve:

- `card_edition_id`;
- `card_id`;
- existing card-variant relationships;
- existing confirmed market-product relationships;
- `created_at`.

An actual update changes `updated_at`.

##### Unchanged

When all compared values are equal:

- do not execute an unnecessary update;
- preserve `updated_at`;
- record `unchanged` through the import outcome structure where edition outcomes are reported.

##### Missing

If an edition is not observed in a later authoritative mapping scope:

- record missing evidence where the scope supports it;
- preserve the edition row;
- preserve `is_active`;
- preserve `retired_at`;
- preserve variants and mappings.

One missing observation must not retire the edition.

##### Retired

Retire an edition only through:

- an explicit source signal; or
- an approved reviewed decision.

Retirement sets:

```text
is_active = false
```

and:

```text
retired_at = retirement timestamp
```

Retirement does not physically delete:

- the edition;
- its variants;
- its historical mappings;
- its evidence.

##### Reactivated

A retired edition may be reactivated through sufficient direct source evidence or an approved reviewed decision.

Reactivation sets:

```text
is_active = true
```

and:

```text
retired_at = null
```

The transition must remain traceable.

##### Conflict

A conflict exists when:

- the same `(card_id, edition_key)` is associated with incompatible evidence;
- the same `(card_id, source_system, source_edition_code)` resolves to a different edition;
- an existing confirmed edition would need to be replaced using weaker evidence;
- a mapping attempts to attach the edition to another canonical card.

A conflict must:

- prevent automatic merge of the conflicting edition;
- preserve the existing confirmed edition;
- create review evidence;
- not silently rename, merge, or reassign the edition.

#### Field normalization

##### `edition_key`

- Store lowercase project-controlled text.
- Use a deterministic separator convention, recommended underscore.
- Trim leading and trailing whitespace before validation.
- Do not generate from unconfirmed free text.
- Do not include the canonical card ID because `card_id` already scopes the key.
- Do not include language or finish.

##### `source_system`

- Trim leading and trailing whitespace.
- Preserve the controlled technical identifier.
- Do not use a human-readable display name.

##### `source_edition_code`

- Trim leading and trailing whitespace.
- Preserve source-significant case and punctuation.
- Do not translate.
- Do not infer from product ordering.

##### `display_name`

- Trim leading and trailing whitespace.
- Preserve professional human-readable capitalization.
- Do not include language or finish unless they are genuinely part of the edition name.
- Do not use display name as the only identity key.

#### Primal Clash example

A conceptual Vulpix edition may contain:

| Column                | Example value                |
| --------------------- | ---------------------------- |
| `card_edition_id`     | Database-generated value     |
| `card_id`             | Internal `xy5-20` card ID    |
| `edition_key`         | `version_1`                  |
| `source_system`       | `cardmarket`                 |
| `source_edition_code` | `V1`                         |
| `display_name`        | `Version 1`                  |
| `is_active`           | `true`                       |
| `retired_at`          | `null`                       |
| `created_at`          | Database-generated timestamp |
| `updated_at`          | Database-generated timestamp |

A second confirmed edition may contain:

| Column                | Example value                                  |
| --------------------- | ---------------------------------------------- |
| `card_edition_id`     | Database-generated value                       |
| `card_id`             | Internal `xy5-20` card ID                      |
| `edition_key`         | `version_2`                                    |
| `source_system`       | `cardmarket`                                   |
| `source_edition_code` | `V2`                                           |
| `display_name`        | `Version 2` or a confirmed human-readable name |
| `is_active`           | `true`                                         |
| `retired_at`          | `null`                                         |
| `created_at`          | Database-generated timestamp                   |
| `updated_at`          | Database-generated timestamp                   |

Language, finish, market-product ID, and price do not belong in the edition row.

#### Expected foreign-key behavior

From `card_variants` to `card_editions`:

- physical deletion of an edition with variants must be restricted.

From confirmed mappings to `card_editions`:

- physical deletion of a referenced edition must be restricted.

Normal import logic must use lifecycle state rather than physical deletion.

#### Index candidates

Indexes are not yet approved, but likely access paths include:

- listing editions by `card_id`;
- lookup by `(card_id, edition_key)`;
- lookup by `(card_id, source_system, source_edition_code)`;
- active edition filtering by `is_active`.

Final indexes must be selected after query patterns and constraint implementation are reviewed.

#### Validation requirements

The first schema validation must confirm:

- multiple editions can belong to one canonical card;
- Vulpix `xy5-20` can represent separate `V1` and `V2` editions;
- the same `edition_key` cannot be duplicated within one card;
- the same `edition_key` can be reused for another card;
- the same source edition code cannot map to two editions of the same card;
- a source edition code may remain null;
- source system and source edition code are either both present or both null;
- blank edition keys are rejected;
- blank display names are rejected;
- card-level confirmation does not create an edition;
- edition-level or variant-level confirmation may create an edition;
- `candidate`, `unmatched`, `ambiguous`, `excluded`, and `unmatched_duplicate_candidate` mappings create no edition;
- repeating the same confirmed mapping creates no duplicate edition;
- an unchanged import preserves `updated_at`;
- a weaker later observation does not replace an existing confirmed edition;
- a missing observation does not delete or retire an edition;
- physical deletion is restricted while variants or mappings reference the edition.

#### Deferred fields

The following fields are not included in the first version:

- edition description;
- source product name;
- release date;
- edition category;
- edition image;
- evidence payload;
- evidence confidence score;
- confirmation method;
- confirmation import run;
- first observed import run;
- latest observed import run;
- retirement reason;
- administrative notes;
- wishlist preference;
- language;
- finish;
- price.

Confirmation evidence remains in mapping-case, observation, and status-history structures.

#### Open questions

- What exact `edition_key` normalization rule will be used?
- Can every confirmed source edition code be converted deterministically into an `edition_key`?
- Should an edition without a source edition code require manual confirmation before creation?
- Is the fallback `Version 1`, `Version 2`, and similar display naming sufficient for the first UI?
- Should `source_system` be limited to `cardmarket` in the first schema version?
- Should lifecycle changes use only import outcomes and mapping status history, or require edition-specific history later?
- Should `updated_at` be maintained by explicit merge logic or a database trigger?

### `card_variants`

#### Purpose

Store one confirmed language and finish combination within a card edition.

A variant represents the most specific catalogue-level physical form currently supported by the MVP data model.

Examples include:

- English normal;
- German normal;
- English reverse holo;
- English holo.

A variant is not:

- a canonical card;
- an edition;
- a Cardmarket market product;
- a price snapshot;
- a wishlist item.

One edition may have multiple variants.

#### Ownership

- Data owner: confirmed mapping process.
- User editing: not allowed through the wishlist workflow.
- Normal import deletion: not allowed.
- Creation from unresolved language or finish evidence: not allowed.
- Retirement: allowed only through explicit source evidence or an approved reviewed decision.
- Wishlist preference: not stored in this table for the MVP.

#### Columns

| Column            | PostgreSQL type                | Nullable | Default                    | Ownership                  | Description                                                                                                          |
| ----------------- | ------------------------------ | -------: | -------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `card_variant_id` | `bigint` generated as identity |       No | Generated                  | Database                   | Internal surrogate primary key for the variant.                                                                      |
| `card_edition_id` | `bigint`                       |       No | None                       | Mapping-owned relationship | References the confirmed edition containing this variant.                                                            |
| `language_code`   | `text`                         |       No | None                       | Mapping-owned identity     | Controlled language code, initially `en` or `de`.                                                                    |
| `finish_code`     | `text`                         |       No | None                       | Mapping-owned identity     | Controlled finish code, initially `normal`, `reverse_holo`, or `holo`.                                                |
| `is_active`       | `boolean`                      |       No | `true`                     | Mapping-owned lifecycle    | Indicates whether the variant is available in ordinary active catalogue views.                                       |
| `retired_at`      | `timestamp with time zone`     |      Yes | `null`                     | Mapping-owned lifecycle    | Timestamp when the variant was explicitly retired. Null while active.                                                |
| `created_at`      | `timestamp with time zone`     |       No | Current database timestamp | Database                   | Timestamp when the production variant row was created.                                                               |
| `updated_at`      | `timestamp with time zone`     |       No | Current database timestamp | Database                   | Timestamp of the latest actual change to a mapping-owned or lifecycle field. An unchanged import must not modify it. |

#### Primary key

```text
card_variant_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- Cardmarket `idProduct`;
- Cardmarket `idMetacard`;
- language code;
- finish code;
- source edition code.

#### Foreign key

```text
card_edition_id
→ card_editions.card_edition_id
```

Required behavior:

- the referenced edition must already exist;
- deleting an edition with variants must be restricted;
- deletion must not cascade from `card_editions` to `card_variants`.

#### Required constraints

##### Variant identity within one edition

```text
UNIQUE (card_edition_id, language_code, finish_code)
```

##### Hierarchy compatibility key

Add the supporting uniqueness required by composite foreign keys:

```text
UNIQUE (card_variant_id, card_edition_id)
```

The same language and finish combination may exist in another edition.

Example:

```text
Vulpix Version 1 / en / normal
```

and:

```text
Vulpix Version 2 / en / normal
```

are different variants because they belong to different editions.

##### Non-empty language code

Conceptual rule:

```text
trim(language_code) <> ''
```

##### Non-empty finish code

Conceptual rule:

```text
trim(finish_code) <> ''
```

##### Controlled language values

Initial allowed values:

- `en`;
- `de`.

Unknown language must not be stored as:

- empty text;
- `unknown`;
- `other`;
- null.

If language cannot be confirmed, the production variant must not be created.

##### Controlled finish values

Initial allowed values:

- `normal`;
- `reverse_holo`;
- `holo`.

Unknown or non-standard finish must not create a production variant.

A dedicated controlled finish code may be added later when a real supported non-standard finish is confirmed.

##### Lifecycle consistency

```text
is_active = true
→ retired_at is null
```

```text
is_active = false
→ retired_at is not null
```

#### Language representation

`language_code` uses controlled lowercase technical identifiers.

Initial values:

| Code | Meaning |
| ---- | ------- |
| `en` | English |
| `de` | German  |

The codes are intended for:

- deterministic uniqueness;
- filtering;
- price eligibility;
- import validation;
- future edition- or variant-specific wishlist preferences.

Human-readable language labels belong to the UI or data dictionary, not to this table.

A generic language lookup table is not required for the first schema version.

#### Finish representation

`finish_code` uses controlled lowercase technical identifiers.

Initial values:

| Code           | Meaning                  |
| -------------- | ------------------------ |
| `normal`       | Standard non-holo finish |
| `reverse_holo` | Reverse-holo finish      |
| `holo`         | Holo finish              |

The exact source-to-finish mapping rules must be documented before the first production merge.

The import process must not infer finish solely from:

- price availability;
- non-null `avg30_holo`;
- product order;
- product ID order;
- product-name similarity;
- candidate ranking;
- an assumed default.

A non-null `avg30_holo` does not by itself prove that the mapped market product represents a holo variant.

#### Creation rule

A production variant may be created only when the accepted mapping has:

```text
confirmation_scope = variant
```

The following must all be confirmed:

- canonical card;
- edition;
- language;
- finish.

A mapping confirmed only at:

```text
confirmation_scope = card
```

must not create a variant.

A mapping confirmed only at:

```text
confirmation_scope = edition
```

must not create a variant.

The following mapping classifications must not create a variant:

- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`.

#### Relationships

```text
card_editions
    1 → many card_variants
```

```text
card_variants
    1 → zero or many card_market_product_mappings
```

A confirmed market-product mapping may reference a variant only when language and finish are supported by sufficient evidence.

#### Import comparison fields

The repeated mapping merge compares normalized values for:

- `language_code`;
- `finish_code`;
- `is_active`;
- `retired_at`.

The following are not ordinary update fields:

- `card_variant_id`;
- `card_edition_id`;
- `created_at`;
- `updated_at`.

Changing `card_edition_id` would change the variant identity and is not permitted through a normal import update.

#### Merge behavior

##### Inserted

Create a variant when:

- the parent edition exists;
- mapping status is `confirmed`;
- confirmation scope is `variant`;
- language is confirmed;
- finish is confirmed;
- no duplicate `(card_edition_id, language_code, finish_code)` exists;
- all run-level validation rules have passed.

##### Updated

Update only when a mapping-owned detail or lifecycle value has changed.

An update must preserve:

- `card_variant_id`;
- `card_edition_id`;
- `language_code`;
- `finish_code`;
- confirmed market-product relationships;
- `created_at`.

An actual update changes `updated_at`.

##### Unchanged

When all compared values are equal:

- do not execute an unnecessary update;
- preserve `updated_at`;
- record `unchanged` through the import outcome structure where variant outcomes are reported.

##### Missing

If a variant is absent from a later authoritative mapping scope:

- record missing evidence where the scope supports it;
- preserve the variant row;
- preserve `is_active`;
- preserve `retired_at`;
- preserve confirmed market-product mappings.

One missing observation must not retire the variant.

##### Retired

Retire a variant only through:

- an explicit source signal; or
- an approved reviewed decision.

Retirement sets:

```text
is_active = false
```

and:

```text
retired_at = retirement timestamp
```

Retirement does not physically delete:

- the variant;
- its confirmed mappings;
- its price history through market products;
- its evidence.

##### Reactivated

A retired variant may be reactivated through sufficient direct evidence or an approved reviewed decision.

Reactivation sets:

```text
is_active = true
```

and:

```text
retired_at = null
```

The transition must remain traceable.

##### Conflict

A conflict exists when:

- the same `(card_edition_id, language_code, finish_code)` is associated with incompatible evidence;
- an existing confirmed variant would need to move to another edition;
- a mapping attempts to change language or finish identity through a normal update;
- weaker evidence attempts to replace an existing confirmed variant;
- an unsupported finish is forced into a production variant;
- a variant-level mapping lacks confirmed language or finish evidence.

A conflict must:

- prevent automatic merge;
- preserve the existing confirmed variant;
- preserve review evidence;
- not silently create a second equivalent variant;
- not silently reclassify the finish.

#### Field normalization

##### `language_code`

- Store lowercase controlled code.
- Trim leading and trailing whitespace before validation.
- Do not store human-readable language names.
- Do not infer language from UI locale.
- Do not infer language from card name alone.
- Do not use null or `other` for unresolved language.

##### `finish_code`

- Store lowercase controlled code.
- Use underscore separators.
- Trim leading and trailing whitespace before validation.
- Do not use free-text source labels directly without a documented mapping rule.
- Do not use `other` for unresolved finish.

#### Primal Clash example

A conceptual confirmed English normal variant may contain:

| Column            | Example value                        |
| ----------------- | ------------------------------------ |
| `card_variant_id` | Database-generated value             |
| `card_edition_id` | Internal Vulpix Version 1 edition ID |
| `language_code`   | `en`                                 |
| `finish_code`     | `normal`                             |
| `is_active`       | `true`                               |
| `retired_at`      | `null`                               |
| `created_at`      | Database-generated timestamp         |
| `updated_at`      | Database-generated timestamp         |

A conceptual English reverse-holo variant may contain:

| Column            | Example value                        |
| ----------------- | ------------------------------------ |
| `card_variant_id` | Database-generated value             |
| `card_edition_id` | Internal Vulpix Version 1 edition ID |
| `language_code`   | `en`                                 |
| `finish_code`     | `reverse_holo`                       |
| `is_active`       | `true`                               |
| `retired_at`      | `null`                               |
| `created_at`      | Database-generated timestamp         |
| `updated_at`      | Database-generated timestamp         |

These rows may be created only when the actual source evidence confirms the language and finish.

The current Primal Clash direct product mapping does not by itself prove that every confirmed market-product mapping supports variant-level creation.

#### Expected foreign-key behavior

From `card_market_product_mappings` to `card_variants`:

- physical deletion of a referenced variant must be restricted.

Normal import logic must use lifecycle state rather than physical deletion.

#### Index candidates

Indexes are not yet approved, but likely access paths include:

- listing variants by `card_edition_id`;
- filtering by `language_code`;
- filtering by `finish_code`;
- active variant filtering by `is_active`;
- lookup by `(card_edition_id, language_code, finish_code)`.

Final indexes must be selected after query patterns, canonical-price rules, and NocoDB access patterns are reviewed.

#### Validation requirements

The first schema validation must confirm:

- one edition can contain multiple variants;
- English and German variants can coexist for the same edition;
- normal and reverse-holo variants can coexist for the same edition;
- the same language and finish combination cannot be duplicated within one edition;
- the same language and finish combination can exist in another edition;
- blank language codes are rejected;
- blank finish codes are rejected;
- unsupported language codes are rejected;
- unsupported finish codes are rejected;
- card-level confirmation creates no variant;
- edition-level confirmation creates no variant;
- only variant-level confirmation may create a variant;
- unresolved language creates no variant;
- unresolved finish creates no variant;
- `candidate`, `unmatched`, `ambiguous`, `excluded`, and `unmatched_duplicate_candidate` mappings create no variant;
- repeating the same confirmed variant mapping creates no duplicate variant;
- an unchanged repeated import preserves `updated_at`;
- a weaker later observation does not replace or move an existing confirmed variant;
- a missing observation does not delete or retire the variant;
- physical deletion is restricted while confirmed mappings reference the variant.

#### Deferred fields

The following fields are not included in the first version:

- source language identifier;
- source finish identifier;
- source variant identifier;
- display name;
- variant description;
- confirmation method;
- evidence payload;
- evidence confidence score;
- first observed import run;
- latest observed import run;
- retirement reason;
- administrative notes;
- variant image;
- market price;
- wishlist preference;
- wanted quantity;
- user notes.

Confirmation evidence remains in mapping-case, observation, candidate, and status-history structures.

#### Open questions

- What exact source evidence will confirm `language_code` for the first import?
- What exact source evidence will distinguish `normal`, `reverse_holo`, and `holo`?
- Does a Cardmarket `idProduct` identify one finish, or can one product expose both `avg30` and `avg30_holo` for different finishes?
- Should variant-level creation be deferred entirely until language and finish fixtures are added?
- Should source language and finish values be preserved in staging only or later added to production?
- Should `updated_at` be maintained by explicit merge logic or a database trigger?

## Market tables

### `market_products`

#### Purpose

Store one independent marketplace product imported from an external market source.

For the first implementation, the market source is Cardmarket.

Example source-scoped identity:

```text
cardmarket / 273532
```

A market product is not:

- a canonical card;
- a card edition;
- a language or finish variant;
- a mapping status;
- a price snapshot;
- a wishlist item.

A valid market product may exist without a confirmed relationship to the canonical catalogue.

#### Ownership

- Data owner: market-product import process.
- User editing: not allowed through the wishlist workflow.
- Normal import deletion: not allowed.
- Mapping classification: not stored in this table.
- Price history: not stored in this table.
- Retirement: allowed only through an explicit source signal or a separately approved reviewed decision.

#### Columns

| Column                  | PostgreSQL type                | Nullable | Default                    | Ownership                           | Description                                                                                                                                |
| ----------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `market_product_id`     | `bigint` generated as identity |       No | Generated                  | Database                            | Internal surrogate primary key for the market product.                                                                                     |
| `source_system`         | `text`                         |       No | None                       | Import-owned identity               | Controlled market source identifier, initially `cardmarket`.                                                                               |
| `source_product_id`     | `text`                         |       No | None                       | Import-owned identity               | Stable product identifier within the source system, for example Cardmarket `idProduct`.                                                    |
| `source_expansion_id`   | `text`                         |      Yes | `null`                     | Import-owned source metadata        | Expansion identifier exactly as represented by the market source, for example Cardmarket `idExpansion`.                                    |
| `expansion_id`          | `bigint`                       |      Yes | `null`                     | Import-owned confirmed relationship | Optional reference to the internal normalized expansion when the cross-source expansion relationship is confirmed.                         |
| `source_metaproduct_id` | `text`                         |      Yes | `null`                     | Import-owned source metadata        | Source metaproduct identifier when available, for example Cardmarket `idMetacard`. It is not the market-product identity.                  |
| `raw_name`              | `text`                         |       No | None                       | Import-owned source metadata        | Product name preserved from the market source after minimal whitespace normalization.                                                      |
| `source_category_id`    | `text`                         |      Yes | `null`                     | Import-owned source metadata        | Source category identifier when available.                                                                                                 |
| `source_category_name`  | `text`                         |      Yes | `null`                     | Import-owned source metadata        | Human-readable source category name when available.                                                                                        |
| `source_created_at`     | `timestamp with time zone`     |      Yes | `null`                     | Import-owned source metadata        | Source-provided product creation timestamp when available.                                                                                 |
| `is_active`             | `boolean`                      |       No | `true`                     | Import-owned lifecycle              | Indicates whether the market product is available in ordinary active market views. A missing observation alone must not change this value. |
| `retired_at`            | `timestamp with time zone`     |      Yes | `null`                     | Import-owned lifecycle              | Timestamp when the market product was explicitly retired. Null while active.                                                               |
| `created_at`            | `timestamp with time zone`     |       No | Current database timestamp | Database                            | Timestamp when the production market-product row was created.                                                                              |
| `updated_at`            | `timestamp with time zone`     |       No | Current database timestamp | Database                            | Timestamp of the latest actual change to an import-owned or lifecycle field. An unchanged import must not modify it.                       |

#### Primary key

```text
market_product_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- Cardmarket `idProduct`;
- Cardmarket `idMetacard`;
- Cardmarket `idExpansion`;
- canonical card ID;
- edition or variant ID.

#### Required business identity

```text
(source_system, source_product_id)
```

This is the stable source-scoped market-product identity.

#### Foreign key

```text
expansion_id
→ expansions.expansion_id
```

The relationship is nullable because a valid market product may be preserved before its internal expansion mapping is confirmed.

Required behavior:

- when present, the internal expansion must already exist;
- deleting a referenced expansion must be restricted;
- absence of an internal expansion mapping must not reject an otherwise valid market product.

#### Required constraints

##### Source-scoped uniqueness

```text
UNIQUE (source_system, source_product_id)
```

One source-scoped product identifier must resolve to at most one production market product.

The same literal source product ID may exist in another source system without collision.

##### Non-empty source system

Conceptual rule:

```text
trim(source_system) <> ''
```

##### Non-empty source product identifier

Conceptual rule:

```text
trim(source_product_id) <> ''
```

##### Non-empty raw name

Conceptual rule:

```text
trim(raw_name) <> ''
```

##### Optional source-value consistency

When present, the following values must contain non-whitespace text:

- `source_expansion_id`;
- `source_metaproduct_id`;
- `source_category_id`;
- `source_category_name`.

##### Lifecycle consistency

```text
is_active = true
→ retired_at is null
```

```text
is_active = false
→ retired_at is not null
```

#### Source identifiers

##### `source_product_id`

`source_product_id` is stored as `text`.

Reasons:

- source identifiers are opaque external values;
- numeric-looking identifiers are not used for arithmetic;
- the same schema may later support non-numeric product identifiers;
- text storage avoids source-specific type assumptions.

For Cardmarket, this value preserves `idProduct`.

##### `source_metaproduct_id`

`source_metaproduct_id` preserves Cardmarket `idMetacard` when available.

It must not be used as:

- the primary key;
- the source-scoped product identity;
- the canonical card identity;
- automatic mapping evidence on its own.

Several market products may share the same metaproduct identifier.

##### `source_expansion_id`

`source_expansion_id` preserves the original market-source expansion identifier even when `expansion_id` is unresolved.

For Cardmarket Primal Clash:

```text
source_expansion_id = 1585
```

The source value must not be replaced by the internal expansion ID.

#### Internal expansion relationship

`expansion_id` may be populated only when the cross-source expansion mapping is confirmed.

Example:

```text
source_expansion_id = 1585
expansion_id = internal Primal Clash expansion ID
```

The import process must not infer an internal expansion solely from:

- matching display names;
- product-name similarity;
- numeric proximity;
- first available expansion;
- undocumented assumptions.

A conflicting expansion relationship must prevent automatic update and create review evidence.

#### Raw source name

`raw_name` preserves the market-source product name.

Normalization is intentionally minimal:

- trim leading and trailing whitespace;
- preserve source spelling;
- preserve source capitalization;
- preserve punctuation;
- do not translate;
- do not use the name as the source identity.

The product name may support mapping evidence, but it must not replace direct source identifiers.

#### Category fields

`source_category_id` and `source_category_name` preserve source classification when available.

They may support:

- MVP exclusions;
- validation;
- duplicate-candidate analysis;
- import reporting.

They must not be used alone to confirm a canonical card mapping.

For example, an Online Code Card may be preserved as a valid market product while its mapping case is classified as `excluded`.

#### Mapping boundary

The following do not belong in `market_products`:

- canonical `card_id`;
- `card_edition_id`;
- `card_variant_id`;
- current mapping status;
- confirmation scope;
- mapping method;
- evidence level;
- candidate target;
- review notes.

These values belong to:

- `card_market_mapping_cases`;
- `mapping_case_observations`;
- `mapping_candidates`;
- `mapping_status_history`;
- `card_market_product_mappings`.

A market product may therefore exist in production while its mapping case is:

- `unmatched`;
- `candidate`;
- `ambiguous`;
- `confirmed`;
- `excluded`;
- `unmatched_duplicate_candidate`.

#### Price boundary

The following do not belong in `market_products`:

- `avg30`;
- `avg30_holo`;
- currency;
- source price snapshot timestamp;
- current derived canonical price.

Price observations belong to `market_price_snapshots`.

This prevents a new price import from overwriting historical market data or changing the identity row.

#### Import comparison fields

The repeated market-product import compares normalized values for:

- `source_expansion_id`;
- `expansion_id`;
- `source_metaproduct_id`;
- `raw_name`;
- `source_category_id`;
- `source_category_name`;
- `source_created_at`;
- `is_active`;
- `retired_at`.

The following fields are identity or database-managed fields and are not ordinary source update values:

- `market_product_id`;
- `source_system`;
- `source_product_id`;
- `created_at`;
- `updated_at`.

The source-scoped identity fields must not be changed by a normal import.

#### Merge behavior

##### Inserted

Create a market-product row when:

- the staging row is structurally valid;
- the source-scoped product identifier does not exist in production;
- required source values are present;
- run-level validation has passed.

A valid market product may be inserted even when:

- no canonical card mapping is confirmed;
- no edition is confirmed;
- no variant is confirmed;
- the internal expansion relationship is unresolved.

##### Updated

Update a market product only when one or more normalized import-owned values differ.

The update must preserve:

- `market_product_id`;
- `source_system`;
- `source_product_id`;
- confirmed mapping relationships;
- mapping case identity;
- market price history;
- `created_at`.

An actual update changes `updated_at`.

##### Unchanged

When all compared values are equal:

- do not execute an unnecessary production update;
- preserve `updated_at`;
- record `unchanged` through the import outcome structure.

##### Missing

When a production market product is absent from a complete authoritative import scope:

- record a `missing` import outcome;
- preserve the product row;
- preserve `is_active`;
- preserve `retired_at`;
- preserve mappings;
- preserve mapping review evidence;
- preserve price snapshots.

One missing observation must not automatically retire the product.

##### Retired

Retire a market product only when supported by:

- an explicit source lifecycle signal; or
- a separately approved and reviewed retirement rule.

Retirement sets:

```text
is_active = false
```

and:

```text
retired_at = retirement timestamp
```

Retirement does not physically delete:

- the product;
- confirmed mappings;
- mapping cases;
- observations;
- candidates;
- price snapshots.

##### Reactivated

A retired market product may be reactivated through sufficient source evidence or an approved reviewed decision.

Reactivation sets:

```text
is_active = true
```

and:

```text
retired_at = null
```

The transition must remain traceable.

##### Rejected

A structurally invalid source product:

- does not create or update a `market_products` row;
- is stored in the rejected-record workflow;
- preserves its raw source reference or payload;
- preserves structured rejection reasons.

##### Mapping unresolved

A valid product with unresolved mapping:

- remains in `market_products`;
- creates or updates a persistent mapping case;
- creates no unsupported catalogue mapping;
- does not create an edition or variant through inference;
- does not contribute to canonical-card pricing unless an eligible confirmed relationship exists.

#### `unmatched_duplicate_candidate`

A Cardmarket product classified as `unmatched_duplicate_candidate`:

- remains present in `market_products`;
- preserves its source identifiers and metadata;
- creates no canonical card, edition, or variant mapping;
- does not contribute to the canonical-card price;
- remains visible through mapping-review and import reports.

The classification itself does not belong in `market_products`.

For the accepted Primal Clash rule, the evidence includes matching:

- `source_metaproduct_id`;
- normalized product name;
- source expansion;
- source category ID;
- source category name;

with inspected differences limited to source product ID and source creation timestamp.

#### Field normalization

##### `source_system`

- Trim leading and trailing whitespace.
- Store a controlled lowercase technical identifier.
- Initial expected value: `cardmarket`.
- Do not store a human-readable source name.

##### `source_product_id`

- Trim leading and trailing whitespace.
- Preserve the source value as text.
- Do not convert it to an integer.
- Do not infer it from listing order or product name.
- Do not reuse a metaproduct identifier.

##### `source_expansion_id`

- Trim leading and trailing whitespace.
- Preserve the source value as text.
- Store null when unavailable.
- Do not replace it with the internal `expansion_id`.

##### `source_metaproduct_id`

- Trim leading and trailing whitespace.
- Preserve the source value as text.
- Store null when unavailable.
- Do not use it as direct canonical identity evidence.

##### `raw_name`

- Trim leading and trailing whitespace.
- Preserve source spelling and punctuation.
- Do not translate.
- Do not silently normalize edition, language, or finish into the name.

##### Category fields

- Trim leading and trailing whitespace.
- Preserve source values.
- Store null when unavailable.
- Do not invent categories to simplify exclusions.

#### Primal Clash example

A conceptual Cardmarket product row may contain:

| Column                  | Example value                      |
| ----------------------- | ---------------------------------- |
| `market_product_id`     | Database-generated value           |
| `source_system`         | `cardmarket`                       |
| `source_product_id`     | `273532`                           |
| `source_expansion_id`   | `1585`                             |
| `expansion_id`          | Internal Primal Clash expansion ID |
| `source_metaproduct_id` | Source value when available        |
| `raw_name`              | Source product name                |
| `source_category_id`    | Source value when available        |
| `source_category_name`  | Source value when available        |
| `source_created_at`     | Source timestamp when available    |
| `is_active`             | `true`                             |
| `retired_at`            | `null`                             |
| `created_at`            | Database-generated timestamp       |
| `updated_at`            | Database-generated timestamp       |

The row does not contain:

- canonical card ID;
- edition code;
- language;
- finish;
- mapping status;
- `avg30`;
- `avg30_holo`;
- wishlist data.

#### Relationships

```text
expansions
    1 → many market_products
```

The relationship is optional from the market-product side until expansion mapping is confirmed.

```text
market_products
    1 → zero or one card_market_mapping_cases
```

```text
market_products
    1 → zero or many card_market_product_mappings over lifecycle
```

```text
market_products
    1 → many market_price_snapshots
```

#### Expected foreign-key behavior

From `card_market_mapping_cases` to `market_products`:

- physical deletion of a referenced market product must be restricted.

From `card_market_product_mappings` to `market_products`:

- physical deletion of a referenced market product must be restricted.

From `market_price_snapshots` to `market_products`:

- physical deletion of a product with price history must be restricted.

Normal lifecycle management must use `is_active` and `retired_at` rather than physical deletion.

#### Index candidates

Indexes are not yet approved, but likely access paths include:

- lookup by `(source_system, source_product_id)`;
- lookup by `source_metaproduct_id`;
- filtering by `expansion_id`;
- lookup by `(source_system, source_expansion_id)`;
- filtering by source category;
- active-product filtering by `is_active`.

`source_metaproduct_id` may receive a non-unique supporting index because multiple products may share it.

Final indexes must be selected after import and validation queries are defined.

#### Validation requirements

The first schema validation must confirm:

- all validated Primal Clash Cardmarket products can be stored;
- each source-scoped product identifier is unique;
- Cardmarket `idProduct` is stored as text;
- Cardmarket `idMetacard` does not act as a unique key;
- multiple products may share the same metaproduct identifier;
- blank source product IDs are rejected;
- blank raw names are rejected;
- source expansion ID may be preserved before internal expansion resolution;
- a valid product may exist without a confirmed card mapping;
- a valid product may exist without a confirmed edition or variant;
- excluded Online Code Card products remain preserved as source products;
- all six `unmatched_duplicate_candidate` products remain preserved;
- unresolved products create no unsupported mapping;
- unresolved and excluded products do not contribute to canonical-card pricing;
- repeating the same import creates no duplicate market products;
- repeating the same import performs zero unnecessary product updates;
- changing one import-owned field updates exactly one expected row;
- an unchanged row preserves `updated_at`;
- a missing observation does not delete or retire the product;
- physical deletion is restricted while mappings, cases, or price snapshots reference the product;
- a forced production merge failure leaves all market-product rows unchanged.

#### Deferred fields

The following fields are not included in the first version:

- source product URL;
- localized product name;
- source language;
- source finish;
- source edition code;
- normalized card name;
- mapping status;
- confirmation scope;
- mapping evidence;
- candidate targets;
- current price;
- minimum price;
- trend price;
- available article count;
- first observed import run;
- latest observed import run;
- last missing import run;
- retirement reason;
- administrative notes;
- raw source payload.

These fields belong to mapping, price, import-control, or evidence structures unless future source requirements establish a clear product-level responsibility.

#### Open questions

- Should `source_category_id` remain text for every market source?
- Should `source_created_at` be considered an import comparison field if the source later corrects it?
- Should the first schema enforce `source_system = cardmarket` with a `CHECK` constraint?
- Can one market product ever move between source expansions, or must such a change be treated as an identity conflict?
- Should `expansion_id` be updated automatically when a previously unresolved expansion mapping becomes confirmed?
- Should product lifecycle changes use only `import_record_outcomes`, or require dedicated history later?
- Should `updated_at` be maintained by explicit merge logic or a database trigger?

### `card_market_product_mappings`

#### Purpose

Store one confirmed production relationship between a market product and the most specific supported canonical catalogue target.

A confirmed relationship may target:

- a canonical card;
- a card edition;
- a card variant.

The target depth depends on the available evidence.

Examples:

```text
confirmation_scope = card
```

means that the canonical card is confirmed, but edition, language, or finish may remain unresolved.

```text
confirmation_scope = edition
```

means that the canonical card and edition are confirmed, but language or finish may remain unresolved.

```text
confirmation_scope = variant
```

means that the canonical card, edition, language, and finish are confirmed.

A production mapping is not:

- a mapping candidate;
- an ambiguous relationship;
- an unmatched observation;
- a rejected source record;
- a market price snapshot.

Only a mapping case with accepted status `confirmed` may create a production mapping.

#### Ownership

- Data owner: confirmed mapping process.
- User editing: not allowed through the wishlist workflow.
- Normal import deletion: not allowed.
- Automatic creation from insufficient evidence: not allowed.
- Automatic replacement by weaker evidence: not allowed.
- Target reassignment: allowed only through an explicit reviewed correction or stronger confirmed evidence.
- Price data: not stored in this table.

#### Columns

| Column                           | PostgreSQL type                | Nullable | Default                    | Ownership                           | Description                                                                                                      |
| -------------------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `card_market_product_mapping_id` | `bigint` generated as identity |       No | Generated                  | Database                            | Internal surrogate primary key for the confirmed relationship.                                                   |
| `market_product_id`              | `bigint`                       |       No | None                       | Mapping-owned relationship          | References the confirmed marketplace product.                                                                    |
| `card_id`                        | `bigint`                       |       No | None                       | Mapping-owned target                | References the confirmed canonical card. Required for every confirmation scope.                                  |
| `card_edition_id`                | `bigint`                       |      Yes | `null`                     | Mapping-owned target                | References the confirmed edition when `confirmation_scope` is `edition` or `variant`.                            |
| `card_variant_id`                | `bigint`                       |      Yes | `null`                     | Mapping-owned target                | References the confirmed variant when `confirmation_scope` is `variant`.                                         |
| `mapping_case_id`                | `bigint`                       |       No | None                       | Mapping-owned evidence relationship | References the persistent mapping case that produced the confirmed relationship.                                 |
| `confirmation_scope`             | `text`                         |       No | None                       | Mapping-owned classification        | Most specific confirmed target level: `card`, `edition`, or `variant`.                                           |
| `confirmation_method`            | `text`                         |       No | None                       | Mapping-owned evidence              | Controlled method used to confirm the relationship.                                                              |
| `evidence_level`                 | `text`                         |       No | None                       | Mapping-owned evidence              | Controlled evidence level supporting confirmation.                                                               |
| `evidence_reference`             | `text`                         |       No | None                       | Mapping-owned evidence              | Durable reference to the source page, fixture record, validation result, or reviewed evidence.                   |
| `confirmed_by_import_run_id`     | `bigint`                       |      Yes | `null`                     | Mapping-owned audit                 | Import run that confirmed the mapping when confirmation was automated or import-derived.                         |
| `confirmed_at`                   | `timestamp with time zone`     |       No | Current database timestamp | Mapping-owned audit                 | Timestamp when the mapping became accepted as confirmed.                                                         |
| `is_active`                      | `boolean`                      |       No | `true`                     | Mapping-owned lifecycle             | Indicates whether this confirmed relationship is the currently active production mapping for the market product. |
| `superseded_at`                  | `timestamp with time zone`     |      Yes | `null`                     | Mapping-owned lifecycle             | Timestamp when the mapping was explicitly superseded or invalidated. Null while active.                          |
| `created_at`                     | `timestamp with time zone`     |       No | Current database timestamp | Database                            | Timestamp when the production mapping row was created.                                                           |

#### Primary key

```text
card_market_product_mapping_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- source product identifier;
- canonical card identifier;
- edition identifier;
- variant identifier;
- mapping case identifier.

#### Foreign keys

##### Market product

```text
market_product_id
→ market_products.market_product_id
```

Required behavior:

- the referenced market product must already exist;
- deleting a referenced market product must be restricted;
- normal lifecycle management must use mapping activation or supersession rather than physical deletion.

##### Canonical card

```text
card_id
→ cards.card_id
```

Required behavior:

- the referenced canonical card must already exist;
- deleting a referenced card must be restricted.

##### Edition hierarchy compatibility

```text
(
    card_edition_id,
    card_id
)
→ card_editions(
    card_edition_id,
    card_id
)
```

Required behavior:

- both columns are null only where permitted by card-level scope;
- the edition belongs to `card_id`;
- deleting a referenced edition is restricted.

##### Variant hierarchy compatibility

```text
(
    card_variant_id,
    card_edition_id
)
→ card_variants(
    card_variant_id,
    card_edition_id
)
```

Required behavior:

- both columns are null where permitted by card- or edition-level scope;
- the variant belongs to `card_edition_id`;
- the edition-to-card composite foreign key proves the remaining hierarchy;
- deleting a referenced variant is restricted.

##### Mapping case and product compatibility

```text
(
    mapping_case_id,
    market_product_id
)
→ card_market_mapping_cases(
    mapping_case_id,
    market_product_id
)
```

Required behavior:

- the mapping case belongs to the same market product;
- the mapping case current accepted status is `confirmed` when an active production mapping is created;
- deleting a referenced mapping case or market product is restricted.

##### Import run

```text
confirmed_by_import_run_id
→ import_runs.import_run_id
```

The relationship is nullable because a mapping may be confirmed through an explicit manual review rather than an import run.

#### Required constraints

##### Controlled confirmation scope

Allowed values:

- `card`;
- `edition`;
- `variant`.

##### Scope and target consistency

When:

```text
confirmation_scope = card
```

then:

```text
card_id is not null
card_edition_id is null
card_variant_id is null
```

When:

```text
confirmation_scope = edition
```

then:

```text
card_id is not null
card_edition_id is not null
card_variant_id is null
```

When:

```text
confirmation_scope = variant
```

then:

```text
card_id is not null
card_edition_id is not null
card_variant_id is not null
```

A more specific target must not be stored when the confirmation scope is less specific.

A less specific target must not be stored when the confirmation scope requires a more specific relationship.

##### One active mapping per market product

A market product may have at most one active confirmed production mapping.

Conceptual rule:

```text
UNIQUE (market_product_id)
WHERE is_active = true
```

Historical superseded mappings may remain preserved.

##### Scope-specific relationship uniqueness

Card scope:

```text
UNIQUE (market_product_id, card_id)
WHERE confirmation_scope = 'card'
```

Edition scope:

```text
UNIQUE (market_product_id, card_id, card_edition_id)
WHERE confirmation_scope = 'edition'
```

Variant scope:

```text
UNIQUE (
    market_product_id,
    card_id,
    card_edition_id,
    card_variant_id
)
WHERE confirmation_scope = 'variant'
```

The active `market_product_id` uniqueness already prevents more than one active mapping per case because one mapping case belongs to one market product. A separate active uniqueness constraint on `mapping_case_id` is not required.

##### Non-empty confirmation method

Conceptual rule:

```text
trim(confirmation_method) <> ''
```

##### Non-empty evidence level

Conceptual rule:

```text
trim(evidence_level) <> ''
```

##### Non-empty evidence reference

Conceptual rule:

```text
trim(evidence_reference) <> ''
```

##### Lifecycle consistency

When:

```text
is_active = true
```

then:

```text
superseded_at is null
```

When:

```text
is_active = false
```

then:

```text
superseded_at is not null
```

#### Confirmation scope

##### `card`

Use `card` when evidence confirms the canonical card but does not safely confirm an edition or variant.

Production effects:

- create the confirmed relationship to `card_id`;
- do not create an edition through inference;
- do not create a variant through inference;
- preserve unresolved edition, language, or finish details in mapping-review structures.

##### `edition`

Use `edition` when evidence confirms:

- canonical card;
- edition.

But does not safely confirm:

- language;
- finish;
- complete variant identity.

Production effects:

- create or reference the confirmed edition;
- create the confirmed relationship to `card_id` and `card_edition_id`;
- do not create a variant through inference.

##### `variant`

Use `variant` only when evidence confirms:

- canonical card;
- edition;
- language;
- finish.

Production effects:

- create or reference the confirmed edition;
- create or reference the confirmed variant;
- create the complete variant-level market-product relationship.

#### Confirmation method

`confirmation_method` identifies how the target was confirmed.

Initial candidate controlled values include:

- `direct_source_identifier`;
- `explicit_source_relationship`;
- `validated_derived_rule`;
- `manual_review`.

For the accepted Primal Clash direct-ID mapping, the expected method is:

```text
direct_source_identifier
```

The exact controlled list must be aligned with `mapping_status_history` and `mapping_case_observations`.

#### Evidence level

Initial allowed values:

- `direct`;
- `derived`;
- `manual`.

`insufficient` must not be used for a production confirmed mapping.

Mappings supported only by insufficient evidence remain:

- `unmatched`;
- `candidate`;
- `ambiguous`;

and create no production mapping.

#### Evidence reference

`evidence_reference` must provide a durable way to locate the confirmation evidence.

Examples include:

- Cardmarket product-page URL;
- fixture path and record identifier;
- validation report reference;
- reviewed administrative record;
- source relationship identifier.

Free-text statements such as `looks correct` are not sufficient.

The evidence reference must not contain secrets.

#### Relationship compatibility

Database constraints or merge validation must confirm:

- `card_edition_id` belongs to `card_id`;
- `card_variant_id` belongs to `card_edition_id`;
- the variant's edition belongs to `card_id`;
- `mapping_case_id` belongs to `market_product_id`.

These compatibility rules are enforced with the composite foreign keys defined above and validated again by the mapping transition transaction.

#### Mapping creation rule

Create a production mapping only when:

- the market product exists;
- the mapping case exists;
- the accepted mapping status is `confirmed`;
- the confirmation scope is known;
- all target references required by the scope exist;
- target relationships are compatible;
- evidence meets the confirmation threshold;
- no active mapping conflict exists;
- all run-level validation rules pass.

The following statuses must not create a production mapping:

- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`.

A rejected source record also creates no mapping.

#### Merge behavior

##### Inserted

Insert a mapping when:

- no equivalent confirmed relationship exists;
- the market product has no conflicting active mapping;
- the mapping case supports confirmation;
- target compatibility has been validated.

##### Unchanged

When the same active confirmed relationship already exists with equivalent accepted evidence:

- do not create a duplicate mapping;
- do not update the production row unnecessarily;
- preserve `confirmed_at`;
- preserve `created_at`;
- record the relevant import or mapping observation separately.

##### More specific confirmation

A mapping may later become more specific.

Example:

```text
card
→ edition
```

or:

```text
edition
→ variant
```

This must not update the old target fields in place.

Recommended lifecycle:

- create a new confirmed mapping row;
- set the previous mapping to inactive;
- set `superseded_at`;
- preserve the old relationship;
- record the status or target transition in mapping history;
- activate the new, more specific mapping.

This preserves the evidence available at each stage.

##### Weaker observation

A weaker later observation must not:

- modify the active confirmed mapping;
- reduce `confirmation_scope`;
- deactivate the mapping;
- replace direct evidence.

The weaker result is recorded only in `mapping_case_observations`.

##### Conflicting confirmation

A conflict exists when:

- another active mapping already exists for the market product;
- the proposed target is incompatible with the existing confirmed target;
- the mapping case belongs to another product;
- the target hierarchy is inconsistent;
- a weaker evidence source attempts to replace stronger confirmation.

A conflict must:

- prevent automatic merge;
- preserve the existing mapping;
- record review evidence;
- not create a second active mapping.

##### Superseded

A mapping may be superseded only through:

- stronger confirmed evidence;
- explicit reviewed correction;
- administrative correction supported by evidence.

Supersession sets:

```text
is_active = false
```

and:

```text
superseded_at = transition timestamp
```

The row remains preserved.

##### Missing

Absence of mapping evidence in one later import run:

- does not delete the mapping;
- does not deactivate the mapping;
- does not reduce confirmation scope;
- may create a missing or weaker observation;
- requires review if the new evidence conflicts with the accepted relationship.

#### Price eligibility boundary

A production mapping is necessary but not always sufficient for canonical-card price eligibility.

Price eligibility also depends on:

- mapping being active;
- accepted mapping status remaining `confirmed`;
- price snapshot selection;
- supported language rules;
- finish interpretation;
- price metric semantics;
- exclusion rules.

A card-level or edition-level confirmed mapping may support traceability without proving which language or finish-specific price is eligible.

The final canonical-price query must therefore not assume that every confirmed mapping is variant-level.

Only mapping and price combinations that satisfy the approved eligibility rule may contribute to the canonical-card minimum `avg30`.

#### `unmatched_duplicate_candidate`

A market product classified as `unmatched_duplicate_candidate`:

- creates no row in `card_market_product_mappings`;
- remains preserved in `market_products`;
- remains represented by its mapping case and observations;
- contributes no canonical-card price.

#### Field immutability

The following fields must not be changed through a normal in-place update:

- `market_product_id`;
- `card_id`;
- `card_edition_id`;
- `card_variant_id`;
- `mapping_case_id`;
- `confirmation_scope`;
- `confirmed_at`;
- `created_at`.

A changed confirmed target or confirmation scope creates a new mapping lifecycle row and supersedes the old row.

Evidence metadata may also be treated as immutable for a confirmed row. New evidence should normally be stored in mapping observations or status history rather than rewriting the original confirmation.

#### Primal Clash examples

##### Card-level confirmation

| Column                | Example value                     |
| --------------------- | --------------------------------- |
| `market_product_id`   | Internal Cardmarket product ID    |
| `card_id`             | Internal `xy5-20` card ID         |
| `card_edition_id`     | `null`                            |
| `card_variant_id`     | `null`                            |
| `confirmation_scope`  | `card`                            |
| `confirmation_method` | `direct_source_identifier`        |
| `evidence_level`      | `direct`                          |
| `evidence_reference`  | Product-page or fixture reference |
| `is_active`           | `true`                            |
| `superseded_at`       | `null`                            |

##### Edition-level confirmation

| Column                | Example value                     |
| --------------------- | --------------------------------- |
| `market_product_id`   | Internal Cardmarket product ID    |
| `card_id`             | Internal `xy5-20` card ID         |
| `card_edition_id`     | Internal Vulpix `V1` edition ID   |
| `card_variant_id`     | `null`                            |
| `confirmation_scope`  | `edition`                         |
| `confirmation_method` | `direct_source_identifier`        |
| `evidence_level`      | `direct`                          |
| `evidence_reference`  | Product-page or fixture reference |
| `is_active`           | `true`                            |
| `superseded_at`       | `null`                            |

##### Variant-level confirmation

| Column                | Example value                                         |
| --------------------- | ----------------------------------------------------- |
| `market_product_id`   | Internal Cardmarket product ID                        |
| `card_id`             | Internal `xy5-20` card ID                             |
| `card_edition_id`     | Internal Vulpix `V1` edition ID                       |
| `card_variant_id`     | Internal English normal variant ID                    |
| `confirmation_scope`  | `variant`                                             |
| `confirmation_method` | `direct_source_identifier` or another accepted method |
| `evidence_level`      | `direct`                                              |
| `evidence_reference`  | Product-page or fixture reference                     |
| `is_active`           | `true`                                                |
| `superseded_at`       | `null`                                                |

The actual Primal Clash mapping data must determine which scope is supported for each product.

Direct product-ID evidence alone must not be assumed to confirm language and finish.

#### Relationships

```text
market_products
    1 → zero or many card_market_product_mappings over lifecycle
```

```text
cards
    1 → zero or many card_market_product_mappings
```

```text
card_editions
    1 → zero or many edition-level or variant-level mappings
```

```text
card_variants
    1 → zero or many variant-level mappings
```

```text
card_market_mapping_cases
    1 → zero or many historical production mappings
```

Only one production mapping may be active for a market product at one time.

#### Index candidates

Indexes are not yet approved, but likely access paths include:

- active mapping lookup by `market_product_id`;
- canonical-card lookup by `card_id`;
- edition lookup by `card_edition_id`;
- variant lookup by `card_variant_id`;
- mapping-case lookup by `mapping_case_id`;
- filtering by `confirmation_scope`;
- active mapping filtering by `is_active`.

A partial unique index on active `market_product_id` is expected.

Final indexes must be selected during migration design.

#### Validation requirements

The first schema validation must confirm:

- a market product can have a card-level confirmed mapping;
- a market product can have an edition-level confirmed mapping;
- a market product can have a variant-level confirmed mapping;
- scope and nullable target columns remain consistent;
- card-level confirmation creates no required edition or variant reference;
- edition-level confirmation requires a compatible edition;
- variant-level confirmation requires a compatible edition and variant;
- the variant belongs to the edition;
- the edition belongs to the card;
- the mapping case belongs to the same market product;
- one market product cannot have two active mappings;
- historical superseded mappings remain preserved;
- `candidate`, `unmatched`, `ambiguous`, `excluded`, and `unmatched_duplicate_candidate` create no production mapping;
- weaker repeated evidence does not demote or replace a confirmed mapping;
- a more specific confirmed relationship supersedes rather than overwrites the previous row;
- duplicate identical confirmation creates no additional active mapping;
- deleting a referenced card, edition, variant, product, or mapping case is restricted;
- unresolved and excluded products contribute no canonical-card price;
- a failed production merge leaves all existing mappings unchanged.

#### Deferred fields

The following fields are not included in the first version:

- source edition code;
- source language;
- source finish;
- candidate rank;
- current mapping status;
- free-text review state;
- confidence percentage;
- current price;
- price metric selection;
- wishlist preference;
- source product URL duplicated from evidence;
- administrative comments.

These values belong to mapping-case, observation, candidate, history, price, or wishlist structures.

#### Open questions

- Which Primal Clash rows support `card`, `edition`, or `variant` confirmation scope?
- Is `evidence_reference` sufficient as one text field, or will multiple evidence records be needed later?
- Should manual confirmation use a separate reviewer identifier field in this table, or remain in `mapping_status_history`?
- Should supersession reference the replacement mapping through a `superseded_by_mapping_id` column?
- Can an active confirmed mapping ever move to a less specific scope through an administrative correction?

### `market_price_snapshots`

#### Purpose

Store one append-only market-price observation for one marketplace product at one source snapshot timestamp.

A price snapshot preserves market-source values as historical evidence.

For the first implementation, the source is Cardmarket and the relevant imported values include:

- `avg30`;
- `avg30_holo`;
- source snapshot timestamp;
- currency.

A price snapshot is not:

- a market product identity;
- a canonical card price;
- a current-price cache;
- a mapping status;
- a wishlist value.

Canonical-card pricing is derived from eligible snapshots through confirmed market-product mappings.

#### Ownership

- Data owner: market-price import process.
- User editing: not allowed.
- Normal import update: not allowed.
- Normal import deletion: not allowed.
- Historical correction: must create explicit corrective evidence rather than silently overwrite a completed snapshot.
- Canonical-card derived price: not stored in this table.

#### Columns

| Column                     | PostgreSQL type                | Nullable | Default                    | Ownership                 | Description                                                                                         |
| -------------------------- | ------------------------------ | -------: | -------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------- |
| `market_price_snapshot_id` | `bigint` generated as identity |       No | Generated                  | Database                  | Internal surrogate primary key for the price observation.                                           |
| `market_product_id`        | `bigint`                       |       No | None                       | Import-owned relationship | References the marketplace product to which the source price values belong.                         |
| `import_run_id`            | `bigint`                       |       No | None                       | Import-owned audit        | References the import run that inserted or recognized the snapshot.                                 |
| `source_snapshot_at`       | `timestamp with time zone`     |       No | None                       | Import-owned identity     | Timestamp identifying the source price snapshot.                                                    |
| `currency_code`            | `text`                         |       No | None                       | Import-owned              | Currency of the imported price values, initially expected to be `EUR`.                              |
| `avg30`                    | `numeric(12, 4)`               |      Yes | `null`                     | Import-owned observation  | Source-provided 30-day average value for the regular price field when available.                    |
| `avg30_holo`               | `numeric(12, 4)`               |      Yes | `null`                     | Import-owned observation  | Source-provided 30-day average value for the holo price field when available.                       |
| `source_reference`         | `text`                         |       No | None                       | Import-owned evidence     | Durable reference to the source artifact, fixture, file, or source record used for the observation. |
| `created_at`               | `timestamp with time zone`     |       No | Current database timestamp | Database                  | Timestamp when the snapshot row was stored in PostgreSQL.                                           |

#### Primary key

```text
market_price_snapshot_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- market-product source ID;
- import-run ID;
- source snapshot timestamp;
- source file row number.

#### Foreign keys

##### Market product

```text
market_product_id
→ market_products.market_product_id
```

Required behavior:

- the referenced market product must already exist;
- a price row must not be inserted for a rejected market product;
- deleting a market product with price history must be restricted;
- normal lifecycle handling must not cascade-delete price snapshots.

##### Import run

```text
import_run_id
→ import_runs.import_run_id
```

Required behavior:

- the import run must exist;
- the run must represent a compatible market-price import scope;
- deleting an import run referenced by snapshots must be restricted.

Snapshot rows are inserted inside the production transaction while the parent run is in `merge_started`.

They become eligible for ordinary current-price queries only after the parent run reaches `succeeded`.

A failed merge rolls back inserted snapshots before the run is marked `merge_failed`.

#### Proposed source-snapshot identity

For the first Cardmarket implementation, the proposed business uniqueness is:

```text
UNIQUE (market_product_id, source_snapshot_at)
```

This means one market product may have at most one stored price observation for one source snapshot timestamp.

Reasons:

- source-system identity is already determined by the parent `market_products` row;
- the imported fixture exposes a source snapshot timestamp;
- repeating the same source snapshot must not create duplicate price history;
- different timestamps remain separate historical observations.

This constraint remains subject to fixture validation before migrations are written.

#### Required constraints

##### Currency code

`currency_code` must contain a supported uppercase currency code.

Initial expected value:

- `EUR`.

Conceptual rule:

```text
currency_code = upper(currency_code)
and trim(currency_code) <> ''
```

The first schema uses:

```text
CHECK (currency_code = 'EUR')
```

A generic currency reference table is not required for the first implementation.

##### Non-negative prices

When present:

```text
avg30 >= 0
```

and:

```text
avg30_holo >= 0
```

Negative market prices are invalid.

Zero is technically distinguishable from null but must be accepted only if it is genuinely present in the source.

The import process must not convert:

- missing value to zero;
- invalid numeric value to zero;
- empty text to zero.

##### At least one price value

The recommended first-version rule is:

```text
avg30 is not null
or avg30_holo is not null
```

A source row with both values null contains no usable price observation.

Such a row may still be preserved in staging or validation evidence, but it should not create a production price snapshot unless an explicit reason for preserving null-only snapshots is approved.

##### Non-empty source reference

Conceptual rule:

```text
trim(source_reference) <> ''
```

##### Snapshot timestamp

`source_snapshot_at` must be non-null for authoritative Cardmarket price imports.

The database processing timestamp `created_at` must not be used as a replacement for a missing source snapshot timestamp.

#### Price precision

The proposed PostgreSQL type is:

```text
numeric(12, 4)
```

Reasons:

- market prices require exact decimal storage;
- floating-point types may introduce representation errors;
- four decimal places preserve source precision beyond ordinary two-decimal display;
- twelve total digits are more than sufficient for the MVP price range.

The UI may display fewer decimal places according to currency formatting.

Stored precision must not be reduced merely because the UI displays two decimals.

#### `avg30`

`avg30` preserves the source-provided regular 30-day average field.

The import process must:

- preserve null when unavailable;
- preserve zero only when explicitly supplied and valid;
- not copy `avg30_holo` into this field;
- not infer finish from the presence of this value;
- not treat this value as the canonical-card price by itself.

#### `avg30_holo`

`avg30_holo` preserves the source-provided holo 30-day average field.

The import process must:

- preserve null when unavailable;
- preserve zero only when explicitly supplied and valid;
- not copy `avg30` into this field;
- not assume that a non-null value proves the market product itself is a confirmed holo variant;
- not automatically create a `holo` card variant.

The value remains source evidence only and does not contribute to the first MVP canonical-price query.

#### Currency boundary

Currency is stored explicitly for every snapshot.

The canonical-card minimum price must not calculate a minimum across different currencies without a separately approved conversion rule.

Currency conversion is outside the MVP scope.

For the first Cardmarket fixture, the expected value is:

```text
EUR
```

#### Source reference

`source_reference` identifies the source artifact used to create the observation.

Examples include:

- fixture file and source product ID;
- source price file path and record reference;
- durable imported artifact identifier;
- validation report reference.

The reference must:

- remain reproducible;
- contain no secrets;
- not rely only on a temporary staging row that may later be removed.

A source checksum may later be stored through `import_runs` rather than duplicated in every price snapshot.

#### Append-only behavior

A completed price snapshot must not be updated through an ordinary import.

When the same source observation is imported again:

- resolve the same market product;
- compare the source snapshot timestamp;
- recognize the existing snapshot;
- create no new row;
- modify no existing row;
- record `unchanged` or equivalent run evidence.

When a later source snapshot is imported:

- create a new row;
- preserve all previous snapshots.

#### Corrective source data

If a source republishes corrected price values under a new snapshot timestamp:

- insert a new snapshot;
- preserve the earlier snapshot.

If a source republishes different values under the same source snapshot timestamp, the import has detected a conflict.

The process must:

- not overwrite the existing snapshot automatically;
- preserve the new staging values;
- record validation evidence;
- fail or pause the conflicting price merge according to the approved run-level rule.

A dedicated correction or supersession structure is deferred.

#### Merge behavior

##### Inserted

Insert a price snapshot when:

- the staging price row is valid;
- the market product exists;
- the source snapshot timestamp is present;
- currency is valid;
- at least one supported price value is present;
- no row exists for the proposed source-snapshot identity;
- run-level validation has passed.

##### Unchanged

When an existing row has the same:

- market product;
- source snapshot timestamp;
- currency;
- `avg30`;
- `avg30_holo`;
- accepted source reference semantics;

then:

- do not insert a duplicate;
- do not update the existing row;
- preserve `created_at`;
- record the observation as unchanged in import evidence.

##### Conflict

A conflict exists when the same proposed identity:

```text
(market_product_id, source_snapshot_at)
```

already exists with different price values or incompatible currency.

A conflict must:

- prevent automatic overwrite;
- preserve the existing historical row;
- preserve the new staging evidence;
- appear in import validation;
- follow an explicit run-level acceptance rule.

##### Rejected

A price source row is rejected when it cannot satisfy the price import contract.

Examples include:

- missing market-product source identifier;
- unresolved required market product;
- missing source snapshot timestamp;
- invalid currency;
- invalid numeric value;
- negative price;
- both supported price values null;
- duplicate conflicting source rows within one authoritative staging scope.

A rejected price row:

- creates no production snapshot;
- remains preserved through rejected-record evidence;
- does not contribute to canonical-card pricing.

##### Missing

A missing price row is not represented as deletion or retirement.

When a product has no price row in a later source snapshot:

- preserve all historical snapshots;
- do not create a fabricated null snapshot unless the source explicitly contains such a record and the null-only policy is approved;
- report missing current-price coverage through validation or derived queries.

Price snapshots do not have `is_active` or `retired_at`.

#### Canonical-card price boundary

The canonical-card `From` price is derived and is not stored in this table.

A price value may participate only when all relevant conditions are satisfied, including:

- the market product has an active confirmed mapping;
- the accepted confirmation scope and source semantics make the metric eligible;
- the product is not `excluded`;
- the product is not unresolved;
- the product is not `unmatched_duplicate_candidate`;
- the language is supported where language can be confirmed;
- the selected metric is non-null;
- the snapshot is selected by the approved current-snapshot rule;
- currencies are compatible.

The current-snapshot rule is:

```text
For each eligible market product,
select the row with the greatest source_snapshot_at
among snapshots belonging to succeeded compatible market-price runs.
```

#### Metric eligibility

The physical table preserves source metrics without claiming their final catalogue meaning.

The first MVP derived-price rule uses only:

```text
avg30
```

and only through an active variant-level mapping whose confirmed variant language is `en` or `de`.

Card-level and edition-level mappings are not price-eligible. `avg30_holo` remains stored but excluded.

#### Primal Clash example

A conceptual row may contain:

| Column                     | Example value                  |
| -------------------------- | ------------------------------ |
| `market_price_snapshot_id` | Database-generated value       |
| `market_product_id`        | Internal Cardmarket product ID |
| `import_run_id`            | Price import run ID            |
| `source_snapshot_at`       | Source-provided timestamp      |
| `currency_code`            | `EUR`                          |
| `avg30`                    | Source decimal value or `null` |
| `avg30_holo`               | Source decimal value or `null` |
| `source_reference`         | Fixture and product reference  |
| `created_at`               | Database-generated timestamp   |

The row does not contain:

- canonical card ID;
- edition ID;
- variant ID;
- mapping status;
- confirmation scope;
- calculated canonical-card minimum;
- converted currency;
- wishlist information.

#### Relationships

```text
market_products
    1 → many market_price_snapshots
```

```text
import_runs
    1 → many market_price_snapshots
```

Price snapshots have no direct foreign key to:

- cards;
- card editions;
- card variants;
- wishlist items.

Those relationships are resolved through market-product mappings.

#### Expected foreign-key behavior

- Deleting a market product referenced by snapshots must be restricted.
- Deleting an import run referenced by snapshots must be restricted.
- Superseding a market-product mapping must not delete historical price snapshots.
- Retiring a market product must preserve its snapshots.

#### Index candidates

Indexes are not yet approved, but likely access paths include:

- lookup by `(market_product_id, source_snapshot_at)`;
- latest snapshot lookup by market product;
- snapshots by `import_run_id`;
- filtering by `source_snapshot_at`;
- price availability checks for non-null `avg30`;
- price availability checks for non-null `avg30_holo`.

A likely supporting index is ordered by:

```text
market_product_id
source_snapshot_at descending
```

Final indexes must be selected during migration and validation-query design.

#### Validation requirements

The first schema validation must confirm:

- a market product can have multiple historical snapshots;
- each snapshot references an existing market product;
- each snapshot references an existing import run;
- Cardmarket price values are stored as exact decimals;
- currency is stored explicitly;
- `EUR` is accepted;
- negative values are rejected;
- null `avg30` is accepted when `avg30_holo` is present;
- null `avg30_holo` is accepted when `avg30` is present;
- both values null do not create a production snapshot under the proposed rule;
- repeating the same fixture creates no duplicate snapshots;
- the same product and timestamp cannot produce two ordinary rows;
- different timestamps create separate historical rows;
- conflicting values for the same product and timestamp do not overwrite existing history;
- historical snapshots remain unchanged after later imports;
- rejected or unresolved source price rows do not enter production;
- snapshots linked to excluded or unresolved products do not automatically contribute to canonical-card pricing;
- the six `unmatched_duplicate_candidate` products contribute no canonical-card price;
- a failed production merge leaves existing snapshots unchanged;
- null values are ignored rather than converted to zero in derived-price validation.

#### Deferred fields

The following fields are not included in the first version:

- low price;
- trend price;
- average price values outside the accepted MVP requirement;
- article count;
- foil low price;
- current-price flag;
- latest-snapshot flag;
- canonical card ID;
- edition ID;
- variant ID;
- metric eligibility flag;
- calculated canonical-card minimum;
- exchange rate;
- converted amount;
- source checksum duplicated from `import_runs`;
- source row number;
- correction reason;
- superseded snapshot reference;
- administrative notes.

These fields may be added only when validated source semantics or an approved application requirement establishes a clear responsibility.

#### Open questions

- Does every authoritative Cardmarket price fixture provide a non-null stable `source_snapshot_at`?
- Is `(market_product_id, source_snapshot_at)` sufficient for every supported source file?
- Should null-only source price observations be discarded, rejected, or preserved as explicit coverage evidence?
- Is `numeric(12, 4)` sufficient for all imported Cardmarket metrics?
- Does one Cardmarket market product represent one finish, or can `avg30` and `avg30_holo` describe distinct finish markets for the same product?
- Should same-timestamp corrected source values require a separate correction table?

## User-owned table

### `wishlist_items`

#### Purpose

Store the current user's wishlist selection for one canonical card.

The MVP uses a presence-based design:

- a row exists when the card is wanted;
- no row exists when the card is not wanted.

This table stores user-generated wishlist data only.

A wishlist item does not represent:

- a canonical card identity;
- an edition;
- a variant;
- a market product;
- a price snapshot;
- an import outcome.

The MVP wishlist references the canonical card.

Edition-, variant-, and market-product-specific preferences are deferred.

#### Ownership

- Data owner: application user.
- Catalogue import ownership: none.
- Market import ownership: none.
- User editing: allowed.
- Normal import deletion: not allowed.
- Normal import update: not allowed.
- Physical deletion by user: allowed when the card is removed from the wishlist.

Catalogue and market imports must not:

- create wishlist items;
- change wishlist quantity;
- change wishlist notes;
- delete wishlist items;
- replace wishlist references;
- copy source-derived values into wishlist fields.

#### Columns

| Column             | PostgreSQL type                | Nullable | Default                    | Ownership               | Description                                                            |
| ------------------ | ------------------------------ | -------: | -------------------------- | ----------------------- | ---------------------------------------------------------------------- |
| `wishlist_item_id` | `bigint` generated as identity |       No | Generated                  | Database                | Internal surrogate primary key for the wishlist item.                  |
| `card_id`          | `bigint`                       |       No | None                       | User-owned relationship | References the canonical card selected by the user.                    |
| `quantity`         | `integer`                      |       No | `1`                        | User-owned              | Wanted quantity for the canonical card.                                |
| `notes`            | `text`                         |      Yes | `null`                     | User-owned              | Optional free-text notes entered by the user.                          |
| `created_at`       | `timestamp with time zone`     |       No | Current database timestamp | Database                | Timestamp when the card was added to the wishlist.                     |
| `updated_at`       | `timestamp with time zone`     |       No | Current database timestamp | Database                | Timestamp of the latest actual user-owned change to quantity or notes. |

#### Primary key

```text
wishlist_item_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- canonical card source ID;
- internal card ID;
- market-product ID;
- user-visible row order.

#### Foreign key

```text
card_id
→ cards.card_id
```

Required behavior:

- the referenced canonical card must already exist;
- deleting a card referenced by a wishlist item must be restricted;
- card updates must preserve the wishlist item;
- card missing observations must preserve the wishlist item;
- card retirement must preserve the wishlist item;
- failed catalogue imports must leave the wishlist item unchanged.

#### Required constraints

##### One wishlist item per canonical card

```text
UNIQUE (card_id)
```

The single-user MVP permits at most one wishlist row per canonical card.

This prevents duplicate wishlist entries for the same card.

##### Positive quantity

```text
quantity >= 1
```

Quantity:

- defaults to `1`;
- must not be null;
- must not be zero;
- must not be negative.

##### Notes normalization

When present, notes may contain user-entered free text.

An empty string should be normalized to null where practical.

The database does not need to reject whitespace-only notes if the application layer normalizes them consistently, but the preferred stored state is:

```text
null
```

rather than empty text.

#### Presence-based wanted state

The table does not contain:

```text
is_wanted
```

Wanted state is determined by row existence.

Examples:

```text
wishlist row exists
→ wanted
```

```text
wishlist row does not exist
→ not wanted
```

Reasons:

- fewer contradictory states;
- no inactive wishlist rows with quantity and notes;
- simple Wishlist view;
- simple export scope;
- one source of truth for membership.

When the user unmarks a card as wanted, the corresponding wishlist row is deleted.

This is a normal user-owned deletion and is different from deleting imported catalogue evidence.

#### Quantity semantics

`quantity` represents the total number of copies the user wants for the canonical card.

For the MVP, it does not distinguish:

- edition;
- language;
- finish;
- market product;
- seller;
- condition.

Example:

```text
card_id = internal xy5-20 card ID
quantity = 2
```

means the user wants two copies of the canonical Vulpix card, without a stored edition or variant preference.

#### Notes semantics

`notes` stores optional user context.

Examples may include:

- preferred language;
- preferred finish;
- target condition;
- budget note;
- purchase reminder.

These notes are free text and do not create structured edition or variant relationships.

The import process must never interpret notes as mapping evidence.

#### User update behavior

##### Inserted

Create a wishlist item when:

- the canonical card exists;
- no wishlist item already exists for the card;
- quantity is valid.

Default behavior:

```text
quantity = 1
notes = null
```

unless the user supplies other values.

##### Updated

Update a wishlist item only through a user or approved application action.

Mutable fields:

- `quantity`;
- `notes`.

An actual change updates `updated_at`.

The update must preserve:

- `wishlist_item_id`;
- `card_id`;
- `created_at`.

##### Unchanged

When the submitted quantity and normalized notes are identical:

- avoid an unnecessary update where practical;
- preserve `updated_at`.

##### Deleted

Delete the row when the user removes the card from the wishlist.

Deletion removes only user-owned wishlist data.

It must not delete or modify:

- `cards`;
- `card_editions`;
- `card_variants`;
- market products;
- mappings;
- price snapshots;
- import evidence.

#### Import isolation

Catalogue imports must not include `wishlist_items` in their merge target set.

The import transaction may read wishlist relationships to validate preservation, but must not mutate them.

The following import outcomes must preserve wishlist data:

- inserted catalogue records;
- updated catalogue records;
- unchanged catalogue records;
- missing catalogue records;
- retired catalogue records;
- failed production merge;
- mapping changes;
- price imports.

A catalogue import must not reset:

- quantity to `1`;
- notes to null;
- card selection state.

#### Card lifecycle interaction

##### Card updated

When import-owned card fields change:

- preserve the wishlist row;
- preserve quantity;
- preserve notes;
- preserve wishlist timestamps unless the user-owned row itself changes.

##### Card missing

When the card receives a missing import outcome:

- preserve the wishlist row;
- preserve quantity;
- preserve notes;
- do not automatically remove the card from the Wishlist view.

The UI may later show that the catalogue record requires review, but this is outside the table responsibility.

##### Card retired

When the card is explicitly retired:

- preserve the wishlist row;
- preserve quantity;
- preserve notes.

The ordinary active catalogue view may hide the card, but the Wishlist view must remain capable of showing the user's saved selection or an appropriate retired-card state.

##### Card physical deletion

Physical deletion must be restricted while a wishlist item references the card.

If an administrative correction ever requires physical deletion, the wishlist relationship must be resolved explicitly and must not be lost through cascade deletion.

#### Timestamps

##### `created_at`

Set when the card is first added to the wishlist.

It remains unchanged through quantity and notes updates.

If the user deletes the wishlist row and later adds the card again, the new row receives a new `created_at`.

##### `updated_at`

Changes only when user-owned values actually change.

The following must not modify `updated_at`:

- catalogue import;
- market-product import;
- price import;
- mapping observation;
- card missing outcome;
- card retirement;
- unchanged wishlist submission.

The recommended implementation is explicit application or merge logic rather than a trigger that updates on every statement regardless of value changes.

#### Export boundary

Wishlist export uses `wishlist_items` as the selection source.

Exported catalogue and market values are joined at export time.

The table must not duplicate:

- card name;
- expansion name;
- collector number;
- edition name;
- language;
- finish;
- source product identifier;
- canonical `From` price.

This prevents catalogue updates from leaving stale copied values in the wishlist row.

The canonical wishlist export includes:

- source card ID;
- card name;
- collector number;
- expansion name;
- quantity;
- notes;
- nullable canonical `From` price;
- currency code;
- price-availability flag;
- card lifecycle state.

It does not include an arbitrary singular variant, language, or external product identifier because several eligible variants or products may exist for one canonical card.

Only `quantity` and `notes` originate from `wishlist_items`.

#### Primal Clash example

A conceptual wishlist row may contain:

| Column             | Example value                             |
| ------------------ | ----------------------------------------- |
| `wishlist_item_id` | Database-generated value                  |
| `card_id`          | Internal `xy5-20` card ID                 |
| `quantity`         | `2`                                       |
| `notes`            | `Prefer German reverse holo if available` |
| `created_at`       | Database-generated timestamp              |
| `updated_at`       | Database-generated timestamp              |

The structured preference remains deferred even when the note mentions a language or finish.

#### Relationships

```text
cards
    1 → zero or one wishlist_items
```

No direct relationship exists from `wishlist_items` to:

- `card_editions`;
- `card_variants`;
- `market_products`;
- `market_price_snapshots`;
- `import_runs`.

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

```text
wishlist_items.card_id
→ cards.card_id
```

An update to non-key card fields has no effect on the wishlist relationship.

The internal `card_id` must remain stable across repeated imports.

#### Index candidates

The uniqueness constraint on `card_id` provides the primary wishlist membership lookup path.

Likely access patterns include:

- list all wishlist items;
- join wishlist items to cards;
- sort by `created_at`;
- sort by `updated_at`.

Additional indexes are not required until the actual Wishlist view and export queries are reviewed.

#### Validation requirements

The first schema validation must confirm:

- a canonical card can have one wishlist item;
- a canonical card cannot have two wishlist items;
- default quantity is `1`;
- quantity `1` is accepted;
- quantity greater than `1` is accepted;
- quantity `0` is rejected;
- negative quantity is rejected;
- null quantity is rejected;
- null notes are accepted;
- user notes are preserved;
- deleting a wishlist item does not delete the card;
- deleting a referenced card is restricted;
- updating card catalogue fields preserves the wishlist item;
- a missing card outcome preserves quantity and notes;
- card retirement preserves quantity and notes;
- repeated catalogue imports preserve all wishlist data;
- repeated market imports preserve all wishlist data;
- price imports preserve all wishlist data;
- a forced production merge rollback preserves all wishlist data;
- CSV export can join the wishlist item to its canonical card without duplicated catalogue fields.

#### Deferred fields

The following fields are not included in the first version:

- `is_wanted`;
- user ID;
- edition preference;
- variant preference;
- language preference;
- finish preference;
- market-product preference;
- condition preference;
- target price;
- purchase status;
- purchased quantity;
- priority;
- tags;
- copied card name;
- copied expansion name;
- copied collector number;
- cached price;
- source product ID;
- import-run metadata;
- deletion history.

These fields require separate post-MVP requirements or an approved scope change.

#### Open questions

- Should whitespace-only notes be rejected by the database or normalized to null by the application layer?
- Is an upper quantity limit required to prevent accidental or invalid values?
- Retired cards remain visible in the Wishlist view while a wishlist row exists.
- Should wishlist deletion history be preserved later, or is physical deletion appropriate for the single-user MVP?
- Should `updated_at` be maintained by application logic or a narrowly defined database trigger?

## Import-control tables

### `import_runs`

#### Purpose

Store one controlled import execution and its declared source scope.

An import run is the root audit record for:

- source loading;
- staging;
- validation;
- production merge;
- rejected records;
- mapping observations;
- merge outcomes;
- price snapshot insertion;
- final reconciliation;
- failure reporting.

An import run is not:

- a staging row;
- a production entity;
- a mapping status;
- a backup record;
- a wishlist operation.

#### Ownership

- Data owner: import-control process.
- User editing: not allowed through the wishlist workflow.
- Mutable while active: yes.
- Mutable after terminal state: no, except through an explicit administrative correction.
- Normal import deletion: not allowed.
- Child evidence deletion through cascade: not allowed.

#### Columns

| Column                      | PostgreSQL type                | Nullable | Default                    | Ownership                      | Description                                                                                                 |
| --------------------------- | ------------------------------ | -------: | -------------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `import_run_id`             | `bigint` generated as identity |       No | Generated                  | Database                       | Internal surrogate primary key for the import execution.                                                    |
| `run_reference`             | `text`                         |       No | None                       | Import-control identity        | Human-readable unique reference for logs and evidence, for example `primal-clash-catalogue-2026-07-28-001`. |
| `run_kind`                  | `text`                         |       No | None                       | Import-control classification  | Controlled type of import operation.                                                                        |
| `source_system`             | `text`                         |       No | None                       | Import-control scope           | Primary external source system processed by the run.                                                        |
| `source_entity_type`        | `text`                         |       No | None                       | Import-control scope           | Primary source entity category processed by the run.                                                        |
| `source_artifact_reference` | `text`                         |       No | None                       | Import-control evidence        | Durable reference to the source file, fixture, directory, or collected artifact.                            |
| `source_artifact_checksum`  | `text`                         |      Yes | `null`                     | Import-control evidence        | Checksum of the source artifact when available.                                                             |
| `scope_type`                | `text`                         |       No | None                       | Import-control scope           | Controlled type describing the import boundary, such as one expansion or a selected subset.                 |
| `scope_reference`           | `text`                         |       No | None                       | Import-control scope           | Stable reference describing the declared scope, for example `pokemon_tcg_data:xy5`.                         |
| `is_authoritative`          | `boolean`                      |       No | `false`                    | Import-control scope           | Indicates whether the run represents a complete authoritative view of the declared scope.                   |
| `status`                    | `text`                         |       No | `created`                  | Import-control lifecycle       | Current lifecycle status of the import run.                                                                 |
| `started_at`                | `timestamp with time zone`     |       No | Current database timestamp | Import-control lifecycle       | Timestamp when the import run was created or started.                                                       |
| `staging_loaded_at`         | `timestamp with time zone`     |      Yes | `null`                     | Import-control lifecycle       | Timestamp when source loading into staging completed.                                                       |
| `validated_at`              | `timestamp with time zone`     |      Yes | `null`                     | Import-control lifecycle       | Timestamp when pre-merge validation completed successfully.                                                 |
| `merge_started_at`          | `timestamp with time zone`     |      Yes | `null`                     | Import-control lifecycle       | Timestamp when the atomic production merge began.                                                           |
| `completed_at`              | `timestamp with time zone`     |      Yes | `null`                     | Import-control lifecycle       | Timestamp when the run reached a terminal state.                                                            |
| `failure_code`              | `text`                         |      Yes | `null`                     | Import-control failure         | Controlled failure code for a failed run.                                                                   |
| `failure_detail`            | `text`                         |      Yes | `null`                     | Import-control failure         | Human-readable failure explanation without secrets.                                                         |
| `importer_version`          | `text`                         |       No | None                       | Import-control reproducibility | Script version, repository commit, release identifier, or equivalent importer revision.                     |
| `total_source_records`      | `integer`                      |      Yes | `null`                     | Validated summary              | Total source records declared or observed in the run.                                                       |
| `valid_source_records`      | `integer`                      |      Yes | `null`                     | Validated summary              | Number of source records that passed source-record validation.                                              |
| `rejected_records`          | `integer`                      |      Yes | `null`                     | Validated summary              | Number of rejected source records.                                                                          |
| `inserted_records`          | `integer`                      |      Yes | `null`                     | Validated summary              | Number of production entity outcomes classified as inserted.                                                |
| `updated_records`           | `integer`                      |      Yes | `null`                     | Validated summary              | Number of production entity outcomes classified as updated.                                                 |
| `unchanged_records`         | `integer`                      |      Yes | `null`                     | Validated summary              | Number of production entity outcomes classified as unchanged.                                               |
| `missing_records`           | `integer`                      |      Yes | `null`                     | Validated summary              | Number of production entities observed as missing within an authoritative scope.                            |
| `retired_records`           | `integer`                      |      Yes | `null`                     | Validated summary              | Number of production entities explicitly retired.                                                           |
| `created_at`                | `timestamp with time zone`     |       No | Current database timestamp | Database                       | Database row creation timestamp.                                                                            |
| `updated_at`                | `timestamp with time zone`     |       No | Current database timestamp | Database                       | Timestamp of the latest actual lifecycle or summary change while the run is active.                         |

#### Primary key

```text
import_run_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- source artifact checksum;
- source timestamp;
- repository commit;
- run reference;
- source file name.

#### Run reference

`run_reference` is a human-readable operational identifier.

Required uniqueness:

```text
UNIQUE (run_reference)
```

It should be deterministic enough for logs and evidence, but business integrity must still rely on `import_run_id`.

Recommended format:

```text
<scope>-<run-kind>-<timestamp-or-sequence>
```

Example:

```text
primal-clash-catalogue-2026-07-28-001
```

The reference must:

- contain non-whitespace text;
- contain no secrets;
- remain stable after run creation.

#### Controlled run kinds

Initial allowed values:

- `catalogue`;
- `market_products`;
- `market_prices`;
- `market_mappings`.

A run kind describes the logical operation.

It does not by itself define whether the run is authoritative.

#### Controlled source entity types

Initial allowed values:

- `card`;
- `market_product`;
- `market_price`;
- `market_mapping`.

The exact list must align with staging and outcome structures.

#### Source system

Initial allowed values:

- `pokemon_tcg_data`;
- `cardmarket`.

Each MVP import run has one source contract. Cross-source orchestration is handled outside the individual database run.

#### Source artifact reference

`source_artifact_reference` identifies the imported input.

Examples:

- fixture directory;
- source file path;
- collected artifact identifier;
- manifest path.

The reference must:

- remain durable after staging cleanup;
- contain no credentials or tokens;
- not rely only on a temporary file path that will be deleted without replacement evidence.

#### Source artifact checksum

`source_artifact_checksum` stores a checksum when practical.

Recommended initial format:

```text
sha256:<hexadecimal digest>
```

The checksum:

- supports repeat-import recognition;
- supports evidence integrity;
- does not replace source-scoped entity identity;
- must not be used as the only run identity.

A null checksum is permitted when the source is not represented by one stable artifact, but the reason should be documented operationally.

#### Scope type

Initial candidate values:

- `expansion`;
- `source_file`;
- `selected_records`;
- `complete_source_snapshot`;

Examples:

```text
scope_type = expansion
scope_reference = pokemon_tcg_data:xy5
```

```text
scope_type = expansion
scope_reference = cardmarket:1585
```

#### Authoritative scope

`is_authoritative = true` means the run represents a complete view of the declared scope for its source entity type.

This flag permits missing-record detection.

Examples:

- complete `xy5` canonical-card fixture: authoritative for canonical cards in `xy5`;
- selected synthetic rejected rows: not authoritative;
- partial price sample: not authoritative;
- complete Cardmarket product snapshot for expansion `1585`: authoritative only if the source and fixture contract establish completeness.

A run must not be marked authoritative merely because:

- the file loaded successfully;
- the fixture contains many rows;
- no validation error occurred;
- the import is called complete informally.

The declared scope must be validated before production merge.

#### Lifecycle status

Initial controlled statuses:

- `created`;
- `staging_loaded`;
- `validation_failed`;
- `validated`;
- `merge_started`;
- `merge_failed`;
- `succeeded`;
- `cancelled`.

#### Successful lifecycle

```text
created
→ staging_loaded
→ validated
→ merge_started
→ succeeded
```

#### Validation failure lifecycle

```text
created
→ staging_loaded
→ validation_failed
```

#### Merge failure lifecycle

```text
created
→ staging_loaded
→ validated
→ merge_started
→ merge_failed
```

#### Cancellation lifecycle

```text
created
→ cancelled
```

or:

```text
staging_loaded
→ cancelled
```

Cancellation after the atomic production merge begins is not allowed unless the merge transaction is rolled back.

#### Terminal states

Terminal statuses:

- `validation_failed`;
- `merge_failed`;
- `succeeded`;
- `cancelled`.

When a run reaches a terminal state:

- `completed_at` is required;
- lifecycle timestamps must no longer change;
- summary values become immutable;
- child outcomes and evidence become append-only;
- ordinary application actions must not reopen the run.

An administrative correction must be explicit and auditable.

#### Required constraints

##### Non-empty run reference

```text
trim(run_reference) <> ''
```

##### Non-empty run kind

```text
trim(run_kind) <> ''
```

##### Non-empty source system

```text
trim(source_system) <> ''
```

##### Non-empty source entity type

```text
trim(source_entity_type) <> ''
```

##### Non-empty artifact reference

```text
trim(source_artifact_reference) <> ''
```

##### Non-empty scope type

```text
trim(scope_type) <> ''
```

##### Non-empty scope reference

```text
trim(scope_reference) <> ''
```

##### Non-empty importer version

```text
trim(importer_version) <> ''
```

##### Terminal completion timestamp

When status is terminal:

```text
completed_at is not null
```

When status is active:

```text
completed_at is null
```

##### Failure-field consistency

For:

- `validation_failed`;
- `merge_failed`;

the run requires:

```text
failure_code is not null
```

For `succeeded`:

```text
failure_code is null
failure_detail is null
```

A cancelled run may use a controlled cancellation code.

##### Lifecycle timestamp order

Where timestamps are present:

```text
started_at
<= staging_loaded_at
<= validated_at
<= merge_started_at
<= completed_at
```

The exact required chain depends on the terminal path.

For example, `validation_failed` does not require `validated_at` or `merge_started_at`.

##### Non-negative summary counts

When present, all summary counts must be:

```text
>= 0
```

##### Summary timing

Summary counts may remain null while a run is active.

Before `succeeded`, required summary fields must be populated and reconciled.

For failed runs, partial counts may be stored when they are accurate and clearly interpreted.

#### Summary reconciliation

Summary columns are operational snapshots.

They are not the primary evidence source.

Detailed evidence remains in:

- staging tables;
- `import_record_outcomes`;
- `rejected_source_records`;
- `mapping_case_observations`;
- `market_price_snapshots`.

Before a run becomes `succeeded`, summary counts must reconcile with the declared scope.

At minimum:

```text
total_source_records
=
valid_source_records
+
rejected_records
```

when the source contract makes this reconciliation applicable.

Entity merge outcomes should reconcile with valid records according to the run kind.

For example, a market-product run may reconcile:

```text
valid_source_records
=
inserted_records
+
updated_records
+
unchanged_records
```

with missing records reported separately because missing production entities do not correspond to current source rows.

The exact formulas must be defined per run kind.

#### Missing detection

Missing detection is allowed only when:

```text
is_authoritative = true
```

and the declared scope has passed validation.

A partial or synthetic run must not produce missing outcomes for records outside its input.

Missing detection compares:

```text
existing production identities in declared scope
minus
validated staged identities in current run
```

Missing observations:

- do not delete production rows;
- do not retire production rows automatically;
- do not modify wishlist data.

#### Transaction boundary

The production merge must execute in one atomic database transaction.

The sequence is:

1. Create the import run.
2. Load source records into staging.
3. Validate staging rows.
4. Validate run-level invariants.
5. Stop before production changes if validation fails.
6. Start the production merge transaction.
7. Merge parent production entities.
8. Merge dependent production entities.
9. Merge confirmed mappings.
10. Insert price snapshots.
11. Record production outcomes that belong inside the merge boundary.
12. Commit.
13. Mark the run as `succeeded`.

If the production merge fails:

- roll back all production changes;
- preserve the previous consistent production state;
- preserve wishlist data;
- mark the run `merge_failed`;
- retain staging and validation evidence.

Run creation, staging loading, and post-rollback failure recording may use separate transactions.

#### Status-transition ownership

The import process is responsible for valid status transitions.

A direct transition such as:

```text
created
→ succeeded
```

is invalid.

A run must not enter:

```text
merge_started
```

before validation succeeds.

A run must not enter:

```text
succeeded
```

before the production transaction commits.

#### `updated_at`

`updated_at` changes only when a real run-level value changes while the run is active.

It must not be modified by repeated reads or evidence queries.

After terminal completion, `updated_at` becomes immutable except for an explicit administrative correction.

Explicit import-control logic is preferred over a generic trigger that updates on every statement.

#### Deletion behavior

Import runs are audit records and must not be deleted through normal operations.

Foreign-key relationships from child tables must use restrictive behavior.

Staging cleanup must delete staging rows according to retention policy without deleting the parent import run.

#### Primal Clash examples

##### Canonical-card run

| Column                 | Example value                       |
| ---------------------- | ----------------------------------- |
| `run_reference`        | `primal-clash-cards-2026-07-28-001` |
| `run_kind`             | `catalogue`                         |
| `source_system`        | `pokemon_tcg_data`                  |
| `source_entity_type`   | `card`                              |
| `scope_type`           | `expansion`                         |
| `scope_reference`      | `pokemon_tcg_data:xy5`              |
| `is_authoritative`     | `true`                              |
| `status`               | `succeeded`                         |
| `total_source_records` | `164`                               |
| `valid_source_records` | `164`                               |
| `rejected_records`     | `0`                                 |

##### Mapping run

| Column               | Example value                                    |
| -------------------- | ------------------------------------------------ |
| `run_reference`      | `primal-clash-mappings-2026-07-28-001`           |
| `run_kind`           | `market_mappings`                                |
| `source_system`      | `cardmarket`                                     |
| `source_entity_type` | `market_mapping`                                 |
| `scope_type`         | `expansion`                                      |
| `scope_reference`    | `cardmarket:1585`                               |
| `is_authoritative`   | `true` only if fixture completeness is validated |
| `status`             | `succeeded`                                      |

Detailed mapping counts remain in mapping observations and import reports rather than being forced into the generic merge-summary columns.

#### Relationships

```text
import_runs
    1 → many staging_cards
```

```text
import_runs
    1 → many staging_market_products
```

```text
import_runs
    1 → many staging_market_prices
```

```text
import_runs
    1 → many staging_market_mappings
```

```text
import_runs
    1 → many import_record_outcomes
```

```text
import_runs
    1 → many rejected_source_records
```

```text
import_runs
    1 → many mapping_case_observations
```

```text
import_runs
    1 → many market_price_snapshots
```

#### Expected foreign-key behavior

- Deleting an import run referenced by staging rows must be restricted until staging cleanup explicitly removes those rows.
- Deleting an import run referenced by permanent evidence must be restricted.
- Staging cleanup must not cascade into outcomes, rejected records, observations, or price snapshots.
- Production entities may reference the import run that created or last changed them only if those relationships are later approved.

#### Index candidates

Likely access paths include:

- lookup by `run_reference`;
- filtering by `status`;
- filtering by `run_kind`;
- filtering by `source_system`;
- filtering by `scope_reference`;
- ordering by `started_at`;
- finding active non-terminal runs;
- finding failed runs;
- finding the latest successful run for one scope.

Potential composite index direction:

```text
source_system
scope_type
scope_reference
status
completed_at descending
```

Final indexes must be selected after import and current-price queries are defined.

#### Validation requirements

The first schema validation must confirm:

- a run receives a generated internal primary key;
- `run_reference` is unique;
- blank required references are rejected;
- an active run may have null summary counts;
- a successful run requires `completed_at`;
- a failed run requires a failure code;
- a successful run cannot retain failure fields;
- lifecycle timestamps remain ordered;
- invalid lifecycle transitions are rejected by the import process;
- missing detection cannot run for a non-authoritative scope;
- a validation failure creates no production changes;
- a merge failure rolls back all production changes;
- wishlist data remains unchanged after validation and merge failures;
- successful summary counts reconcile with detailed evidence;
- the second identical Primal Clash import creates a new import run but no duplicate production entities;
- historical import runs remain preserved after staging cleanup;
- deleting a run referenced by permanent evidence is restricted.

#### Deferred fields

The following fields are not included in the first version:

- scheduler job ID;
- host name;
- container ID;
- database transaction ID;
- retry count;
- parent import run;
- dry-run flag;
- manual approval state;
- warning count;
- excluded mapping count;
- candidate mapping count;
- unmatched mapping count;
- ambiguous mapping count;
- duplicate-candidate count;
- resolved mapping count;
- duration in a stored column;
- backup reference;
- rollback backup ID;
- free-text administrative notes.

Mapping-specific summary counts may later be added if operational reporting demonstrates a clear need.

#### Open questions

- Which summary fields are mandatory for each run kind?
- Should excluded and unresolved mapping counts be added directly to `import_runs` or remain derived?
- Should `source_artifact_checksum` be required for fixture-based imports?
- Should cancelled runs require `failure_code` or a separate cancellation field?
- How long should successful staging rows remain after the run completes?
- Should importer version store a Git commit, script version, release tag, or a structured combination?
- Should active-run status transitions be protected by database constraints, application logic, or both?

### `staging_cards`

#### Purpose

Store normalized canonical-card source records for one import run before validation and production merge.

The table provides a controlled boundary between:

- raw source ingestion;
- record-level normalization;
- run-level validation;
- production merge into `cards`.

A staging card row represents one source card observation within one import run.

It is not:

- the permanent canonical card;
- a rejected-record archive;
- a production merge outcome;
- a wishlist item;
- a market-product mapping.

#### Ownership

- Data owner: catalogue import process.
- User editing: not allowed.
- Production application access: not required.
- Mutable while the parent import run is active: yes.
- Mutable after validation begins: restricted.
- Long-term retention: not required after the configured staging retention period.
- Deletion: allowed only through explicit staging cleanup after permanent evidence has been preserved.

#### Columns

| Column                    | PostgreSQL type                | Nullable | Default                    | Ownership                   | Description                                                                                                                                         |
| ------------------------- | ------------------------------ | -------: | -------------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `staging_card_id`         | `bigint` generated as identity |       No | Generated                  | Database                    | Internal surrogate primary key for the staged row.                                                                                                  |
| `import_run_id`           | `bigint`                       |       No | None                       | Import-control relationship | References the catalogue import run that loaded the source record.                                                                                  |
| `source_record_reference` | `text`                         |       No | None                       | Import-owned identity       | Stable reference to the source record within the imported artifact.                                                                                 |
| `source_system`           | `text`                         |       No | None                       | Import-owned identity       | Controlled catalogue source identifier, initially `pokemon_tcg_data`.                                                                               |
| `source_card_id`          | `text`                         |      Yes | `null`                     | Import-owned source value   | Source-scoped card identifier after basic normalization, for example `xy5-20`. Nullable so malformed source rows can still be staged and validated. |
| `source_expansion_id`     | `text`                         |      Yes | `null`                     | Import-owned source value   | Source expansion identifier after basic normalization, for example `xy5`.                                                                           |
| `collector_number`        | `text`                         |      Yes | `null`                     | Import-owned source value   | Collector number after basic normalization.                                                                                                         |
| `name`                    | `text`                         |      Yes | `null`                     | Import-owned source value   | Card display name after basic normalization.                                                                                                        |
| `rarity`                  | `text`                         |      Yes | `null`                     | Import-owned source value   | Source-provided rarity when available.                                                                                                              |
| `image_small_url`         | `text`                         |      Yes | `null`                     | Import-owned source value   | Small image URL or deterministically validated source reference.                                                                                    |
| `image_large_url`         | `text`                         |      Yes | `null`                     | Import-owned source value   | Large image URL or deterministically validated source reference.                                                                                    |
| `raw_payload`             | `jsonb`                        |       No | None                       | Import-owned evidence       | Raw or minimally transformed source record used for validation and troubleshooting.                                                                 |
| `record_checksum`         | `text`                         |      Yes | `null`                     | Import-owned evidence       | Deterministic checksum of the normalized source record when available.                                                                              |
| `normalization_status`    | `text`                         |       No | `pending`                  | Import-control state        | Current normalization result for the staging row.                                                                                                   |
| `validation_status`       | `text`                         |       No | `pending`                  | Import-control state        | Current record-level validation result.                                                                                                             |
| `validation_completed_at` | `timestamp with time zone`     |      Yes | `null`                     | Import-control state        | Timestamp when record-level validation reached a terminal result.                                                                                   |
| `created_at`              | `timestamp with time zone`     |       No | Current database timestamp | Database                    | Timestamp when the staging row was inserted.                                                                                                        |
| `updated_at`              | `timestamp with time zone`     |       No | Current database timestamp | Database                    | Timestamp of the latest actual staging or validation-state change.                                                                                  |

#### Primary key

```text
staging_card_id
```

The primary key is internal to staging.

It must not be reused as:

- production `card_id`;
- source card identity;
- import outcome identity;
- rejected-record identity.

#### Foreign key

```text
import_run_id
→ import_runs.import_run_id
```

Required behavior:

- the parent import run must already exist;
- the run kind and source entity type must permit card staging;
- deleting the import run must be restricted while staging rows remain;
- staging cleanup must delete child rows explicitly before any administrative run deletion.

#### Required constraints

##### Source-record uniqueness within one run

```text
UNIQUE (import_run_id, source_record_reference)
```

One source record reference must create at most one staging row in one import run.

The same source record reference may appear in another import run.

##### Non-empty source-record reference

Conceptual rule:

```text
trim(source_record_reference) <> ''
```

##### Non-empty source system

Conceptual rule:

```text
trim(source_system) <> ''
```

##### Raw payload required

`raw_payload` must always be present.

A source row that cannot be fully normalized must still preserve its original evidence.

The raw payload must not contain credentials, access tokens, or unrelated secrets.

##### Optional normalized-value consistency

When present, the following values must contain non-whitespace text:

- `source_card_id`;
- `source_expansion_id`;
- `collector_number`;
- `name`;
- `rarity`;
- `image_small_url`;
- `image_large_url`;
- `record_checksum`.

Empty source strings should normally be normalized to null before validation.

#### Why core fields are nullable

Production `cards` requires non-null values for:

- source card ID;
- expansion relationship;
- collector number;
- name.

The corresponding staging fields remain nullable because staging must preserve malformed and incomplete source rows long enough to:

- validate them;
- explain rejection;
- reconcile source counts;
- preserve raw evidence;
- avoid losing records during ingestion.

A null required source value produces a validation failure rather than a staging insert failure.

#### Source record reference

`source_record_reference` identifies the row inside the source artifact.

Examples include:

```text
cards/xy5.json#xy5-20
```

```text
fixture:primal-clash/cards#record-20
```

```text
source-file.json#line-21
```

The reference must be:

- stable within the import artifact;
- reproducible;
- unique within one run;
- independent from the generated staging primary key.

When a valid source ID exists, it may participate in the reference, but the reference must still support malformed rows that have no usable source ID.

#### Raw payload

`raw_payload` preserves the source record used by the importer.

It supports:

- validation troubleshooting;
- rejected-record evidence;
- normalization review;
- fixture reconciliation;
- future parser corrections.

The production merge must not copy the entire raw payload into `cards`.

Before staging cleanup, any payload required for permanent rejection or mapping evidence must be copied to the appropriate permanent evidence structure.

#### Record checksum

`record_checksum` represents the deterministic normalized content of one source row.

Recommended input fields include:

- source system;
- source card ID;
- source expansion ID;
- collector number;
- name;
- rarity;
- image URLs.

The checksum may support:

- duplicate detection inside one run;
- repeated-source comparison;
- debugging normalization differences.

It must not replace:

- `(source_system, source_card_id)` as production identity;
- `source_record_reference` as staging identity;
- source-artifact checksum on `import_runs`.

Recommended representation:

```text
sha256:<hexadecimal digest>
```

#### Normalization status

Initial controlled values:

- `pending`;
- `normalized`;
- `normalization_failed`.

##### `pending`

The source row has been loaded but normalization has not reached a terminal result.

##### `normalized`

The importer completed supported normalization.

This does not mean the row is valid for production.

##### `normalization_failed`

The row could not be normalized according to the source contract.

A normalization failure:

- preserves the staging row;
- preserves `raw_payload`;
- must produce permanent rejection evidence before staging cleanup;
- prevents production merge for the row.

#### Validation status

Initial controlled values:

- `pending`;
- `valid`;
- `rejected`.

##### `pending`

Record-level validation has not completed.

##### `valid`

The row satisfies the card staging contract and may participate in run-level validation.

It does not guarantee that the production run will succeed.

##### `rejected`

The row fails one or more record-level rules and must not enter production.

Structured rejection reasons belong to:

- `rejected_source_records`;
- `rejected_source_record_reasons`.

#### State consistency

##### Pending validation

When:

```text
validation_status = pending
```

then:

```text
validation_completed_at is null
```

##### Terminal validation

When:

```text
validation_status in (valid, rejected)
```

then:

```text
validation_completed_at is not null
```

##### Normalization failure

When:

```text
normalization_status = normalization_failed
```

then the row must not have:

```text
validation_status = valid
```

##### Valid row

When:

```text
validation_status = valid
```

then:

```text
normalization_status = normalized
```

#### Normalization boundary

Staging normalization may perform only documented deterministic transformations.

Supported transformations include:

- trimming leading and trailing whitespace;
- converting empty optional strings to null;
- parsing supported timestamps;
- preserving collector numbers as text;
- normalizing known image URL fields;
- constructing deterministic source references;
- calculating record checksums.

The importer must not:

- invent a missing source card ID;
- infer collector number from card name;
- translate card names;
- assign an internal expansion by name similarity;
- create edition or variant information;
- infer marketplace relationships;
- silently repair materially ambiguous source values.

Materially corrected values require either:

- an approved deterministic source rule; or
- rejection and reviewed correction evidence.

#### Record-level validation

A staging card is valid only when all required conditions hold.

At minimum:

- `source_system` is supported;
- `source_card_id` is non-null and non-empty;
- `source_expansion_id` is non-null and non-empty;
- `collector_number` is non-null and non-empty;
- `name` is non-null and non-empty;
- source identifiers have valid normalized form;
- image URLs satisfy the accepted source rule when present;
- the row contains no unsupported structural conflict;
- the raw payload remains available.

The following are allowed:

- null rarity;
- null small image URL when source evidence permits it;
- null large image URL when source evidence permits it.

The exact image requirements must match the accepted Primal Clash fixture contract.

#### Run-level validation

Rows marked `valid` participate in run-level checks.

For Primal Clash, run-level validation should confirm:

- exactly `164` valid canonical cards are expected for the accepted fixture;
- all valid rows belong to source expansion `xy5`;
- `(source_system, source_card_id)` is unique within the valid staging set;
- source record references are unique;
- collector numbers and names satisfy accepted fixture rules;
- no production merge begins while a staging row remains pending;
- rejected counts reconcile with the parent import run.

A duplicate production identity inside one run must not be resolved through arbitrary row selection.

It must cause:

- rejection of conflicting rows; or
- run-level validation failure;

according to the approved validation rule.

#### Production resolution

A valid staged card resolves production identity through:

```text
(source_system, source_card_id)
```

The production merge then resolves:

```text
source_expansion_id
→ expansion_source_identifiers
→ expansions.expansion_id
```

A valid staging row must not merge into `cards` when its expansion identifier cannot be resolved uniquely.

Such a failure must be detected before production changes begin.

#### Production merge comparison

For an existing production card, compare normalized values for:

- resolved `expansion_id`;
- `collector_number`;
- `name`;
- `rarity`;
- `image_small_url`;
- `image_large_url`.

The staging row does not directly set:

- production `card_id`;
- production lifecycle state without an approved rule;
- production timestamps;
- wishlist fields;
- edition or variant data;
- mapping relationships.

#### Merge outcomes

Each valid staging card should produce one detailed production outcome, such as:

- `inserted`;
- `updated`;
- `unchanged`.

For authoritative scope comparison, existing production cards absent from staging may produce separate:

- `missing`;
- `retired`;

outcomes according to approved lifecycle rules.

The staging row itself must not store the final production outcome.

Detailed outcomes belong to `import_record_outcomes`.

#### Rejected rows

A rejected staging row:

- creates no production card;
- creates no edition;
- creates no variant;
- creates no wishlist item;
- creates no mapping;
- must preserve permanent rejection evidence before staging cleanup.

The staging row may later be deleted under retention policy after permanent rejection evidence has been verified.

#### Mutability

##### Before normalization completes

The importer may populate normalized fields and change:

- `normalization_status`;
- `validation_status`;
- `validation_completed_at`;
- `updated_at`.

##### After validation completes

Normalized source values should become immutable for the run.

A parser correction should normally require:

- a new import run; or
- an explicit reset of the active run before production merge begins.

##### After merge starts

Staging card values must not change.

The merge transaction must operate on a stable validated staging set.

##### After terminal run status

Staging rows are read-only until retention cleanup.

#### Cleanup behavior

Staging cleanup may occur only after:

- the parent run has reached a terminal state;
- required detailed outcomes are preserved;
- rejected-record evidence is preserved;
- mapping evidence derived from staging is preserved;
- source-artifact references remain available;
- retention policy permits deletion.

Cleanup deletes staging rows only.

It must not delete:

- the import run;
- production cards;
- outcomes;
- rejected records;
- wishlist data;
- mappings;
- price snapshots.

#### Primal Clash example

A conceptual valid staged Vulpix row may contain:

| Column                    | Example value                                   |
| ------------------------- | ----------------------------------------------- |
| `staging_card_id`         | Database-generated value                        |
| `import_run_id`           | Primal Clash catalogue import run ID            |
| `source_record_reference` | `cards/xy5.json#xy5-20`                         |
| `source_system`           | `pokemon_tcg_data`                              |
| `source_card_id`          | `xy5-20`                                        |
| `source_expansion_id`     | `xy5`                                           |
| `collector_number`        | `20`                                            |
| `name`                    | `Vulpix`                                        |
| `rarity`                  | Source value or `null`                          |
| `image_small_url`         | `https://images.pokemontcg.io/xy5/20.png`       |
| `image_large_url`         | `https://images.pokemontcg.io/xy5/20_hires.png` |
| `raw_payload`             | Source JSON object                              |
| `record_checksum`         | Deterministic checksum                          |
| `normalization_status`    | `normalized`                                    |
| `validation_status`       | `valid`                                         |
| `validation_completed_at` | Validation timestamp                            |
| `created_at`              | Database-generated timestamp                    |
| `updated_at`              | Latest staging-state timestamp                  |

A malformed row with no source card ID may still be staged with:

```text
source_card_id = null
validation_status = rejected
```

provided that its raw payload and rejection evidence are preserved.

#### Relationships

```text
import_runs
    1 → many staging_cards
```

A staging card has no direct foreign key to:

- `cards`;
- `expansions`;
- `wishlist_items`;
- `card_editions`;
- `card_variants`.

Production identities are resolved during validated merge rather than stored as mutable staging foreign keys.

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

```text
staging_cards.import_run_id
→ import_runs.import_run_id
```

Staging cleanup uses explicit deletion of staging rows.

#### Index candidates

Likely access paths include:

- all rows by `import_run_id`;
- lookup by `(import_run_id, source_record_reference)`;
- valid rows by import run;
- rejected rows by import run;
- lookup by `(import_run_id, source_system, source_card_id)`;
- duplicate detection by source-scoped identity;
- pending validation rows.

Potential supporting index:

```text
import_run_id
validation_status
```

Final indexes must be selected during migration and validation-query design.

#### Validation requirements

The first schema validation must confirm:

- all `164` accepted Primal Clash canonical cards can be staged;
- every source row preserves a raw payload;
- valid `xy5-20` data can be normalized without losing collector-number text;
- null rarity is accepted;
- malformed rows can be staged instead of being lost at insert time;
- blank required values cause rejection rather than production merge;
- source-record references are unique within one run;
- the same source record may appear in a later import run;
- duplicate source-scoped identities within one run are detected;
- no staging row remains pending before production merge;
- a normalization-failed row cannot be marked valid;
- a rejected row creates no production card;
- valid rows resolve the Primal Clash expansion through `pokemon_tcg_data / xy5`;
- unresolved expansion identity prevents production merge;
- repeated identical imports use separate staging rows in separate runs;
- staging cleanup preserves permanent run, outcome, and rejection evidence;
- deleting staging rows does not affect production cards or wishlist data.

#### Deferred fields

The following fields are not included in the first version:

- resolved production `card_id`;
- resolved internal `expansion_id`;
- production merge outcome;
- merge error text;
- source update timestamp;
- parser warning list;
- normalization rule version;
- source row number as a separate numeric field;
- supertype;
- types;
- attacks;
- weaknesses;
- artist;
- legalities;
- local image path;
- image checksum;
- edition data;
- variant data;
- market mapping data.

These fields may be added only when the importer contract establishes a clear staging responsibility.

#### Open questions

- Should `raw_payload` preserve the exact source object or a minimally sanitized representation?
- Should `record_checksum` be mandatory for fixture-based imports?
- Should valid staging rows require both image URLs for the accepted Primal Clash vertical slice?
- Should duplicate source identities reject individual rows or fail the complete run?
- Should source record references use fixture paths, record IDs, row numbers, or a standardized combination?
- Should normalized staging values become database-protected against changes after validation?
- What staging retention period is appropriate after successful and failed imports?

### `staging_market_products`

#### Purpose

Store normalized marketplace product source records for one import run before validation and production merge.

For the first implementation, the source system is Cardmarket.

The table provides a controlled boundary between:

- raw marketplace product ingestion;
- source-field normalization;
- record-level validation;
- run-level reconciliation;
- production merge into `market_products`;
- later mapping classification.

A staging market-product row is not:

- the permanent market product;
- a confirmed catalogue mapping;
- a mapping candidate;
- an exclusion decision;
- a price snapshot;
- a rejected-record archive.

#### Ownership

- Data owner: market-product import process.
- User editing: not allowed.
- Production application access: not required.
- Mutable while the parent import run is active: yes.
- Mutable after validation begins: restricted.
- Normal long-term retention: not required after staging cleanup.
- Deletion: allowed only after permanent outcomes and evidence have been preserved.

#### Columns

| Column                      | PostgreSQL type                | Nullable | Default                    | Ownership                   | Description                                                                                                                                 |
| --------------------------- | ------------------------------ | -------: | -------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `staging_market_product_id` | `bigint` generated as identity |       No | Generated                  | Database                    | Internal surrogate primary key for the staged source row.                                                                                   |
| `import_run_id`             | `bigint`                       |       No | None                       | Import-control relationship | References the market-product import run that loaded the source record.                                                                     |
| `source_record_reference`   | `text`                         |       No | None                       | Import-owned identity       | Stable reference to the source record inside the imported artifact.                                                                         |
| `source_system`             | `text`                         |       No | None                       | Import-owned identity       | Controlled marketplace source identifier, initially `cardmarket`.                                                                           |
| `source_product_id`         | `text`                         |      Yes | `null`                     | Import-owned source value   | Source product identifier after basic normalization, for example Cardmarket `idProduct`. Nullable so malformed records can still be staged. |
| `source_expansion_id`       | `text`                         |      Yes | `null`                     | Import-owned source value   | Source expansion identifier, for example Cardmarket `idExpansion`.                                                                          |
| `source_metaproduct_id`     | `text`                         |      Yes | `null`                     | Import-owned source value   | Source metaproduct identifier, for example Cardmarket `idMetacard`.                                                                         |
| `raw_name`                  | `text`                         |      Yes | `null`                     | Import-owned source value   | Product name after minimal whitespace normalization.                                                                                        |
| `source_category_id`        | `text`                         |      Yes | `null`                     | Import-owned source value   | Source category identifier when available.                                                                                                  |
| `source_category_name`      | `text`                         |      Yes | `null`                     | Import-owned source value   | Source category name when available.                                                                                                        |
| `source_created_at`         | `timestamp with time zone`     |      Yes | `null`                     | Import-owned source value   | Source-provided product creation timestamp when available.                                                                                  |
| `raw_payload`               | `jsonb`                        |       No | None                       | Import-owned evidence       | Raw or minimally transformed source product record.                                                                                         |
| `record_checksum`           | `text`                         |      Yes | `null`                     | Import-owned evidence       | Deterministic checksum of the normalized source product record when available.                                                              |
| `normalization_status`      | `text`                         |       No | `pending`                  | Import-control state        | Current normalization result for the staged row.                                                                                            |
| `validation_status`         | `text`                         |       No | `pending`                  | Import-control state        | Current record-level validation result.                                                                                                     |
| `validation_completed_at`   | `timestamp with time zone`     |      Yes | `null`                     | Import-control state        | Timestamp when validation reached a terminal result.                                                                                        |
| `created_at`                | `timestamp with time zone`     |       No | Current database timestamp | Database                    | Timestamp when the staging row was inserted.                                                                                                |
| `updated_at`                | `timestamp with time zone`     |       No | Current database timestamp | Database                    | Timestamp of the latest actual staging or validation-state change.                                                                          |

#### Primary key

```text
staging_market_product_id
```

The staging primary key must not be reused as:

- production `market_product_id`;
- source product identity;
- mapping case identity;
- import outcome identity.

#### Foreign key

```text
import_run_id
→ import_runs.import_run_id
```

Required behavior:

- the parent import run must already exist;
- the run kind and source entity type must permit market-product staging;
- deleting the import run must be restricted while staging rows remain;
- staging cleanup must delete child rows explicitly.

#### Required constraints

##### Source-record uniqueness within one run

```text
UNIQUE (import_run_id, source_record_reference)
```

The same source record may appear in another import run, but not twice in the same run under the same reference.

##### Non-empty source-record reference

Conceptual rule:

```text
trim(source_record_reference) <> ''
```

##### Non-empty source system

Conceptual rule:

```text
trim(source_system) <> ''
```

##### Raw payload required

`raw_payload` must be present for every staged row.

The payload must preserve enough source evidence to support:

- validation;
- rejection reporting;
- duplicate-candidate review;
- exclusion classification;
- parser troubleshooting.

It must not contain credentials or unrelated secrets.

##### Optional normalized-value consistency

When present, the following values must contain non-whitespace text:

- `source_product_id`;
- `source_expansion_id`;
- `source_metaproduct_id`;
- `raw_name`;
- `source_category_id`;
- `source_category_name`;
- `record_checksum`.

Empty source strings should normally be normalized to null.

#### Why production-required fields are nullable

Production `market_products` requires:

- source product ID;
- raw name.

The corresponding staging columns remain nullable because malformed rows must still be preserved long enough to:

- validate them;
- reconcile source counts;
- create structured rejection evidence;
- avoid silently dropping source records during ingestion.

A missing required source value causes rejection, not staging insertion failure.

#### Source record reference

`source_record_reference` identifies the record inside the source artifact.

Examples:

```text
products.csv#idProduct=273532
```

```text
fixture:primal-clash/cardmarket-products#record-42
```

```text
cardmarket-products.json#line-43
```

The reference must be:

- stable within the source artifact;
- reproducible;
- unique inside one import run;
- usable even when `source_product_id` is missing or invalid.

#### Source product identity

For valid Cardmarket rows:

```text
source_system = cardmarket
source_product_id = normalized idProduct
```

The value is stored as `text`.

The importer must not:

- convert it into the staging primary key;
- derive it from row order;
- replace it with `idMetacard`;
- infer it from product name.

#### Source expansion value

`source_expansion_id` preserves the original market-source expansion identifier.

For Primal Clash:

```text
source_expansion_id = 1585
```

The staging row does not require an internal `expansion_id`.

Internal expansion resolution occurs during validated production merge through:

```text
source_system
source_expansion_id
→ expansion_source_identifiers
→ expansions
```

An unresolved expansion relationship may:

- reject the run when the declared scope requires resolution;
- or preserve the market product without `expansion_id`;

depending on the approved run contract.

#### Source metaproduct value

`source_metaproduct_id` preserves `idMetacard` when available.

It may support:

- grouping;
- mapping evidence;
- duplicate-candidate analysis;
- validation.

It must not be treated as:

- product identity;
- canonical card identity;
- sufficient mapping evidence by itself.

Multiple valid staged products may share the same metaproduct identifier.

#### Product name

`raw_name` preserves the source product name after minimal normalization.

Allowed normalization:

- trim leading and trailing whitespace;
- convert an empty result to null.

The importer must not:

- translate the name;
- replace source punctuation;
- parse and remove possible edition text before preserving the raw name;
- use normalized name as the product identity.

Derived name forms used for mapping comparison should be calculated in mapping staging or observation logic rather than replacing `raw_name`.

#### Category fields

`source_category_id` and `source_category_name` preserve Cardmarket classification where available.

These fields may support:

- detection of Online Code Card products;
- source-scope validation;
- `unmatched_duplicate_candidate` analysis;
- reporting.

A category-based exclusion must not delete the staging row or prevent creation of a valid production market product.

The exclusion belongs to mapping classification, not product-record validation, unless the source row itself is structurally invalid.

#### Source creation timestamp

`source_created_at` preserves the source-provided product timestamp when available.

It may support inspected duplicate-candidate evidence.

It must not:

- participate in source product identity;
- be used as a replacement for missing `source_product_id`;
- automatically determine which duplicate-like product is canonical;
- be interpreted as the price snapshot timestamp.

#### Record checksum

The normalized checksum may include:

- `source_system`;
- `source_product_id`;
- `source_expansion_id`;
- `source_metaproduct_id`;
- `raw_name`;
- category values;
- source creation timestamp.

Recommended representation:

```text
sha256:<hexadecimal digest>
```

The checksum supports:

- duplicate source-row detection;
- repeated import comparison;
- debugging normalization changes.

It does not replace:

- source-scoped product identity;
- source record reference;
- source artifact checksum.

#### Normalization status

Initial controlled values:

- `pending`;
- `normalized`;
- `normalization_failed`.

##### `pending`

The source row has been loaded but normalization is incomplete.

##### `normalized`

Supported deterministic normalization completed.

This does not mean the record is valid for production.

##### `normalization_failed`

The row could not be normalized according to the source contract.

The row:

- remains preserved;
- cannot be marked valid;
- creates no production market product;
- must produce permanent rejection evidence before cleanup.

#### Validation status

Initial controlled values:

- `pending`;
- `valid`;
- `rejected`.

##### `pending`

Record-level validation has not reached a terminal result.

##### `valid`

The row satisfies the market-product source contract and may participate in run-level validation and production merge.

A valid row may still later receive a non-confirmed mapping classification.

##### `rejected`

The source row is structurally invalid and must not enter `market_products`.

Mapping classifications such as:

- `excluded`;
- `unmatched`;
- `candidate`;
- `ambiguous`;
- `unmatched_duplicate_candidate`;

must not be represented as `validation_status = rejected` when the product itself is valid.

#### State consistency

When:

```text
validation_status = pending
```

then:

```text
validation_completed_at is null
```

When:

```text
validation_status in (valid, rejected)
```

then:

```text
validation_completed_at is not null
```

When:

```text
normalization_status = normalization_failed
```

then:

```text
validation_status <> valid
```

When:

```text
validation_status = valid
```

then:

```text
normalization_status = normalized
```

#### Record-level validation

A staged market product is valid when, at minimum:

- `source_system` is supported;
- `source_product_id` is non-null and non-empty;
- `raw_name` is non-null and non-empty;
- source identifiers have valid normalized form;
- source timestamp parses when present;
- raw payload is available;
- the record contains no unsupported structural conflict.

The following may be nullable:

- source expansion ID, if the run contract permits unresolved expansion scope;
- source metaproduct ID;
- category ID;
- category name;
- source creation timestamp.

For the accepted Primal Clash product fixture, source expansion and category evidence may be required by the run-level contract even if the generic staging table allows null.

#### Run-level validation

Rows marked `valid` participate in run-level checks.

For Primal Clash, validation should confirm:

- all expected Cardmarket product records in expansion `1585` are represented;
- `(source_system, source_product_id)` is unique in the valid staging set;
- source-record references are unique;
- all expected source product IDs remain preserved;
- multiple products may share one metaproduct ID;
- four Online Code Card products remain valid source products;
- six duplicate-like products remain valid source products;
- ordinary structural validation does not incorrectly reject unresolved mapping cases;
- no staging row remains pending before production merge;
- valid and rejected counts reconcile with `import_runs`.

Conflicting duplicate source product IDs must not be resolved through arbitrary row selection.

They must cause rejection or run-level validation failure according to the approved rule.

#### Production resolution

A valid staged row resolves production identity through:

```text
(source_system, source_product_id)
```

The optional internal expansion relationship resolves through:

```text
source_system
source_expansion_id
→ expansion_source_identifiers
→ expansions.expansion_id
```

For Cardmarket, the source-system identifier used for expansion resolution must match the identifier stored in `expansion_source_identifiers`.

#### Production merge comparison

For an existing production market product, compare normalized values for:

- `source_expansion_id`;
- resolved `expansion_id`;
- `source_metaproduct_id`;
- `raw_name`;
- `source_category_id`;
- `source_category_name`;
- `source_created_at`.

The staging row must not directly set:

- mapping status;
- canonical card target;
- edition target;
- variant target;
- lifecycle state without an approved rule;
- market prices;
- production timestamps.

#### Merge outcomes

Each valid staged product should produce one detailed production outcome:

- `inserted`;
- `updated`;
- `unchanged`.

For authoritative scope comparison, production products absent from the valid staging set may produce:

- `missing`;
- `retired`;

according to approved lifecycle rules.

The final outcome is stored in `import_record_outcomes`, not in the staging row.

#### Mapping handoff

After or alongside production product resolution, a valid staged market product may contribute an observation to its persistent mapping case.

The handoff may preserve:

- source product ID;
- source expansion ID;
- metaproduct ID;
- raw name;
- category evidence;
- source creation timestamp;
- import run;
- source record reference.

The staging table must not store the final mapping classification.

#### Online Code Card products

A structurally valid Online Code Card product:

- is marked `validation_status = valid`;
- may be inserted into `market_products`;
- is classified as `excluded` in mapping-review structures;
- creates no production card mapping;
- contributes no canonical-card price.

It must not be rejected merely because it is outside MVP catalogue mapping scope.

#### `unmatched_duplicate_candidate` products

A structurally valid duplicate-like product:

- is marked `validation_status = valid`;
- remains preserved in `market_products`;
- receives `unmatched_duplicate_candidate` through mapping classification;
- creates no confirmed production mapping;
- contributes no canonical-card price.

The staging table may preserve the evidence fields needed to derive that classification, but it does not own the classification.

#### Rejected rows

A rejected staged product:

- creates no production market product;
- creates no mapping case requiring production product identity;
- creates no price snapshot;
- must preserve permanent rejection evidence before staging cleanup.

If review evidence is useful for a malformed product without production identity, it remains attached to the rejected-record workflow.

#### Mutability

##### Before normalization completes

The importer may populate normalized fields and update processing statuses.

##### After validation completes

Normalized source values should become immutable for the run.

Parser corrections should normally use a new import run.

##### After production merge starts

Staging rows must not change.

The production transaction must operate on a stable validated dataset.

##### After terminal run status

Rows remain read-only until staging cleanup.

#### Cleanup behavior

Staging cleanup may occur only after:

- the parent run reaches a terminal state;
- detailed merge outcomes are preserved;
- rejection evidence is preserved;
- mapping observations are preserved;
- source artifact references remain durable;
- retention policy permits deletion.

Cleanup must not delete:

- `import_runs`;
- production market products;
- mapping cases;
- mapping observations;
- confirmed mappings;
- price snapshots;
- rejected records.

#### Primal Clash example

A conceptual valid Cardmarket row may contain:

| Column                      | Example value                      |
| --------------------------- | ---------------------------------- |
| `staging_market_product_id` | Database-generated value           |
| `import_run_id`             | Primal Clash market-product run ID |
| `source_record_reference`   | `products.csv#idProduct=273532`    |
| `source_system`             | `cardmarket`                       |
| `source_product_id`         | `273532`                           |
| `source_expansion_id`       | `1585`                             |
| `source_metaproduct_id`     | Source `idMetacard` value          |
| `raw_name`                  | Source product name                |
| `source_category_id`        | Source category ID                 |
| `source_category_name`      | Source category name               |
| `source_created_at`         | Source timestamp                   |
| `raw_payload`               | Source object                      |
| `record_checksum`           | Deterministic checksum             |
| `normalization_status`      | `normalized`                       |
| `validation_status`         | `valid`                            |
| `validation_completed_at`   | Validation timestamp               |
| `created_at`                | Database-generated timestamp       |
| `updated_at`                | Latest staging-state timestamp     |

The same valid structure applies to:

- an Online Code Card product later classified as `excluded`;
- a duplicate-like product later classified as `unmatched_duplicate_candidate`;
- an ordinary product whose card mapping remains unresolved.

#### Relationships

```text
import_runs
    1 → many staging_market_products
```

A staging market product has no direct foreign key to:

- `market_products`;
- `expansions`;
- `cards`;
- mapping cases;
- price snapshots.

Production and mapping identities are resolved during validated processing.

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

```text
staging_market_products.import_run_id
→ import_runs.import_run_id
```

Staging cleanup deletes rows explicitly.

#### Index candidates

Likely access paths include:

- all rows by `import_run_id`;
- lookup by `(import_run_id, source_record_reference)`;
- valid rows by run;
- rejected rows by run;
- lookup by `(import_run_id, source_system, source_product_id)`;
- grouping by `source_metaproduct_id`;
- filtering by source expansion;
- filtering by category;
- pending validation rows.

Potential supporting indexes include:

```text
(import_run_id, validation_status)
```

and:

```text
(import_run_id, source_system, source_product_id)
```

Final indexes must be selected during migration and validation-query design.

#### Validation requirements

The first schema validation must confirm:

- all accepted Primal Clash Cardmarket products can be staged;
- each row preserves raw payload evidence;
- `idProduct`, `idExpansion`, and `idMetacard` remain text values;
- malformed rows can be staged without being silently lost;
- blank source product IDs cause rejection;
- blank product names cause rejection;
- source-record references are unique within one run;
- duplicate source product identities are detected;
- multiple products may share one metaproduct ID;
- Online Code Card products remain valid source products;
- all six duplicate-like products remain valid source products;
- mapping-unresolved products remain valid product records;
- no row remains pending before production merge;
- a normalization-failed row cannot be marked valid;
- rejected rows create no production product;
- valid rows resolve Cardmarket expansion `1585` when the run contract requires it;
- repeating the same fixture in a new run creates new staging rows but no duplicate production products;
- staging cleanup preserves outcomes, rejections, and mapping observations;
- deleting staging rows does not affect production products or mapping history.

#### Deferred fields

The following fields are not included in the first version:

- resolved production `market_product_id`;
- resolved internal `expansion_id`;
- production merge outcome;
- final mapping status;
- confirmation scope;
- candidate card ID;
- edition code;
- language;
- finish;
- price values;
- source product URL;
- parser warning array;
- normalization rule version;
- source row number as a separate integer;
- duplicate-candidate flag;
- exclusion flag;
- review notes.

These values belong to production, mapping, price, outcome, or evidence structures.

#### Open questions

- Which Cardmarket source fields are always present in the accepted fixture?
- Should `source_expansion_id` be required for all valid Cardmarket product rows in the first implementation?
- Should category ID and category name both be required for Primal Clash validation?
- Should duplicate source product IDs reject individual rows or fail the complete run?
- Should `record_checksum` be mandatory for fixture-based imports?
- Should `raw_payload` preserve the exact source object or a sanitized subset?
- Should normalized staging values be database-protected after validation?
- What retention period should apply to successful and failed market-product staging rows?

### `staging_market_prices`

#### Purpose

Store normalized marketplace price source records for one import run before validation and insertion into `market_price_snapshots`.

For the first implementation, the source system is Cardmarket.

The table provides a controlled boundary between:

- raw price ingestion;
- source-field normalization;
- market-product resolution;
- record-level validation;
- duplicate and conflict detection;
- production insertion into `market_price_snapshots`.

A staging market-price row is not:

- a permanent historical price snapshot;
- a current-price cache;
- a canonical-card `From` price;
- a mapping confirmation;
- a variant classification;
- a rejected-record archive.

#### Ownership

- Data owner: market-price import process.
- User editing: not allowed.
- Production application access: not required.
- Mutable while the parent import run is active: yes.
- Mutable after validation begins: restricted.
- Normal long-term retention: not required after staging cleanup.
- Deletion: allowed only after permanent outcomes and rejection evidence have been preserved.

#### Columns

| Column                    | PostgreSQL type                | Nullable | Default                    | Ownership                     | Description                                                                                        |
| ------------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------- |
| `staging_market_price_id` | `bigint` generated as identity |       No | Generated                  | Database                      | Internal surrogate primary key for the staged price row.                                           |
| `import_run_id`           | `bigint`                       |       No | None                       | Import-control relationship   | References the market-price import run that loaded the source record.                              |
| `source_record_reference` | `text`                         |       No | None                       | Import-owned identity         | Stable reference to the price record inside the imported source artifact.                          |
| `source_system`           | `text`                         |       No | None                       | Import-owned identity         | Controlled market source identifier, initially `cardmarket`.                                       |
| `source_product_id`       | `text`                         |      Yes | `null`                     | Import-owned source value     | Source product identifier to be resolved to `market_products`, for example Cardmarket `idProduct`. |
| `source_snapshot_at`      | `timestamp with time zone`     |      Yes | `null`                     | Import-owned source value     | Source-provided timestamp identifying the price snapshot.                                          |
| `currency_code`           | `text`                         |      Yes | `null`                     | Import-owned source value     | Currency of the source price values, initially expected to be `EUR`.                               |
| `avg30_raw`               | `text`                         |      Yes | `null`                     | Import-owned raw value        | Source representation of the regular 30-day average before numeric parsing.                        |
| `avg30`                   | `numeric(12, 4)`               |      Yes | `null`                     | Import-owned normalized value | Parsed regular 30-day average when valid and present.                                              |
| `avg30_holo_raw`          | `text`                         |      Yes | `null`                     | Import-owned raw value        | Source representation of the holo 30-day average before numeric parsing.                           |
| `avg30_holo`              | `numeric(12, 4)`               |      Yes | `null`                     | Import-owned normalized value | Parsed holo 30-day average when valid and present.                                                 |
| `raw_payload`             | `jsonb`                        |       No | None                       | Import-owned evidence         | Raw or minimally transformed source price record.                                                  |
| `record_checksum`         | `text`                         |      Yes | `null`                     | Import-owned evidence         | Deterministic checksum of the normalized source price observation when available.                  |
| `normalization_status`    | `text`                         |       No | `pending`                  | Import-control state          | Current normalization result for the staged row.                                                   |
| `validation_status`       | `text`                         |       No | `pending`                  | Import-control state          | Current record-level validation result.                                                            |
| `validation_completed_at` | `timestamp with time zone`     |      Yes | `null`                     | Import-control state          | Timestamp when record-level validation reached a terminal result.                                  |
| `created_at`              | `timestamp with time zone`     |       No | Current database timestamp | Database                      | Timestamp when the staging row was inserted.                                                       |
| `updated_at`              | `timestamp with time zone`     |       No | Current database timestamp | Database                      | Timestamp of the latest actual staging or validation-state change.                                 |

#### Primary key

```text
staging_market_price_id
```

The staging primary key must not be reused as:

- production `market_price_snapshot_id`;
- source product identity;
- import outcome identity;
- source record identity.

#### Foreign key

```text
import_run_id
→ import_runs.import_run_id
```

Required behavior:

- the parent import run must already exist;
- the run kind and source entity type must permit market-price staging;
- deleting the import run must be restricted while staging rows remain;
- staging cleanup must delete child rows explicitly.

#### Required constraints

##### Source-record uniqueness within one run

```text
UNIQUE (import_run_id, source_record_reference)
```

The same source record reference may appear in another import run, but not twice in the same run.

##### Non-empty source-record reference

Conceptual rule:

```text
trim(source_record_reference) <> ''
```

##### Non-empty source system

Conceptual rule:

```text
trim(source_system) <> ''
```

##### Raw payload required

`raw_payload` must be present for every staged price row.

The payload must preserve enough source evidence to support:

- numeric parsing review;
- rejection reporting;
- duplicate detection;
- same-timestamp conflict analysis;
- source reconciliation;
- parser troubleshooting.

It must not contain credentials or unrelated secrets.

##### Optional normalized-value consistency

When present, the following text values must contain non-whitespace content:

- `source_product_id`;
- `currency_code`;
- `avg30_raw`;
- `avg30_holo_raw`;
- `record_checksum`.

Empty source strings should normally be normalized to null.

#### Why required production fields are nullable

Production `market_price_snapshots` requires:

- a resolved market product;
- source snapshot timestamp;
- currency code;
- at least one valid supported price value.

The corresponding staging values remain nullable because malformed or incomplete rows must still be preserved long enough to:

- validate them;
- reconcile source counts;
- explain rejection;
- avoid silently dropping source records during ingestion.

A missing required value causes validation rejection rather than staging insertion failure.

#### Source record reference

`source_record_reference` identifies the price observation inside the imported artifact.

Examples:

```text
prices.csv#idProduct=273532
```

```text
prices.csv#idProduct=273532&snapshot=2026-07-28T00:00:00Z
```

```text
fixture:primal-clash/cardmarket-prices#record-42
```

The reference must be:

- stable within the source artifact;
- reproducible;
- unique within one import run;
- usable even when the source product ID or timestamp is malformed.

#### Source product resolution

A valid price row resolves the production market product through:

```text
(source_system, source_product_id)
```

The staging table does not store `market_product_id`.

Resolution occurs during validation or production preparation against:

```text
market_products.source_system
market_products.source_product_id
```

A price row whose source product cannot be resolved:

- must not create a production price snapshot;
- must be rejected or fail the run according to the authoritative scope contract;
- must preserve its source evidence.

The importer must not resolve a market product through:

- source metaproduct ID;
- product name;
- row order;
- nearest identifier;
- canonical card mapping.

#### Source snapshot timestamp

`source_snapshot_at` identifies the source observation time.

The importer must not replace a missing source timestamp with:

- staging `created_at`;
- import-run `started_at`;
- file modification time;
- current database timestamp;

unless the source contract explicitly defines one of those values as the authoritative snapshot timestamp.

When the source artifact provides one shared snapshot timestamp for every row, the importer may populate that timestamp deterministically for each staging record.

The source of that shared timestamp must remain documented through:

- `source_artifact_reference`;
- raw payload or manifest evidence;
- import-run metadata.

#### Currency code

`currency_code` preserves the source currency for the price values.

Initial expected value:

```text
EUR
```

Normalization may:

- trim whitespace;
- convert a valid alphabetic currency code to uppercase.

The importer must not:

- assume a currency silently when the source contract does not guarantee it;
- convert prices into another currency;
- combine values from different currencies;
- infer currency from user locale.

If the Cardmarket fixture contract guarantees EUR and omits a row-level field, the importer may populate `EUR` using a documented source-level rule.

#### Raw and normalized price fields

The staging table preserves both raw text and parsed decimal values.

This allows the importer to distinguish:

- missing value;
- empty source value;
- valid zero;
- valid decimal;
- malformed numeric text;
- unsupported decimal formatting.

##### `avg30_raw`

Preserves the source representation before parsing.

Examples:

```text
1.23
```

```text
0
```

```text
null
```

The exact raw representation may instead remain exclusively inside `raw_payload` if the source parser does not expose a stable text value. The dedicated raw column is still recommended for transparent validation.

##### `avg30`

Contains the parsed decimal only when:

- the raw value is present;
- parsing succeeds;
- the value is finite;
- the value is non-negative;
- source formatting is supported.

A missing source value produces null.

A malformed source value must not silently produce null while the record is marked valid.

##### `avg30_holo_raw`

Preserves the source holo-price representation before parsing.

##### `avg30_holo`

Contains the parsed holo decimal only when the same validation rules as `avg30` are satisfied.

A non-null `avg30_holo` must not:

- create a holo variant;
- prove a market product is holo;
- make the metric automatically eligible for canonical-card pricing.

#### Numeric parsing rules

Supported normalization should be deterministic.

At minimum:

- trim surrounding whitespace;
- recognize the source decimal separator defined by the fixture contract;
- reject thousands separators unless explicitly supported;
- reject currency symbols inside numeric fields unless the source parser documents them;
- reject `NaN`;
- reject positive or negative infinity;
- reject negative values;
- preserve zero as zero;
- preserve up to four decimal places without binary floating-point conversion.

The importer should parse into an exact decimal representation before insertion into PostgreSQL.

#### Record checksum

The normalized checksum may include:

- source system;
- source product ID;
- source snapshot timestamp;
- currency code;
- normalized `avg30`;
- normalized `avg30_holo`.

Recommended representation:

```text
sha256:<hexadecimal digest>
```

The checksum may support:

- duplicate detection;
- repeated-source comparison;
- conflict analysis;
- parser troubleshooting.

It must not replace the proposed production identity:

```text
(market_product_id, source_snapshot_at)
```

or the staging identity:

```text
(import_run_id, source_record_reference)
```

#### Normalization status

Initial controlled values:

- `pending`;
- `normalized`;
- `normalization_failed`.

##### `pending`

The source row has been loaded, but normalization is incomplete.

##### `normalized`

Supported field parsing and normalization completed.

This does not mean the row is valid for production.

##### `normalization_failed`

One or more values could not be normalized according to the source contract.

Examples include:

- invalid timestamp;
- invalid decimal syntax;
- unsupported currency representation;
- malformed source identifier.

A normalization-failed row:

- remains preserved in staging;
- cannot be marked valid;
- creates no production price snapshot;
- must produce permanent rejection evidence before cleanup.

#### Validation status

Initial controlled values:

- `pending`;
- `valid`;
- `rejected`.

##### `pending`

Record-level validation has not reached a terminal result.

##### `valid`

The row satisfies the price source contract and may participate in run-level validation and production insertion.

This status does not mean the price is eligible for canonical-card calculation.

##### `rejected`

The row cannot create a production snapshot.

Structured rejection reasons belong to:

- `rejected_source_records`;
- `rejected_source_record_reasons`.

#### State consistency

When:

```text
validation_status = pending
```

then:

```text
validation_completed_at is null
```

When:

```text
validation_status in (valid, rejected)
```

then:

```text
validation_completed_at is not null
```

When:

```text
normalization_status = normalization_failed
```

then:

```text
validation_status <> valid
```

When:

```text
validation_status = valid
```

then:

```text
normalization_status = normalized
```

#### Record-level validation

A staged price record is valid only when:

- `source_system` is supported;
- `source_product_id` is non-null and non-empty;
- the market product can be resolved according to the run contract;
- `source_snapshot_at` is non-null;
- `currency_code` is supported;
- `avg30` is null or non-negative;
- `avg30_holo` is null or non-negative;
- at least one of `avg30` or `avg30_holo` is non-null;
- raw payload is available;
- no source parsing conflict remains unresolved.

A row is rejected when, for example:

- source product ID is missing;
- source timestamp is missing;
- source product cannot be resolved;
- currency is missing or unsupported;
- a price contains invalid numeric text;
- a price is negative;
- both supported price values are null;
- source values exceed supported numeric precision;
- raw and normalized values are inconsistent.

#### Null-only observations

The proposed first-version rule is:

```text
avg30 is not null
or avg30_holo is not null
```

A source record with both values null:

- may remain in staging;
- is marked rejected for production price insertion;
- may preserve useful coverage evidence through rejection records;
- does not create a null-only `market_price_snapshots` row.

This remains open until the authoritative fixture semantics are confirmed.

#### Duplicate detection inside one run

The expected production identity is resolved as:

```text
market product
+
source_snapshot_at
```

Within one staging run, two valid rows resolving to the same:

```text
(source_system, source_product_id, source_snapshot_at)
```

must be compared.

##### Identical duplicate

When currency and normalized price values are identical:

- do not select one row arbitrarily without evidence;
- classify the duplicate according to an approved source rule;
- preserve source references;
- allow at most one production snapshot.

The preferred first implementation is to fail run-level validation unless the source contract explicitly permits identical duplicate rows.

##### Conflicting duplicate

When values differ for the same source product and snapshot timestamp:

- fail run-level validation;
- preserve both rows;
- create conflict evidence;
- insert no conflicting production snapshot.

#### Run-level validation

Rows marked `valid` participate in run-level checks.

At minimum, validation should confirm:

- no staging row remains pending;
- every valid source product resolves uniquely;
- supported currencies are consistent with the run contract;
- source snapshot timestamps satisfy the declared scope;
- no conflicting duplicate snapshot identities exist;
- valid and rejected counts reconcile with `import_runs`;
- the price source scope matches the declared expansion or market-product scope where applicable.

For an authoritative Primal Clash price run, validation should also confirm:

- all expected source price records are represented;
- every valid record belongs to a known Primal Clash Cardmarket product;
- excluded and unresolved market products may still have valid source price rows;
- price presence does not alter mapping classification;
- no source price row creates a variant or mapping.

#### Production insertion

A valid staged row is prepared for insertion by resolving:

```text
source_system
source_product_id
→ market_products.market_product_id
```

The production values are:

- resolved `market_product_id`;
- parent `import_run_id`;
- `source_snapshot_at`;
- `currency_code`;
- `avg30`;
- `avg30_holo`;
- durable `source_reference`.

The staging row must not set:

- canonical card ID;
- edition ID;
- variant ID;
- mapping status;
- metric eligibility;
- canonical-card price;
- production `created_at`.

#### Production comparison

Before insertion, compare against:

```text
market_price_snapshots
```

using the proposed identity:

```text
(market_product_id, source_snapshot_at)
```

Possible results:

- `inserted`;
- `unchanged`;
- `conflict`;
- `rejected`.

##### Inserted

No production snapshot exists for the identity.

Insert one append-only row.

##### Unchanged

An existing snapshot has equivalent:

- currency;
- `avg30`;
- `avg30_holo`;
- accepted source-reference semantics.

Do not insert or update.

##### Conflict

An existing snapshot has different:

- currency;
- `avg30`;
- `avg30_holo`.

Do not overwrite the production row.

Fail or block the relevant merge according to the run-level transaction rule.

#### Merge outcomes

Each valid staged price row should produce a detailed outcome in `import_record_outcomes`, for example:

- `inserted`;
- `unchanged`;
- `conflict`.

Rejected rows are represented through the rejected-record structures.

The staging row itself must not become the permanent outcome record.

#### Mapping and eligibility boundary

A staged price row may be valid even when its market product is:

- unmapped;
- excluded;
- ambiguous;
- `unmatched_duplicate_candidate`;
- confirmed only at card level.

The price source record remains valid market evidence.

Its eligibility for the canonical-card `From` price is determined later through:

- active confirmed mapping;
- confirmation scope;
- language eligibility;
- finish and metric semantics;
- exclusion rules;
- current-snapshot selection.

The staging price table must not contain a boolean such as:

```text
is_price_eligible
```

#### Rejected rows

A rejected staging price row:

- creates no production snapshot;
- does not change the market product;
- does not change mappings;
- does not create variants;
- does not contribute to canonical-card pricing;
- must preserve permanent rejection evidence before staging cleanup.

#### Mutability

##### Before normalization completes

The importer may populate normalized fields and update processing states.

##### After validation completes

Source and normalized values should become immutable for the run.

Parser corrections should normally require a new import run.

##### After production merge starts

Staging rows must not change.

The transaction must operate on a stable validated set.

##### After terminal run status

Rows remain read-only until cleanup.

#### Cleanup behavior

Staging cleanup may occur only after:

- the parent run reaches a terminal state;
- price outcomes are preserved;
- rejected-record evidence is preserved;
- conflicting duplicate evidence is preserved;
- production snapshots have committed or the merge has rolled back;
- source artifact references remain durable;
- retention policy permits deletion.

Cleanup must not delete:

- the import run;
- market products;
- production price snapshots;
- mapping cases;
- confirmed mappings;
- rejected records;
- wishlist data.

#### Primal Clash example

A conceptual valid staged price row may contain:

| Column                    | Example value                      |
| ------------------------- | ---------------------------------- |
| `staging_market_price_id` | Database-generated value           |
| `import_run_id`           | Primal Clash price import run ID   |
| `source_record_reference` | `prices.csv#idProduct=273532`      |
| `source_system`           | `cardmarket`                       |
| `source_product_id`       | `273532`                           |
| `source_snapshot_at`      | Source-provided snapshot timestamp |
| `currency_code`           | `EUR`                              |
| `avg30_raw`               | Source decimal text                |
| `avg30`                   | Parsed decimal or `null`           |
| `avg30_holo_raw`          | Source decimal text or `null`      |
| `avg30_holo`              | Parsed decimal or `null`           |
| `raw_payload`             | Source record                      |
| `record_checksum`         | Deterministic checksum             |
| `normalization_status`    | `normalized`                       |
| `validation_status`       | `valid`                            |
| `validation_completed_at` | Validation timestamp               |
| `created_at`              | Database-generated timestamp       |
| `updated_at`              | Latest staging-state timestamp     |

A malformed negative-price row may remain staged with:

```text
avg30_raw = -1.25
avg30 = -1.2500
validation_status = rejected
```

or with null normalized value when the parser refuses invalid values, provided the raw evidence and rejection reason remain preserved.

#### Relationships

```text
import_runs
    1 → many staging_market_prices
```

A staging market price has no direct foreign key to:

- `market_products`;
- `market_price_snapshots`;
- `cards`;
- `card_editions`;
- `card_variants`;
- mappings.

Production identities are resolved during validated processing.

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

```text
staging_market_prices.import_run_id
→ import_runs.import_run_id
```

Staging cleanup deletes rows explicitly.

#### Index candidates

Likely access paths include:

- all rows by `import_run_id`;
- lookup by `(import_run_id, source_record_reference)`;
- valid rows by run;
- rejected rows by run;
- lookup by `(import_run_id, source_system, source_product_id)`;
- duplicate detection by source product and snapshot timestamp;
- filtering by currency;
- pending validation rows.

Potential supporting indexes include:

```text
(import_run_id, validation_status)
```

and:

```text
(import_run_id, source_system, source_product_id, source_snapshot_at)
```

Final indexes must be selected during migration and validation-query design.

#### Validation requirements

The first schema validation must confirm:

- all accepted Cardmarket price records can be staged;
- every row preserves raw payload evidence;
- source product IDs remain text;
- valid decimal values are parsed exactly;
- zero remains distinct from null;
- empty values do not become zero;
- negative values are rejected;
- malformed decimal text is rejected;
- null `avg30` is accepted when `avg30_holo` is present;
- null `avg30_holo` is accepted when `avg30` is present;
- both values null do not create a production snapshot under the proposed rule;
- missing snapshot timestamp causes rejection;
- unsupported currency causes rejection;
- unresolved market products create no production snapshot;
- source-record references are unique within one run;
- duplicate source snapshot identities are detected;
- conflicting duplicate values fail validation;
- repeating the same source snapshot in a later run creates no duplicate production snapshot;
- a later source snapshot creates a separate production row;
- valid prices for excluded or unresolved products do not automatically contribute to canonical-card pricing;
- a normalization-failed row cannot be marked valid;
- no row remains pending before production merge;
- staging cleanup preserves permanent outcomes and rejected evidence;
- deleting staging rows does not affect production snapshots or wishlist data.

#### Deferred fields

The following fields are not included in the first version:

- resolved production `market_product_id`;
- production snapshot ID;
- production merge outcome;
- canonical card ID;
- edition ID;
- variant ID;
- metric eligibility flag;
- current-price flag;
- source expansion ID;
- source metaproduct ID;
- low price;
- trend price;
- article count;
- source row number as a separate integer;
- parser warning array;
- normalization rule version;
- correction status;
- review notes.

These values belong to production, mapping, outcome, or evidence structures unless a validated source contract establishes a staging responsibility.

#### Open questions

- Does the accepted Cardmarket price fixture provide one shared snapshot timestamp or a timestamp per record?
- Is currency explicit in the source artifact or guaranteed at artifact level?
- Should raw numeric values use dedicated text columns or remain only in `raw_payload`?
- Should null-only observations be rejected or preserved as a special valid coverage state?
- Should identical duplicate source rows fail the run or be deterministically deduplicated?
- What precision and scale are present in the accepted source fixture?
- Should unresolved source product IDs reject individual rows or fail an authoritative run?
- Should `record_checksum` be mandatory for fixture-based price imports?
- Should normalized staging values become database-protected after validation?
- What retention period should apply to successful and failed price staging rows?

### `staging_market_mappings`

#### Purpose

Store normalized market-to-catalogue mapping observations for one import run before validation, review-state persistence, and production mapping merge.

The table provides a controlled boundary between:

- source mapping evidence;
- normalized candidate targets;
- confirmation-scope validation;
- mapping-case observation creation;
- production merge into `card_market_product_mappings`.

A staging mapping row is not:

- the persistent mapping case;
- the current accepted mapping status;
- a production confirmed mapping;
- a production card edition;
- a production card variant;
- a market price snapshot.

#### Ownership

- Data owner: mapping import and validation process.
- User editing: not allowed through the wishlist workflow.
- Manual-review input: may be loaded through an approved reviewed import path.
- Mutable while the parent import run is active: yes.
- Mutable after validation begins: restricted.
- Normal long-term retention: not required after permanent mapping evidence is preserved.
- Deletion: allowed only through staging cleanup after terminal run state and evidence persistence.

#### Columns

| Column                      | PostgreSQL type                | Nullable | Default                    | Ownership                    | Description                                                                                                         |
| --------------------------- | ------------------------------ | -------: | -------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `staging_market_mapping_id` | `bigint` generated as identity |       No | Generated                  | Database                     | Internal surrogate primary key for the staged mapping observation.                                                  |
| `import_run_id`             | `bigint`                       |       No | None                       | Import-control relationship  | References the mapping import run that loaded or generated the observation.                                         |
| `source_record_reference`   | `text`                         |       No | None                       | Import-owned identity        | Stable reference to the mapping record or evidence record inside the imported artifact.                             |
| `market_source_system`      | `text`                         |       No | None                       | Import-owned identity        | Controlled marketplace source identifier, initially `cardmarket`.                                                   |
| `source_product_id`         | `text`                         |      Yes | `null`                     | Import-owned source value    | Marketplace product identifier to be resolved to `market_products`. Nullable so malformed rows can still be staged. |
| `catalogue_source_system`   | `text`                         |      Yes | `null`                     | Import-owned target evidence | Catalogue source system for the proposed canonical target, initially `pokemon_tcg_data`.                            |
| `source_card_id`            | `text`                         |      Yes | `null`                     | Import-owned target evidence | Proposed canonical card source identifier, for example `xy5-20`.                                                    |
| `source_edition_code`       | `text`                         |      Yes | `null`                     | Import-owned target evidence | Proposed source edition code when the evidence supports an edition-level target.                                    |
| `language_code`             | `text`                         |      Yes | `null`                     | Import-owned target evidence | Proposed controlled language code when the evidence supports a variant-level target.                                |
| `finish_code`               | `text`                         |      Yes | `null`                     | Import-owned target evidence | Proposed controlled finish code when the evidence supports a variant-level target.                                  |
| `finish_detail`             | `text`                         |      Yes | `null`                     | Import-owned target evidence | Proposed detail for a confirmed non-standard finish.                                                                |
| `proposed_status`           | `text`                         |      Yes | `null`                     | Import-owned classification  | Proposed mapping classification from the source or deterministic rule.                                              |
| `confirmation_scope`        | `text`                         |      Yes | `null`                     | Import-owned classification  | Proposed confirmed target scope: `card`, `edition`, or `variant`. Null for non-confirmed classifications.           |
| `confirmation_method`       | `text`                         |      Yes | `null`                     | Import-owned evidence        | Proposed confirmation method when status is `confirmed`.                                                            |
| `evidence_level`            | `text`                         |      Yes | `null`                     | Import-owned evidence        | Proposed evidence level supporting the observation.                                                                 |
| `evidence_reference`        | `text`                         |       No | None                       | Import-owned evidence        | Durable source, fixture, page, or review reference supporting the mapping observation.                              |
| `evidence_payload`          | `jsonb`                        |       No | None                       | Import-owned evidence        | Structured mapping evidence preserved for validation and review.                                                    |
| `raw_payload`               | `jsonb`                        |       No | None                       | Import-owned evidence        | Raw or minimally transformed source mapping record.                                                                 |
| `record_checksum`           | `text`                         |      Yes | `null`                     | Import-owned evidence        | Deterministic checksum of the normalized mapping observation when available.                                        |
| `normalization_status`      | `text`                         |       No | `pending`                  | Import-control state         | Current normalization result for the staging row.                                                                   |
| `validation_status`         | `text`                         |       No | `pending`                  | Import-control state         | Current record-level validation result.                                                                             |
| `validation_completed_at`   | `timestamp with time zone`     |      Yes | `null`                     | Import-control state         | Timestamp when validation reached a terminal result.                                                                |
| `created_at`                | `timestamp with time zone`     |       No | Current database timestamp | Database                     | Timestamp when the staging mapping row was inserted.                                                                |
| `updated_at`                | `timestamp with time zone`     |       No | Current database timestamp | Database                     | Timestamp of the latest actual staging or validation-state change.                                                  |

#### Primary key

```text
staging_market_mapping_id
```

The staging primary key must not be reused as:

- persistent mapping-case identity;
- production mapping identity;
- market-product identity;
- canonical-card identity;
- mapping observation identity.

#### Foreign key

```text
import_run_id
→ import_runs.import_run_id
```

Required behavior:

- the parent run must already exist;
- the run kind and source entity type must permit market-mapping staging;
- deleting the import run must be restricted while staging rows remain;
- staging cleanup must delete rows explicitly.

#### Required constraints

##### Source-record uniqueness within one run

```text
UNIQUE (import_run_id, source_record_reference)
```

One mapping evidence record must create at most one staging row under the same source reference in one import run.

##### Non-empty source-record reference

Conceptual rule:

```text
trim(source_record_reference) <> ''
```

##### Non-empty market source system

Conceptual rule:

```text
trim(market_source_system) <> ''
```

##### Non-empty evidence reference

Conceptual rule:

```text
trim(evidence_reference) <> ''
```

##### Evidence payload required

`evidence_payload` must be present for every staged mapping observation.

##### Raw payload required

`raw_payload` must be present for every staged mapping observation.

The raw and structured evidence must not contain:

- credentials;
- tokens;
- unrelated personal data;
- unverifiable free-text claims presented as source evidence.

##### Optional text consistency

When present, the following values must contain non-whitespace text:

- `source_product_id`;
- `catalogue_source_system`;
- `source_card_id`;
- `source_edition_code`;
- `language_code`;
- `finish_code`;
- `finish_detail`;
- `proposed_status`;
- `confirmation_scope`;
- `confirmation_method`;
- `evidence_level`;
- `record_checksum`.

Empty source strings should normally be normalized to null.

#### Why target fields are nullable

A staging mapping row may represent:

- a confirmed card-level relationship;
- a confirmed edition-level relationship;
- a confirmed variant-level relationship;
- a candidate;
- an ambiguous observation;
- an unmatched product;
- an excluded product;
- an unmatched duplicate candidate;
- a malformed mapping record.

Therefore:

- `source_card_id` may be null;
- edition data may be null;
- language and finish may be null;
- `confirmation_scope` may be null;
- `proposed_status` may be null before normalization completes.

Production target requirements are enforced only when a row proposes a confirmed mapping.

#### Source record reference

`source_record_reference` identifies the mapping evidence within the source artifact.

Examples:

```text
mapping.csv#idProduct=273532
```

```text
fixture:primal-clash/mappings#product-273532
```

```text
review:case-42#decision-2026-07-28
```

The reference must be:

- stable within the artifact;
- reproducible;
- unique within one run;
- usable even when the product or target identifiers are malformed.

#### Market-product resolution

A valid staging mapping resolves the market product through:

```text
(market_source_system, source_product_id)
```

against:

```text
market_products
```

The importer must not resolve a product through:

- metaproduct ID alone;
- product name alone;
- row order;
- candidate ranking;
- catalogue card ID.

If the market product cannot be resolved:

- no persistent mapping case observation is created against a production product;
- no production mapping is created;
- the row is rejected or the run fails according to the declared scope contract.

#### Canonical-card resolution

When `source_card_id` is present, resolve the canonical card through:

```text
(catalogue_source_system, source_card_id)
```

against the production `cards` source-scoped identity.

The importer must not resolve a card through:

- card name alone;
- collector number alone;
- source product name alone;
- nearest matching record;
- metaproduct grouping alone.

A non-confirmed candidate may still preserve a proposed source card identifier without creating a production relationship.

#### Proposed mapping statuses

Initial controlled values:

- `confirmed`;
- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`.

These values describe the proposed observation classification.

They do not directly overwrite the persistent mapping case current state until transition rules are validated.

#### Confirmed target consistency

When:

```text
proposed_status = confirmed
```

then:

- `source_product_id` is required;
- `catalogue_source_system` is required;
- `source_card_id` is required;
- `confirmation_scope` is required;
- `confirmation_method` is required;
- `evidence_level` is required.

##### Card-level confirmation

When:

```text
confirmation_scope = card
```

then:

- `source_card_id` is required;
- `source_edition_code` is null;
- `language_code` is null;
- `finish_code` is null;
- `finish_detail` is null.

##### Edition-level confirmation

When:

```text
confirmation_scope = edition
```

then:

- `source_card_id` is required;
- edition identity must be deterministically resolvable;
- `source_edition_code` may be required according to the accepted edition rule;
- `language_code` is null;
- `finish_code` is null;
- `finish_detail` is null.

##### Variant-level confirmation

When:

```text
confirmation_scope = variant
```

then:

- `source_card_id` is required;
- edition identity must be resolvable;
- `language_code` is required;
- `finish_code` is required;
- `finish_detail` follows the `other` consistency rule.

#### Non-confirmed classification consistency

When `proposed_status` is one of:

- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`;

then:

```text
confirmation_scope is null
```

and:

```text
confirmation_method is null
```

A non-confirmed observation may still preserve:

- proposed card target;
- candidate edition data;
- candidate language or finish;
- evidence level;
- evidence payload.

These values remain review evidence and do not create production catalogue entities.

#### Candidate consistency

For:

```text
proposed_status = candidate
```

the row should normally include:

- a resolved market product;
- a proposed canonical target;
- evidence level;
- evidence reference.

A candidate must not be treated as confirmed merely because only one candidate is present.

#### Ambiguous consistency

For:

```text
proposed_status = ambiguous
```

one staging row may preserve:

- one aggregated ambiguous observation; or
- one candidate target among multiple ambiguous candidates.

The selected physical approach must align with `mapping_candidates`.

The recommended responsibility is:

- `staging_market_mappings` stores the source observation;
- `mapping_candidates` stores individual persistent candidate targets.

#### Unmatched consistency

For:

```text
proposed_status = unmatched
```

the row should not require a canonical target.

Unmatched means no supported candidate or confirmed target has been accepted from the available evidence.

#### Excluded consistency

For:

```text
proposed_status = excluded
```

the market product remains structurally valid.

The row must preserve an exclusion reason in `evidence_payload` or a later structured reason field.

For the Primal Clash MVP, Online Code Card products are expected examples.

Excluded rows:

- create or update a mapping case;
- create no production card mapping;
- create no edition or variant;
- contribute no canonical-card price.

#### `unmatched_duplicate_candidate` consistency

For:

```text
proposed_status = unmatched_duplicate_candidate
```

the evidence must support the accepted duplicate-like classification.

For Primal Clash, inspected evidence includes matching:

- source metaproduct identifier;
- normalized product name;
- source expansion;
- source category ID;
- source category name;

with differences limited to:

- source product ID;
- source creation timestamp.

The row must preserve the comparison evidence in `evidence_payload`.

It creates no confirmed production mapping.

#### Confirmation method

Initial candidate values:

- `direct_source_identifier`;
- `explicit_source_relationship`;
- `validated_derived_rule`;
- `manual_review`.

A direct-ID relationship for Primal Clash should use:

```text
direct_source_identifier
```

when the evidence directly associates a Cardmarket product with the canonical card.

The method does not by itself determine confirmation scope.

#### Evidence level

Initial controlled values:

- `direct`;
- `derived`;
- `manual`;
- `insufficient`.

Rules:

- `confirmed` must not use `insufficient`;
- `candidate`, `ambiguous`, and `unmatched` may use `insufficient`;
- `manual` should correspond to reviewed evidence;
- `derived` requires a documented deterministic rule;
- `direct` requires direct source evidence.

#### Evidence payload

`evidence_payload` stores structured mapping evidence.

Possible fields include:

```json
{
  "source_product_id": "273532",
  "source_card_id": "xy5-20",
  "direct_id_match": true,
  "source_expansion_id": "1585",
  "source_metaproduct_id": "12345",
  "normalized_product_name": "Vulpix",
  "source_category_id": "1",
  "source_category_name": "Pokemon Singles"
}
```

The exact JSON schema must be source- and rule-specific.

The production merge must not depend on undocumented ad hoc keys.

#### Record checksum

The normalized checksum may include:

- market source system;
- source product ID;
- catalogue source system;
- source card ID;
- edition code;
- language;
- finish;
- proposed status;
- confirmation scope;
- confirmation method;
- evidence level;
- canonicalized evidence payload.

Recommended representation:

```text
sha256:<hexadecimal digest>
```

The checksum supports:

- duplicate observation detection;
- repeated import comparison;
- parser troubleshooting;
- evidence consistency checks.

It does not replace:

- mapping-case identity;
- source record reference;
- source-scoped market-product identity.

#### Normalization status

Initial controlled values:

- `pending`;
- `normalized`;
- `normalization_failed`.

##### `pending`

The source mapping record has been loaded but normalization is incomplete.

##### `normalized`

Supported deterministic normalization completed.

This does not mean the mapping classification is valid or accepted.

##### `normalization_failed`

The row could not be normalized according to the mapping source contract.

It:

- remains preserved;
- cannot be marked valid;
- creates no persistent mapping observation;
- creates no production mapping;
- must produce rejection evidence before cleanup.

#### Validation status

Initial controlled values:

- `pending`;
- `valid`;
- `rejected`.

##### `pending`

Record-level mapping validation is incomplete.

##### `valid`

The row is structurally valid as a mapping observation.

A valid row may still propose a non-confirmed mapping status.

##### `rejected`

The row is malformed or internally inconsistent and cannot be persisted as an accepted mapping observation.

#### State consistency

When:

```text
validation_status = pending
```

then:

```text
validation_completed_at is null
```

When:

```text
validation_status in (valid, rejected)
```

then:

```text
validation_completed_at is not null
```

When:

```text
normalization_status = normalization_failed
```

then:

```text
validation_status <> valid
```

When:

```text
validation_status = valid
```

then:

```text
normalization_status = normalized
```

#### Record-level validation

A staging mapping row is valid only when:

- market source system is supported;
- source record reference is present;
- evidence reference is present;
- raw and structured evidence are present;
- proposed status is supported;
- market product resolves where the status requires it;
- target fields match confirmation scope;
- non-confirmed statuses have no confirmation scope;
- controlled language and finish values are valid where present;
- `finish_detail` is consistent with `finish_code`;
- confirmation evidence meets the minimum structural requirements;
- no internal target contradiction remains.

A row is rejected when, for example:

- source product ID is missing for a product-specific mapping;
- proposed status is unsupported;
- confirmed status has no card target;
- card-level confirmation includes variant fields;
- variant-level confirmation lacks language or finish;
- non-confirmed status includes a confirmation scope;
- `other` finish lacks detail;
- target source identity cannot be normalized;
- evidence payload is absent.

#### Run-level validation

Valid staging mapping rows participate in run-level checks.

For the accepted Primal Clash fixture, validation should confirm:

- every mapping observation references a known Cardmarket product;
- direct product mappings cover `167` Cardmarket listing variants;
- the confirmed canonical targets cover `164` canonical cards;
- six duplicate-like products remain `unmatched_duplicate_candidate`;
- four Online Code Card products remain `excluded`;
- no ordinary unmatched rows remain;
- no ambiguous rows remain;
- no conflicting confirmed targets remain;
- one market product does not receive multiple incompatible accepted observations in the same run;
- confirmed targets resolve to existing canonical cards;
- edition and variant targets are created only when the evidence supports their scope;
- no unresolved row creates a production mapping;
- run counts reconcile with mapping observations and product scope.

#### Duplicate observations within one run

Two staged rows for the same market product in one run must be evaluated.

##### Equivalent observation

When classification, target, scope, and evidence are equivalent:

- do not choose one arbitrarily without a documented rule;
- preserve both source references if both are legitimate;
- create at most one effective persistent case observation for the same evidence event.

The preferred first implementation is to reject duplicate source references through the uniqueness constraint and fail conflicting duplicate observations during run-level validation.

##### Compatible observations

A market product may have compatible evidence at different levels.

Example:

```text
one observation confirms card
another observation confirms edition
```

The run-level rule may select the stronger supported scope only when:

- both targets are compatible;
- evidence thresholds are met;
- the transition is deterministic;
- all evidence remains preserved.

##### Conflicting observations

Conflicting target or status observations must:

- fail automatic mapping merge;
- preserve all staged evidence;
- create review evidence;
- not create multiple active production mappings.

#### Persistent mapping-case handoff

A valid staging row resolves or creates a persistent mapping case for the market product.

It then creates a `mapping_case_observations` row containing:

- import run;
- proposed status;
- proposed target;
- confirmation scope;
- method;
- evidence level;
- evidence reference;
- structured evidence.

The staging row itself must not become the persistent mapping case.

#### Candidate handoff

When the observation includes one or more proposed targets without confirmation:

- preserve the overall observation in `mapping_case_observations`;
- create individual persistent targets in `mapping_candidates`;
- preserve rank or supporting evidence where available;
- do not create production mappings.

#### Production mapping handoff

A valid staging row may create a production mapping only when:

- proposed status is `confirmed`;
- the persistent mapping-case transition accepts `confirmed`;
- the target resolves;
- the confirmation scope is valid;
- all required production catalogue entities exist or are created through supported rules;
- no active mapping conflict exists;
- run-level validation passes.

Non-confirmed rows create no `card_market_product_mappings` row.

#### Edition and variant creation boundary

##### Edition creation

A confirmed staging mapping may create or resolve an edition only when:

```text
confirmation_scope in (edition, variant)
```

and edition identity is sufficiently evidenced.

##### Variant creation

A confirmed staging mapping may create or resolve a variant only when:

```text
confirmation_scope = variant
```

and language and finish are confirmed.

The importer must not create editions or variants from:

- candidate rows;
- ambiguous rows;
- unmatched rows;
- excluded rows;
- unmatched duplicate candidates;
- confirmed card-level rows.

#### Rejected rows

A rejected staging mapping row:

- creates no mapping-case observation;
- creates no candidate;
- creates no production mapping;
- creates no edition;
- creates no variant;
- must preserve permanent rejection evidence before staging cleanup.

#### Mutability

##### Before normalization completes

The importer may populate normalized values and processing statuses.

##### After validation completes

Normalized mapping content should become immutable for the run.

A correction should normally use a new run or an explicit pre-merge reset.

##### After production merge starts

Staging mapping rows must not change.

##### After terminal run status

Rows remain read-only until staging cleanup.

#### Cleanup behavior

Cleanup may occur only after:

- the parent run reaches a terminal state;
- mapping-case observations are preserved;
- candidate targets are preserved;
- status transitions are preserved;
- confirmed production mappings have committed or rolled back;
- rejection evidence is preserved;
- source artifact references remain durable;
- retention policy permits deletion.

Cleanup must not delete:

- import runs;
- market products;
- mapping cases;
- mapping observations;
- candidates;
- status history;
- confirmed mappings;
- catalogue entities;
- wishlist data.

#### Primal Clash examples

##### Confirmed card-level row

| Column                    | Example value              |
| ------------------------- | -------------------------- |
| `market_source_system`    | `cardmarket`               |
| `source_product_id`       | Cardmarket `idProduct`     |
| `catalogue_source_system` | `pokemon_tcg_data`         |
| `source_card_id`          | `xy5-20`                   |
| `source_edition_code`     | `null`                     |
| `language_code`           | `null`                     |
| `finish_code`             | `null`                     |
| `proposed_status`         | `confirmed`                |
| `confirmation_scope`      | `card`                     |
| `confirmation_method`     | `direct_source_identifier` |
| `evidence_level`          | `direct`                   |

##### Excluded row

| Column                 | Example value                              |
| ---------------------- | ------------------------------------------ |
| `market_source_system` | `cardmarket`                               |
| `source_product_id`    | Online Code Card product ID                |
| `source_card_id`       | `null`                                     |
| `proposed_status`      | `excluded`                                 |
| `confirmation_scope`   | `null`                                     |
| `evidence_level`       | `direct` or `derived`                      |
| `evidence_payload`     | Structured category and exclusion evidence |

##### Duplicate-like unmatched row

| Column                 | Example value                                                    |
| ---------------------- | ---------------------------------------------------------------- |
| `market_source_system` | `cardmarket`                                                     |
| `source_product_id`    | Duplicate-like product ID                                        |
| `proposed_status`      | `unmatched_duplicate_candidate`                                  |
| `confirmation_scope`   | `null`                                                           |
| `evidence_level`       | `derived`                                                        |
| `evidence_payload`     | Metaproduct, name, expansion, category, and timestamp comparison |

#### Relationships

```text
import_runs
    1 → many staging_market_mappings
```

A staging mapping has no direct foreign key to:

- `market_products`;
- `cards`;
- `card_editions`;
- `card_variants`;
- mapping cases;
- mapping candidates;
- production mappings.

All production identities are resolved during validated processing.

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

```text
staging_market_mappings.import_run_id
→ import_runs.import_run_id
```

Staging cleanup deletes rows explicitly.

#### Index candidates

Likely access paths include:

- all rows by `import_run_id`;
- lookup by `(import_run_id, source_record_reference)`;
- filtering by proposed status;
- filtering by validation status;
- lookup by market product source identity;
- lookup by proposed card source identity;
- duplicate detection by product within a run;
- confirmed observations by scope;
- pending validation rows.

Potential supporting indexes include:

```text
(import_run_id, validation_status)
```

```text
(import_run_id, market_source_system, source_product_id)
```

```text
(import_run_id, proposed_status, confirmation_scope)
```

Final indexes must be selected during migration and validation-query design.

#### Validation requirements

The first schema validation must confirm:

- every accepted mapping source row can be staged;
- raw and structured evidence are preserved;
- source product and card identifiers remain text;
- malformed rows can be staged without being silently lost;
- blank required references cause rejection;
- proposed statuses are controlled;
- confirmed status requires a canonical-card target;
- card-level confirmation rejects edition and variant target fields;
- edition-level confirmation requires resolvable edition evidence;
- variant-level confirmation requires language and finish;
- non-confirmed statuses have null confirmation scope;
- `other` finish requires detail;
- unknown language or finish does not create a variant;
- all `167` direct Cardmarket listing mappings remain represented;
- all `164` canonical cards remain covered by accepted mappings;
- six duplicate-like products remain `unmatched_duplicate_candidate`;
- four Online Code Card products remain `excluded`;
- no ordinary unmatched or ambiguous records remain in the accepted fixture;
- no conflicting active production mappings are created;
- repeated identical mapping imports create no duplicate production mapping;
- weaker repeated evidence does not replace confirmed mappings;
- staging cleanup preserves cases, observations, candidates, history, and confirmed mappings;
- deleting staging rows does not affect production catalogue or wishlist data.

#### Deferred fields

The following fields are not included in the first version:

- resolved production `market_product_id`;
- resolved production `card_id`;
- resolved production edition ID;
- resolved production variant ID;
- persistent mapping-case ID;
- persistent candidate ID;
- production mapping ID;
- candidate rank;
- candidate score;
- reviewer user ID;
- review comment;
- review-state field;
- production merge outcome;
- source product URL as a dedicated column;
- parser warning array;
- normalization rule version;
- superseded mapping reference.

These values belong to production, review, candidate, history, or outcome structures unless future evidence demonstrates a clear staging responsibility.

#### Open questions

- Does the accepted mapping fixture contain one row per product or multiple candidate rows per product?
- Should edition identity be represented only through `source_edition_code`, or also through a project-controlled proposed edition key?
- Should candidate rank and score be staged here or only in `mapping_candidates`?
- Should excluded and duplicate-candidate reasons use dedicated columns or remain structured evidence?
- Should equivalent compatible observations be consolidated before persistence or stored as separate mapping-case observations?
- Should `record_checksum` be mandatory for mapping fixtures?
- Should normalized staging content become database-protected after validation?
- What retention period should apply to successful and failed mapping staging rows?

### `import_record_outcomes`

#### Purpose

Store one permanent detailed import result for one production or source-scoped entity evaluated during an import run.

The table provides auditable evidence for outcomes such as:

- inserted;
- updated;
- unchanged;
- missing;
- retired;
- reactivated;
- conflict;
- skipped.

An import outcome explains what the importer determined for a specific entity within one run.

It is not:

- a staging row;
- a rejected-source record;
- a mapping status;
- a production entity;
- an import-run summary;
- a free-text application log.

#### Ownership

- Data owner: import-control and production-merge process.
- User editing: not allowed.
- Normal import update: not allowed after insertion.
- Normal import deletion: not allowed.
- Correction: requires an explicit administrative process.
- Long-term retention: required as permanent import evidence.

#### Columns

| Column                     | PostgreSQL type                | Nullable | Default                    | Ownership                     | Description                                                                                        |
| -------------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------- |
| `import_record_outcome_id` | `bigint` generated as identity |       No | Generated                  | Database                      | Internal surrogate primary key for the detailed import outcome.                                    |
| `import_run_id`            | `bigint`                       |       No | None                       | Import-control relationship   | References the import run that produced the outcome.                                               |
| `entity_type`              | `text`                         |       No | None                       | Import-control classification | Controlled type of entity evaluated by the importer.                                               |
| `source_system`            | `text`                         |      Yes | `null`                     | Import-control identity       | External source system when the evaluated entity has a source-scoped identity.                     |
| `source_entity_id`         | `text`                         |      Yes | `null`                     | Import-control identity       | External source identifier of the evaluated entity when available.                                 |
| `production_entity_id`     | `bigint`                       |      Yes | `null`                     | Import-control reference      | Internal production identifier when a production row exists and the entity type uses a bigint key. |
| `outcome_type`             | `text`                         |       No | None                       | Import-control classification | Controlled result of processing the entity during the run.                                         |
| `change_summary`           | `jsonb`                        |      Yes | `null`                     | Import-control evidence       | Structured summary of actual changed fields or lifecycle transition.                               |
| `source_record_reference`  | `text`                         |      Yes | `null`                     | Import-control evidence       | Durable reference to the source or staging record associated with the outcome.                     |
| `reason_code`              | `text`                         |      Yes | `null`                     | Import-control evidence       | Controlled reason for outcomes that require explanation.                                           |
| `reason_detail`            | `text`                         |      Yes | `null`                     | Import-control evidence       | Human-readable explanation without secrets.                                                        |
| `recorded_at`              | `timestamp with time zone`     |       No | Current database timestamp | Database                      | Timestamp when the permanent outcome was recorded.                                                 |

#### Primary key

```text
import_record_outcome_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- import-run ID;
- source entity ID;
- production entity ID;
- staging row ID.

#### Foreign key

```text
import_run_id
→ import_runs.import_run_id
```

Required behavior:

- the referenced import run must exist;
- deleting an import run with outcomes must be restricted;
- outcomes must remain preserved after staging cleanup;
- a terminal successful run must not lose its detailed outcomes.

#### Entity types

Initial candidate controlled values:

- `expansion`;
- `expansion_source_identifier`;
- `card`;
- `card_edition`;
- `card_variant`;
- `market_product`;
- `card_market_product_mapping`;
- `market_price_snapshot`.

The exact controlled list must match the production entities processed by the importer.

The table should not use arbitrary table names supplied by untrusted input.

#### Outcome types

Initial controlled values:

- `inserted`;
- `updated`;
- `unchanged`;
- `missing`;
- `retired`;
- `reactivated`;
- `conflict`;
- `skipped`.

##### `inserted`

A new production row was created.

##### `updated`

An existing production row changed because one or more accepted import-owned values differed.

##### `unchanged`

The corresponding production row already contained equivalent normalized values.

No unnecessary update was executed.

##### `missing`

An existing production identity was absent from a complete authoritative import scope.

The entity was preserved.

##### `retired`

An existing production row was explicitly moved to inactive lifecycle state through an approved rule.

##### `reactivated`

An inactive production row was explicitly returned to active state.

##### `conflict`

The importer detected incompatible source or production evidence and did not apply the conflicting change.

##### `skipped`

The source or production entity was deliberately excluded from a particular merge action without being structurally rejected.

Use of `skipped` must require a controlled reason code.

#### Rejected-record boundary

Structurally invalid source rows belong to:

- `rejected_source_records`;
- `rejected_source_record_reasons`.

They should not normally create an `import_record_outcomes` row because no valid production identity was evaluated.

Examples include:

- missing required source identity;
- malformed numeric value;
- invalid timestamp;
- unsupported row structure.

An outcome may reference a source record that was valid but could not be merged because of a production conflict.

#### Mapping-status boundary

The following are mapping classifications rather than generic import outcomes:

- `confirmed`;
- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`.

They belong to mapping-case observations and status history.

For example:

```text
market product inserted into market_products
mapping case classified as excluded
```

produces:

- `market_product / inserted` in `import_record_outcomes`;
- `excluded` in mapping structures.

It must not produce:

```text
outcome_type = excluded
```

#### Required constraints

##### Non-empty entity type

Conceptual rule:

```text
trim(entity_type) <> ''
```

##### Non-empty outcome type

Conceptual rule:

```text
trim(outcome_type) <> ''
```

##### Source identity consistency

`source_system` and `source_entity_id` should normally either both be present or both be null.

Conceptual rule:

```text
source_system is null
and source_entity_id is null
```

or:

```text
source_system is not null
and source_entity_id is not null
```

Exceptions require an explicitly documented entity-type rule.

##### Optional text consistency

When present, the following fields must contain non-whitespace text:

- `source_system`;
- `source_entity_id`;
- `source_record_reference`;
- `reason_code`;
- `reason_detail`.

##### Required identity

Every outcome must identify the evaluated entity through at least one of:

- source-scoped identity;
- production entity ID.

Conceptual rule:

```text
production_entity_id is not null
or (
    source_system is not null
    and source_entity_id is not null
)
```

##### Outcome and production identity

For:

- `inserted`;
- `updated`;
- `unchanged`;
- `retired`;
- `reactivated`;

`production_entity_id` is normally required.

For `missing`, the production entity ID is required because the outcome starts from an existing production row.

For `conflict`, production identity may be null when the conflict prevented unique production resolution.

##### Reason-code requirements

A controlled reason code is required for:

- `conflict`;
- `skipped`.

A reason code is recommended for:

- `missing`;
- `retired`;
- `reactivated`.

For ordinary:

- `inserted`;
- `unchanged`;

a reason code is normally null.

#### Detailed-outcome uniqueness

One import run should produce at most one effective outcome for one entity type and one evaluated identity.

Conceptually:

```text
import_run_id
entity_type
resolved entity identity
```

The final physical uniqueness cannot rely on one simple nullable column set because entities may be identified through:

- production ID;
- source-scoped identity;
- both.

Recommended implementation direction:

- one partial unique index for rows with `production_entity_id`;
- one partial unique index for source-only rows.

Conceptual production-identity uniqueness:

```text
UNIQUE (
    import_run_id,
    entity_type,
    production_entity_id
)
WHERE production_entity_id is not null
```

Conceptual source-only uniqueness:

```text
UNIQUE (
    import_run_id,
    entity_type,
    source_system,
    source_entity_id
)
WHERE production_entity_id is null
```

The exact PostgreSQL implementation must be reviewed during migration design.

#### Production entity ID

`production_entity_id` stores the internal bigint primary key of the entity named by `entity_type`.

Examples:

| `entity_type`           | Referenced logical key                            |
| ----------------------- | ------------------------------------------------- |
| `card`                  | `cards.card_id`                                   |
| `market_product`        | `market_products.market_product_id`               |
| `market_price_snapshot` | `market_price_snapshots.market_price_snapshot_id` |

This is a polymorphic reference and cannot be enforced through one ordinary foreign key.

The importer must validate that:

- the entity type is supported;
- the referenced production row exists where required;
- the identifier belongs to the correct production table.

A generic database-level polymorphic foreign key is not proposed.

#### Source identity

`source_system` and `source_entity_id` preserve the source-scoped identity used by the importer.

Examples:

```text
pokemon_tcg_data / xy5-20
```

```text
cardmarket / 273532
```

For entities without one external source identity, such as a project-generated card edition, these fields may be null and `production_entity_id` becomes the required identity.

The importer must not reconstruct source identity from display names.

#### Source record reference

`source_record_reference` points to the source evidence associated with the outcome.

Examples:

```text
cards/xy5.json#xy5-20
```

```text
products.csv#idProduct=273532
```

For `missing` outcomes, no current source record exists.

The field may therefore be null, while `reason_code` explains that the production identity was absent from an authoritative scope.

#### Change summary

`change_summary` stores structured evidence of actual field changes.

Recommended format:

```json
{
  "name": {
    "before": "Old name",
    "after": "New name"
  },
  "rarity": {
    "before": null,
    "after": "Common"
  }
}
```

For lifecycle outcomes:

```json
{
  "is_active": {
    "before": true,
    "after": false
  },
  "retired_at": {
    "before": null,
    "after": "2026-07-28T12:00:00Z"
  }
}
```

The structure must:

- use controlled production field names;
- omit unchanged fields;
- contain no secrets;
- avoid duplicating complete raw source payloads;
- preserve enough evidence to explain the actual production change.

#### Change-summary consistency

##### Inserted

For `inserted`, `change_summary` may contain the initial accepted production values, but storing the complete row is not required.

Recommended approach:

- include key imported fields when useful;
- omit database-managed timestamps and generated IDs unless operationally necessary.

##### Updated

For `updated`, `change_summary` is required and must contain at least one actual changed field.

##### Unchanged

For `unchanged`, `change_summary` should be null or an empty object.

Null is preferred.

##### Missing

For `missing`, `change_summary` should normally be null because the production row is preserved.

##### Retired or reactivated

For `retired` and `reactivated`, `change_summary` is required and must show the lifecycle transition.

##### Conflict

For `conflict`, `change_summary` may contain the incompatible proposed values, but detailed raw evidence should remain in staging or permanent evidence structures.

#### Reason codes

Reason codes are controlled technical identifiers.

Initial candidate examples include:

- `not_observed_in_authoritative_scope`;
- `explicit_source_retirement`;
- `approved_manual_retirement`;
- `source_identity_conflict`;
- `production_value_conflict`;
- `same_snapshot_different_price`;
- `weaker_evidence_ignored`;
- `unsupported_merge_action`;
- `already_processed`;
- `dependency_unresolved`.

The exact controlled set should be organized by entity type and outcome.

A generic reason-code lookup table is deferred.

#### Merge transaction boundary

Outcomes describing committed production changes must be recorded inside the same atomic production transaction as those changes.

This includes:

- `inserted`;
- `updated`;
- `unchanged`, when permanent detailed reporting is required;
- `retired`;
- `reactivated`;
- committed non-mutating conflicts handled inside the run.

If the production transaction rolls back:

- outcomes claiming committed production changes must also roll back;
- the run becomes `merge_failed`;
- failure evidence remains outside or after the rolled-back production transaction;
- no permanent outcome may falsely claim a committed insert or update.

Validation-stage rejection evidence may be recorded before the production transaction because it does not claim a committed production change.

#### Append-only behavior

Once inserted for a terminal import run, an outcome is immutable.

The normal importer must not:

- change `outcome_type`;
- replace entity identity;
- rewrite change summary;
- change reason code;
- delete the row.

A correction requires:

- an explicit administrative record;
- preservation of the original outcome;
- a separately traceable corrective action.

A dedicated outcome-correction table is deferred.

#### Missing outcomes

Missing outcomes may be created only when:

```text
import_runs.is_authoritative = true
```

and the declared scope has passed validation.

A missing outcome must identify:

- the existing production entity;
- the entity type;
- the authoritative run;
- a controlled missing reason.

Missing does not mean:

- deleted;
- retired;
- invalid;
- rejected.

A missing outcome must not modify:

- production lifecycle state;
- wishlist data;
- confirmed mappings;
- price history.

#### Conflict outcomes

A conflict outcome records that a valid processing attempt could not be applied safely.

Examples include:

- same source identity resolving to another production entity;
- same price snapshot identity with different values;
- incompatible active mapping;
- existing edition code resolving to another edition.

A conflict outcome:

- must not claim that a production update occurred;
- must preserve existing production state;
- requires a reason code;
- should reference durable evidence;
- may cause the run to fail depending on the run-level policy.

#### Unchanged outcomes

An unchanged outcome proves idempotent comparison.

It means:

- source identity resolved;
- normalized comparison completed;
- accepted production values were equivalent;
- no update statement was necessary or no actual value changed;
- `updated_at` remained unchanged.

Unchanged outcomes are important for validating repeated imports.

#### Relationship to import-run summaries

`import_runs` may contain summary counts such as:

- inserted records;
- updated records;
- unchanged records;
- missing records;
- retired records.

Those counts must be derived or reconciled against `import_record_outcomes`.

The outcome table is the detailed evidence source.

A successful run must not report summary counts that disagree with the permanent detailed outcomes for the relevant entity scope.

#### Primal Clash examples

##### Inserted card

| Column                    | Example value           |
| ------------------------- | ----------------------- |
| `entity_type`             | `card`                  |
| `source_system`           | `pokemon_tcg_data`      |
| `source_entity_id`        | `xy5-20`                |
| `production_entity_id`    | Internal Vulpix card ID |
| `outcome_type`            | `inserted`              |
| `source_record_reference` | `cards/xy5.json#xy5-20` |
| `reason_code`             | `null`                  |

##### Unchanged market product

| Column                 | Example value              |
| ---------------------- | -------------------------- |
| `entity_type`          | `market_product`           |
| `source_system`        | `cardmarket`               |
| `source_entity_id`     | `273532`                   |
| `production_entity_id` | Internal market product ID |
| `outcome_type`         | `unchanged`                |
| `change_summary`       | `null`                     |

##### Missing card

| Column                    | Example value                         |
| ------------------------- | ------------------------------------- |
| `entity_type`             | `card`                                |
| `source_system`           | `pokemon_tcg_data`                    |
| `source_entity_id`        | Existing card source ID               |
| `production_entity_id`    | Existing internal card ID             |
| `outcome_type`            | `missing`                             |
| `source_record_reference` | `null`                                |
| `reason_code`             | `not_observed_in_authoritative_scope` |

##### Price conflict

| Column                 | Example value                     |
| ---------------------- | --------------------------------- |
| `entity_type`          | `market_price_snapshot`           |
| `source_system`        | `cardmarket`                      |
| `source_entity_id`     | Product ID and snapshot reference |
| `production_entity_id` | Existing snapshot ID or `null`    |
| `outcome_type`         | `conflict`                        |
| `reason_code`          | `same_snapshot_different_price`   |
| `reason_detail`        | Non-secret conflict explanation   |

#### Relationships

```text
import_runs
    1 → many import_record_outcomes
```

The table does not have direct foreign keys to every production table because `production_entity_id` is polymorphic.

Logical relationships are validated by the import process.

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

```text
import_record_outcomes.import_run_id
→ import_runs.import_run_id
```

Staging cleanup has no effect on permanent outcomes.

#### Index candidates

Likely access paths include:

- all outcomes by `import_run_id`;
- filtering by `entity_type`;
- filtering by `outcome_type`;
- lookup by production entity;
- lookup by source-scoped identity;
- reconciliation of run summary counts;
- history of one production entity across runs.

Potential supporting indexes include:

```text
(import_run_id, entity_type, outcome_type)
```

```text
(entity_type, production_entity_id, import_run_id)
```

```text
(source_system, source_entity_id, import_run_id)
```

Final indexes must be selected during migration and reporting-query design.

#### Validation requirements

The first schema validation must confirm:

- every outcome references an existing import run;
- entity and outcome types are controlled;
- each outcome has a usable source or production identity;
- duplicate effective outcomes for one entity in one run are rejected;
- `updated` requires a non-empty change summary;
- `unchanged` has no changed fields;
- `missing` requires an existing production entity;
- missing outcomes are created only for authoritative runs;
- `conflict` requires a reason code;
- `skipped` requires a reason code;
- successful run summary counts reconcile with detailed outcomes;
- repeated identical Primal Clash imports produce `unchanged` outcomes rather than duplicate production rows;
- committed outcomes roll back when the production transaction fails;
- rejected staging rows remain represented by rejection structures rather than false production outcomes;
- excluded mapping cases remain mapping classifications rather than generic import outcomes;
- staging cleanup does not remove detailed outcomes;
- outcomes cannot be changed after the parent run reaches a terminal state.

#### Deferred fields

The following fields are not included in the first version:

- direct foreign key for every production entity type;
- staging table name;
- staging row ID;
- transaction ID;
- importer step name;
- retry number;
- processing duration;
- reviewer identifier;
- correction reference;
- before-row payload;
- after-row payload;
- warning array;
- severity;
- free-text administrative notes;
- source artifact checksum duplicated from `import_runs`.

These fields may be added only when operational reporting or correction requirements establish a clear responsibility.

#### Open questions

- Should `unchanged` outcomes be stored for every row, or only summarized for large imports?
- Should `production_entity_id` remain a polymorphic bigint, or should entity-specific nullable foreign keys be used?
- Should source-only conflict outcomes use a generated composite `source_entity_id` when no single external identifier exists?
- Which outcome types are valid for each entity type?
- Which reason codes are mandatory for `missing`, `retired`, and `reactivated`?
- Should `change_summary` use one shared JSON schema or an entity-specific schema?
- Should committed `unchanged` outcomes be inserted inside the production transaction?
- How should administrative corrections preserve and supersede incorrect historical outcomes?

## Rejected and mapping-review tables

### `rejected_source_records`

#### Purpose

Store one permanent rejected source record produced during import normalization or validation.

The table preserves source evidence for a row that must not enter the corresponding production structure.

A rejected source record supports:

- source-count reconciliation;
- troubleshooting;
- parser review;
- validation-rule review;
- repeated-import comparison;
- audit of why production data was not changed.

A rejected source record is not:

- a staging row;
- a production entity;
- a merge outcome;
- a mapping classification;
- a general application error log.

#### Ownership

- Data owner: import-control and validation process.
- User editing: not allowed.
- Normal import update: not allowed after insertion.
- Normal import deletion: not allowed.
- Long-term retention: required as permanent import evidence.
- Correction: requires an explicit administrative process that preserves the original rejection.

#### Columns

| Column                      | PostgreSQL type                | Nullable | Default                    | Ownership                     | Description                                                                                                   |
| --------------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `rejected_source_record_id` | `bigint` generated as identity |       No | Generated                  | Database                      | Internal surrogate primary key for the permanent rejected record.                                             |
| `import_run_id`             | `bigint`                       |       No | None                       | Import-control relationship   | References the import run in which the source row was rejected.                                               |
| `source_entity_type`        | `text`                         |       No | None                       | Import-control classification | Controlled source-record category, for example `card`, `market_product`, `market_price`, or `market_mapping`. |
| `source_system`             | `text`                         |       No | None                       | Import-control identity       | External source system from which the rejected row originated.                                                |
| `source_record_reference`   | `text`                         |       No | None                       | Import-control identity       | Durable reference to the rejected row within the imported source artifact.                                    |
| `source_entity_id`          | `text`                         |      Yes | `null`                     | Import-control identity       | Source entity identifier when one could be extracted safely from the rejected row.                            |
| `rejection_stage`           | `text`                         |       No | None                       | Import-control classification | Processing stage at which the row became unusable.                                                            |
| `raw_payload`               | `jsonb`                        |       No | None                       | Import-control evidence       | Raw or minimally sanitized source record preserved for review.                                                |
| `normalized_payload`        | `jsonb`                        |      Yes | `null`                     | Import-control evidence       | Partially normalized representation available when normalization completed far enough to preserve it.         |
| `record_checksum`           | `text`                         |      Yes | `null`                     | Import-control evidence       | Deterministic checksum of the rejected source observation when available.                                     |
| `summary_reason_code`       | `text`                         |       No | None                       | Import-control evidence       | Primary controlled reason code used for high-level reporting.                                                 |
| `summary_reason_detail`     | `text`                         |      Yes | `null`                     | Import-control evidence       | Human-readable primary explanation without secrets.                                                           |
| `rejected_at`               | `timestamp with time zone`     |       No | Current database timestamp | Database                      | Timestamp when the permanent rejection record was created.                                                    |

#### Primary key

```text
rejected_source_record_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- staging row ID;
- source entity ID;
- source record reference;
- import-run ID.

#### Foreign key

```text
import_run_id
→ import_runs.import_run_id
```

Required behavior:

- the referenced import run must exist;
- deleting an import run with rejected records must be restricted;
- staging cleanup must not remove permanent rejection evidence;
- terminal failed and successful runs must preserve their rejected records.

#### Required uniqueness

One source record should create at most one permanent rejected-record header in one import run.

```text
UNIQUE (
    import_run_id,
    source_entity_type,
    source_system,
    source_record_reference
)
```

Multiple validation failures for the same row are stored in `rejected_source_record_reasons`, not as duplicate rejected-record headers.

#### Required constraints

##### Non-empty source entity type

```text
trim(source_entity_type) <> ''
```

##### Non-empty source system

```text
trim(source_system) <> ''
```

##### Non-empty source-record reference

```text
trim(source_record_reference) <> ''
```

##### Non-empty rejection stage

```text
trim(rejection_stage) <> ''
```

##### Raw payload required

`raw_payload` must always be present.

The importer must not create a permanent rejection record without preserving enough source evidence to explain the failure.

##### Non-empty summary reason

```text
trim(summary_reason_code) <> ''
```

##### Optional text consistency

When present, the following fields must contain non-whitespace text:

- `source_entity_id`;
- `record_checksum`;
- `summary_reason_detail`.

#### Source entity types

Initial controlled values:

- `expansion`;
- `card`;
- `market_product`;
- `market_price`;
- `market_mapping`.

The exact list should align with:

- staging tables;
- import-run source entity types;
- validation rules.

The table should not accept arbitrary table names or user-provided type names.

#### Rejection stages

Initial controlled values:

- `ingestion`;
- `normalization`;
- `record_validation`;
- `dependency_resolution`;
- `run_validation`;
- `production_precondition`.

##### `ingestion`

The source row could be read as a record but failed an ingestion-level contract.

Examples:

- unsupported encoding in one field;
- malformed record envelope;
- missing required source object structure.

A source artifact that cannot be opened at all is a run-level failure and may produce no individual rejected record.

##### `normalization`

The row could not be normalized deterministically.

Examples:

- invalid timestamp;
- unsupported numeric syntax;
- malformed source identifier;
- incompatible field type.

##### `record_validation`

Normalization completed, but the normalized row failed one or more record-level rules.

Examples:

- missing required card name;
- missing source product ID;
- negative market price;
- unsupported confirmation scope.

##### `dependency_resolution`

The row is structurally valid but a required production or source dependency could not be resolved.

Examples:

- card source expansion cannot resolve to an internal expansion;
- price row references an unknown market product;
- confirmed mapping references an unknown canonical card.

Whether dependency failure rejects one row or fails the entire run depends on the authoritative run contract.

##### `run_validation`

The row participates in a run-level conflict.

Examples:

- duplicate source identity within one run;
- conflicting duplicate price observations;
- incompatible mapping observations for one market product.

##### `production_precondition`

The normalized row is valid, but a required production precondition prevents merge.

Examples:

- source identity already belongs to another production entity;
- active mapping conflict;
- same snapshot identity already exists with different values.

Some production conflicts may instead be represented through `import_record_outcomes`. The boundary must remain consistent:

- structurally unusable source row → rejected record;
- valid entity evaluation blocked by production conflict → import outcome `conflict`.

#### Rejected-record boundary

Use `rejected_source_records` when the source observation itself cannot be accepted as a valid input record for its target process.

Examples:

- missing required source identity;
- malformed decimal;
- unsupported status;
- invalid scope and target combination;
- unresolved required dependency under the run contract.

Do not use this table for:

- a valid market product classified as `excluded`;
- a valid product classified as `unmatched`;
- a valid product classified as `unmatched_duplicate_candidate`;
- a valid mapping candidate;
- a valid unchanged production record;
- a missing production entity.

Those belong to mapping structures or import outcomes.

#### Source record reference

`source_record_reference` must identify the rejected row within the source artifact.

Examples:

```text
cards/xy5.json#line-21
```

```text
products.csv#record-42
```

```text
prices.csv#idProduct=273532&row=42
```

```text
mapping-fixture.json#product-273532
```

It must be:

- stable within the import artifact;
- reproducible;
- independent from staging row IDs;
- usable when the source entity ID is missing.

#### Source entity ID

`source_entity_id` is optional because rejected rows may lack a usable source identity.

Examples:

- valid extracted card ID despite missing name;
- valid product ID despite malformed category;
- null when the identifier itself is missing or malformed.

The importer must not invent an identifier for convenience.

For composite source observations, a documented composite text representation may be used when one durable source identifier does not exist.

#### Raw payload

`raw_payload` preserves the source evidence that produced the rejection.

It should contain:

- the original source record where practical;
- or a minimally sanitized equivalent that preserves all validation-relevant fields.

It must not contain:

- credentials;
- access tokens;
- unrelated secrets;
- unnecessary personal information.

The raw payload must not be silently corrected after rejection.

#### Normalized payload

`normalized_payload` stores the partial normalized representation when useful.

Examples:

- trimmed source identifiers;
- parsed fields that succeeded;
- null-normalized optional values;
- rejected normalized numeric value;
- proposed mapping scope.

It may be null when normalization failed before a meaningful normalized representation existed.

The normalized payload must not be treated as production data.

#### Record checksum

The checksum may support:

- duplicate rejection detection;
- repeated-source comparison;
- parser regression analysis;
- evidence integrity.

Recommended representation:

```text
sha256:<hexadecimal digest>
```

The checksum must not replace:

- source record reference;
- source identity;
- import-run relationship.

The checksum input should be defined consistently per source entity type.

#### Summary reason code

`summary_reason_code` provides one primary reason for reporting and quick filtering.

Examples:

- `missing_required_source_id`;
- `missing_required_name`;
- `invalid_timestamp`;
- `invalid_decimal`;
- `negative_price`;
- `unsupported_currency`;
- `all_price_metrics_null`;
- `duplicate_source_identity`;
- `unresolved_required_expansion`;
- `unresolved_market_product`;
- `unsupported_mapping_status`;
- `invalid_confirmation_scope`;
- `missing_mapping_evidence`;
- `conflicting_duplicate_observation`.

The full set of reasons belongs to `rejected_source_record_reasons`.

The primary reason should be selected deterministically according to documented validation precedence.

#### Multiple rejection reasons

One rejected source record may fail several independent validation rules.

Example:

```text
source product ID missing
raw name blank
source expansion ID malformed
```

The header row stores:

```text
summary_reason_code = missing_required_source_id
```

while all reasons are stored in:

```text
rejected_source_record_reasons
```

The summary code must not cause secondary reasons to be discarded.

#### Insert behavior

Create a rejected source record when:

- the source row has been staged or otherwise identified;
- normalization or validation reaches a terminal rejected result;
- the source reference is known;
- the raw payload is available;
- at least one structured rejection reason exists.

The rejected-record header and its reason rows should be inserted in one transaction.

#### Repeated import behavior

The same source record rejected in a later import run creates a new rejection record for the new run.

This is expected because:

- each run is independently auditable;
- validation rules or importer versions may differ;
- source artifacts may change;
- repeated failure history is meaningful.

Within the same run, the same rejected source reference must not create duplicate headers.

#### Append-only behavior

After insertion, rejected records are immutable.

The importer must not:

- change the source identity;
- replace raw payload;
- rewrite the summary reason;
- delete the record after staging cleanup.

If a later importer version accepts the same source row:

- the previous rejection remains preserved;
- the later run records the accepted merge outcome separately.

#### Transaction boundary

Record-level rejection evidence may be inserted before the production merge transaction because it does not claim a committed production change.

However:

- the rejected header and all reason rows must be atomic together;
- a run must not reach `succeeded` until rejected counts reconcile;
- a failed production merge must preserve validation-stage rejection evidence.

#### Relationship to staging

A rejected record may originate from:

- `staging_cards`;
- `staging_market_products`;
- `staging_market_prices`;
- `staging_market_mappings`.

The permanent table does not require a direct foreign key to a staging row because staging data may later be deleted.

The durable relationship uses:

- `import_run_id`;
- source entity type;
- source system;
- source record reference;
- raw payload.

A staging row ID may appear inside operational logs, but it should not be the only permanent reference.

#### Relationship to import-run summaries

For applicable run kinds:

```text
import_runs.rejected_records
```

must reconcile with the number of rejected source-record headers in the declared scope.

One rejected source record counts once regardless of how many reasons it has.

#### Primal Clash examples

##### Rejected card

| Column                    | Example value                 |
| ------------------------- | ----------------------------- |
| `source_entity_type`      | `card`                        |
| `source_system`           | `pokemon_tcg_data`            |
| `source_record_reference` | `cards/xy5.json#line-21`      |
| `source_entity_id`        | `null` or extracted source ID |
| `rejection_stage`         | `record_validation`           |
| `summary_reason_code`     | `missing_required_source_id`  |
| `raw_payload`             | Original source card object   |

##### Rejected price

| Column                    | Example value               |
| ------------------------- | --------------------------- |
| `source_entity_type`      | `market_price`              |
| `source_system`           | `cardmarket`                |
| `source_record_reference` | `prices.csv#record-42`      |
| `source_entity_id`        | `273532`                    |
| `rejection_stage`         | `normalization`             |
| `summary_reason_code`     | `invalid_decimal`           |
| `normalized_payload`      | Partial parsed price record |

##### Valid excluded product

An Online Code Card product is not stored here merely because it is outside MVP mapping scope.

It remains:

- a valid `market_products` row;
- a mapping case classified as `excluded`.

#### Relationships

```text
import_runs
    1 → many rejected_source_records
```

```text
rejected_source_records
    1 → many rejected_source_record_reasons
```

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

```text
rejected_source_records.import_run_id
→ import_runs.import_run_id
```

For reason rows, the recommended behavior is:

```text
ON DELETE RESTRICT
```

during normal operation.

Administrative cleanup of an erroneously created rejection record, if ever approved, must remove reason rows and the header explicitly within one audited procedure.

#### Index candidates

Likely access paths include:

- all rejected records by `import_run_id`;
- filtering by `source_entity_type`;
- filtering by `source_system`;
- filtering by `summary_reason_code`;
- lookup by source record reference;
- history of rejection for one source entity ID;
- summary reconciliation.

Potential supporting indexes include:

```text
(import_run_id, source_entity_type)
```

```text
(import_run_id, summary_reason_code)
```

```text
(source_system, source_entity_id, rejected_at)
```

Final indexes must be selected during migration and reporting-query design.

#### Validation requirements

The first schema validation must confirm:

- every rejected record references an existing import run;
- raw payload is always present;
- source record reference is unique within the entity scope of one run;
- malformed rows can be preserved without a usable source entity ID;
- every rejected header has at least one reason row;
- one rejected row may have multiple reasons;
- summary reason is one of the stored structured reasons;
- staging cleanup does not delete permanent rejection evidence;
- repeated rejection in a later run creates a separate historical record;
- valid Online Code Card products are not misclassified as rejected;
- valid duplicate-like market products are not misclassified as rejected;
- valid unresolved mappings are not misclassified as rejected;
- rejected rows create no production entity or production mapping;
- successful run rejection counts reconcile with rejected-record headers;
- a merge rollback does not remove validation-stage rejection evidence;
- rejected records cannot be modified after the run reaches a terminal state.

#### Deferred fields

The following fields are not included in the first version:

- direct staging-row foreign key;
- source artifact checksum duplicated from `import_runs`;
- importer stack trace;
- exception class;
- parser module name;
- severity;
- retry status;
- resolution status;
- resolved-by user;
- resolution notes;
- accepted-later run ID;
- correction reference;
- source line number as a dedicated integer;
- source column number;
- raw payload compression metadata.

These fields may be added only when operational support or correction workflows establish a clear responsibility.

#### Open questions

- Which rejection stages should be controlled in the first implementation?
- Should unresolved required dependencies always create rejected rows, or sometimes only fail run-level validation?
- Should `normalized_payload` be mandatory for `record_validation` failures?
- Should the primary summary reason follow a global precedence rule or entity-specific precedence?
- Should the table record the importer version directly, or rely exclusively on `import_runs`?
- How long must raw rejected payloads be retained?
- Should accepted-later resolution be represented through a dedicated relationship to a later import run?
- Should source record references follow one standardized format across all staging tables?

### `rejected_source_record_reasons`

#### Purpose

Store one structured rejection reason attached to one permanent rejected source record.

A rejected source record may fail multiple independent validation rules.

This table preserves every accepted rejection reason without duplicating the rejected source-record header.

Examples include:

- missing source identifier;
- blank required name;
- invalid timestamp;
- invalid decimal;
- unsupported currency;
- unresolved required dependency;
- conflicting duplicate source identity.

A rejection reason is not:

- a rejected source-record header;
- a staging validation status;
- a production merge outcome;
- a mapping classification;
- an application exception log.

#### Ownership

- Data owner: import validation process.
- User editing: not allowed.
- Normal import update: not allowed after insertion.
- Normal import deletion: not allowed.
- Long-term retention: required with the parent rejected record.
- Correction: requires an explicit administrative process that preserves the original reason.

#### Columns

| Column                             | PostgreSQL type                | Nullable | Default                    | Ownership                     | Description                                                                           |
| ---------------------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------- | ------------------------------------------------------------------------------------- |
| `rejected_source_record_reason_id` | `bigint` generated as identity |       No | Generated                  | Database                      | Internal surrogate primary key for the structured rejection reason.                   |
| `rejected_source_record_id`        | `bigint`                       |       No | None                       | Import-control relationship   | References the permanent rejected source-record header.                               |
| `reason_code`                      | `text`                         |       No | None                       | Import-control classification | Controlled technical identifier for the failed validation rule.                       |
| `reason_detail`                    | `text`                         |      Yes | `null`                     | Import-control evidence       | Human-readable explanation specific to this rejected record.                          |
| `field_name`                       | `text`                         |      Yes | `null`                     | Import-control evidence       | Normalized source or staging field associated with the failure when applicable.       |
| `source_value`                     | `text`                         |      Yes | `null`                     | Import-control evidence       | Safe textual representation of the rejected source value when useful and appropriate. |
| `rule_reference`                   | `text`                         |       No | None                       | Import-control evidence       | Durable identifier of the validation or normalization rule that produced the reason.  |
| `reason_order`                     | `integer`                      |       No | None                       | Import-control presentation   | Deterministic order of reasons within the rejected record.                            |
| `created_at`                       | `timestamp with time zone`     |       No | Current database timestamp | Database                      | Timestamp when the rejection reason was permanently recorded.                         |

#### Primary key

```text
rejected_source_record_reason_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- parent rejected-record ID;
- rule reference;
- reason order;
- source field name.

#### Foreign key

```text
rejected_source_record_id
→ rejected_source_records.rejected_source_record_id
```

Required behavior:

- the parent rejected record must already exist;
- deleting a rejected record with reasons must be restricted during normal operation;
- staging cleanup must not affect rejection reasons;
- deleting an import run indirectly referenced by rejected records must remain restricted.

#### Required constraints

##### Non-empty reason code

Conceptual rule:

```text
trim(reason_code) <> ''
```

##### Non-empty rule reference

Conceptual rule:

```text
trim(rule_reference) <> ''
```

##### Positive reason order

```text
reason_order >= 1
```

##### Unique order within one rejected record

```text
UNIQUE (
    rejected_source_record_id,
    reason_order
)
```

Each reason occupies one deterministic position within the parent record.

##### Duplicate reason prevention

The same validation rule should not create the same reason twice for one rejected record.

Proposed uniqueness:

```text
UNIQUE (
    rejected_source_record_id,
    reason_code,
    rule_reference
)
```

This assumes one rule produces at most one effective reason for one source record.

If the same rule can fail independently for several fields, the physical uniqueness may need to include `field_name`.

Alternative:

```text
UNIQUE (
    rejected_source_record_id,
    reason_code,
    rule_reference,
    field_name
)
```

with null-safe PostgreSQL handling.

The final constraint must follow the validation-rule design.

##### Optional text consistency

When present, the following values must contain non-whitespace text:

- `reason_detail`;
- `field_name`;
- `source_value`.

Empty strings should normally be normalized to null.

#### Reason codes

`reason_code` is a controlled technical identifier describing the validation failure category.

Initial candidate values include:

##### Identity failures

- `missing_required_source_id`;
- `blank_source_id`;
- `invalid_source_id`;
- `duplicate_source_identity`;
- `conflicting_source_identity`.

##### Required-field failures

- `missing_required_name`;
- `blank_required_name`;
- `missing_required_expansion`;
- `missing_required_collector_number`;
- `missing_required_timestamp`;
- `missing_required_currency`;
- `missing_required_evidence`.

##### Parsing and normalization failures

- `invalid_timestamp`;
- `invalid_decimal`;
- `invalid_integer`;
- `unsupported_decimal_format`;
- `numeric_precision_exceeded`;
- `invalid_url`;
- `unsupported_source_value`.

##### Market-price failures

- `negative_price`;
- `all_price_metrics_null`;
- `unsupported_currency`;
- `conflicting_duplicate_price`;
- `unresolved_market_product`.

##### Mapping failures

- `unsupported_mapping_status`;
- `invalid_confirmation_scope`;
- `missing_card_target`;
- `missing_edition_target`;
- `missing_variant_language`;
- `missing_variant_finish`;
- `invalid_finish_detail`;
- `unresolved_catalogue_card`;
- `incompatible_target_hierarchy`;
- `conflicting_mapping_observation`.

##### Dependency failures

- `unresolved_required_expansion`;
- `unresolved_required_dependency`;
- `production_identity_conflict`;
- `active_mapping_conflict`.

The exact controlled list must be aligned with implemented validation rules.

#### Rule reference

`rule_reference` identifies the exact rule that produced the rejection reason.

Recommended formats include:

```text
cards.required.source_card_id
```

```text
market_prices.avg30.non_negative
```

```text
market_mappings.confirmed.variant.requires_language
```

```text
run.cards.unique_source_identity
```

A rule reference must be:

- stable across repeated runs;
- specific enough to locate importer logic or documentation;
- independent from the human-readable reason text;
- free from secrets;
- suitable for grouping rejection statistics.

The rule reference should remain stable even when `reason_detail` wording improves.

#### Reason detail

`reason_detail` provides a concise human-readable explanation.

Example:

```text
The source card identifier is required but was missing.
```

Another example:

```text
The value "-1.25" is invalid because market prices must be non-negative.
```

The detail must:

- explain the failure clearly;
- avoid stack traces;
- avoid credentials and secrets;
- avoid relying on undocumented abbreviations;
- not replace the controlled reason code or rule reference.

The same reason code may use different details when record-specific context is useful.

#### Field name

`field_name` identifies the source or normalized field associated with the failure.

Examples:

- `source_card_id`;
- `raw_name`;
- `source_snapshot_at`;
- `avg30`;
- `currency_code`;
- `confirmation_scope`;
- `language_code`.

Use the normalized import-contract field name rather than an arbitrary display label.

`field_name` may be null when:

- the reason applies to the complete row;
- several fields participate in the conflict;
- the failure is run-level;
- no single field is responsible.

Examples of row-level reasons:

- duplicate source identity;
- incompatible target hierarchy;
- conflicting duplicate observation.

#### Source value

`source_value` may preserve a safe textual representation of the rejected value.

Examples:

```text
-1.25
```

```text
not-a-date
```

```text
variant
```

It may be null when:

- the value is absent;
- the value is already fully preserved in raw payload;
- the value is too large;
- the value contains sensitive information;
- several values caused the failure.

The importer must not store secrets or complete large payloads in `source_value`.

Complex evidence belongs in the parent raw or normalized payload.

#### Reason ordering

`reason_order` provides deterministic display and reporting order.

The order should follow documented validation precedence.

Recommended ordering approach:

1. source identity failures;
2. required-field failures;
3. normalization and parsing failures;
4. dependency-resolution failures;
5. cross-field consistency failures;
6. run-level conflicts.

Example:

| `reason_order` | `reason_code`                |
| -------------: | ---------------------------- |
|            `1` | `missing_required_source_id` |
|            `2` | `missing_required_name`      |
|            `3` | `invalid_timestamp`          |

The order must not depend on:

- database execution plan;
- unordered JSON iteration;
- incidental validator registration order;
- source-file row order.

#### Relationship to summary reason

Every rejected source record has:

```text
rejected_source_records.summary_reason_code
```

The summary reason must correspond to one of its child reason rows.

Conceptual validation:

```text
rejected_source_records.summary_reason_code
=
one rejected_source_record_reasons.reason_code
for the same rejected_source_record_id
```

Recommended rule:

```text
summary_reason_code
=
reason_code of reason_order = 1
```

This creates a deterministic primary reason.

If a different precedence rule is chosen, it must remain documented and reproducible.

The database may not be able to enforce this rule through a simple `CHECK` constraint. It may require:

- importer validation;
- a deferred constraint trigger;
- or terminal run reconciliation.

#### Insert behavior

Rejection reasons should be inserted with the rejected-record header in one transaction.

Required sequence:

1. determine all accepted validation failures;
2. order them deterministically;
3. select the primary summary reason;
4. insert `rejected_source_records`;
5. insert all corresponding reason rows;
6. verify that the primary summary reason is present;
7. commit.

A rejected-record header must not remain without at least one reason row.

#### Multiple reasons

A source record may contain several independent failures.

Example rejected card:

```text
source_card_id is missing
collector_number is blank
name is blank
```

Expected child rows:

| `reason_order` | `reason_code`                       | `field_name`       |
| -------------: | ----------------------------------- | ------------------ |
|            `1` | `missing_required_source_id`        | `source_card_id`   |
|            `2` | `missing_required_collector_number` | `collector_number` |
|            `3` | `missing_required_name`             | `name`             |

The importer must not stop after the first failure when additional safe deterministic validation can be completed.

However, dependent checks should not produce misleading cascade errors.

Example:

- when `source_snapshot_at` cannot be parsed, do not also report timestamp-range rules that require a valid timestamp.

#### Cascade-error prevention

Validation should distinguish primary failures from consequences.

For example, when `source_product_id` is missing:

- report `missing_required_source_id`;
- do not also report `unresolved_market_product`, because resolution could not be attempted meaningfully.

When `confirmation_scope` is unsupported:

- report `invalid_confirmation_scope`;
- avoid producing multiple target-consistency reasons that depend on a valid scope.

The reason set should be complete but not noisy or misleading.

#### Record-level and run-level reasons

Most reasons are record-level.

A reason may also originate from run-level validation when one row participates in a conflict.

Examples:

- duplicate source identity;
- conflicting price values for the same product and snapshot;
- incompatible mapping observations.

For a conflict involving several source rows:

- each affected rejected record may receive a structured reason;
- the shared conflict identity should be preserved in `reason_detail`, `source_value`, normalized payload, or another durable evidence field;
- no one row should be selected arbitrarily as valid.

#### Append-only behavior

Once inserted, a rejection reason is immutable.

The normal importer must not:

- change its reason code;
- change its field name;
- replace its source value;
- reorder it;
- delete it after staging cleanup.

When a validation rule changes in a later importer version:

- historical reasons remain unchanged;
- the later run uses the new rule result;
- importer version is resolved through the parent import run.

#### Correction behavior

If a rejection reason was created incorrectly:

- preserve the original reason;
- record an explicit administrative correction;
- do not silently rewrite history.

A dedicated correction structure is deferred.

Until such a structure exists, corrections should be documented outside ordinary import execution and treated as exceptional administrative work.

#### Repeated import behavior

The same source record rejected in a later import run receives a new parent rejected record and new reason rows.

This allows comparison of:

- importer versions;
- validation rules;
- source changes;
- repeated failures;
- later successful acceptance.

Reason rows are unique only within their parent rejected record, not globally.

#### Primal Clash examples

##### Invalid price

Parent rejected record:

```text
source_entity_type = market_price
source_entity_id = 273532
summary_reason_code = negative_price
```

Reason row:

| Column           | Example value                      |
| ---------------- | ---------------------------------- |
| `reason_code`    | `negative_price`                   |
| `field_name`     | `avg30`                            |
| `source_value`   | `-1.25`                            |
| `rule_reference` | `market_prices.avg30.non_negative` |
| `reason_order`   | `1`                                |

##### Invalid confirmed variant mapping

Possible reason rows:

| `reason_order` | `reason_code`              | `field_name`    | `rule_reference`                                      |
| -------------: | -------------------------- | --------------- | ----------------------------------------------------- |
|            `1` | `missing_variant_language` | `language_code` | `market_mappings.confirmed.variant.requires_language` |
|            `2` | `missing_variant_finish`   | `finish_code`   | `market_mappings.confirmed.variant.requires_finish`   |

##### Duplicate card identity

Possible reason row:

| Column           | Example value                       |
| ---------------- | ----------------------------------- |
| `reason_code`    | `duplicate_source_identity`         |
| `field_name`     | `source_card_id`                    |
| `source_value`   | `xy5-20`                            |
| `rule_reference` | `run.cards.unique_source_identity`  |
| `reason_order`   | Determined by validation precedence |

#### Relationships

```text
rejected_source_records
    1 → many rejected_source_record_reasons
```

Every rejected source record must have at least one reason.

A reason belongs to exactly one rejected source record.

#### Expected foreign-key behavior

Recommended normal-operation behavior:

```text
ON DELETE RESTRICT
```

for:

```text
rejected_source_record_reasons.rejected_source_record_id
→ rejected_source_records.rejected_source_record_id
```

Staging cleanup has no effect on reason rows.

Administrative deletion, if ever approved, must remove the parent and child evidence through one explicit audited procedure.

#### Index candidates

Likely access paths include:

- all reasons for one rejected record ordered by `reason_order`;
- filtering by `reason_code`;
- filtering by `rule_reference`;
- filtering by `field_name`;
- rejection statistics by import run through the parent relationship;
- finding all failures produced by one validation rule.

Potential supporting indexes include:

```text
(rejected_source_record_id, reason_order)
```

```text
(reason_code, created_at)
```

```text
(rule_reference, created_at)
```

```text
(field_name, reason_code)
```

Final indexes must be selected during migration and reporting-query design.

#### Validation requirements

The first schema validation must confirm:

- every reason references an existing rejected source record;
- every rejected source record has at least one reason;
- reason codes are non-empty and controlled;
- rule references are non-empty;
- reason order begins at `1`;
- reason order is unique within one rejected record;
- duplicate effective reasons are rejected;
- optional empty text values are normalized to null;
- the parent summary reason is present among the child reasons;
- the primary reason is selected deterministically;
- one rejected row may contain several independent reasons;
- dependent cascade errors are not produced unnecessarily;
- repeated rejection in another import run creates separate reason rows;
- staging cleanup does not delete permanent reason evidence;
- reason rows cannot be changed after the parent run reaches a terminal state.

#### Deferred fields

The following fields are not included in the first version:

- validation severity;
- warning or error classification;
- validation-rule version;
- validator component name;
- exception class;
- stack trace;
- source JSON path;
- source line and column numbers;
- suggested correction;
- resolution status;
- resolved-by identifier;
- correction reference;
- accepted-later run ID;
- machine-localized message key;
- user-facing translated message.

These fields may be added only when importer support or review workflows establish a clear responsibility.

#### Open questions

- Should reason codes use one global controlled list or entity-specific namespaces?
- Should `summary_reason_code` always equal the reason at `reason_order = 1`?
- Can one validation rule legitimately produce several reasons for different fields of the same record?
- Should uniqueness include `field_name` using null-safe PostgreSQL semantics?
- Should `source_value` be omitted entirely because raw and normalized payloads already preserve it?
- Should rule references include an explicit version?
- Which validation failures should be suppressed as consequences of earlier primary failures?
- Should administrative correction history use a dedicated table?

### `card_market_mapping_cases`

#### Purpose

Store one persistent mapping-review case for one marketplace product.

A mapping case is the durable container for the complete mapping lifecycle of a market product.

It connects:

- the market product;
- mapping observations from multiple import runs;
- candidate catalogue targets;
- accepted status transitions;
- confirmed production mappings;
- review history.

One market product has one persistent mapping case.

A mapping case is not:

- one import-run observation;
- one candidate target;
- a confirmed production mapping;
- a market product;
- a price snapshot;
- a rejected source record.

#### Ownership

- Data owner: mapping and review process.
- User editing through wishlist workflow: not allowed.
- Automated updates: restricted to accepted status transitions and case metadata.
- Manual review: allowed only through an explicit reviewed workflow.
- Normal import deletion: not allowed.
- Physical deletion: not allowed while observations, candidates, history, or production mappings reference the case.
- Long-term retention: required.

#### Columns

| Column                         | PostgreSQL type                | Nullable | Default                    | Ownership                           | Description                                                                       |
| ------------------------------ | ------------------------------ | -------: | -------------------------- | ----------------------------------- | --------------------------------------------------------------------------------- |
| `mapping_case_id`              | `bigint` generated as identity |       No | Generated                  | Database                            | Internal surrogate primary key for the persistent mapping case.                   |
| `market_product_id`            | `bigint`                       |       No | None                       | Mapping-owned identity              | References the marketplace product reviewed by this case.                         |
| `current_status`               | `text`                         |       No | `unmatched`                | Mapping-owned state                 | Current accepted mapping classification for the market product.                   |
| `current_confirmation_scope`   | `text`                         |      Yes | `null`                     | Mapping-owned state                 | Most specific accepted confirmation scope when `current_status = confirmed`.      |
| `current_card_id`              | `bigint`                       |      Yes | `null`                     | Mapping-owned accepted target       | Current accepted canonical-card target when confirmed.                            |
| `current_card_edition_id`      | `bigint`                       |      Yes | `null`                     | Mapping-owned accepted target       | Current accepted edition target for edition- or variant-level confirmation.       |
| `current_card_variant_id`      | `bigint`                       |      Yes | `null`                     | Mapping-owned accepted target       | Current accepted variant target for variant-level confirmation.                   |
| `status_source_observation_id` | `bigint`                       |      Yes | `null`                     | Mapping-owned evidence relationship | Observation that supports the current accepted case state.                        |
| `first_observed_at`            | `timestamp with time zone`     |       No | Current database timestamp | Mapping-owned audit                 | Timestamp when the market product first entered the mapping workflow.             |
| `last_observed_at`             | `timestamp with time zone`     |       No | Current database timestamp | Mapping-owned audit                 | Timestamp of the latest accepted observation processed for the case.              |
| `resolved_at`                  | `timestamp with time zone`     |      Yes | `null`                     | Mapping-owned audit                 | Timestamp when the case most recently entered a resolved terminal classification. |
| `created_at`                   | `timestamp with time zone`     |       No | Current database timestamp | Database                            | Timestamp when the mapping-case row was created.                                  |
| `updated_at`                   | `timestamp with time zone`     |       No | Current database timestamp | Database                            | Timestamp of the latest actual accepted case-state change.                        |

#### Primary key

```text
mapping_case_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- market-product ID;
- source product ID;
- mapping observation ID;
- confirmed production mapping ID.

#### Market-product foreign key

```text
market_product_id
→ market_products.market_product_id
```

Required behavior:

- the referenced market product must already exist;
- deleting a market product with a mapping case must be restricted;
- retiring the market product must preserve the mapping case;
- price imports must not modify the case.

#### One case per market product

Required uniqueness:

```text
UNIQUE (market_product_id)
```

A market product must not have several independent active review cases.

All later observations and status changes belong to the same persistent case.

This guarantees:

```text
market_products
    1 → exactly one card_market_mapping_cases
```

after mapping-case initialization.

A market product may temporarily have no case immediately after product insertion if case creation is performed in a later controlled step, but the accepted import workflow should normally create or resolve the case deterministically.

#### Current accepted statuses

Initial controlled values:

- `confirmed`;
- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`.

These values describe the current accepted case state.

They are not generic import outcomes.

#### Status semantics

##### `confirmed`

The market product has one accepted catalogue relationship supported by sufficient evidence.

The relationship may be confirmed at:

- card level;
- edition level;
- variant level.

A confirmed case requires:

- current canonical card;
- confirmation scope;
- compatible target hierarchy;
- active production mapping.

##### `candidate`

One or more plausible catalogue targets exist, but the evidence is insufficient for confirmation.

A candidate case:

- may have persistent candidate rows;
- has no production mapping;
- does not contribute to canonical-card pricing;
- is not automatically promoted because only one candidate exists.

##### `unmatched`

No accepted target and no sufficiently supported candidate currently exists.

An unmatched case:

- has no accepted target;
- has no production mapping;
- may receive new observations later.

##### `ambiguous`

Several incompatible plausible targets remain and the available evidence cannot select one safely.

An ambiguous case:

- may have multiple candidate rows;
- has no active production mapping;
- requires stronger evidence or review.

##### `excluded`

The product is valid market data but intentionally outside the supported catalogue-mapping scope.

For the Primal Clash MVP, Online Code Card products are examples.

An excluded case:

- preserves the market product;
- preserves price observations;
- has no production card mapping;
- contributes no canonical-card price.

##### `unmatched_duplicate_candidate`

The product is preserved as a valid source product and classified as duplicate-like under the accepted evidence rule, but remains intentionally unmapped.

It:

- has no accepted target;
- has no production mapping;
- contributes no canonical-card price;
- remains reviewable.

#### Current-target columns

The case stores the current accepted target for convenient review and consistency checks.

These columns mirror the active confirmed relationship:

- `current_card_id`;
- `current_card_edition_id`;
- `current_card_variant_id`;
- `current_confirmation_scope`.

The authoritative historical production relationship remains in:

```text
card_market_product_mappings
```

The case columns are current-state projections and must remain synchronized with the active production mapping.

They must not replace production mapping history.

#### Foreign keys for accepted targets

##### Canonical card

```text
current_card_id
→ cards.card_id
```

##### Card edition

```text
current_card_edition_id
→ card_editions.card_edition_id
```

##### Card variant

```text
current_card_variant_id
→ card_variants.card_variant_id
```

Required behavior:

- target columns are nullable for non-confirmed statuses;
- deletion of referenced catalogue targets must be restricted;
- edition and variant compatibility must be validated;
- confirmed targets must match the active production mapping.

#### Observation foreign key

```text
status_source_observation_id
→ mapping_case_observations.mapping_case_observation_id
```

The field identifies the observation currently supporting the accepted case state.

It may be null:

- immediately after case initialization;
- for an explicitly created administrative case before its first observation;
- during a controlled transitional operation inside one transaction.

For a terminal accepted state after processing, a supporting observation is expected.

The referenced observation must belong to the same mapping case.

#### Required constraints

##### Controlled current status

`current_status` must be one of the approved mapping statuses.

##### Confirmation-state consistency

When:

```text
current_status = confirmed
```

then:

```text
current_confirmation_scope is not null
current_card_id is not null
resolved_at is not null
```

When:

```text
current_status <> confirmed
```

then:

```text
current_confirmation_scope is null
current_card_id is null
current_card_edition_id is null
current_card_variant_id is null
```

A non-confirmed case must not retain an accepted production target.

##### Card-level target consistency

When:

```text
current_confirmation_scope = card
```

then:

```text
current_card_id is not null
current_card_edition_id is null
current_card_variant_id is null
```

##### Edition-level target consistency

When:

```text
current_confirmation_scope = edition
```

then:

```text
current_card_id is not null
current_card_edition_id is not null
current_card_variant_id is null
```

##### Variant-level target consistency

When:

```text
current_confirmation_scope = variant
```

then:

```text
current_card_id is not null
current_card_edition_id is not null
current_card_variant_id is not null
```

##### Target hierarchy consistency

When an edition is present:

- it must belong to `current_card_id`.

When a variant is present:

- it must belong to `current_card_edition_id`;
- that edition must belong to `current_card_id`.

This requires validated merge logic, composite constraints, or both.

##### Timestamp order

Conceptual rule:

```text
first_observed_at <= last_observed_at
```

When `resolved_at` is present:

```text
first_observed_at <= resolved_at
```

##### Resolved-state consistency

The initial recommended resolved statuses are:

- `confirmed`;
- `excluded`;
- `unmatched_duplicate_candidate`.

For these statuses:

```text
resolved_at is not null
```

The following normally remain unresolved:

- `candidate`;
- `unmatched`;
- `ambiguous`.

For these statuses:

```text
resolved_at is null
```

Whether `unmatched` should count as operationally resolved remains an open decision.

#### Case initialization

Create a mapping case when a valid production market product first enters the mapping workflow.

Recommended initial state:

```text
current_status = unmatched
current_confirmation_scope = null
current_card_id = null
current_card_edition_id = null
current_card_variant_id = null
resolved_at = null
```

The same transaction should create the first mapping observation where possible.

Repeated imports must resolve the existing case through:

```text
market_product_id
```

and must not create a duplicate case.

#### Observation processing

Every valid mapping observation belongs to one persistent case.

Processing an observation involves:

1. resolve `market_product_id`;
2. resolve or create the mapping case;
3. insert `mapping_case_observations`;
4. validate whether the observation changes accepted state;
5. insert `mapping_status_history` when a transition occurs;
6. update the mapping case current-state projection;
7. create, preserve, or supersede a production mapping when applicable.

An observation does not automatically change the case.

Weaker or equivalent evidence may be preserved without changing the current state.

#### State transition principles

##### Equivalent repeated observation

When a later observation supports the same accepted status and target:

- preserve the new observation;
- update `last_observed_at`;
- do not create duplicate production mapping;
- do not rewrite `resolved_at`;
- do not create a false status transition;
- update `updated_at` only if accepted case metadata actually changes.

Whether updating `last_observed_at` counts as a meaningful `updated_at` change should be decided consistently.

##### Stronger compatible evidence

A stronger compatible observation may transition:

```text
unmatched → candidate
candidate → confirmed
ambiguous → confirmed
card-level confirmed → edition-level confirmed
edition-level confirmed → variant-level confirmed
```

The transition must:

- preserve previous observations;
- create a status-history row;
- supersede an older less-specific production mapping where required;
- update the current target projection atomically.

##### Weaker later evidence

Weaker evidence must not automatically:

- demote `confirmed`;
- remove an accepted target;
- lower confirmation scope;
- replace direct evidence;
- reactivate unresolved review.

The weaker observation is stored without changing accepted state unless an explicit reviewed correction is approved.

##### Conflicting evidence

Conflicting evidence must:

- preserve the current accepted state;
- create an observation;
- create candidate or review evidence where appropriate;
- prevent automatic target reassignment;
- not create a second active production mapping.

A conflict may cause the import run to fail depending on the declared run policy.

##### Administrative correction

An accepted confirmed target may be corrected only through:

- stronger direct evidence;
- explicit reviewed decision;
- auditable status transition;
- production mapping supersession.

The existing case remains the same because the market product identity remains the same.

#### Allowed transition direction

Initial candidate transitions include:

```text
unmatched → candidate
unmatched → ambiguous
unmatched → confirmed
unmatched → excluded
unmatched → unmatched_duplicate_candidate
```

```text
candidate → ambiguous
candidate → confirmed
candidate → unmatched
candidate → excluded
candidate → unmatched_duplicate_candidate
```

```text
ambiguous → candidate
ambiguous → confirmed
ambiguous → unmatched
ambiguous → excluded
ambiguous → unmatched_duplicate_candidate
```

```text
confirmed → confirmed
```

where the target becomes more specific or is corrected through accepted evidence.

Transitions away from `confirmed` must require explicit reviewed correction.

Transitions away from `excluded` or `unmatched_duplicate_candidate` must require stronger evidence or review because these are accepted resolved classifications.

The final transition matrix belongs in `mapping_status_history` design and importer validation.

#### Synchronization with production mappings

When the case is confirmed:

- exactly one active `card_market_product_mappings` row must exist for the market product;
- its `mapping_case_id` must equal this case;
- its scope and targets must equal the case current-state columns.

When the case is not confirmed:

- no active production mapping may exist for the market product.

Conceptual invariant:

```text
current_status = confirmed
↔ exactly one active production mapping exists
```

This invariant likely requires transaction-level validation rather than one simple database constraint.

#### Candidate boundary

Candidate targets do not belong in the current target columns.

They belong to:

```text
mapping_candidates
```

A case may have:

- zero candidates;
- one candidate;
- multiple candidates;
- historical inactive candidates.

Only an accepted confirmed target is projected into the current target columns.

#### Mapping-case observation boundary

Detailed source evidence does not belong directly in this table.

The case does not store:

- raw mapping payload;
- candidate score;
- source product name;
- metaproduct comparison;
- direct-ID evidence details;
- exclusion evidence payload.

Those belong to:

```text
mapping_case_observations
```

The case stores only the accepted current state and lifecycle metadata.

#### Price eligibility boundary

The mapping case does not directly store price eligibility.

A confirmed case is required for mapped pricing, but eligibility still depends on:

- active production mapping;
- confirmation scope;
- language rules;
- finish and metric semantics;
- selected market-price snapshot;
- exclusion rules.

Non-confirmed cases contribute no canonical-card price.

#### Primal Clash expectations

The accepted Primal Clash mapping fixture should result in persistent cases for all valid Cardmarket products in scope.

Expected classifications include:

- confirmed cases covering `167` mapped Cardmarket listing variants;
- `6` cases classified as `unmatched_duplicate_candidate`;
- `4` cases classified as `excluded`;
- no remaining ordinary unmatched cases;
- no ambiguous cases;
- no conflicting confirmed cases.

The exact number of mapping cases must equal the number of valid market products that entered the mapping workflow.

Confirmed coverage of `164` canonical cards does not mean there are only `164` cases, because several market products may map to the same canonical card.

#### Primal Clash examples

##### Confirmed card-level case

| Column                         | Example value                  |
| ------------------------------ | ------------------------------ |
| `market_product_id`            | Internal Cardmarket product ID |
| `current_status`               | `confirmed`                    |
| `current_confirmation_scope`   | `card`                         |
| `current_card_id`              | Internal `xy5-20` card ID      |
| `current_card_edition_id`      | `null`                         |
| `current_card_variant_id`      | `null`                         |
| `status_source_observation_id` | Supporting observation ID      |
| `resolved_at`                  | Confirmation timestamp         |

##### Excluded case

| Column                         | Example value                        |
| ------------------------------ | ------------------------------------ |
| `market_product_id`            | Internal Online Code Card product ID |
| `current_status`               | `excluded`                           |
| `current_confirmation_scope`   | `null`                               |
| `current_card_id`              | `null`                               |
| `current_card_edition_id`      | `null`                               |
| `current_card_variant_id`      | `null`                               |
| `status_source_observation_id` | Exclusion observation ID             |
| `resolved_at`                  | Exclusion acceptance timestamp       |

##### Duplicate-like case

| Column                         | Example value                      |
| ------------------------------ | ---------------------------------- |
| `market_product_id`            | Internal duplicate-like product ID |
| `current_status`               | `unmatched_duplicate_candidate`    |
| `current_confirmation_scope`   | `null`                             |
| `current_card_id`              | `null`                             |
| `current_card_edition_id`      | `null`                             |
| `current_card_variant_id`      | `null`                             |
| `status_source_observation_id` | Supporting observation ID          |
| `resolved_at`                  | Classification timestamp           |

#### Relationships

```text
market_products
    1 → 1 card_market_mapping_cases
```

```text
card_market_mapping_cases
    1 → many mapping_case_observations
```

```text
card_market_mapping_cases
    1 → many mapping_candidates
```

```text
card_market_mapping_cases
    1 → many mapping_status_history
```

```text
card_market_mapping_cases
    1 → zero or many card_market_product_mappings over lifecycle
```

Only one production mapping may be active at a time.

#### Expected foreign-key behavior

Recommended behavior for all referenced production entities:

```text
ON DELETE RESTRICT
```

This includes:

- market product;
- current card;
- current edition;
- current variant;
- supporting observation.

Historical cleanup must use explicit reviewed procedures rather than cascade deletion.

#### Index candidates

Likely access paths include:

- lookup by `market_product_id`;
- filtering by `current_status`;
- filtering confirmed cases by `current_card_id`;
- filtering by confirmation scope;
- finding unresolved cases;
- finding cases not observed recently;
- reconciliation with active production mappings.

Potential supporting indexes include:

```text
(current_status, last_observed_at)
```

```text
(current_card_id)
WHERE current_status = 'confirmed'
```

```text
(current_confirmation_scope)
WHERE current_status = 'confirmed'
```

The uniqueness constraint on `market_product_id` provides the primary case lookup.

Final indexes must be selected during migration and review-query design.

#### Validation requirements

The first schema validation must confirm:

- one market product can have at most one mapping case;
- repeated imports resolve the existing case;
- all accepted Primal Clash market products receive persistent cases;
- confirmed cases require a canonical-card target;
- card-level confirmation contains no edition or variant target;
- edition-level confirmation requires a compatible edition;
- variant-level confirmation requires a compatible edition and variant;
- non-confirmed cases contain no accepted target columns;
- confirmed cases have exactly one matching active production mapping;
- non-confirmed cases have no active production mapping;
- the supporting observation belongs to the same case;
- candidate targets remain in `mapping_candidates`, not current target columns;
- weaker repeated evidence does not demote a confirmed case;
- compatible stronger evidence may increase confirmation scope;
- conflicting evidence does not replace the accepted target automatically;
- six Primal Clash cases remain `unmatched_duplicate_candidate`;
- four Primal Clash cases remain `excluded`;
- no unresolved case contributes to canonical-card pricing;
- case history remains after staging cleanup;
- deleting referenced products or accepted targets is restricted.

#### Deferred fields

The following fields are not included in the first version:

- separate review-state column;
- assigned reviewer;
- review priority;
- due date;
- review notes;
- case title;
- current candidate count;
- confidence score;
- source product URL;
- exclusion reason code;
- duplicate-candidate reason code;
- latest import run ID;
- latest status-history ID;
- active production mapping ID;
- lock version;
- manual-review flag;
- archived state.

These fields may be added only when the review workflow establishes a clear responsibility.

#### Open questions

- Should `unmatched` be considered unresolved or a resolved negative result?
- Should `resolved_at` remain populated when a resolved case later returns to review?
- Should `last_observed_at` update for every equivalent observation?
- Should the mapping case store current target columns, or derive them only from the active production mapping?
- Should `status_source_observation_id` be required for every accepted state?
- Should a production mapping be created in the same transaction as the confirmed case transition?
- Should excluded and duplicate-candidate reasons be projected into dedicated case columns?
- What exact transition matrix should be allowed between mapping statuses?
- Should case-state synchronization with active production mappings be enforced through deferred database triggers or importer reconciliation?

### `mapping_case_observations`

#### Purpose

Store one permanent mapping observation for one persistent mapping case.

An observation records what one import run, source artifact, validation rule, or reviewed decision concluded about a market product at a specific point in time.

It may describe:

- a confirmed relationship;
- a candidate relationship;
- an unmatched result;
- an ambiguous result;
- an exclusion;
- an unmatched duplicate candidate;
- weaker evidence that does not change the accepted case state;
- conflicting evidence requiring review.

An observation is not:

- the current accepted mapping-case state;
- a production confirmed mapping;
- one candidate target;
- a mapping status transition;
- a staging row;
- a rejected source record.

#### Ownership

- Data owner: mapping import, validation, and review process.
- User editing through wishlist workflow: not allowed.
- Manual-review creation: allowed only through an explicit reviewed workflow.
- Normal import update: not allowed after insertion.
- Normal import deletion: not allowed.
- Long-term retention: required as permanent mapping evidence.
- Correction: requires a new observation or explicit administrative correction rather than rewriting the original row.

#### Columns

| Column                        | PostgreSQL type                | Nullable | Default                    | Ownership                     | Description                                                                                                                             |
| ----------------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `mapping_case_observation_id` | `bigint` generated as identity |       No | Generated                  | Database                      | Internal surrogate primary key for the observation.                                                                                     |
| `mapping_case_id`             | `bigint`                       |       No | None                       | Mapping-owned relationship    | References the persistent mapping case receiving the observation.                                                                       |
| `import_run_id`               | `bigint`                       |      Yes | `null`                     | Mapping-owned audit           | Import run that produced the observation when import-derived. Null for an explicitly reviewed manual observation outside an import run. |
| `source_record_reference`     | `text`                         |       No | None                       | Mapping-owned evidence        | Durable reference to the source record, fixture row, page, review decision, or evidence artifact.                                       |
| `observation_status`          | `text`                         |       No | None                       | Mapping-owned classification  | Status proposed or observed by this evidence event.                                                                                     |
| `proposed_confirmation_scope` | `text`                         |      Yes | `null`                     | Mapping-owned classification  | Proposed confirmation scope when the observation status is `confirmed`.                                                                 |
| `proposed_card_id`            | `bigint`                       |      Yes | `null`                     | Mapping-owned target evidence | Proposed canonical-card target when one is supported by the observation.                                                                |
| `proposed_card_edition_id`    | `bigint`                       |      Yes | `null`                     | Mapping-owned target evidence | Proposed edition target when supported.                                                                                                 |
| `proposed_card_variant_id`    | `bigint`                       |      Yes | `null`                     | Mapping-owned target evidence | Proposed variant target when supported.                                                                                                 |
| `confirmation_method`         | `text`                         |      Yes | `null`                     | Mapping-owned evidence        | Method used to support a confirmed observation.                                                                                         |
| `evidence_level`              | `text`                         |       No | None                       | Mapping-owned evidence        | Controlled evidence strength for the observation.                                                                                       |
| `evidence_reference`          | `text`                         |       No | None                       | Mapping-owned evidence        | Durable reference to the underlying source or reviewed evidence.                                                                        |
| `evidence_payload`            | `jsonb`                        |       No | None                       | Mapping-owned evidence        | Structured observation evidence used for validation and review.                                                                         |
| `observation_result`          | `text`                         |       No | None                       | Mapping-owned processing      | Indicates whether the observation changed, supported, conflicted with, or was ignored by the accepted case state.                       |
| `result_reason_code`          | `text`                         |      Yes | `null`                     | Mapping-owned processing      | Controlled reason explaining the observation result when required.                                                                      |
| `result_reason_detail`        | `text`                         |      Yes | `null`                     | Mapping-owned processing      | Human-readable explanation without secrets.                                                                                             |
| `observed_at`                 | `timestamp with time zone`     |       No | Current database timestamp | Mapping-owned audit           | Timestamp of the source evidence event or reviewed observation.                                                                         |
| `created_at`                  | `timestamp with time zone`     |       No | Current database timestamp | Database                      | Timestamp when the observation row was stored.                                                                                          |

#### Primary key

```text
mapping_case_observation_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- mapping case ID;
- import-run ID;
- source product ID;
- production mapping ID;
- candidate ID.

#### Mapping-case foreign key

```text
mapping_case_id
→ card_market_mapping_cases.mapping_case_id
```

Required behavior:

- the mapping case must already exist;
- deleting a case with observations must be restricted;
- observations must remain preserved after staging cleanup;
- one observation belongs to exactly one mapping case.

#### Import-run foreign key

```text
import_run_id
→ import_runs.import_run_id
```

The relationship is nullable.

It is required when the observation is produced by:

- staging mapping import;
- automated mapping validation;
- import-run reconciliation;
- source-derived mapping evidence.

It may be null when the observation is produced by:

- explicit manual review;
- administrative correction;
- evidence imported through a future review workflow that is not represented as an import run.

Deleting a referenced import run must be restricted.

#### Target foreign keys

##### Canonical card

```text
proposed_card_id
→ cards.card_id
```

##### Card edition

```text
proposed_card_edition_id
→ card_editions.card_edition_id
```

##### Card variant

```text
proposed_card_variant_id
→ card_variants.card_variant_id
```

Required behavior:

- target fields are nullable;
- deleting a referenced target must be restricted;
- edition and variant compatibility must be validated;
- proposed targets do not become accepted solely because foreign keys resolve.

#### Required constraints

##### Non-empty source-record reference

```text
trim(source_record_reference) <> ''
```

##### Non-empty observation status

```text
trim(observation_status) <> ''
```

##### Non-empty evidence level

```text
trim(evidence_level) <> ''
```

##### Non-empty evidence reference

```text
trim(evidence_reference) <> ''
```

##### Evidence payload required

`evidence_payload` must always be present.

It may be an empty JSON object only when the evidence reference itself is sufficient under an explicitly approved rule.

The preferred state is a structured payload containing all validation-relevant evidence.

##### Non-empty observation result

```text
trim(observation_result) <> ''
```

##### Optional text consistency

When present, the following fields must contain non-whitespace text:

- `confirmation_method`;
- `result_reason_code`;
- `result_reason_detail`.

#### Observation statuses

Initial controlled values:

- `confirmed`;
- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`.

These values describe the observation itself.

They do not automatically replace:

```text
card_market_mapping_cases.current_status
```

#### Observation results

Initial controlled values:

- `accepted_transition`;
- `accepted_support`;
- `accepted_more_specific`;
- `recorded_weaker`;
- `recorded_conflict`;
- `recorded_no_change`;
- `rejected_transition`.

##### `accepted_transition`

The observation caused the mapping case to move to another accepted status.

Example:

```text
unmatched → candidate
```

##### `accepted_support`

The observation supports the existing accepted status and target without changing them.

Example:

```text
confirmed card-level observation
supports existing confirmed card-level case
```

##### `accepted_more_specific`

The observation increases confirmation specificity while remaining target-compatible.

Examples:

```text
card → edition
```

```text
edition → variant
```

##### `recorded_weaker`

The observation contains weaker evidence than the accepted case state.

It is preserved but does not change the current state.

##### `recorded_conflict`

The observation conflicts with the accepted target or classification.

It is preserved for review and does not replace the current state automatically.

##### `recorded_no_change`

The observation is valid but produces no accepted transition.

This may apply to repeated unresolved or excluded evidence.

##### `rejected_transition`

The observation is valid as evidence, but its proposed state change is not allowed by the transition rules.

This differs from a structurally rejected staging record.

#### Confirmed observation consistency

When:

```text
observation_status = confirmed
```

then:

- `proposed_confirmation_scope` is required;
- `proposed_card_id` is required;
- `confirmation_method` is required;
- `evidence_level` must not be `insufficient`.

##### Card-level confirmation

When:

```text
proposed_confirmation_scope = card
```

then:

```text
proposed_card_id is not null
proposed_card_edition_id is null
proposed_card_variant_id is null
```

##### Edition-level confirmation

When:

```text
proposed_confirmation_scope = edition
```

then:

```text
proposed_card_id is not null
proposed_card_edition_id is not null
proposed_card_variant_id is null
```

##### Variant-level confirmation

When:

```text
proposed_confirmation_scope = variant
```

then:

```text
proposed_card_id is not null
proposed_card_edition_id is not null
proposed_card_variant_id is not null
```

#### Non-confirmed observation consistency

When `observation_status` is one of:

- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`;

then:

```text
proposed_confirmation_scope is null
confirmation_method is null
```

A non-confirmed observation may still reference:

- one proposed card;
- one proposed edition;
- one proposed variant;

when the row represents one specific candidate or ambiguous target.

However, the preferred design is:

- observation row stores the overall observed state;
- `mapping_candidates` stores individual candidate targets.

For `unmatched`, `excluded`, and `unmatched_duplicate_candidate`, proposed target columns should normally be null.

#### Candidate observation

A candidate observation means at least one plausible target exists but confirmation threshold is not met.

The observation should preserve:

- evidence level;
- evidence reference;
- structured evidence;
- candidate-generation method where relevant.

Individual targets belong in `mapping_candidates`.

A case with one candidate must not automatically become confirmed.

#### Ambiguous observation

An ambiguous observation indicates multiple incompatible plausible targets.

The observation should preserve:

- ambiguity reason;
- evidence supporting each plausible path;
- candidate generation context.

Individual targets belong in `mapping_candidates`.

#### Excluded observation

An excluded observation must preserve a structured exclusion reason.

For the Primal Clash MVP, Online Code Card evidence may include:

- source category;
- source product name;
- source expansion;
- explicit exclusion rule.

The observation:

- may transition the case to `excluded`;
- creates no production mapping;
- creates no edition or variant;
- contributes no canonical-card price.

#### `unmatched_duplicate_candidate` observation

The evidence payload must preserve the accepted duplicate-like comparison.

Expected evidence may include:

- source metaproduct ID;
- normalized product name;
- source expansion;
- source category ID;
- source category name;
- compared market product IDs;
- source creation timestamps;
- inspected differing fields.

The observation:

- may transition the case to `unmatched_duplicate_candidate`;
- creates no production mapping;
- contributes no canonical-card price.

#### Confirmation method

Initial controlled values:

- `direct_source_identifier`;
- `explicit_source_relationship`;
- `validated_derived_rule`;
- `manual_review`.

The exact list should match:

- `staging_market_mappings`;
- `card_market_product_mappings`;
- `mapping_status_history`.

A confirmed direct Cardmarket product-to-card relationship should normally use:

```text
direct_source_identifier
```

The method does not determine confirmation scope by itself.

#### Evidence level

Initial controlled values:

- `direct`;
- `derived`;
- `manual`;
- `insufficient`.

Rules:

- confirmed observations must not use `insufficient`;
- candidates and ambiguous observations may use `insufficient`;
- excluded observations may use direct or derived evidence;
- duplicate-candidate observations normally use derived evidence unless explicitly reviewed;
- manual evidence must correspond to a reviewed action.

#### Evidence reference

`evidence_reference` locates the durable evidence source.

Examples:

```text
fixture:primal-clash/mappings#product-273532
```

```text
cardmarket-product-page:<source-product-id>
```

```text
review:case-42#decision-2026-07-28
```

It must:

- remain stable after staging cleanup;
- contain no secrets;
- identify evidence more precisely than a generic statement such as `manual check`;
- support later review.

#### Evidence payload

The payload stores structured evidence relevant to the observation.

Example direct mapping evidence:

```json
{
  "market_source_system": "cardmarket",
  "source_product_id": "273532",
  "catalogue_source_system": "pokemon_tcg_data",
  "source_card_id": "xy5-20",
  "direct_id_match": true
}
```

Example exclusion evidence:

```json
{
  "source_category_name": "Online Code Cards",
  "exclusion_rule": "mvp.exclude_online_code_cards"
}
```

Example duplicate-candidate evidence:

```json
{
  "matched_source_metaproduct_id": true,
  "matched_normalized_name": true,
  "matched_source_expansion_id": true,
  "matched_source_category_id": true,
  "matched_source_category_name": true,
  "differing_fields": [
    "source_product_id",
    "source_created_at"
  ]
}
```

The exact JSON schema must be documented per observation method or rule.

#### Target hierarchy consistency

When `proposed_card_edition_id` is present:

- the edition must belong to `proposed_card_id`.

When `proposed_card_variant_id` is present:

- the variant must belong to `proposed_card_edition_id`;
- the edition must belong to `proposed_card_id`.

These rules require:

- validated merge logic;
- composite constraints;
- or both.

#### Observation result consistency

##### Accepted transition

For:

```text
observation_result = accepted_transition
```

the observation must correspond to a `mapping_status_history` row that changes accepted case state.

##### Accepted more specific

For:

```text
observation_result = accepted_more_specific
```

the case remains confirmed, but its scope or target specificity increases.

A corresponding status-history or target-transition record is required.

##### Accepted support

For:

```text
observation_result = accepted_support
```

the observation status and target must be compatible with the current accepted case state.

##### Recorded weaker

For:

```text
observation_result = recorded_weaker
```

a reason code is required.

Suggested code:

```text
weaker_than_accepted_evidence
```

##### Recorded conflict

For:

```text
observation_result = recorded_conflict
```

a reason code is required.

Suggested codes include:

- `conflicting_confirmed_target`;
- `conflicting_confirmation_scope`;
- `conflicting_mapping_status`;
- `incompatible_target_hierarchy`.

##### Rejected transition

For:

```text
observation_result = rejected_transition
```

a reason code is required.

The observation remains valid evidence even though its proposed transition is not accepted.

#### Result reason codes

Initial candidate values include:

- `equivalent_observation`;
- `same_status_new_evidence`;
- `more_specific_compatible_target`;
- `weaker_than_accepted_evidence`;
- `conflicting_confirmed_target`;
- `conflicting_confirmation_scope`;
- `conflicting_mapping_status`;
- `incompatible_target_hierarchy`;
- `transition_requires_manual_review`;
- `resolved_status_protected`;
- `insufficient_confirmation_evidence`;
- `candidate_not_unique_enough`;
- `no_supported_target`;
- `accepted_exclusion_rule`;
- `accepted_duplicate_candidate_rule`.

The exact controlled list must align with the transition matrix.

#### Observation uniqueness

The same exact evidence event must not be inserted more than once for one case.

Recommended conceptual uniqueness:

```text
mapping_case_id
import_run_id
source_record_reference
```

Because `import_run_id` may be null, the final PostgreSQL implementation requires null-safe handling.

Possible rules:

```text
UNIQUE (
    mapping_case_id,
    import_run_id,
    source_record_reference
)
NULLS NOT DISTINCT
```

where supported and appropriate.

An observation from another import run may use the same source record reference and still create a new historical row.

#### Observation timestamp

`observed_at` represents the evidence event time.

Preferred source order:

1. explicit reviewed decision timestamp;
2. source artifact observation timestamp;
3. import-run observation timestamp;
4. database insertion timestamp as fallback only when the evidence contract defines no earlier timestamp.

`created_at` always represents storage time.

The two values may differ.

#### Insert behavior

Create an observation when:

- the mapping case exists;
- the evidence event is structurally valid;
- source reference and evidence are preserved;
- proposed status is controlled;
- target hierarchy is valid where present;
- observation result has been determined.

The observation should normally be inserted before or together with:

- candidate rows;
- status-history transition;
- current case-state update;
- production mapping creation or supersession.

All accepted state changes must occur atomically.

#### Append-only behavior

Observations are immutable after insertion.

The normal process must not:

- change observed status;
- change target;
- replace evidence;
- rewrite result classification;
- delete old weaker or conflicting evidence.

A later correction creates a new observation.

#### Relationship to case state

The observation table contains evidence history.

The case table contains the current accepted projection.

Several observations may exist without changing current state.

Example:

```text
confirmed case
+ equivalent repeated direct observation
+ weaker name-based candidate observation
+ conflicting manual proposal
```

All three later observations remain preserved, but only explicitly accepted evidence changes the current case state.

#### Relationship to status history

`mapping_status_history` stores accepted transitions.

An observation should create a status-history row only when:

- the accepted status changes;
- confirmation scope changes;
- accepted target changes;
- a confirmed mapping is corrected or made more specific;
- a resolved classification is explicitly reopened.

Equivalent or weaker observations create no status transition.

#### Relationship to candidates

One observation may generate zero, one, or many `mapping_candidates`.

Candidate rows should reference the observation that produced them.

The observation stores the overall classification and evidence context.

The candidate rows store each proposed target separately.

#### Relationship to production mapping

A confirmed observation may create or supersede a production mapping only after:

- transition validation;
- target resolution;
- case-state acceptance;
- conflict checks;
- run-level validation.

The observation itself is not the production relationship.

#### Primal Clash expectations

For the accepted Primal Clash mapping fixture:

- each valid market product receives at least one mapping observation;
- direct mapped products receive confirmed observations;
- six duplicate-like products receive `unmatched_duplicate_candidate` observations;
- four Online Code Card products receive `excluded` observations;
- no accepted observation remains ordinary `unmatched`;
- no accepted observation remains `ambiguous`;
- weaker or repeated observations do not create duplicate production mappings.

#### Primal Clash examples

##### Confirmed observation

| Column                        | Example value                               |
| ----------------------------- | ------------------------------------------- |
| `mapping_case_id`             | Persistent case for Cardmarket product      |
| `import_run_id`               | Mapping import run ID                       |
| `source_record_reference`     | Fixture mapping record                      |
| `observation_status`          | `confirmed`                                 |
| `proposed_confirmation_scope` | `card`                                      |
| `proposed_card_id`            | Internal `xy5-20` card ID                   |
| `confirmation_method`         | `direct_source_identifier`                  |
| `evidence_level`              | `direct`                                    |
| `observation_result`          | `accepted_transition` or `accepted_support` |

##### Excluded observation

| Column                        | Example value             |
| ----------------------------- | ------------------------- |
| `observation_status`          | `excluded`                |
| `proposed_confirmation_scope` | `null`                    |
| `proposed_card_id`            | `null`                    |
| `evidence_level`              | `direct` or `derived`     |
| `observation_result`          | `accepted_transition`     |
| `result_reason_code`          | `accepted_exclusion_rule` |

##### Weaker observation after confirmation

| Column               | Example value                   |
| -------------------- | ------------------------------- |
| `observation_status` | `candidate`                     |
| `evidence_level`     | `insufficient`                  |
| `observation_result` | `recorded_weaker`               |
| `result_reason_code` | `weaker_than_accepted_evidence` |

The existing confirmed case and production mapping remain unchanged.

#### Relationships

```text
card_market_mapping_cases
    1 → many mapping_case_observations
```

```text
import_runs
    1 → many mapping_case_observations
```

The import-run relationship is optional.

```text
mapping_case_observations
    1 → many mapping_candidates
```

```text
mapping_case_observations
    1 → zero or one accepted mapping_status_history transition
```

One observation may also support the current mapping-case state through:

```text
card_market_mapping_cases.status_source_observation_id
```

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

- mapping case;
- import run;
- proposed card;
- proposed edition;
- proposed variant.

Observations must survive staging cleanup and ordinary lifecycle changes.

#### Index candidates

Likely access paths include:

- all observations by `mapping_case_id`;
- observations by `import_run_id`;
- latest observations by case;
- filtering by observation status;
- filtering by observation result;
- filtering by evidence level;
- finding conflicts and weaker evidence;
- lookup by source record reference;
- reconciliation with current case state.

Potential supporting indexes include:

```text
(mapping_case_id, observed_at desc)
```

```text
(import_run_id, observation_status)
```

```text
(observation_result, observed_at)
```

```text
(mapping_case_id, evidence_level, observed_at desc)
```

Final indexes must be selected during migration and review-query design.

#### Validation requirements

The first schema validation must confirm:

- every observation references an existing mapping case;
- import-derived observations reference an existing import run;
- manual observations may have null import-run ID;
- source and evidence references are non-empty;
- evidence payload is preserved;
- observation statuses are controlled;
- confirmed observations require scope, card target, method, and sufficient evidence;
- card-level confirmation has no edition or variant target;
- edition-level confirmation has a compatible edition;
- variant-level confirmation has a compatible edition and variant;
- non-confirmed observations have no confirmation scope;
- target hierarchy remains compatible;
- duplicate evidence events in one run are rejected;
- equivalent repeated observations remain preserved without false transitions;
- weaker evidence does not alter confirmed case state;
- conflicts remain preserved without automatic reassignment;
- accepted transitions have corresponding status-history rows;
- observations survive staging cleanup;
- historical observations cannot be modified after insertion;
- all accepted Primal Clash product classifications remain represented.

#### Deferred fields

The following fields are not included in the first version:

- reviewer identifier;
- review comment;
- candidate count;
- candidate score summary;
- source product name duplicated from evidence payload;
- source metaproduct ID as a dedicated column;
- exclusion reason as a dedicated column;
- duplicate-candidate reason as a dedicated column;
- current-case status snapshot;
- production mapping ID;
- status-history ID;
- superseded observation ID;
- correction reference;
- evidence schema version;
- confidence percentage;
- severity;
- administrative notes.

These fields may be added only when review, evidence-versioning, or operational requirements establish a clear responsibility.

#### Open questions

- Should manual review always be represented by a dedicated import run instead of allowing null `import_run_id`?
- Should one observation be allowed to reference one proposed target directly, or should all non-confirmed targets exist only in `mapping_candidates`?
- Should `observation_result` be determined before insertion or updated atomically during accepted transition processing?
- Should equivalent observations update `card_market_mapping_cases.last_observed_at`?
- Should accepted confirmation-scope changes use a dedicated target-transition type in `mapping_status_history`?
- Should evidence payloads have versioned JSON schemas?
- Should exact observation uniqueness use PostgreSQL `NULLS NOT DISTINCT`?
- Should every accepted case state require `status_source_observation_id`?

### `mapping_candidates`

#### Purpose

Store one proposed catalogue target produced by one mapping observation.

A mapping observation may generate:

- no candidates;
- one candidate;
- several candidates.

Each candidate represents one possible target hierarchy for the market product under review.

A candidate may target:

- a canonical card;
- a card edition;
- a card variant.

A candidate is not:

- the accepted mapping-case state;
- a confirmed production mapping;
- a mapping observation;
- a status transition;
- a market product;
- a manually approved relationship by itself.

#### Ownership

- Data owner: mapping analysis and review process.
- User editing through wishlist workflow: not allowed.
- Automated creation: allowed from deterministic candidate-generation logic.
- Manual creation: allowed only through an explicit reviewed workflow.
- Normal import update: not allowed after insertion.
- Normal import deletion: not allowed.
- Candidate lifecycle changes: represented through active-state fields or later observations rather than rewriting identity.
- Long-term retention: required as review evidence.

#### Columns

| Column                        | PostgreSQL type                | Nullable | Default                    | Ownership                           | Description                                                                                    |
| ----------------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| `mapping_candidate_id`        | `bigint` generated as identity |       No | Generated                  | Database                            | Internal surrogate primary key for the candidate.                                              |
| `mapping_case_id`             | `bigint`                       |       No | None                       | Mapping-owned relationship          | References the persistent mapping case for the market product.                                 |
| `mapping_case_observation_id` | `bigint`                       |       No | None                       | Mapping-owned evidence relationship | References the observation that produced or introduced the candidate.                          |
| `candidate_scope`             | `text`                         |       No | None                       | Mapping-owned classification        | Most specific proposed target level: `card`, `edition`, or `variant`.                          |
| `candidate_card_id`           | `bigint`                       |       No | None                       | Mapping-owned target                | Proposed canonical-card target. Required for every candidate.                                  |
| `candidate_card_edition_id`   | `bigint`                       |      Yes | `null`                     | Mapping-owned target                | Proposed edition target for edition- or variant-level candidates.                              |
| `candidate_card_variant_id`   | `bigint`                       |      Yes | `null`                     | Mapping-owned target                | Proposed variant target for variant-level candidates.                                          |
| `candidate_rank`              | `integer`                      |      Yes | `null`                     | Mapping-owned comparison            | Optional deterministic rank within the producing observation.                                  |
| `candidate_score`             | `numeric(8, 6)`                |      Yes | `null`                     | Mapping-owned comparison            | Optional normalized score produced by a documented candidate-generation method.                |
| `generation_method`           | `text`                         |       No | None                       | Mapping-owned evidence              | Controlled method that generated the candidate.                                                |
| `evidence_level`              | `text`                         |       No | None                       | Mapping-owned evidence              | Controlled strength of evidence supporting this candidate.                                     |
| `evidence_reference`          | `text`                         |       No | None                       | Mapping-owned evidence              | Durable reference to the source, fixture, rule, or reviewed evidence supporting the candidate. |
| `evidence_payload`            | `jsonb`                        |       No | None                       | Mapping-owned evidence              | Structured candidate-specific evidence.                                                        |
| `candidate_state`             | `text`                         |       No | `active`                   | Mapping-owned lifecycle             | Current review lifecycle of this candidate.                                                    |
| `state_reason_code`           | `text`                         |      Yes | `null`                     | Mapping-owned lifecycle             | Controlled reason explaining why the candidate became inactive, rejected, or selected.         |
| `created_at`                  | `timestamp with time zone`     |       No | Current database timestamp | Database                            | Timestamp when the candidate was stored.                                                       |
| `state_changed_at`            | `timestamp with time zone`     |      Yes | `null`                     | Mapping-owned lifecycle             | Timestamp when `candidate_state` last changed from its initial active state.                   |

#### Primary key

```text
mapping_candidate_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- mapping case ID;
- mapping observation ID;
- card ID;
- candidate rank;
- production mapping ID.

#### Mapping-case foreign key

```text
mapping_case_id
→ card_market_mapping_cases.mapping_case_id
```

Required behavior:

- the referenced mapping case must already exist;
- deleting a case with candidates must be restricted;
- the candidate must belong to the same case as its source observation;
- staging cleanup must not affect persistent candidates.

#### Observation foreign key

```text
mapping_case_observation_id
→ mapping_case_observations.mapping_case_observation_id
```

Required behavior:

- the producing observation must already exist;
- the observation must belong to the same `mapping_case_id`;
- deleting an observation with candidates must be restricted;
- one candidate belongs to exactly one producing observation.

#### Target foreign keys

##### Canonical card

```text
candidate_card_id
→ cards.card_id
```

##### Card edition

```text
candidate_card_edition_id
→ card_editions.card_edition_id
```

##### Card variant

```text
candidate_card_variant_id
→ card_variants.card_variant_id
```

Required behavior:

- the canonical-card target is required;
- edition and variant targets are nullable according to candidate scope;
- deleting referenced catalogue targets must be restricted;
- target hierarchy compatibility must be validated.

#### Required constraints

##### Controlled candidate scope

Allowed values:

- `card`;
- `edition`;
- `variant`.

##### Card-level candidate consistency

When:

```text
candidate_scope = card
```

then:

```text
candidate_card_id is not null
candidate_card_edition_id is null
candidate_card_variant_id is null
```

##### Edition-level candidate consistency

When:

```text
candidate_scope = edition
```

then:

```text
candidate_card_id is not null
candidate_card_edition_id is not null
candidate_card_variant_id is null
```

##### Variant-level candidate consistency

When:

```text
candidate_scope = variant
```

then:

```text
candidate_card_id is not null
candidate_card_edition_id is not null
candidate_card_variant_id is not null
```

##### Target hierarchy consistency

When an edition is present:

- it must belong to `candidate_card_id`.

When a variant is present:

- it must belong to `candidate_card_edition_id`;
- that edition must belong to `candidate_card_id`.

This requires validated merge logic, composite constraints, or both.

##### Positive candidate rank

When present:

```text
candidate_rank >= 1
```

##### Candidate score range

The proposed normalized range is:

```text
0 <= candidate_score
and candidate_score <= 1
```

A score is optional.

Absence of a score does not invalidate a candidate.

##### Non-empty generation method

```text
trim(generation_method) <> ''
```

##### Non-empty evidence level

```text
trim(evidence_level) <> ''
```

##### Non-empty evidence reference

```text
trim(evidence_reference) <> ''
```

##### Evidence payload required

`evidence_payload` must always be present.

It should contain candidate-specific evidence, not only a copy of the full observation payload.

##### Candidate state

Initial controlled values:

- `active`;
- `selected`;
- `rejected`;
- `superseded`;
- `withdrawn`.

##### Candidate-state timestamp consistency

When:

```text
candidate_state = active
```

then:

```text
state_changed_at is null
```

When:

```text
candidate_state <> active
```

then:

```text
state_changed_at is not null
```

##### Candidate-state reason consistency

For:

- `rejected`;
- `superseded`;
- `withdrawn`;

`state_reason_code` is required.

For:

- `active`;
- `selected`;

`state_reason_code` may be null unless a documented selection reason is required.

#### Candidate identity

The same exact proposed target should not be duplicated for one observation.

Conceptual uniqueness:

```text
mapping_case_observation_id
candidate_scope
candidate_card_id
candidate_card_edition_id
candidate_card_variant_id
```

Because edition and variant IDs are nullable, the final PostgreSQL implementation requires null-safe uniqueness.

Possible implementation:

```text
UNIQUE NULLS NOT DISTINCT (
    mapping_case_observation_id,
    candidate_scope,
    candidate_card_id,
    candidate_card_edition_id,
    candidate_card_variant_id
)
```

where supported and approved.

#### Candidate rank

`candidate_rank` represents deterministic ordering within one observation.

It may be used when the candidate-generation process produces an ordered list.

Rules:

- rank `1` means highest-ranked candidate;
- lower numeric values represent stronger ranking;
- rank must not be treated as confirmation;
- rank must not be assigned arbitrarily;
- equal rank may be allowed only if the method explicitly supports ties.

Recommended uniqueness when rank is present:

```text
UNIQUE (
    mapping_case_observation_id,
    candidate_rank
)
WHERE candidate_rank is not null
```

This rule assumes no tied ranks.

If ties are required, the uniqueness constraint must be omitted or redesigned.

#### Candidate score

`candidate_score` stores a normalized score from a documented method.

It may represent:

- name similarity;
- collector-number match score;
- combined deterministic matching score;
- reviewed confidence transformed into a controlled score.

A score must not:

- automatically confirm a target;
- replace evidence level;
- hide unsupported heuristics;
- be compared across unrelated generation methods unless explicitly calibrated.

The method and score semantics must be documented together.

#### Generation method

Initial candidate values may include:

- `direct_identifier_candidate`;
- `normalized_name_match`;
- `collector_number_match`;
- `metaproduct_grouping`;
- `validated_combined_rule`;
- `manual_review`.

A generation method describes how the candidate was proposed.

It does not imply that the candidate is confirmed.

For example:

```text
generation_method = normalized_name_match
```

may produce a candidate with insufficient evidence.

#### Evidence level

Initial controlled values:

- `direct`;
- `derived`;
- `manual`;
- `insufficient`.

Most candidate rows are expected to use:

- `derived`;
- `insufficient`;
- `manual`.

A candidate with `direct` evidence may still remain unconfirmed when:

- target hierarchy is incomplete;
- evidence conflicts with another target;
- confirmation threshold has not been formally accepted;
- only a broader or narrower target can be supported.

#### Evidence reference

`evidence_reference` locates the candidate-specific evidence.

Examples:

```text
fixture:primal-clash/mappings#product-273532:candidate-xy5-20
```

```text
rule:normalized-name-match:v1
```

```text
review:case-42#candidate-2
```

It must:

- remain durable after staging cleanup;
- contain no secrets;
- identify the evidence more precisely than a generic description;
- remain stable for later review.

#### Evidence payload

The candidate payload stores evidence specific to one proposed target.

Example:

```json
{
  "market_product_name": "Vulpix",
  "candidate_card_name": "Vulpix",
  "normalized_name_equal": true,
  "source_expansion_id": "1585",
  "candidate_expansion_id": "xy5",
  "collector_number_match": false
}
```

Another example:

```json
{
  "source_metaproduct_id": "12345",
  "candidate_source_card_id": "xy5-20",
  "generation_rule": "mapping.name_and_expansion.v1",
  "score_components": {
    "name": 1.0,
    "expansion": 1.0,
    "collector_number": 0.0
  }
}
```

The exact JSON schema should be versioned or documented per generation method.

#### Candidate states

##### `active`

The candidate remains under consideration.

An active candidate:

- is not accepted as the production mapping;
- may coexist with other active candidates;
- may be reviewed in NocoDB or another review interface.

##### `selected`

The candidate became the accepted target through a confirmed mapping transition.

Selection does not itself create the production mapping.

The selection state must correspond to:

- accepted mapping-case transition;
- status-history entry;
- active production mapping with compatible target.

At most one candidate should normally be selected for one accepted transition.

##### `rejected`

The candidate was explicitly rejected by stronger evidence or review.

The candidate remains preserved.

##### `superseded`

A later observation produced a better or more specific candidate, making this candidate no longer current.

Superseded does not necessarily mean the original candidate was structurally incorrect.

##### `withdrawn`

The candidate was withdrawn because the generation rule, source evidence, or review input was invalidated.

#### Single-candidate rule

One active candidate does not imply confirmation.

The importer must not apply:

```text
one candidate
→ confirmed
```

unless a separate approved rule establishes that the candidate evidence itself meets the confirmation threshold.

This prevents accidental confirmation from incomplete candidate generation.

#### Candidate selection

A candidate may become `selected` only when:

- the mapping case accepts `confirmed`;
- the selected target is compatible with the confirmed scope;
- sufficient evidence exists;
- the transition is represented in `mapping_status_history`;
- the corresponding production mapping is created or activated in the same transaction.

Selection should not be updated independently from the accepted case transition.

#### Observation compatibility

A candidate must belong to the same mapping case as its observation.

The observation status should normally be:

- `candidate`;
- `ambiguous`;
- or a confirmed observation preserving alternative targets for review.

For the first implementation, candidate creation from confirmed observations should be avoided unless a real requirement exists.

An observation classified as:

- `unmatched`;
- `excluded`;
- `unmatched_duplicate_candidate`;

should normally create no candidate rows.

#### Case-state boundary

Candidate rows do not populate:

- `card_market_mapping_cases.current_card_id`;
- `current_card_edition_id`;
- `current_card_variant_id`.

Only an accepted confirmed target may populate those fields.

A case may remain:

```text
current_status = candidate
```

while holding one or many active candidates.

#### Production-mapping boundary

A candidate does not create a row in:

```text
card_market_product_mappings
```

until a confirmed accepted transition occurs.

The production mapping must not be derived from candidate rank or score alone.

#### Candidate replacement

A later observation may produce a new candidate set.

Recommended behavior:

- preserve historical candidates;
- mark no-longer-current candidates as `superseded` where appropriate;
- create new candidate rows linked to the later observation;
- do not rewrite old target or evidence fields.

Candidate lifecycle transitions should be atomic with the observation processing that causes them.

#### Repeated observation behavior

When a later import produces the same candidate target with equivalent evidence:

- create a new observation;
- either create a new candidate linked to the new observation or record the candidate only through observation evidence;
- do not mutate the historical candidate's producing observation;
- avoid presenting duplicated active candidates as separate current review options.

This creates an open design choice between:

- observation-specific candidate history;
- one persistent candidate identity across observations.

The proposed first version keeps candidates observation-specific and may use case-level review queries to collapse equivalent active targets.

#### Conflict handling

A candidate conflicts with the accepted case state when:

- it points to another canonical card;
- its edition does not belong to the accepted card;
- its variant does not belong to the proposed edition;
- it proposes weaker incompatible scope;
- it contradicts stronger direct evidence.

A conflicting candidate:

- remains preserved;
- must not replace the accepted target automatically;
- may be marked `rejected` or remain active for manual review;
- should be accompanied by a conflict observation result.

#### Primal Clash expectations

The accepted Primal Clash fixture currently has:

- no remaining ordinary ambiguous rows;
- no remaining ordinary unmatched rows;
- confirmed direct mappings;
- six `unmatched_duplicate_candidate` products;
- four excluded Online Code Card products.

Therefore the validated fixture may produce few or no active candidate rows.

The table remains required for:

- future unmatched products;
- ambiguous products;
- weaker mapping evidence;
- manual review;
- future expansions.

The six duplicate-like products should not receive speculative canonical-card candidates solely because they resemble mapped products.

#### Primal Clash example

A future candidate row may contain:

| Column                        | Example value                              |
| ----------------------------- | ------------------------------------------ |
| `mapping_case_id`             | Persistent case for one Cardmarket product |
| `mapping_case_observation_id` | Candidate observation ID                   |
| `candidate_scope`             | `card`                                     |
| `candidate_card_id`           | Internal `xy5-20` card ID                  |
| `candidate_card_edition_id`   | `null`                                     |
| `candidate_card_variant_id`   | `null`                                     |
| `candidate_rank`              | `1`                                        |
| `candidate_score`             | `0.950000`                                 |
| `generation_method`           | `validated_combined_rule`                  |
| `evidence_level`              | `derived`                                  |
| `candidate_state`             | `active`                                   |

This row does not create a production mapping until a separate confirmed transition accepts it.

#### Relationships

```text
card_market_mapping_cases
    1 → many mapping_candidates
```

```text
mapping_case_observations
    1 → many mapping_candidates
```

```text
cards
    1 → many mapping_candidates
```

```text
card_editions
    1 → many edition- or variant-level mapping_candidates
```

```text
card_variants
    1 → many variant-level mapping_candidates
```

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

- mapping case;
- mapping observation;
- proposed card;
- proposed edition;
- proposed variant.

Candidates are historical review evidence and must survive staging cleanup.

#### Index candidates

Likely access paths include:

- all candidates by `mapping_case_id`;
- all candidates by `mapping_case_observation_id`;
- active candidates for one case;
- candidates ordered by rank;
- candidates by proposed card;
- candidates by state;
- selected candidates;
- candidates produced by one generation method.

Potential supporting indexes include:

```text
(mapping_case_id, candidate_state, candidate_rank)
```

```text
(mapping_case_observation_id, candidate_rank)
```

```text
(candidate_card_id, candidate_state)
```

```text
(generation_method, evidence_level)
```

Final indexes must be selected during migration and review-query design.

#### Validation requirements

The first schema validation must confirm:

- every candidate references an existing case and observation;
- the observation belongs to the same case;
- candidate scope is controlled;
- card-level candidates contain no edition or variant target;
- edition-level candidates require a compatible edition;
- variant-level candidates require a compatible edition and variant;
- target hierarchy is valid;
- candidate ranks are positive;
- candidate scores remain between `0` and `1`;
- duplicate exact targets within one observation are rejected;
- evidence reference and payload are preserved;
- one candidate does not automatically confirm a mapping;
- selected candidates correspond to accepted confirmed transitions;
- non-selected candidates create no production mapping;
- historical candidates survive later observations and staging cleanup;
- duplicate-like Primal Clash products receive no speculative candidates without supported evidence;
- candidate rows cannot be modified after their lifecycle state is finalized.

#### Deferred fields

The following fields are not included in the first version:

- persistent candidate identity across observations;
- reviewer identifier;
- review comment;
- candidate display label;
- score breakdown columns;
- score model version;
- evidence schema version;
- rejection detail;
- selected production mapping ID;
- selected status-history ID;
- parent candidate ID;
- superseding candidate ID;
- candidate group ID;
- candidate comparison batch ID;
- manual priority;
- review due date;
- administrative notes.

These fields may be added only when review and candidate-management requirements establish a clear responsibility.

#### Open questions

- Should candidates remain observation-specific, or should equivalent candidates be persistent across observations?
- Should `candidate_score` exist in the first schema before one calibrated scoring method is implemented?
- Should tied candidate ranks be allowed?
- Should a selected candidate remain `selected` after a later more-specific target supersedes it?
- Should `state_changed_at` and `candidate_state` be replaced by a dedicated candidate-state history table?
- Should confirmed observations be allowed to create alternative candidate rows?
- Should candidate evidence payloads use versioned schemas?
- Should exact target uniqueness use PostgreSQL `NULLS NOT DISTINCT`?

### `mapping_status_history`

#### Purpose

Store one accepted mapping-case state transition.

The table provides an immutable history of changes to the accepted state of a persistent mapping case.

A history row may record:

- a change from one mapping status to another;
- initial acceptance of a mapping status;
- confirmation of a canonical-card target;
- an increase in confirmation scope;
- correction of an accepted confirmed target;
- reopening of a previously resolved case;
- acceptance of an exclusion;
- acceptance of an unmatched duplicate candidate classification.

A status-history row is not:

- every mapping observation;
- a candidate target;
- the current mapping-case state;
- a production mapping;
- an import outcome;
- a free-text review log.

Only an observation or reviewed action that changes the accepted case state creates a history row.

#### Ownership

- Data owner: mapping transition and review process.
- User editing through wishlist workflow: not allowed.
- Automated insertion: allowed only for accepted deterministic transitions.
- Manual transition insertion: allowed only through an explicit reviewed workflow.
- Normal update: not allowed after insertion.
- Normal deletion: not allowed.
- Long-term retention: required.
- Correction: represented by a later transition rather than rewriting history.

#### Columns

| Column                        | PostgreSQL type                | Nullable | Default                    | Ownership                           | Description                                                                                     |
| ----------------------------- | ------------------------------ | -------: | -------------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------- |
| `mapping_status_history_id`   | `bigint` generated as identity |       No | Generated                  | Database                            | Internal surrogate primary key for the accepted transition.                                     |
| `mapping_case_id`             | `bigint`                       |       No | None                       | Mapping-owned relationship          | References the persistent mapping case whose accepted state changed.                            |
| `mapping_case_observation_id` | `bigint`                       |       No | None                       | Mapping-owned evidence relationship | Observation that caused or supported the accepted transition.                                   |
| `import_run_id`               | `bigint`                       |      Yes | `null`                     | Mapping-owned audit                 | Import run associated with the transition when import-derived.                                  |
| `previous_status`             | `text`                         |      Yes | `null`                     | Mapping-owned prior state           | Accepted mapping status before the transition. Null only for the first recorded accepted state. |
| `new_status`                  | `text`                         |       No | None                       | Mapping-owned new state             | Accepted mapping status after the transition.                                                   |
| `previous_confirmation_scope` | `text`                         |      Yes | `null`                     | Mapping-owned prior state           | Previous accepted confirmation scope when the prior status was confirmed.                       |
| `new_confirmation_scope`      | `text`                         |      Yes | `null`                     | Mapping-owned new state             | New accepted confirmation scope when the new status is confirmed.                               |
| `previous_card_id`            | `bigint`                       |      Yes | `null`                     | Mapping-owned prior target          | Previous accepted canonical-card target.                                                        |
| `new_card_id`                 | `bigint`                       |      Yes | `null`                     | Mapping-owned new target            | New accepted canonical-card target.                                                             |
| `previous_card_edition_id`    | `bigint`                       |      Yes | `null`                     | Mapping-owned prior target          | Previous accepted edition target.                                                               |
| `new_card_edition_id`         | `bigint`                       |      Yes | `null`                     | Mapping-owned new target            | New accepted edition target.                                                                    |
| `previous_card_variant_id`    | `bigint`                       |      Yes | `null`                     | Mapping-owned prior target          | Previous accepted variant target.                                                               |
| `new_card_variant_id`         | `bigint`                       |      Yes | `null`                     | Mapping-owned new target            | New accepted variant target.                                                                    |
| `transition_type`             | `text`                         |       No | None                       | Mapping-owned classification        | Controlled description of the accepted state change.                                            |
| `transition_method`           | `text`                         |       No | None                       | Mapping-owned evidence              | Controlled method by which the transition was accepted.                                         |
| `transition_reason_code`      | `text`                         |       No | None                       | Mapping-owned evidence              | Controlled reason for the accepted transition.                                                  |
| `transition_reason_detail`    | `text`                         |      Yes | `null`                     | Mapping-owned evidence              | Human-readable explanation without secrets.                                                     |
| `changed_at`                  | `timestamp with time zone`     |       No | Current database timestamp | Mapping-owned audit                 | Timestamp when the accepted case transition occurred.                                           |
| `created_at`                  | `timestamp with time zone`     |       No | Current database timestamp | Database                            | Timestamp when the history row was stored.                                                      |

#### Primary key

```text
mapping_status_history_id
```

The primary key is an internal surrogate identifier.

It must not reuse:

- mapping-case ID;
- observation ID;
- production mapping ID;
- import-run ID.

#### Mapping-case foreign key

```text
mapping_case_id
→ card_market_mapping_cases.mapping_case_id
```

Required behavior:

- the mapping case must already exist;
- deleting a case with history must be restricted;
- all history rows must remain preserved after staging cleanup;
- one transition belongs to exactly one mapping case.

#### Observation foreign key

```text
mapping_case_observation_id
→ mapping_case_observations.mapping_case_observation_id
```

Required behavior:

- the observation must already exist;
- the observation must belong to the same `mapping_case_id`;
- deleting the observation must be restricted;
- the observation result should indicate an accepted transition or accepted increase in specificity.

Expected observation results include:

- `accepted_transition`;
- `accepted_more_specific`.

An equivalent supporting observation must not create a status-history row.

#### Import-run foreign key

```text
import_run_id
→ import_runs.import_run_id
```

The field is nullable because an accepted transition may result from an explicit manual review outside an import run.

When the source observation references an import run, the history row should normally reference the same run.

Deleting a referenced import run must be restricted.

#### Target foreign keys

The table preserves both previous and new accepted targets.

Foreign keys apply to:

- `previous_card_id`;
- `new_card_id`;
- `previous_card_edition_id`;
- `new_card_edition_id`;
- `previous_card_variant_id`;
- `new_card_variant_id`.

Targets reference:

```text
cards.card_id
card_editions.card_edition_id
card_variants.card_variant_id
```

Required behavior:

- fields are nullable according to status and confirmation scope;
- deleting a historically referenced target must be restricted;
- target hierarchy compatibility must be validated;
- historical references must survive later supersession.

#### Controlled mapping statuses

Both `previous_status` and `new_status`, when present, use:

- `confirmed`;
- `candidate`;
- `unmatched`;
- `ambiguous`;
- `excluded`;
- `unmatched_duplicate_candidate`.

#### Initial transition

The first history row for a case may use:

```text
previous_status = null
```

The row records the first accepted state established by a valid observation.

Example:

```text
null → unmatched
```

or, when case initialization and direct confirmation occur atomically:

```text
null → confirmed
```

Only one history row per case may have null `previous_status`.

#### Required constraints

##### Non-empty new status

```text
trim(new_status) <> ''
```

##### Non-empty transition type

```text
trim(transition_type) <> ''
```

##### Non-empty transition method

```text
trim(transition_method) <> ''
```

##### Non-empty transition reason code

```text
trim(transition_reason_code) <> ''
```

##### Optional text consistency

When present, `transition_reason_detail` must contain non-whitespace text.

##### Actual state change required

A history row must represent a meaningful accepted change.

At least one of the following must differ:

- status;
- confirmation scope;
- canonical-card target;
- edition target;
- variant target.

Conceptual rule:

```text
previous_status is distinct from new_status
or previous_confirmation_scope is distinct from new_confirmation_scope
or previous_card_id is distinct from new_card_id
or previous_card_edition_id is distinct from new_card_edition_id
or previous_card_variant_id is distinct from new_card_variant_id
```

Equivalent repeated observations create no history row.

##### Previous confirmed-state consistency

When:

```text
previous_status = confirmed
```

then:

- `previous_confirmation_scope` is required;
- `previous_card_id` is required;
- previous target columns must match the previous scope.

When:

```text
previous_status is not null
and previous_status <> confirmed
```

then:

- `previous_confirmation_scope` is null;
- previous target columns are null.

##### New confirmed-state consistency

When:

```text
new_status = confirmed
```

then:

- `new_confirmation_scope` is required;
- `new_card_id` is required;
- new target columns must match the new scope.

When:

```text
new_status <> confirmed
```

then:

- `new_confirmation_scope` is null;
- new target columns are null.

##### Card-level scope consistency

For either previous or new state, when scope is `card`:

- card ID is required;
- edition ID is null;
- variant ID is null.

##### Edition-level scope consistency

When scope is `edition`:

- card ID is required;
- edition ID is required;
- variant ID is null.

##### Variant-level scope consistency

When scope is `variant`:

- card ID is required;
- edition ID is required;
- variant ID is required.

##### Target hierarchy consistency

For both previous and new states:

- edition must belong to card;
- variant must belong to edition;
- edition of the variant must belong to card.

These rules require validated transition logic, composite constraints, or both.

##### Observation-case consistency

The referenced observation must belong to the same mapping case.

##### Transition ordering

For each mapping case, `changed_at` must not be earlier than the prior accepted transition.

Conceptual rule:

```text
previous history.changed_at <= current changed_at
```

This requires importer validation or a database trigger because it compares separate rows.

#### Transition types

Initial controlled values:

- `initial_state`;
- `status_change`;
- `confirmation`;
- `confirmation_scope_increase`;
- `confirmed_target_correction`;
- `resolved_classification`;
- `reopened_for_review`;
- `manual_override`.

##### `initial_state`

Creates the first accepted state for the mapping case.

Expected:

```text
previous_status = null
```

##### `status_change`

Changes from one non-confirmed state to another.

Examples:

```text
unmatched → candidate
candidate → ambiguous
ambiguous → candidate
```

##### `confirmation`

Changes a non-confirmed case to `confirmed`.

Examples:

```text
candidate → confirmed
unmatched → confirmed
ambiguous → confirmed
```

##### `confirmation_scope_increase`

Keeps status `confirmed` while increasing supported specificity.

Examples:

```text
confirmed card → confirmed edition
confirmed edition → confirmed variant
```

The accepted target must remain hierarchy-compatible.

##### `confirmed_target_correction`

Keeps status `confirmed` but changes the accepted target through stronger evidence or reviewed correction.

This transition:

- must not occur through weak automated evidence;
- must supersede the active production mapping;
- must preserve the previous target;
- requires a strong reason code.

##### `resolved_classification`

Moves a case into an accepted non-confirmed resolved classification.

Examples:

```text
unmatched → excluded
candidate → unmatched_duplicate_candidate
```

##### `reopened_for_review`

Moves a resolved case back into an unresolved review state.

Examples:

```text
excluded → candidate
unmatched_duplicate_candidate → ambiguous
confirmed → candidate
```

Reopening a confirmed case must require explicit reviewed correction or stronger contradictory evidence.

##### `manual_override`

Represents an explicitly reviewed transition that does not fit an ordinary automated path.

Use must be rare and always include a durable reason and supporting observation.

#### Transition methods

Initial controlled values:

- `automated_direct_evidence`;
- `automated_validated_rule`;
- `manual_review`;
- `administrative_correction`.

##### `automated_direct_evidence`

Used when direct evidence satisfies the accepted transition rule.

##### `automated_validated_rule`

Used when a documented deterministic derived rule supports the transition.

It must not be used for ad hoc heuristic selection.

##### `manual_review`

Used when a reviewer explicitly accepts the transition.

##### `administrative_correction`

Used for exceptional correction of an accepted historical state.

#### Transition reason codes

Initial candidate values include:

- `initial_mapping_case_state`;
- `direct_identifier_confirmed`;
- `explicit_source_relationship_confirmed`;
- `candidate_evidence_accepted`;
- `ambiguity_resolved`;
- `confirmation_scope_became_more_specific`;
- `stronger_evidence_changed_target`;
- `approved_manual_target_correction`;
- `online_code_card_excluded`;
- `duplicate_candidate_rule_accepted`;
- `new_evidence_reopened_case`;
- `previous_classification_invalidated`;
- `manual_review_decision`.

The exact list must align with the transition matrix.

#### Transition matrix

The initial candidate matrix permits:

```text
null → unmatched
null → candidate
null → ambiguous
null → confirmed
null → excluded
null → unmatched_duplicate_candidate
```

```text
unmatched → candidate
unmatched → ambiguous
unmatched → confirmed
unmatched → excluded
unmatched → unmatched_duplicate_candidate
```

```text
candidate → unmatched
candidate → ambiguous
candidate → confirmed
candidate → excluded
candidate → unmatched_duplicate_candidate
```

```text
ambiguous → unmatched
ambiguous → candidate
ambiguous → confirmed
ambiguous → excluded
ambiguous → unmatched_duplicate_candidate
```

Confirmed-to-confirmed transitions may allow:

- scope increase;
- accepted target correction.

Transitions away from `confirmed` require explicit reviewed handling.

Transitions away from `excluded` or `unmatched_duplicate_candidate` require stronger evidence or review.

The final matrix must be approved before migrations and importer logic are implemented.

#### Previous-state verification

Before inserting a history row, the process must verify that the supplied previous state equals the current accepted state in:

```text
card_market_mapping_cases
```

This prevents:

- stale concurrent transitions;
- skipped history entries;
- inconsistent previous-state snapshots;
- accidental overwriting of a newer accepted state.

Recommended transaction sequence:

1. lock the mapping-case row;
2. read current accepted state;
3. compare it with proposed previous state;
4. validate the transition;
5. insert the history row;
6. update the mapping case;
7. create or supersede production mapping where required;
8. update candidate states where required;
9. commit.

#### Synchronization with mapping case

After insertion, the history row's new state must equal the mapping case current projection.

Conceptual invariant:

```text
latest mapping_status_history new state
=
card_market_mapping_cases current state
```

This includes:

- status;
- confirmation scope;
- card target;
- edition target;
- variant target.

#### Synchronization with production mapping

When `new_status = confirmed`:

- exactly one compatible active production mapping must exist after the transaction;
- its case ID must match;
- its scope and targets must equal the history row new state.

When a confirmed state becomes non-confirmed:

- the previous active production mapping must be superseded or deactivated;
- no active production mapping may remain.

When confirmation becomes more specific or corrected:

- preserve the previous production mapping;
- supersede it;
- create the replacement active mapping.

#### Synchronization with candidate state

When confirmation selects a stored candidate:

- the accepted candidate should become `selected`;
- incompatible candidates may remain active for review or become rejected according to the approved workflow;
- the candidate transition must occur in the same transaction.

A history row does not require a candidate row when direct evidence confirms a target without candidate generation.

#### Observation-result consistency

A referenced observation should have:

```text
observation_result = accepted_transition
```

for a status change, confirmation, resolved classification, or reopening.

For a confirmation-scope increase:

```text
observation_result = accepted_more_specific
```

A history row must not reference an observation recorded as:

- `accepted_support`;
- `recorded_weaker`;
- `recorded_conflict`;
- `recorded_no_change`;
- `rejected_transition`.

#### History uniqueness

One observation should create at most one accepted transition.

Recommended uniqueness:

```text
UNIQUE (mapping_case_observation_id)
```

This enforces:

```text
one observation
→ zero or one mapping_status_history row
```

A complex administrative transition requiring several state changes should use several explicit observations rather than several history rows from one observation.

#### Initial-state uniqueness

Only one row per case may have null `previous_status`.

Conceptual partial uniqueness:

```text
UNIQUE (mapping_case_id)
WHERE previous_status is null
```

#### Append-only behavior

History rows are immutable after insertion.

The normal process must not:

- change previous state;
- change new state;
- rewrite transition type;
- alter the reason;
- delete the transition.

A later correction creates another transition that preserves both states.

#### Failed transaction behavior

Status history, mapping-case update, candidate-state update, and production-mapping changes must be atomic.

If any part fails:

- no history row remains;
- the mapping-case current state remains unchanged;
- the active production mapping remains unchanged;
- candidate states remain unchanged.

This prevents history from claiming a transition that did not commit.

#### Primal Clash expectations

For the first accepted Primal Clash mapping run:

- every newly initialized case receives an initial accepted-state transition;
- confirmed products receive confirmation transitions;
- four Online Code Card cases receive accepted exclusion transitions;
- six duplicate-like cases receive accepted duplicate-candidate classification transitions;
- no ambiguous accepted state remains;
- no ordinary unmatched accepted state remains after final validated mapping;
- repeated identical mapping imports create observations but no duplicate history transitions.

The exact initial transition sequence depends on whether case creation and final classification occur in one transaction or through an initial unmatched state followed by a second transition.

The recommended approach is to avoid artificial transitions when the final accepted state is already known during case creation.

#### Primal Clash examples

##### Initial confirmed state

| Column                   | Example value                 |
| ------------------------ | ----------------------------- |
| `previous_status`        | `null`                        |
| `new_status`             | `confirmed`                   |
| `new_confirmation_scope` | `card`                        |
| `new_card_id`            | Internal `xy5-20` card ID     |
| `transition_type`        | `initial_state`               |
| `transition_method`      | `automated_direct_evidence`   |
| `transition_reason_code` | `direct_identifier_confirmed` |

##### Confirmation-scope increase

| Column                        | Example value                             |
| ----------------------------- | ----------------------------------------- |
| `previous_status`             | `confirmed`                               |
| `new_status`                  | `confirmed`                               |
| `previous_confirmation_scope` | `card`                                    |
| `new_confirmation_scope`      | `edition`                                 |
| `previous_card_id`            | Internal card ID                          |
| `new_card_id`                 | Same internal card ID                     |
| `new_card_edition_id`         | Confirmed edition ID                      |
| `transition_type`             | `confirmation_scope_increase`             |
| `transition_reason_code`      | `confirmation_scope_became_more_specific` |

##### Exclusion

| Column                   | Example value                                |
| ------------------------ | -------------------------------------------- |
| `previous_status`        | `null` or previous unresolved status         |
| `new_status`             | `excluded`                                   |
| all target columns       | `null`                                       |
| `transition_type`        | `resolved_classification` or `initial_state` |
| `transition_reason_code` | `online_code_card_excluded`                  |

#### Relationships

```text
card_market_mapping_cases
    1 → many mapping_status_history
```

```text
mapping_case_observations
    1 → zero or one mapping_status_history
```

```text
import_runs
    1 → many mapping_status_history
```

The import-run relationship is optional.

Historical target relationships point to:

- cards;
- card editions;
- card variants.

#### Expected foreign-key behavior

Recommended behavior:

```text
ON DELETE RESTRICT
```

for:

- mapping case;
- source observation;
- import run;
- previous and new catalogue targets.

History must survive:

- staging cleanup;
- production mapping supersession;
- market-product retirement;
- later case transitions.

#### Index candidates

Likely access paths include:

- complete history by `mapping_case_id`;
- latest transition by case;
- transitions by import run;
- filtering by transition type;
- filtering by new status;
- finding confirmed-target corrections;
- reconciliation with current case state.

Potential supporting indexes include:

```text
(mapping_case_id, changed_at desc)
```

```text
(import_run_id, new_status)
```

```text
(transition_type, changed_at)
```

```text
(new_card_id, changed_at)
WHERE new_status = 'confirmed'
```

The uniqueness constraint on `mapping_case_observation_id` provides observation-to-transition lookup.

Final indexes must be selected during migration and review-query design.

#### Validation requirements

The first schema validation must confirm:

- every history row references an existing case and observation;
- the observation belongs to the same case;
- one observation creates at most one accepted transition;
- one case has at most one initial transition;
- new status is controlled;
- non-confirmed states contain no accepted target;
- confirmed states require scope and compatible targets;
- previous state matches the case state before transition;
- new state matches the case state after transition;
- history rows represent an actual change;
- equivalent repeated observations create no history row;
- weaker and conflicting observations create no accepted transition;
- confirmation-scope increase preserves compatible hierarchy;
- confirmed target correction requires an approved method and reason;
- production mapping changes commit atomically with history;
- failed transactions leave no false history rows;
- repeated identical Primal Clash mapping imports do not duplicate transitions;
- historical target references remain preserved after later supersession;
- staging cleanup does not remove status history.

#### Deferred fields

The following fields are not included in the first version:

- direct reference to previous production mapping;
- direct reference to new production mapping;
- selected candidate ID;
- reviewer identifier;
- approval timestamp separate from `changed_at`;
- transition sequence number;
- optimistic lock version;
- transition payload;
- before-case JSON;
- after-case JSON;
- correction-of-history ID;
- transition severity;
- review comment;
- evidence schema version;
- rollback transition flag.

These fields may be added only when review, concurrency, or administrative-correction requirements establish a clear responsibility.

#### Open questions

- Should the first accepted state be written directly, or should every case begin as `unmatched` and transition afterward?
- Should `import_run_id` always equal the import run of the source observation?
- Should one observation ever create more than one history row?
- Should transitions away from `confirmed` be permitted in automated processing?
- Should confirmed target correction use a dedicated reviewer or approval field?
- Should `transition_type = manual_override` remain separate from `transition_method = manual_review`?
- Should a transition sequence number be stored per case to simplify ordering and concurrency checks?
- Should previous and new targets remain duplicated in history, or be represented through references to production mapping rows?
- Should synchronization with the current case and active production mapping be enforced through deferred database constraints or importer reconciliation?

## Relationship rules

### Catalogue hierarchy

```text
expansion
→ canonical card
→ edition
→ language and finish variant
```

The hierarchy defines increasingly specific catalogue targets. It does not require every confirmed market-product mapping to reach the variant level.

### Market relationship

```text
market product
→ confirmed card, edition, or variant target
→ append-only price snapshots
```

A confirmed relationship must record its confirmation scope.

### Wishlist relationship

```text
canonical card
→ zero or one wishlist item
```

The MVP wishlist does not reference edition, variant, or market product.

### Mapping-review relationship

```text
market product
→ persistent mapping case
→ per-run observations
→ zero or many candidates
→ accepted status and scope history
→ optional confirmed production mapping
```

### Import relationship

```text
import run
→ staging records
→ validation
→ production merge outcomes
→ rejected records
→ mapping observations
```

## Uniqueness summary

The proposed minimum business uniqueness rules are:

| Table | Proposed business uniqueness |
|---|---|
| `expansion_source_identifiers` | `(source_system, source_expansion_id)` |
| `cards` | `(source_system, source_card_id)` |
| `card_editions` | `(card_id, edition_key)` |
| `card_variants` | `(card_edition_id, language_code, finish_code)` |
| `market_products` | `(source_system, source_product_id)` |
| `market_price_snapshots` | `(market_product_id, source_snapshot_at)` |
| `wishlist_items` | `card_id` |
| `staging_cards` | `(import_run_id, source_record_reference)` |
| `staging_market_products` | `(import_run_id, source_record_reference)` |
| `staging_market_prices` | `(import_run_id, source_record_reference)` |
| `staging_market_mappings` | `(import_run_id, source_record_reference)` |
| `card_market_mapping_cases` | `market_product_id` |
| `mapping_case_observations` | `(mapping_case_id, import_run_id, source_record_reference)` with null-safe handling for `import_run_id` |

Additional required rule:

- one market product has at most one active confirmed production mapping.

The following uniqueness rules remain unresolved:

- universal `(expansion_id, collector_number)` uniqueness;
- physical uniqueness for scoped mappings with nullable edition and variant targets;
- edition identity when no source edition code or confirmed project edition key is available;
- candidate-target uniqueness when optional edition and variant references are null.

## Lifecycle classes

### Current-state production

- `expansions`
- `expansion_source_identifiers`
- `cards`
- `card_editions`
- `card_variants`
- `market_products`
- `card_market_product_mappings`
- `wishlist_items`
- `card_market_mapping_cases`

These records may change according to their ownership boundaries.

Normal imports must not physically delete imported catalogue or market entities.

### Active-run and terminal audit state

- `import_runs`

An import run is mutable while active and immutable after reaching a terminal state, except for a documented administrative correction.

### Append-only history and evidence

- `market_price_snapshots`
- `import_record_outcomes`
- `rejected_source_records`
- `rejected_source_record_reasons`
- `mapping_case_observations`
- `mapping_status_history`

Completed historical evidence must not be destructively rewritten.

### Temporary staging

- `staging_cards`
- `staging_market_products`
- `staging_market_prices`
- `staging_market_mappings`

Staging retention must be documented before the first operational import.

### Reviewable candidate state

- `mapping_candidates`

Candidate rows remain preserved through selection, rejection, or supersession.

## Controlled values

The physical implementation must define controlled values for at least:

- import-run lifecycle status;
- authoritative scope type;
- merge outcome;
- mapping status;
- confirmation scope;
- evidence level;
- mapping method;
- language;
- finish;
- rejection reason;
- mapping reason;
- mapping-status change source;
- production active or retired state.

A separate review-state controlled value is deferred.

Controlled values may initially use text columns with database constraints.

The final implementation choice between text constraints, PostgreSQL enums, and reference tables remains open.

## Import ownership matrix

| Table | Import-owned | Mapping-owned | User-owned | Append-only |
|---|---:|---:|---:|---:|
| `expansions` | Yes | No | No | No |
| `expansion_source_identifiers` | Yes | No | No | No |
| `cards` | Yes | No | No | No |
| `card_editions` | No | Yes | No | No |
| `card_variants` | No | Yes | No | No |
| `market_products` | Yes | No | No | No |
| `card_market_product_mappings` | No | Yes | No | History-preserving |
| `market_price_snapshots` | Yes | No | No | Yes |
| `wishlist_items` | No | No | Yes | No |
| `import_runs` | Yes | No | No | After terminal state |
| staging tables | Yes | No | No | No |
| `import_record_outcomes` | Yes | No | No | After terminal state |
| rejected-record tables | Yes | No | No | After terminal state |
| `card_market_mapping_cases` | No | Yes | No | No |
| `mapping_case_observations` | No | Yes | No | Yes |
| `mapping_candidates` | No | Yes | No | History-preserving |
| `mapping_status_history` | No | Yes | No | Yes |

## Derived values

### Canonical-card minimum `avg30`

The informational canonical-card price is not stored as an intrinsic field in `cards`.

Prices remain attached to `market_products` through `market_price_snapshots`.

The calculation must eventually:

- include only active confirmed mappings;
- respect the accepted English and German market scope;
- ignore null price values;
- exclude `candidate` mappings;
- exclude `unmatched` mappings;
- exclude `ambiguous` mappings;
- exclude `excluded` records;
- exclude `unmatched_duplicate_candidate` records;
- return no fabricated value when no eligible non-null price exists;
- preserve and display currency;
- be labelled as `From`;
- be labelled as a 30-day average.

The displayed value is informational and is not a purchase quote.

The exact join path and metric-selection rule are not yet confirmed because the current fixture does not independently establish language and finish for every mapping, and the source preserves separate `avg30` and `avg30_holo` fields.

Before the final query is defined, the project must determine:

- which confirmed mapping scopes are eligible for price contribution;
- how English and German eligibility is established;
- when `avg30` is used;
- when `avg30_holo` is used;
- whether one market product can provide prices for more than one finish interpretation;
- how unresolved finish or language affects eligibility.

### Current snapshot selection

The recommended direction is to use the latest eligible snapshot per market product from the latest successful relevant price import scope.

This rule must be confirmed before validation queries are finalized.

## Deletion and retirement rules

- Normal repeated imports must not physically delete imported expansions.
- Normal repeated imports must not physically delete cards.
- Normal repeated imports must not physically delete editions.
- Normal repeated imports must not physically delete variants.
- Normal repeated imports must not physically delete market products.
- Confirmed mappings must not be deleted solely because a later import provides weaker or missing evidence.
- Missing observations do not automatically retire an entity.
- Retirement requires an explicit source signal or a separately approved and validated rule.
- Wishlist references must survive card updates, missing observations, retirement, and failed imports.
- User deletion of a wishlist item is allowed.
- Physical deletion of a card referenced by a wishlist item must be restricted.
- Price snapshots and completed audit evidence are not deleted by normal catalogue imports.

## Staging retention

The final staging retention period remains open.

Initial policy direction:

- retain staging for failed runs until investigation is complete;
- retain successful-run staging for a limited operational period;
- retain import runs and outcomes;
- retain rejected-record evidence;
- retain mapping observations and status history;
- retain append-only price snapshots;
- retain raw source fixtures or durable raw-source references outside temporary staging.

The exact retention period must be defined before operational import cleanup is implemented.

## Primal Clash validation expectations

The physical model must support validation of the accepted Primal Clash fixture.

Expected production and review behavior:

- `164` canonical cards are stored without duplicate source-scoped identities;
- `167` directly evidenced listing relationships become confirmed at the most specific target scope actually supported by the fixture;
- card-level confirmation does not create an edition or variant;
- edition-level confirmation may create the supported edition but does not invent language or finish;
- variant-level confirmation may create the supported edition and variant;
- `4` Online Code Card products are classified as `excluded`;
- excluded products create no catalogue mapping and contribute no canonical-card price;
- `6` duplicate-like products are classified as `unmatched_duplicate_candidate`;
- those six products remain in `market_products`;
- those six products create no edition, variant, or confirmed mapping;
- those six products contribute no canonical-card price;
- no ordinary unmatched, candidate, ambiguous, or conflict rows remain in the accepted real fixture;
- synthetic rejected, unmatched, candidate, and ambiguous rows can be represented;
- repeating the identical import produces zero uncontrolled duplicates;
- repeating the identical import produces zero unnecessary production updates;
- repeating the identical price fixture produces zero duplicate snapshots;
- wishlist quantity and notes remain unchanged;
- a forced production merge failure rolls back all production changes;
- market price snapshots remain append-only;
- import counts reconcile with the declared authoritative scope.

## Deferred tables and structures

The following are deferred from the initial physical model:

- `staging_expansions`;
- generic `evidence_records`;
- `manual_reviews`;
- `card_images`;
- generic source-system registry;
- language lookup table;
- finish lookup table;
- rejection-reason lookup table;
- mapping-reason lookup table;
- import-summary table;
- validation-rule registry.

#### `staging_expansions`

The first Primal Clash implementation may use a documented and idempotent bootstrap or seed operation for the validated expansion identity.

A typed expansion staging table must be reconsidered before batch expansion imports.

### Generic evidence table

Evidence references remain in domain-specific review tables during the first implementation.

A generic evidence table should be introduced only when:

- one evidence record is reused by multiple cases;
- one candidate requires multiple evidence records;
- file attachments require independent lifecycle management;
- manual review workflow becomes more complex;
- evidence duplication becomes operationally significant.

#### `card_images`

Canonical-card image references may initially remain in `cards`.

A separate table should be considered when local image storage requires multiple files, checksums, storage status, replacement history, or multiple managed sizes.

### Review state

A separate review-state field or table is deferred until the project defines and validates a real operational review queue.

Current reviewability can be derived from mapping status and status-history evidence.

## Open questions

The following questions must be resolved before writing migrations:

- What exact normalized fields are import-owned in each production table?
- What is the final physical identity of an edition when no source edition code is available?
- Is `edition_key` always derived automatically, or can it require manual confirmation?
- Does the actual source data support a universal `(expansion_id, collector_number)` uniqueness constraint?
- What exact language and finish controlled values are required by the Primal Clash fixture?
- Which confirmed Primal Clash mappings support `card`, `edition`, or `variant` confirmation scope?
- What source evidence establishes English or German eligibility?
- What source evidence establishes finish?
- What source field determines whether `avg30` or `avg30_holo` is eligible?
- Can one market product provide eligible prices for more than one finish interpretation?
- Is `(market_product_id, source_snapshot_at)` valid for every authoritative Cardmarket price import?
- How is the latest eligible price snapshot selected?
- Are mapping candidates allowed to reference only existing production editions and variants?
- How are card-level candidates promoted when edition or finish becomes known?
- Which mapping reason codes are required?
- Which rejection reason codes are required?
- Which import-run conditions cause run-level failure rather than row-level rejection?
- How will raw rejected payloads be retained?
- How long will successful staging rows be retained?
- How will manual mapping review be performed through NocoDB or administrative SQL?
- Which timestamps are source timestamps and which are database processing timestamps?
- Which current-state tables require `is_active`, `retired_at`, or both?
- How are source records that reappear after a missing observation reported?
- How will a confirmed mapping conflict be represented without silently replacing the existing mapping?
- How will a stronger mapping observation promote confirmation scope without losing history?

## Deferred decisions

The following decisions are outside the current table-responsibility review:

- PostgreSQL column types;
- primary-key implementation;
- UUID versus integer surrogate keys;
- PostgreSQL enum versus text constraint implementation;
- exact foreign-key actions;
- index definitions;
- migration framework;
- migration numbering;
- database schemas or namespaces;
- NocoDB-specific display fields;
- automatic staging cleanup;
- physical backup implementation;
- final image-storage paths.

## Cross-table consistency review

### Catalogue hierarchy

Reviewed tables:

```text
expansions
→ expansion_source_identifiers
→ cards
→ card_editions
→ card_variants
```

### Review result

The hierarchy is conceptually consistent:

- internal expansion identity is separated from source-scoped expansion identifiers;
- canonical cards belong to one internal expansion;
- editions belong to one canonical card;
- variants belong to one edition;
- card-, edition-, and variant-level identities remain separate;
- unresolved evidence does not create editions or variants;
- normal lifecycle handling uses retirement rather than physical deletion.

The current design is suitable for migration planning after the corrections below are applied.

### Required correction 1 — Define how expansions enter production

`expansions` and `expansion_source_identifiers` are described as import-owned production data, and the `expansions` merge rules refer to a staged expansion record.

However, the 21-table model contains no:

```text
staging_expansions
```

or equivalent staging structure.

The existing staging inventory begins with:

```text
staging_cards
```

Therefore the current model does not define a physical path for importing an expansion before its cards are merged.

#### Recommended MVP decision

Do not add a twenty-second table for the first vertical slice.

For MVP:

- create `expansions` through a controlled bootstrap or seed migration;
- create accepted `expansion_source_identifiers` in the same transaction;
- treat these rows as configuration-backed production data for the first implementation;
- let `staging_cards` and `staging_market_products` resolve their source expansion IDs through the seeded identifiers.

For Primal Clash, bootstrap:

```text
expansion_key = primal_clash
```

with:

```text
pokemon_tcg_data / xy5
cardmarket / 1585
```

The `expansions` and `expansion_source_identifiers` sections should replace references to staged expansion records with references to the controlled bootstrap process.

A general expansion-import staging table may be added later when multi-expansion ingestion requires it.

### Required correction 2 — Fix ownership wording in `card_editions`

The table is owned by the confirmed mapping process, but its ownership section currently states:

```text
Display-name updates: allowed only when the value is import-owned
```

This conflicts with the column definition, which correctly labels `display_name` as mapping-owned.

Replace it with:

```text
Display-name updates: allowed only when the value is mapping-owned and supported by accepted evidence.
```

The overall ownership boundary already distinguishes import-owned catalogue entities from mapping-owned editions and variants.

### Required correction 3 — Resolve `other` finish identity

The current variant uniqueness is:

```text
UNIQUE (
    card_edition_id,
    language_code,
    finish_code
)
```

At the same time, `finish_code = other` uses `finish_detail` to distinguish a confirmed non-standard finish.

This creates a collision when one edition and language have two different non-standard finishes:

```text
en / other / cosmos_holo
en / other / cracked_ice_holo
```

Both rows would have the same unique identity.

#### Recommended MVP decision

Remove `other` from the initial allowed finish values.

Initial controlled values should be:

```text
normal
reverse_holo
holo
```

Add a new controlled finish code when the first real supported non-standard finish is discovered.

This is preferable to including free-text `finish_detail` in a business identity.

Consequences:

- remove `finish_detail` from the first migration;
- remove its consistency rules;
- retain it as a deferred field;
- reject or preserve unsupported finishes in mapping evidence until a controlled code is approved.

### Required correction 4 — Define enforceable hierarchy foreign keys

Simple foreign keys prove that a referenced row exists, but do not prove that:

```text
card_edition_id belongs to card_id
```

or that:

```text
card_variant_id belongs to card_edition_id
```

This becomes important in:

- `card_market_product_mappings`;
- mapping cases;
- mapping observations;
- mapping candidates;
- mapping status history.

The data model already recognizes that hierarchy compatibility requires composite constraints or merge validation.

#### Recommended PostgreSQL strategy

Add supporting unique constraints:

```text
UNIQUE (
    card_edition_id,
    card_id
)
```

to `card_editions`.

Add:

```text
UNIQUE (
    card_variant_id,
    card_edition_id
)
```

to `card_variants`.

Tables that store both target levels can then use composite foreign keys:

```text
(card_edition_id, card_id)
→ card_editions(card_edition_id, card_id)
```

and:

```text
(card_variant_id, card_edition_id)
→ card_variants(card_variant_id, card_edition_id)
```

This allows PostgreSQL to enforce the hierarchy instead of relying only on importer logic.

### Confirmed cross-table invariants

The following invariants are approved for migration design:

```text
expansion_source_identifiers.expansion_id
→ expansions.expansion_id
```

```text
cards.expansion_id
→ expansions.expansion_id
```

```text
card_editions.card_id
→ cards.card_id
```

```text
card_variants.card_edition_id
→ card_editions.card_edition_id
```

All use:

```text
ON DELETE RESTRICT
```

Additional invariants:

- one source-scoped expansion identifier resolves to one internal expansion;
- one source-scoped card identifier resolves to one canonical card;
- one edition key is unique within one card;
- one controlled language and finish combination is unique within one edition;
- a card-level confirmation creates no edition or variant;
- an edition-level confirmation may create an edition but no variant;
- only variant-level confirmation may create a variant;
- parent retirement does not cascade into child lifecycle updates;
- active catalogue queries must account for parent lifecycle state;
- child records remain preserved when a parent is retired;
- missing observations never cause automatic retirement.

### Parent lifecycle rule

The database may contain:

```text
expansion.is_active = false
card.is_active = true
```

or:

```text
card.is_active = false
edition.is_active = true
```

because parent retirement must not rewrite all child history.

This is acceptable.

Ordinary active catalogue queries must require every relevant ancestor to be active.

For example, an active variant view should require:

```text
expansion active
and card active
and edition active
and variant active
```

### Approved migration order for this hierarchy

```text
1. expansions
2. expansion_source_identifiers
3. cards
4. card_editions
5. card_variants
```

Supporting composite unique constraints should be created before tables that reference hierarchical target pairs.

### Review status

```text
Catalogue hierarchy review: passed with required corrections
```

The following accepted corrections are carried into migration design:

- the expansion bootstrap decision is recorded;
- `card_editions` ownership wording is corrected;
- `other` finish handling is resolved;
- composite hierarchy constraints are added to the migration plan.

### Market products, mapping cases, production mappings, and price snapshots

Reviewed tables:

```text
market_products
→ card_market_mapping_cases
→ card_market_product_mappings
→ market_price_snapshots
```

Supporting review structures considered:

```text
mapping_case_observations
mapping_status_history
mapping_candidates
import_runs
```

#### Review result

The market and mapping lifecycle is conceptually consistent:

- a market product has an independent source-scoped identity;
- price snapshots remain attached to the market product rather than the canonical card;
- one persistent mapping case stores the current accepted classification for one market product;
- observations preserve per-run evidence without automatically changing accepted state;
- status history preserves accepted transitions;
- production mappings exist only for confirmed accepted states;
- historical mappings are superseded rather than overwritten;
- unresolved, excluded, and duplicate-candidate products remain preserved without contributing to canonical-card pricing.

The model correctly separates current accepted mapping state, historical evidence, production relationships, and market-price history.

The block passes review with the required corrections and migration decisions below.

#### Required correction 1 — Correct the market-product-to-case cardinality

The current relationship is described as:

```text
market_products
    1 → 1 card_market_mapping_cases
```

However, `market_products` may be inserted before mapping processing creates or resolves its persistent mapping case.

The physical relationship from the market-product side is therefore:

```text
market_products
    1 → zero or one card_market_mapping_cases
```

The required uniqueness remains:

```text
UNIQUE (market_product_id)
```

in `card_market_mapping_cases`.

Operationally, after a complete successful mapping run for a supported product scope, every valid in-scope market product should have exactly one mapping case.

Therefore the distinction is:

```text
physical cardinality:
market product → zero or one mapping case
```

```text
post-mapping-run invariant:
every valid in-scope market product → exactly one mapping case
```

This preserves the ability to load valid market products before mapping classification without weakening the final reconciliation requirement.

#### Required correction 2 — Enforce mapping-case and market-product compatibility

`card_market_product_mappings` stores both:

```text
market_product_id
mapping_case_id
```

Simple foreign keys can prove that both rows exist, but cannot prove that the mapping case belongs to the same market product.

The document already requires this compatibility, but the physical enforcement strategy must be made explicit.

Add a supporting unique constraint to `card_market_mapping_cases`:

```text
UNIQUE (
    mapping_case_id,
    market_product_id
)
```

Then use a composite foreign key from `card_market_product_mappings`:

```text
(mapping_case_id, market_product_id)
→ card_market_mapping_cases(
    mapping_case_id,
    market_product_id
)
```

The ordinary single-column foreign key from:

```text
mapping_case_id
→ card_market_mapping_cases.mapping_case_id
```

becomes unnecessary when the composite foreign key is present.

This allows PostgreSQL to prevent a production mapping from combining:

- one market product;
- another market product's mapping case.

#### Required correction 3 — Use scope-specific active-mapping uniqueness

The model requires:

```text
one market product
→ at most one active confirmed production mapping
```

The principal required partial unique index is:

```text
UNIQUE (market_product_id)
WHERE is_active = true
```

The proposed additional partial uniqueness on:

```text
mapping_case_id
WHERE is_active = true
```

is logically redundant because:

- one mapping case belongs to one market product;
- one market product has at most one active mapping;
- every mapping uses the matching case through the composite foreign key.

The first migration should therefore require only the active `market_product_id` uniqueness unless a separate query or workflow demonstrates a need for the second partial index.

#### Required correction 4 — Define exact target uniqueness per scope

One exact confirmed relationship must not be duplicated historically.

A single nullable uniqueness definition over:

```text
market_product_id
card_id
card_edition_id
card_variant_id
```

is vulnerable to nullable-column semantics and is harder to reason about.

Use three scope-specific unique indexes.

##### Card scope

```text
UNIQUE (
    market_product_id,
    card_id
)
WHERE confirmation_scope = 'card'
```

##### Edition scope

```text
UNIQUE (
    market_product_id,
    card_id,
    card_edition_id
)
WHERE confirmation_scope = 'edition'
```

##### Variant scope

```text
UNIQUE (
    market_product_id,
    card_id,
    card_edition_id,
    card_variant_id
)
WHERE confirmation_scope = 'variant'
```

These indexes prevent duplicate historical rows for the same exact target and scope while still permitting:

```text
card
→ edition
→ variant
```

as separate lifecycle records.

The separate partial unique index on active `market_product_id` ensures that only one of these rows is active.

#### Required correction 5 — Apply composite target foreign keys

The production mapping must enforce the target hierarchy confirmed in the catalogue review.

Required supporting constraints:

```text
card_editions:
UNIQUE (card_edition_id, card_id)
```

```text
card_variants:
UNIQUE (card_variant_id, card_edition_id)
```

Required mapping foreign keys:

```text
(card_edition_id, card_id)
→ card_editions(card_edition_id, card_id)
```

```text
(card_variant_id, card_edition_id)
→ card_variants(card_variant_id, card_edition_id)
```

Together with scope consistency checks, these prevent:

- an edition from another card;
- a variant from another edition;
- a variant whose edition belongs to another card.

For card-level mappings, both composite foreign-key components containing nullable child values remain null as required by the scope rule.

#### Required correction 6 — Treat the mapping case as a projection, not independent truth

The following data is intentionally duplicated:

```text
card_market_mapping_cases.current_status
card_market_mapping_cases.current_confirmation_scope
card_market_mapping_cases.current target columns
```

and:

```text
latest mapping_status_history new state
```

and, for confirmed cases:

```text
active card_market_product_mappings scope and targets
```

This duplication is acceptable because each structure has a distinct responsibility:

- mapping case: current accepted projection;
- status history: append-only accepted transitions;
- production mapping: active and historical queryable relationships.

The document already defines the required atomic sequence:

1. lock the mapping case;
2. validate the proposed transition;
3. insert status history;
4. update the case projection;
5. create or supersede the production mapping;
6. update candidate state;
7. commit.

This sequence must be treated as one transactional invariant.

A normal application action must not update these tables independently.

#### Confirmed synchronization invariant

When:

```text
card_market_mapping_cases.current_status = 'confirmed'
```

then exactly one compatible active mapping must exist.

Its values must equal:

```text
mapping_case_id
market_product_id
confirmation_scope
card_id
card_edition_id
card_variant_id
```

from the mapping case current projection.

When:

```text
current_status <> 'confirmed'
```

no active production mapping may exist.

Conceptually:

```text
current_status = 'confirmed'
↔ exactly one compatible active production mapping exists
```

This is explicitly required by the current model.

PostgreSQL cannot enforce the complete bidirectional rule with ordinary row-level `CHECK` constraints.

The first implementation must therefore use:

- one transaction-controlled mapping service or importer path;
- row locking on the mapping case;
- database uniqueness and foreign keys for local integrity;
- a reconciliation validation query before commit or before the run becomes `succeeded`.

A deferred constraint trigger is possible but is not required for the first migration.

#### Required correction 7 — Define active product eligibility

The canonical price path currently emphasizes an active confirmed mapping.

It must also require:

```text
market_products.is_active = true
```

An inactive or retired market product must not contribute a current informational `From` price even when:

- its historical mapping remains active accidentally;
- historical price snapshots remain available;
- its mapping evidence remains confirmed.

The normal transition that retires a market product should preserve mappings and snapshots for history.

Current-price eligibility must filter the parent market-product lifecycle independently.

#### Required correction 8 — Clarify price-snapshot import-run timing

`market_price_snapshots.import_run_id` references the run that inserts or recognizes the snapshot.

During the atomic production transaction, that run cannot yet have status:

```text
succeeded
```

because the run becomes successful only after the transaction commits.

The insertion-time rule should therefore be:

```text
import run status = merge_started
```

with a compatible run kind and source scope.

After commit:

```text
import run status = succeeded
```

Only snapshots belonging to successful completed runs are eligible for ordinary current-price queries.

If the merge fails:

- snapshot inserts roll back;
- the run becomes `merge_failed`;
- no failed-run production snapshot remains.

This aligns snapshot ownership with the existing import transaction boundary.

#### Required correction 9 — Confirm the price-snapshot business identity

The proposed uniqueness is:

```text
UNIQUE (
    market_product_id,
    source_snapshot_at
)
```

This is consistent for the first Cardmarket implementation when:

- the parent market product identifies the source system;
- the source provides one observation per product and timestamp;
- the first schema supports only `EUR`.

The first migration may use this rule.

It must also enforce:

```text
currency_code = 'EUR'
```

for the MVP.

Without an MVP currency restriction, the identity would need to consider whether two currencies may legitimately exist for the same product and timestamp.

Currency conversion remains outside scope.

#### Required correction 10 — Define current snapshot selection per product

The phrase:

```text
latest successful relevant price import scope
```

is not sufficiently precise for SQL implementation.

Use this proposed selection rule:

```text
For each eligible market product,
select the row with the greatest source_snapshot_at
among snapshots belonging to succeeded compatible price runs.
```

This is a per-product rule.

It avoids incorrectly removing a product's latest available price merely because it was absent from a later run covering another scope.

When two snapshots for one product have the same timestamp, the uniqueness constraint allows only one ordinary production row.

When no eligible snapshot exists, the product contributes no value.

#### Blocking issue — `avg30` versus `avg30_holo`

The table preserves both:

```text
avg30
avg30_holo
```

but the accepted MVP price requirement is the minimum eligible non-null Cardmarket `avg30` for supported English and German mappings.

The current fixture does not independently prove language and finish for every confirmed product, and a non-null `avg30_holo` does not itself prove a holo variant. The data model also states that direct product-ID evidence must not automatically be treated as variant-level evidence.

Therefore:

- `avg30` may be stored and considered according to the approved mapping eligibility rule;
- `avg30_holo` should remain preserved as source evidence;
- `avg30_holo` must not contribute to the first canonical-card `From` price until its source semantics and finish relationship are explicitly validated;
- the presence of `avg30_holo` must not create a variant;
- the presence of `avg30_holo` must not upgrade confirmation scope.

Recommended first-MVP pricing decision:

```text
eligible metric = avg30 only
```

Keep `avg30_holo` stored but excluded from the initial derived-price query.

This matches the documented minimum non-null `avg30` requirement and avoids inventing finish identity.

#### Decision — English and German price eligibility

##### Context

The MVP supports English and German market variants, but the mapping model intentionally leaves language unresolved for less-specific confirmations:

```text
confirmation_scope = card
→ language_code is unresolved
```

```text
confirmation_scope = edition
→ language_code is unresolved
```

Only:

```text
confirmation_scope = variant
```

requires a confirmed `language_code`.

The current Primal Clash direct product-ID evidence does not by itself prove language or complete variant identity.

##### Decision

For the first MVP canonical-card price query, a market-product mapping is language-eligible only when:

```text
confirmation_scope = 'variant'
```

and the referenced active variant has:

```text
language_code IN ('en', 'de')
```

A confirmed mapping with:

```text
confirmation_scope = 'card'
```

or:

```text
confirmation_scope = 'edition'
```

is not language-eligible for the canonical-card `From` price.

Such mappings remain valid confirmed production relationships for:

- catalogue traceability;
- mapping evidence;
- edition representation;
- future language enrichment.

They do not contribute a price until language is confirmed through stronger evidence and the relationship is superseded by a compatible variant-level mapping.

##### Eligibility rule

A price value may contribute to the canonical-card `From` price only when all of the following are true:

```text
card_market_product_mappings.is_active = true
```

```text
card_market_product_mappings.confirmation_scope = 'variant'
```

```text
card_variants.is_active = true
```

```text
card_variants.language_code IN ('en', 'de')
```

```text
card_editions.is_active = true
```

```text
cards.is_active = true
```

```text
expansions.is_active = true
```

```text
market_products.is_active = true
```

```text
market_price_snapshots.avg30 IS NOT NULL
```

The selected snapshot must also belong to a successful compatible price import and satisfy the approved current-snapshot rule.

##### Initial metric

The first MVP query uses:

```text
avg30
```

only.

`avg30_holo` remains stored as source evidence but is not eligible until its exact finish semantics and relationship to Cardmarket products are validated.

##### Card- and edition-level mappings

A card- or edition-level confirmed mapping:

- remains active and valid;
- does not require an invented language;
- does not create a synthetic variant;
- does not receive a default `en` or `de`;
- does not contribute to the canonical-card price;
- may later be superseded by a variant-level mapping when language and finish evidence becomes available.

##### Unknown language

Unknown or unresolved language must not be represented as:

```text
en
```

```text
de
```

```text
other
```

```text
unknown
```

or an assumed default.

When language is unresolved:

- preserve the mapping at the supported card or edition scope;
- preserve candidate language evidence in staging or mapping observations;
- display no canonical-card `From` price from that product;
- do not create a variant.

##### Consequence for Primal Clash

The validated Primal Clash direct product mappings remain confirmed at the most specific evidence-supported scope.

If no mapping currently has confirmed variant-level English or German evidence, the canonical-card `From` price remains unavailable for those cards.

This is an accepted evidence limitation rather than a data-model failure.

The implementation must not weaken the language rule merely to increase price coverage.

##### Future extension

A card- or edition-level mapping may become price-eligible later only through one of these approved changes:

- stronger evidence allows creation of an English or German variant and a variant-level mapping;
- validated Cardmarket source semantics prove that a product-level `avg30` has a precisely defined supported-language scope;
- a separate reviewed price-eligibility model is introduced through a future ADR.

Until one of these conditions is accepted, card- and edition-level mappings remain price-ineligible.

##### Validation requirements

The first implementation must confirm:

- an active English variant-level mapping may contribute `avg30`;
- an active German variant-level mapping may contribute `avg30`;
- another language does not contribute;
- a card-level mapping does not contribute;
- an edition-level mapping does not contribute;
- a null language does not contribute;
- unresolved language creates no variant;
- no default language is assigned;
- `avg30_holo` does not contribute;
- excluded, unmatched, ambiguous, candidate, and `unmatched_duplicate_candidate` cases do not contribute;
- inactive products, cards, editions, variants, or expansions do not contribute;
- a card with no eligible mapping returns a null `From` price rather than zero;
- stronger variant-level confirmation may supersede a card- or edition-level mapping without rewriting history.

##### Review status

```text
English/German eligibility:
resolved
```

Accepted first-MVP rule:

```text
Only active variant-level mappings with confirmed language en or de
are eligible for canonical-card avg30 pricing.
```

#### Canonical-card price join path

After the above decisions, the derived query path is:

```text
cards
→ active card_market_product_mappings
→ active market_products
→ latest eligible market_price_snapshots
```

The mapping case does not need to participate in the ordinary price query when transactional synchronization is trusted.

However, a separate validation query must confirm:

```text
active production mapping
=
confirmed current mapping-case projection
```

This avoids repeating current-state classification joins in every catalogue query while still detecting drift.

#### Exclusion behavior

The following case statuses create no active production mapping:

```text
candidate
unmatched
ambiguous
excluded
unmatched_duplicate_candidate
```

Therefore they contribute no canonical-card price.

For the accepted Primal Clash fixture:

- four Online Code Card products remain valid `market_products` rows with `excluded` cases;
- six duplicate-like products remain valid `market_products` rows with `unmatched_duplicate_candidate` cases;
- neither group creates a production mapping;
- neither group contributes to the canonical-card price.

This is consistent with the accepted project boundary.

#### Confirmed cross-table invariants

The following invariants are approved for migration design:

```text
card_market_mapping_cases.market_product_id
→ market_products.market_product_id
```

with:

```text
UNIQUE (market_product_id)
ON DELETE RESTRICT
```

```text
card_market_product_mappings.market_product_id
→ market_products.market_product_id
```

```text
card_market_product_mappings(
    mapping_case_id,
    market_product_id
)
→ card_market_mapping_cases(
    mapping_case_id,
    market_product_id
)
```

```text
market_price_snapshots.market_product_id
→ market_products.market_product_id
```

```text
market_price_snapshots.import_run_id
→ import_runs.import_run_id
```

All production and historical relationships use restrictive deletion behavior.

Additional approved invariants:

- one source-scoped market product identity is unique;
- one market product has at most one persistent mapping case;
- one market product has at most one active production mapping;
- only confirmed accepted case state may have an active production mapping;
- active mapping scope and targets equal the mapping-case current projection;
- mapping target hierarchy is enforced through composite foreign keys;
- production mapping changes preserve historical rows through supersession;
- price snapshots are append-only;
- repeated identical price imports create no duplicate snapshots;
- historical snapshots remain preserved after mapping supersession or product retirement;
- unresolved and excluded classifications create no production mapping;
- an inactive market product contributes no current price;
- failed merge transactions leave cases, mappings, and snapshots unchanged.

#### Approved migration order for this block

This block depends on catalogue target tables and `import_runs`.

Recommended order:

```text
1. market_products
2. card_market_mapping_cases
3. card_market_product_mappings
4. market_price_snapshots
```

However, `card_market_mapping_cases` also references `mapping_case_observations` through:

```text
status_source_observation_id
```

while observations reference the mapping case.

This creates a migration dependency cycle.

The cycle should be handled by:

1. creating `card_market_mapping_cases` without the `status_source_observation_id` foreign key;
2. creating `mapping_case_observations`;
3. adding the case-to-observation foreign key with `ALTER TABLE`;
4. creating `mapping_status_history`;
5. creating `card_market_product_mappings`;
6. creating `market_price_snapshots`.

The final global migration order will be approved after the import and review-table block is checked.

#### Required validation queries

Before migration readiness is approved, define queries that detect:

- a market product with more than one mapping case;
- a confirmed case without exactly one active production mapping;
- a non-confirmed case with an active production mapping;
- an active mapping whose product or case does not match;
- an active mapping whose scope differs from the case;
- an active mapping whose targets differ from the case;
- an edition target belonging to another card;
- a variant target belonging to another edition;
- more than one active mapping for one market product;
- duplicate exact historical mappings at the same scope;
- duplicate price snapshots for one product and source timestamp;
- price snapshots attached to failed or incompatible import runs;
- current-price rows using inactive products;
- excluded or duplicate-candidate cases contributing to price;
- `avg30_holo` contributing despite the approved MVP exclusion;
- non-EUR snapshots entering the first MVP query.

#### Review status

```text
Market and mapping lifecycle review:
passed with required corrections; pricing eligibility resolved
```

The following accepted corrections are carried into migration design:

- market-product-to-case cardinality wording is corrected;
- composite case/product foreign-key enforcement is approved;
- scope-specific mapping uniqueness is approved;
- mapping target composite foreign keys are approved;
- inactive-product price exclusion is documented;
- price-run timing and per-product snapshot selection are documented;
- the first-MVP metric decision is reflected in the price query and validation plan;
- the resolved variant-only English/German eligibility rule is reflected in migrations and validation queries.

### Import and audit lifecycle

Reviewed tables:

```text
import_runs
→ staging_cards
→ staging_market_products
→ staging_market_prices
→ staging_market_mappings
→ import_record_outcomes
→ rejected_source_records
→ rejected_source_record_reasons
```

Supporting audit and review structures considered:

```text
mapping_case_observations
mapping_candidates
mapping_status_history
market_price_snapshots
card_market_product_mappings
```

#### Review result

The import and audit model is conceptually consistent:

- every import execution has one root `import_runs` record;
- source records enter mutable staging before production changes;
- malformed source records can be staged and investigated rather than silently discarded;
- record-level validation is separated from run-level validation;
- production changes occur only after validation succeeds;
- the production merge is transactional;
- rejected records, merge outcomes, mapping observations, mapping transitions, and price snapshots remain as permanent evidence;
- staging cleanup does not remove permanent evidence;
- repeated imports create new run and observation records without duplicating production entities;
- failed validation creates no production changes;
- failed production merge rolls back all production changes and preserves wishlist data.

The block passes review with the required decisions and corrections below.

#### Decision 1 — Use separate import runs for each MVP pipeline

The current `import_runs` model permits:

```text
run_kind = vertical_slice
source_system = combined
source_entity_type = combined
```

A combined run would have to coordinate:

- catalogue cards;
- Cardmarket products;
- mapping evidence;
- Cardmarket prices.

This makes several fields ambiguous:

- one `source_system`;
- one `source_entity_type`;
- one source artifact;
- one checksum;
- one authoritative scope;
- one set of summary counts.

It also complicates failure recovery because the source datasets have different validation and lifecycle rules.

##### Accepted MVP rule

Use separate import runs:

```text
catalogue
market_products
market_mappings
market_prices
```

Recommended Primal Clash sequence:

```text
1. bootstrap Primal Clash expansion identities
2. catalogue card run for pokemon_tcg_data / xy5
3. Cardmarket product run for cardmarket / 1585
4. mapping run for the validated Primal Clash mapping fixture
5. Cardmarket price run
```

The first schema should not use:

```text
run_kind = vertical_slice
```

or:

```text
source_system = combined
```

for production imports.

A higher-level orchestration concept may be introduced later without making one database run represent several independent source contracts.

##### Consequences

Initial controlled `run_kind` values:

```text
catalogue
market_products
market_mappings
market_prices
```

Initial controlled `source_entity_type` values:

```text
card
market_product
market_mapping
market_price
```

Initial controlled `source_system` values:

```text
pokemon_tcg_data
cardmarket
```

The bootstrap of `expansions` and `expansion_source_identifiers` remains configuration-backed for the first vertical slice and does not require a staging expansion run.

#### Decision 2 — Define the import-run transaction sequence precisely

The current model correctly separates staging work from the atomic production transaction.

The accepted run sequence is:

```text
created
→ staging_loaded
→ validated
→ merge_started
→ succeeded
```

##### Before the production transaction

The importer may:

- create the run;
- load staging rows;
- normalize staging rows;
- validate individual rows;
- create permanent rejection records and reasons;
- validate complete-run invariants;
- calculate expected merge actions.

No production catalogue, market, mapping, or price row may change before validation succeeds.

##### Inside the production transaction

The importer may:

- merge production entities;
- create or update mapping cases;
- insert mapping observations that belong to the accepted merge;
- insert accepted status transitions;
- create or supersede production mappings;
- insert market-price snapshots;
- insert `import_record_outcomes`;
- update run summary counts required for reconciliation;
- verify post-merge invariants.

The run must already have:

```text
status = merge_started
```

before production rows are inserted.

##### After commit

After the production transaction commits:

```text
status = succeeded
completed_at = completion timestamp
```

The final status update may occur immediately after commit in a separate small transaction.

Ordinary current-state queries must use evidence only from runs with:

```text
status = succeeded
```

##### Merge failure

When the production transaction fails:

- all production changes roll back;
- inserted outcomes inside the transaction roll back;
- inserted mapping history inside the transaction rolls back;
- inserted price snapshots inside the transaction roll back;
- existing production and wishlist data remain unchanged;
- the run is marked `merge_failed` after rollback;
- staging and rejection evidence remain available.

This prevents permanent evidence from falsely claiming that rolled-back production changes occurred.

#### Decision 3 — Define evidence mutability by lifecycle stage

The phrase “append-only after the import run has completed” must not imply that permanent evidence can be freely rewritten while the run is active.

Accepted rules:

##### Staging tables

Staging rows are mutable only while:

```text
run status IN (
    created,
    staging_loaded
)
```

Validation fields may be finalized while the run is being validated.

After:

```text
status = validated
```

normalized source values become immutable.

After:

```text
status = merge_started
```

all staging values are immutable.

After a terminal run state, staging rows are read-only until cleanup.

##### Rejected records and rejection reasons

Once inserted, rejection evidence is immutable even while the run remains active.

A parser or validation correction requires:

- a new import run; or
- an explicit reset before permanent rejection evidence is finalized.

Normal processing must not rewrite an existing rejected record into a valid row.

##### Import outcomes

An `import_record_outcomes` row is immutable immediately after insertion.

It must be inserted only when the related production result is known.

##### Mapping observations

A `mapping_case_observations` row is immutable immediately after insertion.

A later import creates a new observation rather than updating the previous observation.

##### Mapping status history

A `mapping_status_history` row is immutable immediately after insertion.

Corrections create later transitions.

##### Price snapshots

A `market_price_snapshots` row is immutable immediately after insertion.

Corrected source values create a later snapshot or an explicit future correction record.

#### Required correction 1 — Add deterministic outcome uniqueness

`import_record_outcomes` currently requires entity identity but does not fully define how duplicate outcomes within one run are prevented.

One evaluated entity must produce at most one final outcome of the same entity type in one run.

Use two identity paths.

##### Source-backed outcome

When source identity is available:

```text
UNIQUE (
    import_run_id,
    entity_type,
    source_system,
    source_entity_id
)
WHERE source_system IS NOT NULL
  AND source_entity_id IS NOT NULL
```

##### Production-only outcome

For outcomes such as `missing`, where evaluation starts from an existing production entity:

```text
UNIQUE (
    import_run_id,
    entity_type,
    production_entity_id
)
WHERE source_system IS NULL
  AND source_entity_id IS NULL
  AND production_entity_id IS NOT NULL
```

The importer must not emit both identity forms as separate outcomes for the same logical entity.

When both source and production identity are available, the source-backed identity is the primary run-level uniqueness path and `production_entity_id` records the resolved target.

#### Required correction 2 — Keep `production_entity_id` intentionally polymorphic

`import_record_outcomes.production_entity_id` may refer to several tables depending on `entity_type`.

A normal foreign key cannot reference several production tables.

Accepted design:

- retain `production_entity_id` as a scalar audit identifier;
- do not create a database foreign key from this column;
- require a controlled `entity_type`;
- validate the referenced table and identifier before inserting the outcome;
- preserve source identity whenever the entity has one;
- use reconciliation queries to detect invalid audit references.

This is acceptable because `import_record_outcomes` is an audit log, not the relationship source of truth.

The application must not use `production_entity_id` without interpreting `entity_type`.

#### Required correction 3 — Define rejected-record uniqueness

One source row should create one permanent rejected-record parent per import run.

Required uniqueness:

```text
UNIQUE (
    import_run_id,
    source_entity_type,
    source_record_reference
)
```

Several validation problems for that row belong in:

```text
rejected_source_record_reasons
```

rather than duplicate `rejected_source_records` rows.

The parent `summary_reason_code` identifies the primary reporting reason.

Child reasons preserve every structured failure.

#### Required correction 4 — Define rejection-reason ordering and uniqueness

Each rejected record may have several reasons.

The first migration should include a deterministic reason order, such as:

```text
reason_sequence integer
```

with:

```text
reason_sequence >= 1
```

and:

```text
UNIQUE (
    rejected_source_record_id,
    reason_sequence
)
```

Also prevent accidental duplicate reason codes for one rejected record unless the same code may legitimately describe separate source fields.

Recommended MVP rule:

```text
UNIQUE (
    rejected_source_record_id,
    reason_code,
    field_name
)
```

using a null-safe strategy for `field_name`.

This provides deterministic reporting and prevents repeated insertion of the same validation problem.

#### Required correction 5 — Standardize staging processing states

All four staging tables use the same conceptual states:

```text
normalization_status:
pending
normalized
normalization_failed
```

```text
validation_status:
pending
valid
rejected
```

The same database checks should be used consistently across:

- `staging_cards`;
- `staging_market_products`;
- `staging_market_prices`;
- `staging_market_mappings`.

Required state rules:

```text
validation_status = 'valid'
→ normalization_status = 'normalized'
```

```text
normalization_status = 'normalization_failed'
→ validation_status <> 'valid'
```

```text
validation_status = 'pending'
→ validation_completed_at IS NULL
```

```text
validation_status IN ('valid', 'rejected')
→ validation_completed_at IS NOT NULL
```

A run must not enter:

```text
status = validated
```

while any staging row for that run remains:

```text
normalization_status = pending
```

or:

```text
validation_status = pending
```

#### Required correction 6 — Define duplicate source-identity handling

The staging uniqueness constraints prevent duplicate `source_record_reference`, but two different source references may still claim the same production identity.

Examples:

```text
two card rows with the same:
(source_system, source_card_id)
```

```text
two market-product rows with the same:
(source_system, source_product_id)
```

```text
two price rows with the same:
(source_system, source_product_id, source_snapshot_at)
```

For authoritative fixture imports, accepted rule:

- conflicting duplicate identities fail run-level validation;
- the importer must not select the first or last row;
- no production merge begins;
- all conflicting rows remain staged;
- structured rejection or validation evidence identifies every conflict.

Individual-row rejection is insufficient when the importer cannot prove which duplicate row is authoritative.

#### Required correction 7 — Define durable source references

Permanent evidence tables contain `source_record_reference`.

These references must not point only to:

- staging primary keys;
- temporary database row numbers;
- temporary extracted files that will be deleted;
- transient local paths without a retained artifact reference.

A durable reference should combine:

```text
import_runs.source_artifact_reference
```

with a stable record locator, for example:

```text
cards/xy5.json#xy5-20
```

or:

```text
products.csv#idProduct=273532
```

Staging cleanup is allowed only when every permanent evidence row remains traceable to the retained source artifact or fixture.

#### Required correction 8 — Define staging cleanup as a separate operation

Staging cleanup must not be part of the production merge transaction.

Accepted cleanup requirements:

- the parent run is terminal;
- production outcomes are complete;
- rejected records and reasons are complete;
- mapping observations are complete;
- status history is complete;
- source artifacts remain retained;
- reconciliation queries pass;
- the configured retention period has elapsed.

Cleanup deletes only:

```text
staging_cards
staging_market_products
staging_market_prices
staging_market_mappings
```

It must not delete:

```text
import_runs
import_record_outcomes
rejected_source_records
rejected_source_record_reasons
mapping_case_observations
mapping_candidates
mapping_status_history
market_price_snapshots
production entities
wishlist_items
```

Recommended initial retention:

```text
successful runs: 30 days
failed runs: 90 days
```

These periods are operational defaults and may be adjusted before implementation without changing table identity.

#### Required correction 9 — Resolve the mapping-case observation dependency cycle

The mapping audit structure contains a deliberate cycle:

```text
card_market_mapping_cases.status_source_observation_id
→ mapping_case_observations.mapping_case_observation_id
```

while:

```text
mapping_case_observations.mapping_case_id
→ card_market_mapping_cases.mapping_case_id
```

Migration order must handle this explicitly.

Accepted strategy:

1. create `card_market_mapping_cases` without the observation foreign key;
2. create `mapping_case_observations`;
3. add the case-to-observation foreign key with `ALTER TABLE`;
4. create `mapping_candidates`;
5. create `mapping_status_history`;
6. create `card_market_product_mappings`.

All cycle relationships use:

```text
ON DELETE RESTRICT
```

#### Required correction 10 — Enforce observation-to-case compatibility

Structures that store both:

```text
mapping_case_id
mapping_case_observation_id
```

must prove that the observation belongs to the same case.

Add a supporting unique constraint:

```text
mapping_case_observations:
UNIQUE (
    mapping_case_observation_id,
    mapping_case_id
)
```

Then use composite foreign keys from:

```text
mapping_candidates
mapping_status_history
```

where both identifiers are stored:

```text
(
    mapping_case_observation_id,
    mapping_case_id
)
→ mapping_case_observations(
    mapping_case_observation_id,
    mapping_case_id
)
```

This prevents a candidate or transition from combining:

- one mapping case;
- another case's observation.

#### Required correction 11 — Define one accepted transition per observation

One mapping observation may lead to:

- no accepted state transition; or
- one accepted state transition.

Required partial uniqueness:

```text
UNIQUE (source_observation_id)
WHERE source_observation_id IS NOT NULL
```

in `mapping_status_history`.

Manual transitions may have no source observation.

A manual transition still requires:

- a controlled transition method;
- a reason code;
- an explicit reviewed workflow;
- optional `import_run_id = null`.

#### Required correction 12 — Add a per-case transition sequence

`changed_at` alone is not sufficient for deterministic transition ordering:

- timestamps may be equal;
- database resolution may be insufficient;
- concurrent operations may race.

Add:

```text
transition_sequence integer
```

to `mapping_status_history`.

Required constraints:

```text
transition_sequence >= 1
```

```text
UNIQUE (
    mapping_case_id,
    transition_sequence
)
```

The first accepted state uses:

```text
transition_sequence = 1
```

A transition transaction must:

1. lock the mapping case;
2. read the latest sequence;
3. verify previous state;
4. insert the next sequence;
5. update the case projection;
6. update the production mapping;
7. commit.

`changed_at` remains the audit timestamp but no longer acts as the only ordering mechanism.

#### Decision 4 — Candidate evidence and candidate state

`mapping_candidates` preserves candidate-specific evidence and also contains candidate lifecycle state.

Accepted MVP behavior:

- candidate target and evidence fields are immutable after insertion;
- `candidate_state` and `state_changed_at` may change only inside the accepted mapping transition transaction;
- a candidate may transition from `active` to `selected`, `rejected`, or `superseded`;
- candidate rows are never deleted;
- the accepted mapping transition is preserved independently in `mapping_status_history`;
- only one candidate may be selected by one accepted transition;
- a selected candidate does not itself create a production mapping outside the transition transaction.

A dedicated candidate-state history table is deferred because `mapping_status_history` preserves the accepted target transition.

#### Decision 5 — Initial mapping-case state

Every new valid in-scope market product receives one persistent mapping case.

Accepted initial state:

```text
current_status = unmatched
```

The case is created without an accepted catalogue target.

Initial case creation also creates a first history row:

```text
previous_status = null
new_status = unmatched
transition_sequence = 1
```

This provides a complete accepted-state history from case creation.

A mapping observation in the same transaction may immediately support another accepted state, but that change must create the next explicit history row rather than silently changing the initial state.

#### Decision 6 — Import summary reconciliation

Because MVP import runs are separated by pipeline, summary reconciliation can be defined per run kind.

##### Catalogue run

```text
total_source_records
=
valid_source_records
+
rejected_records
```

```text
valid_source_records
=
inserted_records
+
updated_records
+
unchanged_records
```

`missing_records`, `retired_records`, and reactivation outcomes are counted separately because they begin from production state rather than current source rows.

##### Market-product run

Use the same reconciliation structure as catalogue runs.

##### Market-price run

```text
total_source_records
=
valid_source_records
+
rejected_records
```

Valid rows reconcile to:

```text
inserted
+
unchanged
```

Price snapshots are append-only and do not have ordinary `updated` outcomes.

Conflicting same-identity price observations prevent the run from succeeding.

##### Mapping run

```text
total_source_records
=
valid_source_records
+
rejected_records
```

Every valid staged mapping row creates exactly one:

```text
mapping_case_observation
```

Accepted state transitions are a subset of valid observations.

Therefore mapping observation counts and status counts should be derived from permanent observation and history tables rather than forced into the generic inserted, updated, and unchanged production summary fields.

For a mapping run, generic production summary fields may remain null unless a precise interpretation is approved.

#### Confirmed cross-table invariants

The following invariants are approved for migration design:

```text
every staging row
→ exactly one import_run
```

```text
every import_record_outcome
→ exactly one import_run
```

```text
every rejected_source_record
→ exactly one import_run
```

```text
every rejected_source_record_reason
→ exactly one rejected_source_record
```

```text
every automated mapping observation
→ exactly one import_run
```

```text
every automated mapping transition
→ one compatible mapping case
  and zero or one compatible source observation
```

Additional approved invariants:

- one source record reference is unique within its staging table and import run;
- all staging rows are terminally validated before production merge;
- rejected source rows create no production entity;
- each rejected source row has at least one structured reason;
- one logical evaluated entity has at most one final import outcome per run;
- import outcomes never act as production relationships;
- permanent evidence remains after staging cleanup;
- mapping observations never overwrite accepted case state by themselves;
- accepted mapping transitions are ordered per case;
- status history, case projection, candidate state, and production mapping change atomically;
- failed production transactions leave no false outcome or mapping-history rows;
- successful repeated imports create new run and observation evidence without duplicating production state;
- no import path modifies wishlist-owned fields.

#### Approved migration order for this block

The complete order still depends on production catalogue and market tables.

Recommended audit and import order:

```text
1. import_runs
2. staging_cards
3. staging_market_products
4. staging_market_prices
5. staging_market_mappings
6. import_record_outcomes
7. rejected_source_records
8. rejected_source_record_reasons
9. card_market_mapping_cases
10. mapping_case_observations
11. add card_market_mapping_cases.status_source_observation_id FK
12. mapping_candidates
13. mapping_status_history
14. card_market_product_mappings
15. market_price_snapshots
```

Production parent tables required by these relationships must be created earlier according to the final global migration order.

#### Required validation queries

Before migration readiness is approved, define queries that detect:

- active import runs left indefinitely in non-terminal states;
- terminal runs without `completed_at`;
- successful runs with failure fields;
- failed runs without a failure code;
- lifecycle timestamps in invalid order;
- staging rows that remain pending before merge;
- valid staging rows with unresolved required production identities;
- duplicate production identities inside one staging run;
- successful runs whose summary counts do not reconcile;
- duplicate import outcomes for one logical entity and run;
- outcomes that reference nonexistent polymorphic production IDs;
- rejected records without reasons;
- duplicate rejected-record parents for one source row;
- permanent evidence that references only deleted staging data;
- mapping candidates whose observation belongs to another case;
- mapping history whose observation belongs to another case;
- more than one accepted transition from one observation;
- duplicate or missing transition sequences;
- case projection that differs from the latest status history;
- active production mapping that differs from confirmed case state;
- mapping observations or history tied to failed runs but visible as accepted production state;
- staging cleanup that would remove the only remaining source evidence;
- any catalogue or market import that changes `wishlist_items`.

#### Review status

```text
Import and audit lifecycle review:
passed with required corrections
```

The following accepted corrections are carried into migration design:

- separate MVP run kinds are recorded as the accepted approach;
- outcome uniqueness is defined;
- rejected-record and reason uniqueness is defined;
- common staging-state constraints are approved;
- duplicate source-identity handling is approved;
- durable source-reference rules are documented;
- staging retention and cleanup rules are recorded;
- observation-to-case composite foreign keys are approved;
- one-transition-per-observation uniqueness is approved;
- `transition_sequence` is added to the migration plan;
- per-run-kind summary reconciliation is documented.

### Canonical price path and wishlist/export isolation

Reviewed tables:

```text
expansions
→ cards
→ card_editions
→ card_variants
→ card_market_product_mappings
→ market_products
→ market_price_snapshots
```

User-owned and export structures considered:

```text
wishlist_items
import_runs
card_market_mapping_cases
```

#### Review result

The canonical price and wishlist model is conceptually consistent:

- the canonical-card `From` price is derived rather than stored;
- market-price observations remain attached to independent market products;
- only active, sufficiently confirmed mappings may connect prices to canonical cards;
- language and finish eligibility are determined through confirmed variants;
- the MVP wishlist references only the canonical card;
- wishlist quantity and notes remain user-owned;
- catalogue imports, mapping changes, and price imports do not mutate wishlist data;
- export joins catalogue and market values at execution time instead of copying them into `wishlist_items`;
- cards without an eligible market price remain valid catalogue and wishlist records.

The block passes review with the decisions and corrections below.

#### Decision 1 — Define the canonical `From` price precisely

For one canonical card, the MVP `From` price is:

```text
the minimum non-null eligible avg30
across the latest eligible snapshot
of every eligible mapped market product
```

Equivalent conceptual expression:

```text
MIN(latest_eligible_snapshot.avg30)
GROUP BY card_id
```

The value is:

- informational;
- denominated in `EUR`;
- derived at query time;
- nullable;
- not a purchase offer;
- not stored in `cards`;
- not stored in `wishlist_items`;
- not stored in `market_products`;
- not written back during price imports.

#### Approved price path

```text
expansions
→ cards
→ card_editions
→ card_variants
→ active card_market_product_mappings
→ active market_products
→ latest eligible market_price_snapshots
```

The ordinary price query does not need to join:

```text
card_market_mapping_cases
```

when the case projection and active production mapping have passed the required reconciliation checks.

Mapping cases remain part of audit and validation rather than the primary runtime price path.

#### Decision 2 — Require a complete active catalogue ancestry

A price contributes only when the complete catalogue ancestry is active.

Required predicates:

```text
expansions.is_active = true
```

```text
cards.is_active = true
```

```text
card_editions.is_active = true
```

```text
card_variants.is_active = true
```

```text
card_market_product_mappings.is_active = true
```

```text
market_products.is_active = true
```

A retired parent must not contribute to an ordinary current `From` price even when its child rows remain individually active for historical preservation.

Parent retirement does not cascade into child lifecycle updates.

The price query is responsible for applying the complete active ancestry.

#### Decision 3 — Require variant-level English or German confirmation

The accepted MVP language rule is:

```text
card_market_product_mappings.confirmation_scope = 'variant'
```

and:

```text
card_variants.language_code IN ('en', 'de')
```

Only these mappings are language-eligible.

Mappings confirmed only at:

```text
card
```

or:

```text
edition
```

remain valid production relationships but contribute no canonical price.

The implementation must not assign a default language to make these mappings price-eligible.

#### Decision 4 — Use only `avg30` for the first MVP query

The eligible metric is:

```text
market_price_snapshots.avg30
```

The value:

```text
avg30_holo
```

remains preserved as source evidence but is excluded from the first canonical price query.

A non-null `avg30_holo` must not:

- create a variant;
- prove a holo finish;
- upgrade mapping confirmation scope;
- replace a null `avg30`;
- contribute independently to the minimum.

#### Decision 5 — Select the latest snapshot independently per product

For every eligible market product, select:

```text
the row with the greatest source_snapshot_at
among snapshots belonging to succeeded compatible market-price runs
```

This is a per-product selection.

It must not select one global price run and then discard valid current prices for products absent from that run unless the source contract explicitly defines a complete global snapshot.

Conceptual PostgreSQL direction:

```text
ROW_NUMBER() OVER (
    PARTITION BY market_product_id
    ORDER BY source_snapshot_at DESC
) = 1
```

Only snapshots whose parent import run has:

```text
status = 'succeeded'
```

and a compatible price run kind and source scope are eligible.

#### Snapshot tie behavior

The production uniqueness rule:

```text
UNIQUE (
    market_product_id,
    source_snapshot_at
)
```

prevents two ordinary snapshots for the same product and source timestamp.

A repeated import with the same timestamp and identical values creates no new snapshot.

The same timestamp with conflicting values is an import conflict and must not overwrite the existing snapshot.

#### Decision 6 — Restrict MVP currency to EUR

The first schema and query use:

```text
currency_code = 'EUR'
```

The canonical minimum must not combine currencies.

Currency conversion remains outside MVP scope.

A non-EUR snapshot:

- may be rejected by the first import contract;
- must not enter the MVP price query;
- must not be converted using an inferred exchange rate.

#### Decision 7 — Define null and zero semantics

##### Null price

When no eligible non-null `avg30` exists:

```text
From price = null
```

The UI or export may display:

```text
Price unavailable
```

or leave the field empty.

It must not display:

```text
0
```

```text
0.00 EUR
```

or a fabricated fallback price.

##### Zero price

A stored zero is distinct from null.

A zero may participate only when:

- the source explicitly supplied zero;
- the value passed source validation;
- the import did not convert empty or invalid text to zero.

If Cardmarket zero represents missing or unusable data, that source-specific rule must be documented before zero becomes eligible.

Until that rule is validated, zero values should be reported separately during fixture validation.

#### Decision 8 — Define canonical aggregation granularity

The aggregate is grouped by:

```text
cards.card_id
```

not by:

- expansion;
- collector number;
- card name;
- edition;
- variant;
- wishlist item;
- market product.

Several eligible variants and market products may contribute candidate values to one canonical card.

The minimum produces one nullable price per canonical card.

#### Duplicate market products

A market product classified as:

```text
unmatched_duplicate_candidate
```

has no active confirmed production mapping.

Therefore it cannot enter the canonical price path.

The price query must not independently reproduce duplicate-candidate classification through:

- product-name matching;
- metaproduct grouping;
- minimum-price selection;
- source product ordering.

Eligibility comes only through the active confirmed mapping.

#### Excluded and unresolved market products

The following mapping case states create no eligible production mapping:

```text
candidate
unmatched
ambiguous
excluded
unmatched_duplicate_candidate
```

Products in these states:

- remain preserved;
- may retain price snapshots;
- may remain visible in review tooling;
- contribute no canonical `From` price.

#### Superseded mappings

Historical inactive mappings must not contribute.

Required predicate:

```text
card_market_product_mappings.is_active = true
```

When a mapping becomes more specific:

```text
card
→ edition
→ variant
```

only the new active mapping is considered.

The historical mapping remains preserved but price-ineligible.

#### Decision 9 — Define the runtime price result as a view or query

The first implementation should expose the derived price through a database view or a documented reusable query.

Recommended conceptual view:

```text
canonical_card_current_prices
```

Suggested output columns:

| Column                      | Meaning                                                    |
| --------------------------- | ---------------------------------------------------------- |
| `card_id`                   | Canonical card identity                                    |
| `currency_code`             | `EUR` when a price exists                                  |
| `from_price`                | Minimum eligible non-null `avg30`                          |
| `eligible_product_count`    | Number of eligible products with a selected snapshot       |
| `priced_variant_count`      | Number of distinct eligible variants contributing products |
| `latest_source_snapshot_at` | Latest contributing snapshot timestamp                     |
| `calculated_at`             | Optional query timestamp only if operationally useful      |

The view must not become an additional source of truth.

A materialized view or stored price cache is deferred until performance measurements demonstrate a need.

#### Required correction 1 — Do not require a price for catalogue validity

A canonical card remains valid when:

- it has no mapping;
- its mappings are unresolved;
- it has only card- or edition-level mappings;
- no English or German variant is confirmed;
- eligible products have no `avg30`;
- the latest price import omitted the product;
- its eligible product is retired.

Price availability must not control:

- card insertion;
- card activation;
- wishlist membership;
- card search visibility;
- card export eligibility.

Price is optional derived information.

#### Required correction 2 — Make wishlist isolation explicit in every import path

The following processes have no write ownership over `wishlist_items`:

```text
catalogue import
market-product import
mapping import
price import
staging cleanup
rejection handling
mapping review
mapping supersession
card retirement
```

They must not:

- create wishlist rows;
- delete wishlist rows;
- change `quantity`;
- change `notes`;
- change `card_id`;
- update wishlist timestamps;
- replace a retired card reference;
- clear wishlist membership after a missing observation.

The only ordinary wishlist mutations are user-owned:

```text
insert
update quantity
update notes
delete
```

#### Wishlist foreign-key behavior

Required relationship:

```text
wishlist_items.card_id
→ cards.card_id
```

with:

```text
ON DELETE RESTRICT
```

Do not use:

```text
ON DELETE CASCADE
```

A physical card deletion must fail while a wishlist row references it.

Ordinary lifecycle changes use:

```text
cards.is_active
cards.retired_at
```

rather than deleting the card.

#### Decision 10 — Define retired-card behavior in Wishlist

A retired canonical card remains visible in the Wishlist context when the user still has a wishlist row.

Recommended Wishlist behavior:

- preserve the row;
- preserve quantity;
- preserve notes;
- show the card as retired or inactive;
- return a null current `From` price;
- prevent the retired card from disappearing silently;
- allow the user to remove it from the wishlist.

The ordinary active catalogue view may exclude retired cards.

The Wishlist view must use different visibility logic because it represents user-owned persistent state.

#### Decision 11 — Use presence-based wishlist membership

Wanted state remains:

```text
wishlist row exists
→ wanted
```

```text
wishlist row does not exist
→ not wanted
```

Do not add:

```text
is_wanted
```

to `wishlist_items`.

This avoids contradictory states such as:

```text
is_wanted = false
quantity = 2
```

Removing a card from the wishlist deletes only the user-owned row.

It does not modify the canonical card or any market data.

#### Decision 12 — Keep quantity canonical-card scoped

For MVP:

```text
wishlist_items.quantity
```

represents the desired quantity of the canonical card.

It does not distinguish:

- edition;
- language;
- finish;
- market product;
- condition;
- seller.

A note may mention preferences, but free text does not create structured variant relationships.

This means that canonical `From` price is informational for the card and is not automatically multiplied by quantity unless a specific display or export field requests an estimated total.

#### Optional estimated total

When needed, a derived estimated total may be calculated as:

```text
quantity * from_price
```

It must remain nullable when `from_price` is null.

It must not be stored in `wishlist_items`.

It must be clearly labelled as an estimate rather than an offer or committed purchase cost.

#### Decision 13 — Define the Wishlist view join path

Recommended Wishlist query path:

```text
wishlist_items
→ cards
→ expansions
LEFT JOIN canonical_card_current_prices
```

Use a left join for the price view.

This ensures that wishlist rows remain visible when no eligible price exists.

Conceptual output:

| Field                | Source                   |
| -------------------- | ------------------------ |
| card identity        | `cards`                  |
| card name            | `cards`                  |
| collector number     | `cards`                  |
| expansion name       | `expansions`             |
| quantity             | `wishlist_items`         |
| notes                | `wishlist_items`         |
| current `From` price | derived price view       |
| currency             | derived price view       |
| card lifecycle state | `cards` and `expansions` |

Do not use an inner join to the price path because that would hide unpriced wishlist items.

#### Decision 14 — Define catalogue and wishlist view separation

##### Catalogue view

Selection source:

```text
cards
```

Recommended default filters:

```text
cards.is_active = true
expansions.is_active = true
```

Wishlist membership is joined optionally.

Current price is joined optionally.

##### Wishlist view

Selection source:

```text
wishlist_items
```

No active-card filter may remove a saved wishlist row.

Catalogue lifecycle fields may be displayed as status.

Current price is joined optionally.

This difference must be preserved in NocoDB views or application queries.

#### Decision 15 — Define export selection source

Wishlist CSV export uses:

```text
wishlist_items
```

as the root selection source.

The export must not begin from:

- active cards;
- market products;
- eligible prices;
- mapping cases.

Starting from `wishlist_items` ensures that every user-selected card is exported even when:

- the card is retired;
- the card has no market mapping;
- no eligible English or German variant exists;
- price is unavailable.

#### Approved MVP export fields

Recommended required fields:

```text
source_card_id
card_name
collector_number
expansion_name
quantity
notes
from_price
currency_code
price_available
card_active
```

Optional traceability fields:

```text
expansion_key
eligible_product_count
latest_source_snapshot_at
```

Edition, language, finish, and external product ID should not be presented as one canonical value when several eligible variants or products contribute to the minimum.

#### Required correction 3 — Avoid ambiguous singular market fields in export

The current wishlist description says export may include:

```text
variant
language
external product identifier
minimum eligible avg30
```

This is ambiguous because one canonical card may have:

- several eligible variants;
- several eligible products;
- different products producing the minimum over time.

The canonical-card export should not include one arbitrary:

```text
variant
language
external product identifier
```

unless those fields refer specifically to the product that produced the current minimum.

Recommended MVP choice:

- omit singular variant and external product columns from the canonical wishlist export;
- export only canonical card data, wishlist data, and the derived `From` price.

A separate diagnostic price export may later expose contributing products and variants.

#### Optional minimum-source traceability

If product-level price traceability is required in the Wishlist export, define deterministic fields:

```text
from_price_market_product_id
from_price_source_product_id
from_price_variant_id
```

The selection must use an explicit tie-break rule when several products have the same minimum.

Recommended tie-break order:

```text
avg30 ascending
source_snapshot_at descending
market_product_id ascending
```

These fields are not required for the first MVP export.

#### Decision 16 — Define export price formatting

The database returns:

```text
numeric amount
currency code
```

as separate values.

CSV formatting should preserve machine-readable values.

Recommended output:

```text
from_price = 1.2300
currency_code = EUR
```

Do not store or export the database amount only as:

```text
€1.23
```

because that reduces portability.

A user-facing display may format the same value as:

```text
€1.23
```

#### Decision 17 — Define price freshness visibility

Because the price is based on snapshots, the UI and export should be able to show price freshness.

Recommended derived field:

```text
latest_source_snapshot_at
```

This is the latest timestamp among snapshots that contributed candidate values to the card's current minimum calculation.

For precise minimum-source traceability, a separate field may expose the timestamp of the product that actually produced the minimum.

The first MVP should at least avoid presenting an old price as though it were real-time.

#### Decision 18 — Define export consistency

One export execution should observe a transactionally consistent database snapshot.

The export must not combine:

- an old active mapping;
- a newly committed price;
- a partially completed mapping transition;
- a partially updated wishlist row.

Recommended PostgreSQL behavior:

```text
one read-only transaction
```

using the default statement snapshot when the export is one SQL statement.

For a multi-query export process, use a consistent transaction snapshot.

#### Required correction 4 — Protect catalogue fields in the wishlist interface

The data model defines ownership boundaries, but NocoDB or another UI may expose joined catalogue fields as editable.

The implementation must ensure:

- `quantity` and `notes` are user-editable;
- wishlist membership is user-editable;
- catalogue identity and display fields are read-only;
- mapping fields are read-only;
- price fields are read-only;
- source identifiers are read-only;
- lifecycle fields are not editable through the ordinary wishlist workflow.

This is an application and permissions requirement rather than a new table constraint.

#### Canonical price pseudocode

Conceptual query stages:

```text
1. select active variant-level mappings
2. join active en/de variants
3. join active editions, cards, expansions, and products
4. select latest succeeded-run snapshot per market product
5. discard rows where avg30 is null
6. require currency_code = EUR
7. calculate minimum avg30 per card
8. left join the result to catalogue and wishlist views
```

Conceptual SQL shape:

```sql
WITH latest_product_prices AS (
    SELECT
        snapshots.market_product_id,
        snapshots.avg30,
        snapshots.currency_code,
        snapshots.source_snapshot_at,
        ROW_NUMBER() OVER (
            PARTITION BY snapshots.market_product_id
            ORDER BY snapshots.source_snapshot_at DESC
        ) AS snapshot_rank
    FROM market_price_snapshots AS snapshots
    JOIN import_runs AS runs
      ON runs.import_run_id = snapshots.import_run_id
    WHERE runs.status = 'succeeded'
      AND runs.run_kind = 'market_prices'
      AND snapshots.currency_code = 'EUR'
),
eligible_prices AS (
    SELECT
        mappings.card_id,
        prices.market_product_id,
        prices.avg30,
        prices.source_snapshot_at
    FROM card_market_product_mappings AS mappings
    JOIN market_products AS products
      ON products.market_product_id = mappings.market_product_id
    JOIN card_variants AS variants
      ON variants.card_variant_id = mappings.card_variant_id
    JOIN card_editions AS editions
      ON editions.card_edition_id = mappings.card_edition_id
    JOIN cards
      ON cards.card_id = mappings.card_id
    JOIN expansions
      ON expansions.expansion_id = cards.expansion_id
    JOIN latest_product_prices AS prices
      ON prices.market_product_id = products.market_product_id
     AND prices.snapshot_rank = 1
    WHERE mappings.is_active = true
      AND mappings.confirmation_scope = 'variant'
      AND products.is_active = true
      AND variants.is_active = true
      AND variants.language_code IN ('en', 'de')
      AND editions.is_active = true
      AND cards.is_active = true
      AND expansions.is_active = true
      AND prices.avg30 IS NOT NULL
)
SELECT
    card_id,
    MIN(avg30) AS from_price,
    'EUR' AS currency_code
FROM eligible_prices
GROUP BY card_id;
```

The final SQL must use the actual approved controlled-value and import-run column definitions.

#### Confirmed cross-table invariants

The following invariants are approved for migration and query design:

```text
wishlist_items.card_id
→ cards.card_id
```

with:

```text
UNIQUE (wishlist_items.card_id)
ON DELETE RESTRICT
```

Additional approved invariants:

- canonical price is derived and nullable;
- one card receives at most one current derived `From` price row;
- only active variant-level English or German mappings are eligible;
- only active catalogue ancestry and active market products are eligible;
- only the latest eligible succeeded-run snapshot per product is considered;
- only non-null `avg30` contributes;
- `avg30_holo` does not contribute to the first MVP query;
- only EUR contributes;
- unresolved, excluded, ambiguous, candidate, and duplicate-candidate products do not contribute;
- wishlist membership does not depend on price availability;
- retired or unpriced wishlist cards remain visible in the Wishlist view;
- imports do not modify wishlist-owned fields;
- export starts from `wishlist_items`;
- export joins catalogue and price fields at execution time;
- no catalogue, mapping, or price values are duplicated in `wishlist_items`;
- unavailable price is null rather than zero;
- wishlist export remains complete when market data is missing.

#### Required validation queries

Before migration readiness is approved, define queries or tests that confirm:

- an active English variant-level mapping contributes `avg30`;
- an active German variant-level mapping contributes `avg30`;
- card- and edition-level mappings do not contribute;
- unsupported languages do not contribute;
- inactive expansions, cards, editions, variants, mappings, or products do not contribute;
- historical superseded mappings do not contribute;
- `avg30_holo` does not contribute;
- non-EUR snapshots do not contribute;
- failed-run snapshots do not contribute;
- only the latest eligible snapshot per product contributes;
- null `avg30` values are ignored;
- no eligible value returns null rather than zero;
- duplicate-candidate and excluded products do not contribute;
- minimum is grouped by canonical `card_id`;
- multiple eligible products produce the correct minimum;
- a newer snapshot changes the derived price without modifying the wishlist row;
- a mapping supersession changes eligibility without modifying the wishlist row;
- a card retirement preserves its wishlist row but removes its current price;
- an unpriced wishlist card remains visible;
- wishlist quantity and notes survive every import type;
- export contains one row per wishlist item;
- export does not omit retired or unpriced wishlist items;
- export contains no arbitrary singular variant or product identifier;
- deleting a referenced card is restricted;
- deleting a wishlist item does not alter catalogue or market data;
- a consistent export snapshot is produced during concurrent price or mapping updates.

#### Review status

```text
Canonical price path and wishlist/export isolation review:
passed with required corrections
```

The following accepted requirements are carried into migration and view design:

- the canonical price view or reusable query contract is approved;
- active ancestry filters are documented in the price query;
- latest-snapshot-per-product selection is recorded;
- null and zero price semantics are approved;
- retired-card Wishlist visibility is recorded;
- canonical and Wishlist view selection sources are documented;
- MVP CSV export fields are approved;
- ambiguous singular variant, language, and product columns are removed from the canonical wishlist export;
- catalogue and price fields are protected from ordinary wishlist editing.

## Migration readiness

### Review coverage

Cross-table consistency review has been completed for:

```text
Catalogue hierarchy
```

```text
Market products, mapping lifecycle, and price snapshots
```

```text
Import and audit lifecycle
```

```text
Canonical price path and wishlist/export isolation
```

All `21` initial tables have detailed proposed data dictionaries.

The model passed conceptual review and was translated into an incremental PostgreSQL migration set. The reviewed table-dictionary corrections were applied before migration authoring, and the physical schema has now been created and validated in the local PostgreSQL environment.

### Overall readiness status

```text
Data dictionary: complete
Cross-table review: complete
Reviewed corrections: applied
Conceptual model: passed
SQL migrations: implemented through 17 incremental dbmate migrations
Rollback validation: passed locally
Schema-wide validation: passed locally
Implementation: physical schema implemented locally
```

The migration-design work has been completed for the initial schema.

The implemented migration set now includes:

- exact PostgreSQL constraints;
- controlled values;
- foreign-key enforcement;
- partial unique indexes;
- deterministic migration order;
- reversible `migrate:down` sections;
- executable schema-wide validation.

Remaining work belongs to data loading and behavioural validation rather than initial schema creation. This includes fixture bootstrap, import merge execution, repeat-import testing, runtime price derivation, and wishlist workflow validation.

### Accepted MVP decisions

#### Expansion bootstrap

For the first Primal Clash vertical slice:

- `expansions` is populated through controlled bootstrap or seed logic;
- `expansion_source_identifiers` is populated in the same controlled transaction;
- no `staging_expansions` table is added to the first schema;
- the bootstrap creates one Primal Clash expansion;
- `pokemon_tcg_data / xy5` and `cardmarket / 1585` resolve to that same expansion;
- a general expansion-import pipeline is deferred until multi-expansion ingestion requires it.

#### Catalogue hierarchy

The accepted hierarchy is:

```text
expansions
→ cards
→ card_editions
→ card_variants
```

Rules:

- cards belong to exactly one expansion;
- editions belong to exactly one canonical card;
- variants belong to exactly one edition;
- card-level confirmation creates no edition or variant;
- edition-level confirmation may create an edition but no variant;
- only variant-level confirmation may create a variant;
- missing observations do not cause automatic retirement;
- retirement preserves all dependent records;
- physical deletion uses restrictive foreign keys.

#### Variant language scope

Initial controlled language values:

```text
en
de
```

Unknown language:

- creates no variant;
- is not stored as `unknown`;
- is not stored as `other`;
- is not assigned a default language;
- remains represented only through less-specific mapping evidence.

#### Variant finish scope

Initial controlled finish values:

```text
normal
reverse_holo
holo
```

The generic value:

```text
other
```

is excluded from the first migration.

A new explicit controlled finish code must be approved when the first supported non-standard finish is encountered.

`finish_detail` is deferred from the first migration.

#### Market-product identity

Market-product identity is:

```text
UNIQUE (
    source_system,
    source_product_id
)
```

For the first implementation:

```text
source_system = cardmarket
```

A market product may exist without:

- a confirmed canonical mapping;
- an edition;
- a variant;
- a current price.

#### Persistent mapping case

The physical relationship is:

```text
market_products
    1 → zero or one card_market_mapping_cases
```

After a successful complete mapping run for an in-scope product set:

```text
every valid in-scope market product
→ exactly one mapping case
```

A mapping case stores the current accepted projection.

Observations and status history preserve evidence and transitions.

#### Mapping lifecycle

One market product may have:

```text
zero or many historical production mappings
```

but at most:

```text
one active production mapping
```

A more specific confirmed relationship:

```text
card
→ edition
→ variant
```

creates a new mapping row and supersedes the previous row.

It does not overwrite the previous target in place.

Only a mapping case whose current accepted state is:

```text
confirmed
```

may have one active production mapping.

All other case statuses have no active production mapping.

#### Supported mapping statuses

Initial accepted statuses:

```text
unmatched
candidate
ambiguous
confirmed
excluded
unmatched_duplicate_candidate
```

The following create no production mapping:

```text
unmatched
candidate
ambiguous
excluded
unmatched_duplicate_candidate
```

#### English and German price eligibility

A market-product mapping is price-eligible only when:

```text
confirmation_scope = variant
```

and the referenced active variant has:

```text
language_code IN ('en', 'de')
```

Card-level and edition-level mappings remain valid confirmed relationships but are not eligible for canonical-card pricing.

No language is inferred from Cardmarket scope, product name, user locale, or price-field availability.

#### MVP price metric

The first MVP canonical price uses:

```text
avg30
```

only.

`avg30_holo`:

- remains stored as source evidence;
- does not create a holo variant;
- does not upgrade confirmation scope;
- does not replace null `avg30`;
- does not contribute to the first MVP canonical price.

#### Currency

The first MVP market-price currency is:

```text
EUR
```

The first migration may enforce:

```text
currency_code = 'EUR'
```

Currency conversion is outside MVP scope.

#### Canonical `From` price

For one canonical card:

```text
From price
=
minimum non-null eligible avg30
across the latest eligible snapshot
for each eligible mapped market product
```

The aggregate is grouped by:

```text
cards.card_id
```

The result is:

- derived;
- nullable;
- informational;
- not stored in `cards`;
- not stored in `wishlist_items`;
- not stored in `market_products`.

When no eligible value exists:

```text
From price = null
```

It must not become zero.

#### Latest snapshot selection

For each eligible market product, select:

```text
the greatest source_snapshot_at
among snapshots belonging to succeeded compatible market-price runs
```

Snapshot selection is performed independently per product.

The initial business uniqueness is:

```text
UNIQUE (
    market_product_id,
    source_snapshot_at
)
```

A same-timestamp value conflict prevents automatic overwrite.

#### Import-run model

The MVP uses separate import runs:

```text
catalogue
market_products
market_mappings
market_prices
```

The first production implementation does not use:

```text
vertical_slice
combined
```

as database run-kind or source-system values.

Recommended Primal Clash execution order:

```text
1. expansion bootstrap
2. catalogue card run
3. market-product run
4. mapping run
5. market-price run
```

#### Import lifecycle

Successful lifecycle:

```text
created
→ staging_loaded
→ validated
→ merge_started
→ succeeded
```

Validation failure:

```text
created
→ staging_loaded
→ validation_failed
```

Merge failure:

```text
created
→ staging_loaded
→ validated
→ merge_started
→ merge_failed
```

No production changes occur before validation succeeds.

Production changes occur in one atomic transaction.

A merge failure rolls back:

- production entities;
- mapping changes;
- mapping history created inside the transaction;
- price snapshots;
- import outcomes.

Wishlist data remains unchanged.

#### Evidence lifecycle

Immediately immutable after insertion:

```text
import_record_outcomes
rejected_source_records
rejected_source_record_reasons
mapping_case_observations
mapping_status_history
market_price_snapshots
```

Staging records become immutable after validation and remain read-only until cleanup.

A later source observation creates new evidence rather than rewriting completed evidence.

#### Staging cleanup

Staging cleanup is a separate post-run operation.

Initial proposed retention:

```text
successful runs: 30 days
failed runs: 90 days
```

Cleanup may delete only:

```text
staging_cards
staging_market_products
staging_market_prices
staging_market_mappings
```

Permanent audit, production, mapping, market, and wishlist data must remain.

#### Wishlist ownership

The MVP wishlist references:

```text
cards.card_id
```

Wanted state is presence-based:

```text
wishlist row exists
→ wanted
```

User-owned writable fields:

```text
quantity
notes
```

Catalogue, market, mapping, price, and cleanup processes have no write ownership over `wishlist_items`.

#### Wishlist visibility

A retired or unpriced card remains visible when a wishlist row exists.

The Wishlist view starts from:

```text
wishlist_items
```

not from active cards or eligible prices.

Price is joined with a left join.

The ordinary Catalogue view may filter inactive cards and expansions.

#### Wishlist export

Wishlist CSV export starts from:

```text
wishlist_items
```

Recommended first fields:

```text
source_card_id
card_name
collector_number
expansion_name
quantity
notes
from_price
currency_code
price_available
card_active
```

The canonical export does not include an arbitrary singular:

```text
variant
language
market product
external product identifier
```

because several eligible variants or products may exist for one canonical card.

### Applied document corrections

The following reviewed corrections are reflected in the table dictionaries and migration plan.

#### `expansions`

Replace staging-based expansion merge wording with the accepted controlled bootstrap process.

Do not refer to a nonexistent:

```text
staging_expansions
```

table in the first implementation.

#### `card_editions`

Replace:

```text
Display-name updates: allowed only when the value is import-owned
```

with:

```text
Display-name updates: allowed only when the value is mapping-owned and supported by accepted evidence.
```

Add supporting uniqueness:

```text
UNIQUE (
    card_edition_id,
    card_id
)
```

for composite hierarchy foreign keys.

#### `card_variants`

Remove from the first schema:

```text
finish_code = other
finish_detail
```

Update:

- columns;
- controlled finish values;
- constraints;
- examples;
- merge behavior;
- validation requirements;
- open questions.

Add supporting uniqueness:

```text
UNIQUE (
    card_variant_id,
    card_edition_id
)
```

#### `market_products`

Change the mapping-case relationship from:

```text
1 → one
```

to:

```text
1 → zero or one
```

Document the post-mapping-run requirement for exactly one case per valid in-scope product.

#### `card_market_mapping_cases`

Add supporting uniqueness:

```text
UNIQUE (
    mapping_case_id,
    market_product_id
)
```

Document that:

```text
status_source_observation_id
```

is added as a foreign key only after `mapping_case_observations` exists.

#### `mapping_case_observations`

Add supporting uniqueness:

```text
UNIQUE (
    mapping_case_observation_id,
    mapping_case_id
)
```

This supports composite compatibility foreign keys from candidates and status history.

#### `card_market_product_mappings`

Replace simple case compatibility with:

```text
(
    mapping_case_id,
    market_product_id
)
→ card_market_mapping_cases(
    mapping_case_id,
    market_product_id
)
```

Add hierarchy foreign keys:

```text
(
    card_edition_id,
    card_id
)
→ card_editions(
    card_edition_id,
    card_id
)
```

```text
(
    card_variant_id,
    card_edition_id
)
→ card_variants(
    card_variant_id,
    card_edition_id
)
```

Use one active-mapping partial unique index:

```text
UNIQUE (market_product_id)
WHERE is_active = true
```

Use scope-specific exact-target uniqueness.

Card scope:

```text
UNIQUE (
    market_product_id,
    card_id
)
WHERE confirmation_scope = 'card'
```

Edition scope:

```text
UNIQUE (
    market_product_id,
    card_id,
    card_edition_id
)
WHERE confirmation_scope = 'edition'
```

Variant scope:

```text
UNIQUE (
    market_product_id,
    card_id,
    card_edition_id,
    card_variant_id
)
WHERE confirmation_scope = 'variant'
```

Remove or mark as unnecessary the redundant active uniqueness on `mapping_case_id`.

#### `market_price_snapshots`

Document:

```text
currency_code = 'EUR'
```

for the first migration.

Document insertion while the parent run is:

```text
merge_started
```

and runtime eligibility only after the run reaches:

```text
succeeded
```

Replace ambiguous current-snapshot wording with the accepted latest-snapshot-per-product rule.

Document that only `avg30` contributes to the first MVP canonical price.

#### `import_runs`

Remove or defer controlled values:

```text
vertical_slice
combined
```

for the first implementation.

Document separate run kinds and per-run-kind summary reconciliation.

#### Staging tables

Apply the same controlled processing states and checks to all four staging tables.

Required states:

```text
normalization_status:
pending
normalized
normalization_failed
```

```text
validation_status:
pending
valid
rejected
```

Apply consistent timestamp and state checks.

Document that conflicting duplicate production identities fail run-level validation.

#### `import_record_outcomes`

Add source-backed uniqueness:

```text
UNIQUE (
    import_run_id,
    entity_type,
    source_system,
    source_entity_id
)
WHERE source_system IS NOT NULL
  AND source_entity_id IS NOT NULL
```

Add production-only uniqueness:

```text
UNIQUE (
    import_run_id,
    entity_type,
    production_entity_id
)
WHERE source_system IS NULL
  AND source_entity_id IS NULL
  AND production_entity_id IS NOT NULL
```

Document that `production_entity_id` is intentionally polymorphic and has no direct foreign key.

#### `rejected_source_records`

Add:

```text
UNIQUE (
    import_run_id,
    source_entity_type,
    source_record_reference
)
```

One rejected source row has one parent record and several child reasons.

#### `rejected_source_record_reasons`

Add:

```text
reason_sequence integer
```

with:

```text
reason_sequence >= 1
```

and:

```text
UNIQUE (
    rejected_source_record_id,
    reason_sequence
)
```

Add null-safe duplicate-reason prevention for:

```text
rejected_source_record_id
reason_code
field_name
```

#### `mapping_candidates`

Where both case and observation identifiers exist, use:

```text
(
    mapping_case_observation_id,
    mapping_case_id
)
→ mapping_case_observations(
    mapping_case_observation_id,
    mapping_case_id
)
```

Document candidate evidence immutability and transactional candidate-state updates.

#### `mapping_status_history`

Add:

```text
transition_sequence integer
```

with:

```text
transition_sequence >= 1
```

and:

```text
UNIQUE (
    mapping_case_id,
    transition_sequence
)
```

Add:

```text
UNIQUE (source_observation_id)
WHERE source_observation_id IS NOT NULL
```

Use the composite observation-to-case foreign key where both identifiers exist.

#### `wishlist_items`

Document explicitly that:

- retired cards remain visible through the Wishlist view;
- price joins use a left join;
- imports cannot update wishlist timestamps;
- export starts from `wishlist_items`;
- singular arbitrary product and variant fields are omitted from the canonical export.

### Approved first-migration controlled values

The following registry is authoritative for the first PostgreSQL migration.

All stored project-defined values use lowercase technical identifiers with underscore separators. External standard identifiers retain their standard representation.

Values not listed here must be rejected or deferred until explicitly approved.

#### `source_system`

Included:

```text
pokemon_tcg_data
cardmarket
```

Not valid in the first migration:

```text
combined
```

One import run represents one primary source contract. Cross-source mapping evidence remains source-specific.

#### `run_kind`

Included:

```text
catalogue
market_products
market_mappings
market_prices
```

Not valid in the first migration:

```text
vertical_slice
```

A higher-level orchestration process may coordinate several runs, but it is not stored as one combined production import run.

#### `source_entity_type`

Included for `import_runs`:

```text
card
market_product
market_mapping
market_price
```

Included for permanent outcome and rejection evidence where applicable:

```text
expansion
card
market_product
market_mapping
market_price
```

`expansion` remains available for evidence compatibility. The first Primal Clash expansion is created through controlled bootstrap logic rather than an expansion staging run.

Not valid:

```text
combined
```

#### `scope_type`

Included:

```text
expansion
source_file
selected_records
complete_source_snapshot
```

Not valid in the first migration:

```text
vertical_slice
```

The initial Primal Clash production runs normally use `expansion`. Synthetic validation runs may use `selected_records`.

#### `import_run_status`

Included:

```text
created
staging_loaded
validation_failed
validated
merge_started
merge_failed
succeeded
cancelled
```

Terminal values:

```text
validation_failed
merge_failed
succeeded
cancelled
```

#### `mapping_status`

Included:

```text
confirmed
candidate
unmatched
ambiguous
excluded
unmatched_duplicate_candidate
```

`rejected` is not a mapping status. Structurally invalid source observations are represented through `rejected_source_records`.

`revalidated` is an event or observation result, not a persistent current mapping status.

#### `confirmation_scope`

Included:

```text
card
edition
variant
```

The value is required only for confirmed mappings. Non-confirmed mapping observations store a null confirmation scope.

#### `confirmation_method`

Included:

```text
direct_source_identifier
explicit_source_relationship
validated_derived_rule
manual_review
```

The accepted Primal Clash product-page evidence uses `direct_source_identifier`.

#### `evidence_level`

Included:

```text
direct
derived
manual
insufficient
```

A confirmed mapping must not use `insufficient`.

#### `language_code`

Included:

```text
en
de
```

Not valid:

```text
unknown
other
```

An unresolved language creates no `card_variants` row and remains represented through less-specific mapping evidence.

#### `finish_code`

Included:

```text
normal
reverse_holo
holo
```

Not valid in the first migration:

```text
other
```

Unknown finish is not stored as a controlled finish value and does not create a variant. `finish_detail` is deferred.

#### `currency_code`

Included:

```text
EUR
```

Other currency values are rejected by the first MVP market-price import contract. Currency uses uppercase representation because it is an external standard identifier.

#### `normalization_status`

Included consistently across all staging tables:

```text
pending
normalized
normalization_failed
```

#### `validation_status`

Included consistently across all staging tables:

```text
pending
valid
rejected
```

Required state relationships:

```text
validation_status = 'valid'
→ normalization_status = 'normalized'
```

```text
normalization_status = 'normalization_failed'
→ validation_status <> 'valid'
```

No staging row may remain pending when its import run enters `validated`.

#### `import_outcome`

Included:

```text
inserted
updated
unchanged
missing
retired
reactivated
conflict
skipped
```

The following are not import outcomes:

```text
rejected
unmatched
ambiguous
candidate
confirmed
excluded
unmatched_duplicate_candidate
```

Rejected source records belong to rejection evidence. Mapping classifications belong to mapping-case and observation structures.

`missing` records absence from an authoritative scope and does not change lifecycle state. `retired` and `reactivated` represent explicit lifecycle changes. `conflict` and `skipped` require controlled reason codes.

#### `mapping_observation_result`

Included:

```text
accepted_transition
accepted_support
accepted_more_specific
recorded_weaker
recorded_conflict
recorded_no_change
rejected_transition
```

A rejected transition is preserved evidence. It is not equivalent to a structurally rejected source record.

#### `rejection_stage`

Included:

```text
ingestion
normalization
record_validation
dependency_resolution
run_validation
production_precondition
```

Boundary:

```text
structurally unusable source record
→ rejected_source_records
```

```text
valid entity evaluation blocked by a production conflict
→ import_record_outcomes.outcome_type = conflict
```

#### Explicitly deferred or invalid first-migration values

```text
source_system = combined
run_kind = vertical_slice
source_entity_type = combined
scope_type = vertical_slice
language_code = unknown
language_code = other
finish_code = other
```

New source systems, languages, finishes, currencies, run kinds, scopes, and lifecycle values require an explicit controlled-value review before entering production data.

### Approved first-migration PostgreSQL DDL strategy

#### Database namespace

Use the default PostgreSQL schema:

```text
public
```

Separate PostgreSQL schemas such as `catalogue`, `market`, or `import_control`
are deferred. The first migration expresses domain boundaries through tables,
foreign keys, ownership rules, and restricted write paths.

#### Primary keys

All internal surrogate primary keys use:

```text
bigint GENERATED BY DEFAULT AS IDENTITY
```

Every primary key receives an explicit named primary-key constraint.

External source identifiers remain `text` and retain separate source-scoped
business-identity constraints.

UUID primary keys are not required for the first migration because the MVP is a
single-node deployment without distributed or offline writes.

#### Controlled-value implementation

Use PostgreSQL `text` columns with named `CHECK` constraints for the approved
first-migration controlled values.

Do not use PostgreSQL enum types for the first migration.

Use the following patterns:

```text
CHECK (status IN (...))
```

```text
CHECK (
    value IS NULL
    OR value IN (...)
)
```

Do not create generic lookup tables only to represent the approved small static
value sets.

#### Text integrity

Required technical identifiers use:

```text
CHECK (
    value = btrim(value)
    AND value <> ''
)
```

Required human-readable text uses:

```text
CHECK (btrim(value) <> '')
```

Database constraints do not silently change letter case. Source and application
normalization remain explicit import or application responsibilities.

Source values that appear numeric remain `text` where they are identifiers,
including:

```text
source_product_id
source_expansion_id
collector_number
```

#### Timestamps

All timestamps use:

```text
timestamp with time zone
```

Database-generated processing timestamps use:

```text
DEFAULT CURRENT_TIMESTAMP
```

Source timestamps do not receive database defaults.

`created_at` receives `DEFAULT CURRENT_TIMESTAMP`.

`updated_at` receives `DEFAULT CURRENT_TIMESTAMP` on insert, but the first
migration does not create a generic automatic-update trigger. Merge and
application logic must update `updated_at` only when owned values actually
change. An unchanged repeated import must preserve the existing timestamp.

Append-only tables do not receive `updated_at` unless explicitly required by
the table contract.

#### Deletion and update behavior

Use explicit:

```text
ON UPDATE RESTRICT
ON DELETE RESTRICT
```

for production, market, mapping, import-evidence, staging, price, and wishlist
relationships.

Do not use `ON DELETE CASCADE` in the first migration.

Staging cleanup, wishlist removal, and other intentional deletion workflows use
explicit statements rather than referential cascades.

Optional provenance references also remain restrictive when the referenced row
is preserved audit evidence.

#### Lifecycle checks

For tables using:

```text
is_active
retired_at
```

enforce:

```text
CHECK (
    (is_active = true AND retired_at IS NULL)
    OR
    (is_active = false AND retired_at IS NOT NULL)
)
```

For mapping rows using:

```text
is_active
superseded_at
```

enforce the equivalent rule:

```text
CHECK (
    (is_active = true AND superseded_at IS NULL)
    OR
    (is_active = false AND superseded_at IS NOT NULL)
)
```

`is_active` is not nullable.

#### Business uniqueness

Use named `UNIQUE` constraints for unconditional business identities,
including:

```text
(source_system, source_expansion_id)
(source_system, source_card_id)
(source_system, source_product_id)
(card_id, edition_code)
(card_edition_id, language_code, finish_code)
(card_id) on wishlist_items
(run_reference)
```

Do not use empty strings, zero values, `unknown`, or another sentinel to emulate
null-safe uniqueness.

#### Null-safe and scope-dependent uniqueness

Use partial unique indexes when the valid identity depends on
`confirmation_scope` or active lifecycle state.

Use separate scope-specific unique indexes where required:

```text
WHERE confirmation_scope = 'card'
```

```text
WHERE confirmation_scope = 'edition'
```

```text
WHERE confirmation_scope = 'variant'
```

Do not use `NULLS NOT DISTINCT` in the first migration. Scope-specific partial
indexes express the mapping rules more clearly and avoid treating unrelated null
combinations as equivalent.

#### Scope-specific mapping checks

For card scope require:

```text
confirmation_scope = 'card'
card_id IS NOT NULL
card_edition_id IS NULL
card_variant_id IS NULL
```

For edition scope require:

```text
confirmation_scope = 'edition'
card_id IS NOT NULL
card_edition_id IS NOT NULL
card_variant_id IS NULL
```

For variant scope require:

```text
confirmation_scope = 'variant'
card_id IS NOT NULL
card_edition_id IS NOT NULL
card_variant_id IS NOT NULL
```

Non-confirmed mapping cases may retain less-specific or null target projections
only where the unresolved-state contract explicitly allows them.

#### Composite hierarchy foreign keys

Create supporting unique constraints for:

```text
card_editions (card_edition_id, card_id)
```

```text
card_variants (card_variant_id, card_edition_id, card_id)
```

Mapping structures then use composite foreign keys such as:

```text
(card_edition_id, card_id)
→ card_editions (card_edition_id, card_id)
```

```text
(card_variant_id, card_edition_id, card_id)
→ card_variants (
    card_variant_id,
    card_edition_id,
    card_id
)
```

This prevents a mapping row from combining a card, edition, and variant from
different catalogue hierarchy branches.

#### Active-row uniqueness

Use partial unique indexes to enforce current active state while preserving
history.

Required active mapping guarantees include:

```text
UNIQUE (market_product_id)
WHERE is_active = true
```

and, where required by the mapping-case contract:

```text
UNIQUE (card_market_mapping_case_id)
WHERE is_active = true
```

Superseded historical rows remain outside these active-row uniqueness rules.

#### Price snapshot constraints

Use the unconditional identity:

```text
UNIQUE (
    market_product_id,
    source_snapshot_at
)
```

Currency is not part of snapshot identity. A repeated product and source
timestamp with conflicting currency or price values is a conflict rather than a
new snapshot.

Price columns use:

```text
numeric(12, 4)
```

Required checks include:

```text
avg30 IS NULL OR avg30 >= 0
```

```text
avg30_holo IS NULL OR avg30_holo >= 0
```

```text
avg30 IS NOT NULL OR avg30_holo IS NOT NULL
```

```text
currency_code = 'EUR'
```

#### JSON storage

Raw source payloads and structured evidence use:

```text
jsonb
```

Do not create GIN indexes on raw payload columns without a demonstrated query
requirement.

#### Numeric and quantity checks

`wishlist_items.quantity` uses:

```text
integer NOT NULL DEFAULT 1
CHECK (quantity > 0)
```

No upper limit is introduced in the first migration.

Expansion totals use non-negative checks:

```text
printed_total IS NULL OR printed_total >= 0
```

```text
total IS NULL OR total >= 0
```

When both are present, enforce:

```text
printed_total IS NULL
OR total IS NULL
OR total >= printed_total
```

#### Index policy

Create indexes only when they support an accepted integrity rule or a known
first-MVP access pattern.

Required categories are:

- primary-key indexes;
- unique-constraint indexes;
- partial unique indexes;
- child-side foreign-key indexes for expected joins and restrictive parent
  operations;
- indexes required by executable validation queries;
- indexes required by current catalogue, Wishlist, staging-processing, and
  current-price access paths.

Do not create standalone indexes for every status, boolean, or timestamp.

For composite indexes, order equality-filter columns before range or ordering
columns.

A representative staging-processing index is:

```text
(import_run_id, validation_status)
```

#### Naming convention

Use lowercase `snake_case` PostgreSQL identifiers.

Constraint names use:

```text
pk_<table>
fk_<table>__<referenced_table>
uq_<table>__<business_key>
ck_<table>__<rule>
```

Index names use:

```text
ix_<table>__<columns_or_purpose>
ux_<table>__<columns_or_purpose>
```

Representative names include:

```text
pk_cards
fk_cards__expansions
uq_cards__source_identity
ck_cards__active_retirement
ux_card_market_product_mappings__active_product
ix_staging_cards__run_validation
```

Use a concise business-rule name when listing every indexed column would create
an unreadable or excessively long identifier.

#### DDL execution strategy

Each migration file:

- executes inside a transaction where the selected migration tool supports it;
- creates tables before adding the cycle-breaking foreign key;
- creates supporting unique constraints before dependent composite foreign
  keys;
- does not use `CREATE ... IF NOT EXISTS`;
- does not use `DROP ... IF EXISTS`;
- fails when the actual schema state differs from the expected migration state;
- does not mix destructive data cleanup with schema creation;
- does not contain production import logic, except for separately approved
  bootstrap reference rows.

The dependency cycle between `card_market_mapping_cases` and
`mapping_case_observations` is resolved through the documented later
`ALTER TABLE` step.

#### Cross-row invariants

Ordinary foreign keys, unique constraints, partial unique indexes, and `CHECK`
constraints enforce row-local and key-based integrity.

The following cross-row invariants remain transactional application and
executable reconciliation-query responsibilities:

- a confirmed case has exactly one compatible active mapping;
- a non-confirmed case has no active mapping;
- the case projection matches the latest accepted status history;
- candidate state, case projection, history, and production mapping change
  atomically;
- all staging rows are terminal before a run becomes validated;
- summary counts reconcile before success;
- no false permanent evidence survives a rolled-back merge.

Deferred database constraint triggers may be considered later but are not
required for the first migration.

### Approved global migration order

The first migration uses the following dependency-safe order:

```text
1. expansions
2. expansion_source_identifiers
3. cards
4. card_editions
5. card_variants
6. market_products
7. wishlist_items
8. import_runs
9. staging_cards
10. staging_market_products
11. staging_market_prices
12. staging_market_mappings
13. import_record_outcomes
14. rejected_source_records
15. rejected_source_record_reasons
16. card_market_mapping_cases
17. mapping_case_observations
18. add card_market_mapping_cases.status_source_observation_id foreign key
19. mapping_candidates
20. mapping_status_history
21. card_market_product_mappings
22. market_price_snapshots
```

The model still contains `21` physical tables.

Step `18` is an `ALTER TABLE` operation used to resolve the mapping-case and observation dependency cycle.

Supporting unique constraints required by later composite foreign keys must be created with their parent tables before dependent foreign keys are added. In particular:

- `card_editions` creates its hierarchy-supporting composite unique key before any edition-target foreign key;
- `card_variants` creates its hierarchy-supporting composite unique key before any variant-target foreign key;
- `card_market_mapping_cases` creates `UNIQUE (mapping_case_id, market_product_id)` before the confirmed-mapping table;
- `mapping_case_observations` creates `UNIQUE (mapping_case_observation_id, mapping_case_id)` before candidate and history compatibility foreign keys.

The order is approved for first-migration authoring. The later migration-tooling decision may change file grouping, but it must not change this dependency order without a new review.

### Proposed migration file sequence

A practical migration sequence may be split as:

```text
001_create_catalogue_tables.sql
002_create_market_product_table.sql
003_create_wishlist_table.sql
004_create_import_control_tables.sql
005_create_staging_tables.sql
006_create_import_audit_tables.sql
007_create_mapping_review_tables.sql
008_add_mapping_cycle_constraints.sql
009_create_confirmed_mapping_table.sql
010_create_market_price_snapshot_table.sql
011_create_derived_views.sql
012_add_validation_queries.sql
```

The exact naming convention should match the selected migration framework.

### Required derived views

#### Canonical card current prices

Proposed view:

```text
canonical_card_current_prices
```

Required behavior:

- one row per priced canonical card;
- variant-level mappings only;
- language `en` or `de`;
- complete active ancestry;
- active market product;
- latest succeeded-run snapshot per product;
- `avg30` only;
- EUR only;
- minimum grouped by `card_id`;
- no row or null price when no eligible value exists.

Suggested output:

```text
card_id
from_price
currency_code
eligible_product_count
priced_variant_count
latest_source_snapshot_at
```

#### Catalogue view

Root:

```text
cards
```

Default lifecycle filters:

```text
cards.is_active = true
expansions.is_active = true
```

Wishlist membership and current price are optional joins.

#### Wishlist view

Root:

```text
wishlist_items
```

Joins:

```text
cards
expansions
LEFT JOIN canonical_card_current_prices
```

Do not filter out inactive cards or expansions when doing so would hide a saved wishlist row.

Expose lifecycle state instead.

### Required validation suite

#### Schema validation

Confirm:

- all primary keys generate correctly;
- all required foreign keys reject invalid references;
- all restrictive deletions work;
- all controlled-value checks work;
- lifecycle checks work;
- partial unique indexes work;
- composite hierarchy foreign keys work;
- mapping-case/product compatibility works;
- observation/case compatibility works;
- source-scoped identities remain unique.

#### Primal Clash catalogue validation

Confirm:

```text
164 canonical cards
```

All cards resolve through:

```text
pokemon_tcg_data / xy5
```

to the bootstrapped Primal Clash expansion.

#### Cardmarket product validation

Confirm:

- all accepted in-scope products are preserved;
- four Online Code Card products remain valid products with excluded mapping cases;
- six duplicate-like products remain valid products with `unmatched_duplicate_candidate` cases;
- unresolved products create no production mapping;
- source product IDs remain text;
- metaproduct IDs are not unique product identities.

#### Mapping validation

Confirm:

- `167` accepted direct product relationships are represented at the most specific evidence-supported scope;
- insufficient evidence creates no edition or variant;
- one product has at most one active mapping;
- case state and active mapping reconcile;
- superseded mappings remain historical;
- weaker observations do not demote confirmed state;
- one observation creates at most one accepted transition;
- transition sequence is continuous per case.

#### Price validation

Confirm:

- snapshots are append-only;
- repeated identical price imports create no duplicates;
- conflicting same-timestamp values do not overwrite history;
- only succeeded-run snapshots are eligible;
- only the latest snapshot per product is selected;
- only `avg30` contributes;
- `avg30_holo` does not contribute;
- only EUR contributes;
- only active English or German variant-level mappings contribute;
- excluded and duplicate-candidate products do not contribute;
- no eligible price returns null rather than zero.

#### Wishlist validation

Confirm:

- one wishlist item per card;
- quantity is at least one;
- quantity and notes survive every import type;
- card retirement preserves the wishlist row;
- unpriced cards remain visible;
- deleting a wishlist row does not affect catalogue data;
- deleting a referenced card is restricted;
- export returns one row per wishlist item;
- export does not omit retired or unpriced cards.

#### Repeat-import validation

Run the complete Primal Clash sequence twice.

The second sequence must:

- create new import-run records;
- create new staging and permitted observation evidence;
- create no duplicate production expansions;
- create no duplicate cards;
- create no duplicate market products;
- create no duplicate editions or variants;
- create no duplicate active mappings;
- create no duplicate same-timestamp price snapshots;
- preserve unchanged production `updated_at` values;
- preserve all wishlist data.

#### Rollback validation

Force failures during:

- catalogue merge;
- market-product merge;
- mapping transition;
- price-snapshot insertion.

After rollback:

- production state matches the pre-run state;
- no partial mapping transition remains;
- no false status-history row remains;
- no false production outcome remains;
- no partial price snapshot remains;
- wishlist data remains unchanged;
- the run reaches `merge_failed`;
- staging and failure evidence remain available.

### Approved executable validation query contract

The first-migration validation suite uses two complementary check classes:

```text
read_only_query
transactional_test
```

A read-only validation query must return exactly one row with this shape:

```text
check_id text
actual_value bigint or text
expected_value bigint or text
passed boolean
detail text
```

For count-based invariant checks, success normally means:

```text
actual_value = 0
expected_value = 0
passed = true
```

For fixture-count checks, `expected_value` is the documented Primal Clash
count.

A validation runner must fail when:

- a query returns no row;
- a query returns more than one row;
- `passed` is not `true`;
- the query raises an error;
- the check identifier is missing or duplicated in one validation run.

Validation queries are read-only and must not repair data.

Transactional tests may create temporary fixture rows inside an explicit test
transaction. Each transactional test must roll back its fixture data after
asserting the expected database behavior.

#### Validation severity

Each check has one of these severities:

```text
critical
warning
```

A `critical` failure blocks migration acceptance, import acceptance, or release
validation as applicable.

A `warning` records a review item but does not by itself prove physical
corruption. The first migration uses `critical` for every check listed below
unless a later section explicitly marks it as `warning`.

#### Schema and relationship checks

##### `schema.source_identity_duplicates`

Purpose: detect duplicate source-scoped identities in production tables.

Executable pattern:

```sql
WITH violations AS (
    SELECT source_system, source_card_id
    FROM cards
    GROUP BY source_system, source_card_id
    HAVING count(*) > 1
)
SELECT
    'schema.source_identity_duplicates' AS check_id,
    count(*)::bigint AS actual_value,
    0::bigint AS expected_value,
    count(*) = 0 AS passed,
    'Duplicate canonical-card source identities' AS detail
FROM violations;
```

Equivalent checks are required for:

```text
expansion_source_identifiers
market_products
```

##### `schema.invalid_catalogue_hierarchy`

Purpose: confirm that edition and variant ancestry is internally consistent.

```sql
WITH violations AS (
    SELECT v.card_variant_id
    FROM card_variants AS v
    JOIN card_editions AS e
      ON e.card_edition_id = v.card_edition_id
    WHERE v.card_id <> e.card_id
)
SELECT
    'schema.invalid_catalogue_hierarchy' AS check_id,
    count(*)::bigint AS actual_value,
    0::bigint AS expected_value,
    count(*) = 0 AS passed,
    'Variant card_id must match its edition card_id' AS detail
FROM violations;
```

##### `schema.invalid_mapping_hierarchy`

Purpose: confirm that active mapping targets belong to one compatible card,
edition, and variant branch.

```sql
WITH violations AS (
    SELECT m.card_market_product_mapping_id
    FROM card_market_product_mappings AS m
    LEFT JOIN card_editions AS e
      ON e.card_edition_id = m.card_edition_id
    LEFT JOIN card_variants AS v
      ON v.card_variant_id = m.card_variant_id
    WHERE
        (m.confirmation_scope IN ('edition', 'variant')
         AND e.card_id IS DISTINCT FROM m.card_id)
        OR
        (m.confirmation_scope = 'variant'
         AND (v.card_id IS DISTINCT FROM m.card_id
              OR v.card_edition_id IS DISTINCT FROM m.card_edition_id))
)
SELECT
    'schema.invalid_mapping_hierarchy' AS check_id,
    count(*)::bigint AS actual_value,
    0::bigint AS expected_value,
    count(*) = 0 AS passed,
    'Mapping targets must form one catalogue hierarchy branch' AS detail
FROM violations;
```

##### `schema.multiple_active_mappings_per_product`

```sql
WITH violations AS (
    SELECT market_product_id
    FROM card_market_product_mappings
    WHERE is_active = true
    GROUP BY market_product_id
    HAVING count(*) > 1
)
SELECT
    'schema.multiple_active_mappings_per_product' AS check_id,
    count(*)::bigint AS actual_value,
    0::bigint AS expected_value,
    count(*) = 0 AS passed,
    'One market product may have at most one active mapping' AS detail
FROM violations;
```

##### `schema.invalid_lifecycle_pairs`

The suite must run equivalent zero-violation queries for every table using:

```text
is_active / retired_at
is_active / superseded_at
```

The check fails when an active row has a retirement or supersession timestamp,
or when an inactive row lacks the required timestamp.

#### Mapping lifecycle checks

##### `mapping.case_active_mapping_reconciliation`

```sql
WITH violations AS (
    SELECT c.mapping_case_id
    FROM card_market_mapping_cases AS c
    LEFT JOIN card_market_product_mappings AS m
      ON m.mapping_case_id = c.mapping_case_id
     AND m.is_active = true
    GROUP BY c.mapping_case_id, c.mapping_status
    HAVING
        (c.mapping_status = 'confirmed' AND count(m.card_market_product_mapping_id) <> 1)
        OR
        (c.mapping_status <> 'confirmed' AND count(m.card_market_product_mapping_id) <> 0)
)
SELECT
    'mapping.case_active_mapping_reconciliation' AS check_id,
    count(*)::bigint AS actual_value,
    0::bigint AS expected_value,
    count(*) = 0 AS passed,
    'Confirmed cases require one active mapping; other cases require none' AS detail
FROM violations;
```

##### `mapping.case_projection_matches_history`

The latest accepted `mapping_status_history` row per case must match the current
case projection.

```sql
WITH latest_history AS (
    SELECT DISTINCT ON (mapping_case_id)
        mapping_case_id,
        to_status,
        confirmation_scope,
        card_id,
        card_edition_id,
        card_variant_id
    FROM mapping_status_history
    ORDER BY mapping_case_id, transition_sequence DESC
), violations AS (
    SELECT c.mapping_case_id
    FROM card_market_mapping_cases AS c
    LEFT JOIN latest_history AS h
      ON h.mapping_case_id = c.mapping_case_id
    WHERE h.mapping_case_id IS NULL
       OR h.to_status IS DISTINCT FROM c.mapping_status
       OR h.confirmation_scope IS DISTINCT FROM c.confirmation_scope
       OR h.card_id IS DISTINCT FROM c.card_id
       OR h.card_edition_id IS DISTINCT FROM c.card_edition_id
       OR h.card_variant_id IS DISTINCT FROM c.card_variant_id
)
SELECT
    'mapping.case_projection_matches_history' AS check_id,
    count(*)::bigint AS actual_value,
    0::bigint AS expected_value,
    count(*) = 0 AS passed,
    'Current case projection must match latest accepted history' AS detail
FROM violations;
```

##### `mapping.transition_sequence_gaps`

```sql
WITH ordered AS (
    SELECT
        mapping_case_id,
        transition_sequence,
        row_number() OVER (
            PARTITION BY mapping_case_id
            ORDER BY transition_sequence
        ) AS expected_sequence
    FROM mapping_status_history
), violations AS (
    SELECT mapping_case_id, transition_sequence
    FROM ordered
    WHERE transition_sequence <> expected_sequence
)
SELECT
    'mapping.transition_sequence_gaps' AS check_id,
    count(*)::bigint AS actual_value,
    0::bigint AS expected_value,
    count(*) = 0 AS passed,
    'Transition sequence must be continuous from one per mapping case' AS detail
FROM violations;
```

##### `mapping.multiple_accepted_transitions_per_observation`

The check counts observations referenced by more than one accepted status
transition. Expected result: zero.

#### Price-path checks

##### `price.latest_eligible_snapshot_per_product`

The canonical price implementation must select exactly one latest eligible
snapshot per market product by:

```text
source_snapshot_at DESC
market_price_snapshot_id DESC
```

and only from `succeeded` import runs.

A reconciliation query must compare the product IDs and selected snapshot IDs
from the production price view/query against an independently calculated
`row_number()` result. Expected mismatch count: zero.

##### `price.ineligible_rows_contribute`

The query must count rows contributing to the canonical price despite any of
the following:

- inactive expansion;
- inactive card;
- inactive edition;
- inactive variant;
- inactive mapping;
- inactive market product;
- non-variant confirmation scope;
- language outside `en` and `de`;
- currency outside `EUR`;
- failed or non-succeeded import run;
- null `avg30`;
- excluded mapping case;
- `unmatched_duplicate_candidate` mapping case.

Expected result: zero.

##### `price.avg30_holo_only_contributes`

Count products whose selected eligible snapshot has null `avg30`, non-null
`avg30_holo`, and still contributes a canonical price. Expected result: zero.

##### `price.card_minimum_mismatch`

For every priced card, compare the exposed `from_price` with an independently
calculated:

```text
MIN(latest eligible avg30)
```

Expected mismatch count: zero.

##### `price.unpriced_card_returns_zero`

Count catalogue or wishlist rows where no eligible price exists but the exposed
price equals numeric zero instead of null. Expected result: zero.

#### Primal Clash fixture checks

##### `fixture.primal_clash_card_count`

```sql
SELECT
    'fixture.primal_clash_card_count' AS check_id,
    count(*)::bigint AS actual_value,
    164::bigint AS expected_value,
    count(*) = 164 AS passed,
    'Canonical cards resolved through pokemon_tcg_data / xy5' AS detail
FROM cards AS c
JOIN expansion_source_identifiers AS esi
  ON esi.expansion_id = c.expansion_id
WHERE esi.source_system = 'pokemon_tcg_data'
  AND esi.source_expansion_id = 'xy5';
```

##### `fixture.primal_clash_confirmed_mapping_count`

Expected result:

```text
167
```

The query counts active confirmed mapping cases backed by accepted direct source
identifier evidence for the Primal Clash scope.

##### `fixture.primal_clash_excluded_count`

Expected result:

```text
4
```

The query counts Primal Clash cases with:

```text
mapping_status = excluded
```

and the controlled Online Code Card exclusion reason.

##### `fixture.primal_clash_duplicate_candidate_count`

Expected result:

```text
6
```

The query counts Primal Clash cases with:

```text
mapping_status = unmatched_duplicate_candidate
```

##### `fixture.primal_clash_ordinary_unresolved_count`

Count Primal Clash cases with:

```text
candidate
unmatched
ambiguous
```

Expected result:

```text
0
```

#### Wishlist and export checks

##### `wishlist.duplicate_items`

Count cards with more than one wishlist row. Expected result: zero.

##### `wishlist.invalid_quantity`

Count rows where quantity is null or less than one. Expected result: zero.

##### `wishlist.orphan_items`

Count wishlist rows without a canonical card. Expected result: zero.

##### `wishlist.export_row_count_mismatch`

Compare:

```text
count(wishlist_items)
```

with the row count returned by the approved wishlist export query.

Expected difference: zero.

The export query must retain retired and unpriced wishlist cards and must not
multiply one wishlist item through market-product joins.

##### `wishlist.export_contains_singular_market_identity`

The first-migration export contract must not expose an arbitrary single variant,
language, finish, or market-product identifier for a canonical-card wishlist
item.

This check is implemented as an approved-column-list test against the export
view or query definition.

#### Import-run and staging checks

##### `import.nonterminal_staging_in_validated_runs`

Count staging rows with pending normalization or validation status whose parent
run is `validated`, `merge_started`, or `succeeded`.

Expected result: zero.

##### `import.invalid_run_status_order`

Count runs whose timestamps or recorded transitions prove an impossible status
order, including success before merge completion or merge start before
validation completion.

Expected result: zero.

##### `import.summary_reconciliation_mismatch`

For each succeeded run, compare stored summary counts with the detailed staging,
outcome, rejection, mapping, and snapshot evidence applicable to its `run_kind`.

Expected mismatch count: zero.

##### `import.duplicate_effective_outcomes`

Count more than one effective production outcome for the same entity and import
run under the approved outcome identity rules.

Expected result: zero.

##### `import.invalid_outcome_payload`

Count outcomes violating their type-specific contract, including:

- `updated` without a non-empty change summary;
- `unchanged` with changed fields;
- `missing` without an existing production entity;
- `conflict` without a reason code;
- `skipped` without a reason code.

Expected result: zero.

##### `import.rejection_reasonless_records`

Count rejected records without at least one controlled rejection reason.

Expected result: zero.

#### Repeat-import transactional test contract

The complete Primal Clash sequence is executed twice against the same database.

The second sequence must assert:

```text
new import_runs > 0
new production expansions = 0
new production cards = 0
new production market products = 0
new production editions = 0
new production variants = 0
new active mappings = 0
new duplicate same-timestamp snapshots = 0
updated production rows = 0
changed wishlist rows = 0
```

Permitted new evidence includes:

```text
import_runs
staging rows
unchanged outcomes
new observations that do not duplicate prohibited effective evidence
```

The test must compare pre-run and post-run snapshots of all wishlist rows,
including `quantity`, `notes`, `created_at`, and `updated_at`.

#### Rollback transactional test contract

Force one failure in each production merge category:

```text
catalogue merge
market-product merge
mapping transition
price-snapshot insertion
```

For each forced failure:

- capture a pre-transaction checksum or deterministic row snapshot;
- begin the production merge transaction;
- perform at least one valid change before the forced error;
- force the error;
- roll back;
- compare production and wishlist state with the pre-transaction snapshot;
- verify that the run reaches `merge_failed` outside the rolled-back production
  transaction;
- verify that staging and validation evidence remain available;
- verify that no false production outcome, status-history row, mapping, or price
  snapshot remains.

Every comparison must pass exactly.

#### Constraint-behavior transactional tests

The suite must explicitly attempt and reject:

- duplicate source-scoped card identity;
- duplicate source-scoped market-product identity;
- duplicate wishlist item for one card;
- quantity zero;
- negative quantity;
- unsupported controlled values;
- invalid lifecycle pairs;
- incompatible edition/card composite reference;
- incompatible variant/edition/card composite reference;
- second active mapping for one market product;
- deletion of a referenced expansion;
- deletion of a referenced card;
- deletion of an import run with retained evidence.

Each test passes only when PostgreSQL rejects the statement with the expected
constraint class and the surrounding test transaction remains recoverable.

#### Validation execution order

Run validation in this order:

```text
1. schema and constraint-behavior tests
2. catalogue hierarchy queries
3. mapping lifecycle queries
4. import-run and staging queries
5. price-path queries
6. wishlist and export queries
7. Primal Clash fixture-count queries
8. repeat-import tests
9. rollback tests
```

A later check must not be used to hide or compensate for an earlier failure.

#### Validation evidence

Each validation execution must preserve:

```text
validation run reference
repository commit or release identifier
PostgreSQL version
migration version
fixture version or checksum
check_id
severity
actual_value
expected_value
passed
execution timestamp
failure detail
```

The evidence must contain no secrets or raw credentials.

#### Validation acceptance rule

The first migration validation is accepted only when:

```text
all required checks executed
all check identifiers are unique
all critical checks passed
Primal Clash fixture counts match
repeat-import tests passed
rollback tests passed
```

Warnings, when introduced later, must be listed explicitly and may not be
silently treated as passing critical checks.

### Approved migration tooling and file convention

#### Selected tool

Use `dbmate` as the first-migration execution tool.

The selection is based on the following project requirements:

- migrations remain explicit PostgreSQL SQL rather than ORM-generated code;
- the tool is framework-independent and does not require SQLAlchemy or an
  application runtime;
- each PostgreSQL migration runs atomically inside a transaction by default;
- applied versions are recorded in a dedicated migration-history table;
- the tool is available as a small standalone binary and as a Docker image;
- migration status, strict ordering, rollback, waiting for PostgreSQL, and
  schema dumping are supported without a custom migration runner.

The first implementation must pin an explicit `dbmate` release or container
image digest. The project must not depend on an unpinned `latest` image in CI or
production.

#### Alternatives not selected

`Alembic` is not selected because the project does not currently use
SQLAlchemy models, and adding SQLAlchemy migration infrastructure would create
an unnecessary ORM-shaped dependency around a deliberately SQL-first schema.

`Flyway` is not selected because its broader runtime and configuration surface
are unnecessary for the single-database MVP. Its versioned SQL model remains a
valid future alternative if deployment or team requirements change.

A custom `psql` migration runner is not selected because recreating migration
history, ordering, failure handling, and status inspection would add avoidable
project-specific code.

#### Repository layout

Use the following database artifact layout:

```text
db/
├── migrations/
├── validation/
├── fixtures/
└── schema.sql
```

Responsibilities:

- `db/migrations/` contains immutable versioned schema migrations;
- `db/validation/` contains executable read-only validation queries and
  transactional test scripts;
- `db/fixtures/` contains database-specific synthetic or vertical-slice loading
  helpers that are not production migrations;
- `db/schema.sql` is generated by `dbmate` and committed for schema review;
- `db/schema.sql` must not be edited manually and is not the authoritative
  migration history.

Existing source fixtures under `data/fixtures/` remain source-data evidence.
They must not be duplicated into `db/fixtures/` unless a database-specific test
representation is required.

#### Migration file naming

Use the `dbmate` format:

```text
<UTC timestamp>_<imperative_snake_case_description>.sql
```

The timestamp format is:

```text
YYYYMMDDHHMMSS
```

Example:

```text
20260728120000_create_catalogue_foundation.sql
```

Naming rules:

- generate timestamps in UTC;
- use lowercase ASCII `snake_case`;
- begin descriptions with an imperative verb such as `create`, `add`,
  `enforce`, `backfill`, `retire`, or `remove`;
- describe one cohesive schema change;
- do not use issue numbers as the only description;
- do not rename the numeric version after the migration is shared or applied;
- never create two files with the same leading numeric version.

#### Migration file structure

Every migration file must contain both directives:

```sql
-- migrate:up

-- migrate:down
```

Rules:

- `migrate:up` is mandatory and contains the authoritative forward change;
- the default transaction behavior remains enabled;
- `transaction:false` is prohibited unless a PostgreSQL statement cannot run in
  a transaction and the exception is documented and reviewed;
- `migrate:down` is implemented only when reversal is safe, deterministic, and
  validated;
- an unsafe rollback section remains intentionally empty with an explanatory SQL
  comment rather than containing destructive best-effort SQL;
- production recovery may use forward-fix migrations or backup restoration when
  a safe automatic down migration does not exist.

The initial catalogue-foundation migration must have a tested down section
because it creates new empty schema objects and can be reversed safely before
production data is loaded.

#### Execution convention

Use:

```text
dbmate --strict migrate
```

for applying pending migrations to an existing database.

Use `dbmate up` only in explicitly approved local or disposable environments
where database creation by the migration user is intended. Production and the
Raspberry Pi deployment must use a pre-created database and `dbmate migrate`.

Required execution rules:

- provide the connection through `DATABASE_URL`;
- keep credentials outside the repository;
- use `--strict` so an out-of-order migration fails;
- run `dbmate status --exit-code` in validation and deployment checks;
- run migrations before NocoDB is allowed to use a newly expected schema;
- stop deployment when migration or validation fails;
- do not grant the ordinary NocoDB connection role schema-owner privileges;
- use a dedicated migration role or controlled administrative connection;
- preserve command output as implementation evidence without exposing secrets.

The migration-history table remains:

```text
public.schema_migrations
```

The table is tool-owned and must not be modified manually.

#### Schema dump convention

After every successful migration or rollback in development and CI:

```text
dbmate dump
```

must regenerate:

```text
db/schema.sql
```

The generated schema must be committed when it changes. CI must fail when:

- migrations cannot be applied to a clean PostgreSQL database;
- strict migration status fails;
- the regenerated `db/schema.sql` differs from the committed file;
- executable validation checks fail.

The PostgreSQL client used for the dump must be compatible with the database
server version.

#### Migration immutability

After a migration has been merged to the default branch or applied to a shared
environment:

- do not edit its SQL;
- do not reuse its version;
- do not reorder it;
- correct mistakes through a new forward migration;
- preserve the original migration and validation evidence.

Before merge, a migration may be replaced only when it has not been applied to
any shared environment and the pull request evidence is regenerated.

#### Initial migration decomposition

The first schema implementation should follow the approved global migration
order through cohesive files rather than one file per table. The initial planned
sequence is:

```text
1. create_catalogue_foundation
2. create_import_control
3. create_market_and_mapping_lifecycle
4. create_wishlist
5. add_cycle_breaking_mapping_foreign_key
6. create_runtime_views
```

The exact number of files may change during implementation when transaction or
review boundaries require it, but table dependencies and the approved global
order must not be bypassed.

Bootstrap data, source fixture loading, and production import logic must not be
hidden inside schema migrations unless the row is required for schema integrity
and has been explicitly approved as migration-owned reference data.

#### Validation of the tooling decision

Before the first migration is considered implemented, validate that:

- the pinned `dbmate` version runs on the development environment and target
  Raspberry Pi architecture, directly or through the approved container;
- a clean PostgreSQL database accepts all migrations in strict order;
- a second migration run applies zero migrations;
- `dbmate status --exit-code` succeeds;
- the safe initial rollback works in a disposable database;
- reapplying after rollback recreates the same schema;
- `db/schema.sql` is reproducible;
- the approved validation suite passes;
- migration failure leaves no partial schema change;
- logs and committed artifacts contain no credentials.

### Remaining real blockers

No migration-readiness blockers remain.

The exact first-migration controlled-value registry, PostgreSQL DDL strategy,
global migration order, executable validation query contract, and migration
tooling and file convention are approved.

### Resolved items

```text
exact first-migration controlled-value registry
```

```text
exact first-migration PostgreSQL DDL strategy
```

```text
approved global migration order
```

```text
approved executable validation query contract
```

```text
approved migration tooling and file convention
```

The following are no longer blockers:

```text
initial table inventory
```

```text
canonical card versus market-product identity
```

```text
canonical card → edition → variant hierarchy
```

```text
wishlist target level
```

```text
market-product mapping target scopes
```

```text
unresolved mapping preservation
```

```text
duplicate-candidate handling
```

```text
English/German price eligibility
```

```text
avg30 versus avg30_holo for MVP pricing
```

```text
EUR-only MVP pricing
```

```text
latest snapshot selection per product
```

```text
separate import runs
```

```text
staging and production transaction boundary
```

```text
wishlist/import ownership isolation
```

```text
retired and unpriced Wishlist visibility
```

```text
canonical export root and price null semantics
```

### Migration gate

All documented migration-readiness conditions are satisfied.

```text
Migration readiness: Approved
Migration status: Implemented and locally validated
```

The approved migration design has been implemented as `17` incremental dbmate migrations rather than one monolithic SQL file.

Local validation completed on 2026-07-29 confirmed:

- `21` project tables and `22` total tables including `schema_migrations`;
- `17` applied migrations and `0` pending migrations;
- successful rollback and reapplication of each migration or migration package;
- expected primary keys, foreign keys, unique constraints, check constraints, and indexes;
- source-scoped uniqueness for cards and market products;
- mapping-case and active-mapping cardinality rules;
- hierarchy consistency across cards, editions, variants, and mappings;
- append-only price-snapshot identity and production price constraints;
- compatibility of price snapshots with successful `market_prices` import runs;
- wishlist isolation from catalogue, market-product, variant, and price fields.

The permanent executable validation is stored at:

```text
scripts/database/validate_schema.sql
```

The validation completed successfully with:

```text
schema validation passed
```

The next concrete task is to prepare and validate the controlled Primal Clash bootstrap and first import path without changing the accepted schema boundaries.
