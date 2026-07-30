# Primal Clash Source-to-Target Mapping

## Status

Partially implemented and validated.

## Controlled Slice

The first controlled import slice covers canonical Primal Clash card records only.

```text
data/fixtures/primal-clash/canonical-cards.json
→ import_runs
→ staging_cards
```

This slice validates source ingestion, normalization, record-level validation, image-reference extraction, source-count reconciliation, and staging uniqueness.

UNIQUE (import_run_id, source_record_reference)

It does not perform a production merge and must not modify `expansions`, `expansion_source_identifiers`, `cards`, market-data tables, mapping tables, price tables, or `wishlist_items`.

## Source Artifact

| Property               | Value                                             |
| ---------------------- | ------------------------------------------------- |
| Path                   | `data/fixtures/primal-clash/canonical-cards.json` |
| Source system          | `pokemon_tcg_data`                                |
| Source expansion ID    | `xy5`                                             |
| Expected record count  | `164`                                             |
| Record collection      | `records`                                         |
| Source record identity | `records[].id`                                    |

The source artifact uses the following envelope:

| Source field   | Expected value or role             |
| -------------- | ---------------------------------- |
| `sourceFile`   | Original source artifact reference |
| `sourceSystem` | Catalogue source identifier        |
| `setId`        | Source-scoped expansion identifier |
| `recordCount`  | Declared number of records         |
| `records`      | Canonical-card source records      |

The importer must reject the complete run before staging when:

* the top-level payload is not a JSON object;
* `records` is not a JSON array;
* `recordCount` is not an integer;
* `recordCount` does not equal the number of elements in `records`;
* `sourceSystem` is missing or unsupported;
* `setId` is missing or does not match the controlled import scope.

## Source-to-Staging Field Mapping

| Source field                                | Normalization rule                                                                                      | `staging_cards` target    |           Required for valid record | Validation failure                                             |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------- | ----------------------------------: | -------------------------------------------------------------- |
| Import context                              | Parent `import_runs.import_run_id`                                                                      | `import_run_id`           |                                 Yes | Importer error; staging must stop                              |
| `records[].id` plus stable artifact context | Build a reproducible reference such as `canonical-cards.json#xy5-1`                                     | `source_record_reference` |                                 Yes | Importer error if no stable reference can be created           |
| Top-level `sourceSystem`                    | Trim surrounding whitespace; require controlled value `pokemon_tcg_data`                                | `source_system`           |                                 Yes | Reject run for unsupported or missing source system            |
| `records[].id`                              | Trim surrounding whitespace; normalize empty string to `null`                                           | `source_card_id`          |                                 Yes | Record validation failure                                      |
| Top-level `setId`                           | Trim surrounding whitespace; normalize empty string to `null`                                           | `source_expansion_id`     |                                 Yes | Record validation failure                                      |
| `records[].number`                          | Convert to text without numeric coercion; trim surrounding whitespace; normalize empty string to `null` | `collector_number`        |                                 Yes | Record validation failure                                      |
| `records[].name`                            | Preserve Unicode text; trim surrounding whitespace; normalize empty string to `null`                    | `name`                    |                                 Yes | Record validation failure                                      |
| `records[].rarity`                          | Preserve source text; trim surrounding whitespace; normalize empty string to `null`                     | `rarity`                  |                                  No | No rejection when absent                                       |
| `records[].images.small`                    | Preserve the HTTPS URL as text; trim surrounding whitespace; normalize empty string to `null`           | `image_small_url`         | Required for this validated fixture | Record validation failure                                      |
| `records[].images.large`                    | Preserve the HTTPS URL as text; trim surrounding whitespace; normalize empty string to `null`           | `image_large_url`         | Required for this validated fixture | Record validation failure                                      |
| Complete `records[]` object                 | Preserve the complete source record without dropping unsupported fields                                 | `raw_payload`             |                                 Yes | Importer error if serialization fails                          |
| Normalized source record | Calculate a deterministic SHA-256 checksum from the documented canonical JSON serialization | `record_checksum` | Required by the Primal Clash importer contract, although nullable in the physical schema | Importer error if checksum generation fails |
| Importer state                              | Set after normalization completes                                                                       | `normalization_status`    |                                 Yes | Must not remain `pending` after normalization                  |
| Validator state                             | Set after record-level validation completes                                                             | `validation_status`       |                                 Yes | Must not remain `pending` after validation                     |
| Validation completion time                  | Set when validation reaches a terminal result                                                           | `validation_completed_at` |           Required after validation | Validation failure if terminal status has no timestamp         |

## Raw Payload Preservation

The complete source record must be stored in `raw_payload`.

For the current fixture, this includes fields that are not projected into dedicated staging columns:

* `supertype`;
* `subtypes`;
* `hp`;
* `types`;
* `evolvesTo`;
* `attacks`;
* `weaknesses`;
* `retreatCost`;
* `convertedRetreatCost`;
* `artist`;
* `flavorText`;
* `nationalPokedexNumbers`;
* `legalities`;
* the complete `images` object.

These fields are preserved as source evidence but are not part of the first production catalogue projection.

The importer must not silently alter, infer, translate, or enrich these values.

## Staging-to-Production Projection

The first dry run does not execute this projection. It documents the later production merge boundary.

| `staging_cards` source                                                                | `cards` target     | Merge rule                                                                                              |
| ------------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------- |
| Resolved normalized expansion identity from `source_system` and `source_expansion_id` | `expansion_id`     | Resolve through `expansion_source_identifiers`; do not create an expansion implicitly during card merge |
| `source_system`                                                                       | `source_system`    | Insert or compare as part of production identity                                                        |
| `source_card_id`                                                                      | `source_card_id`   | Insert or compare as part of production identity                                                        |
| `collector_number`                                                                    | `collector_number` | Insert or update only through the controlled merge                                                      |
| `name`                                                                                | `name`             | Insert or update only through the controlled merge                                                      |
| `rarity`                                                                              | `rarity`           | Insert or update; preserve `null` when unavailable                                                      |
| `image_small_url`                                                                     | `image_small_url`  | Insert or update from validated source metadata                                                         |
| `image_large_url`                                                                     | `image_large_url`  | Insert or update from validated source metadata                                                         |

The production identity is:

```text
(source_system, source_card_id)
```

The first dry run must not resolve `expansion_id` or write any row to `cards`.

## Record-Level Validation Rules

A staged record is valid only when all of the following are true:

* `source_record_reference` is non-empty;
* `source_system` equals `pokemon_tcg_data`;
* `source_card_id` is non-empty;
* `source_expansion_id` equals `xy5`;
* `collector_number` is non-empty;
* `name` is non-empty;
* `raw_payload` is present;
* `image_small_url` is non-empty;
* `image_large_url` is non-empty;
* both image references use HTTPS;
* both image references use the expected `images.pokemontcg.io` host;
* `image_small_url` matches the expected `xy5/<collector-number>.png` pattern;
* `image_large_url` matches the expected `xy5/<collector-number>_hires.png` pattern;
* no duplicate `(import_run_id, source_record_reference)` exists;
* no duplicate valid `(import_run_id, source_system, source_card_id)` exists.

For the validated Primal Clash fixture, the expected result is:

```text
source records: 164
normalized records: 164
valid records: 164
rejected records: 0
missing small image references: 0
missing large image references: 0
duplicate source record references: 0
duplicate source card identities: 0
```

## Dry-Run Isolation

The dry run may modify only:

* `import_runs`;
* `staging_cards`;
* rejected-record tables when an actual invalid source record is encountered.

The following tables must have identical row counts before and after the dry run:

* `expansions`;
* `expansion_source_identifiers`;
* `cards`;
* `card_editions`;
* `card_variants`;
* `market_products`;
* `card_market_product_mappings`;
* `market_price_snapshots`;
* `card_market_mapping_cases`;
* `mapping_case_observations`;
* `mapping_candidates`;
* `mapping_status_history`;
* `wishlist_items`;
* `import_record_outcomes`.

## First Dry-Run Acceptance Criteria

The first controlled slice is accepted when:

* exactly one catalogue import run is created;
* the run scope identifies `pokemon_tcg_data:xy5`;
* the importer reads exactly `164` source records;
* exactly `164` rows are inserted into `staging_cards`;
* every source record is represented once;
* all staging rows belong to the same import run;
* all `164` records reach a valid terminal validation state;
* no staging row remains in `pending` normalization or validation state;
* no rejected source records are created;
* all image references are present and valid;
* run-level counts reconcile with staging and rejection counts;
* no production, market, mapping, price, or wishlist table changes;
* the existing permanent Primal Clash fixture validator continues to pass.

## Source artifact

`data/fixtures/primal-clash/canonical-cards.json`

## Import Run Contract

The first controlled slice creates one `import_runs` record with the following values:

| Column                      | Value                                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------- |
| `run_reference`             | A unique reproducible execution reference, for example `primal-clash-catalogue-dry-run-001` |
| `run_kind`                  | `catalogue`                                                                                 |
| `source_system`             | `pokemon_tcg_data`                                                                          |
| `source_entity_type`        | `card`                                                                                      |
| `source_artifact_reference` | `data/fixtures/primal-clash/canonical-cards.json`                                           |
| `source_artifact_checksum`  | SHA-256 checksum of the complete source artifact                                            |
| `scope_type`                | `expansion`                                                                                 |
| `scope_reference`           | `pokemon_tcg_data:xy5`                                                                      |
| `is_authoritative`          | `true`                                                                                      |
| `importer_version`          | Importer implementation version or repository revision                                      |
| Initial `status`            | `created`                                                                                   |

The controlled dry-run lifecycle is:

```text
created
→ staging_loaded
→ validated
```

The importer must update lifecycle timestamps consistently:

| Status           | Required timestamp state                                                      |
| ---------------- | ----------------------------------------------------------------------------- |
| `created`        | `started_at` populated; later lifecycle timestamps `NULL`                     |
| `staging_loaded` | `staging_loaded_at` populated                                                 |
| `validated`      | `validated_at` populated; `merge_started_at` and `completed_at` remain `NULL` |

`validated` is the successful terminal point of this dry-run workflow, but it is not a terminal database lifecycle status. It indicates that staging validation completed successfully and that the run is eligible for a later merge.

The dry run must not use `succeeded`.

The `succeeded` status is reserved for a completed production merge and requires all import and merge summary counts to be populated.

For a successful dry run, the expected summary is:

| Column                 | Expected value |
| ---------------------- | -------------: |
| `total_source_records` |          `164` |
| `valid_source_records` |          `164` |
| `rejected_records`     |            `0` |
| `inserted_records`     |         `NULL` |
| `updated_records`      |         `NULL` |
| `unchanged_records`    |         `NULL` |
| `missing_records`      |         `NULL` |
| `retired_records`      |         `NULL` |
| `failure_code`         |         `NULL` |
| `failure_detail`       |         `NULL` |

If source or record validation fails, the run must use:

```text
validation_failed
```

A failed validation run must:

* populate `failure_code`;
* optionally populate `failure_detail`;
* populate `completed_at`;
* never populate `merge_started_at`;
* never modify production tables.

## Staging State Contract

Every `staging_cards` row begins with:

```text
normalization_status = pending
validation_status = pending
validation_completed_at = NULL
```

A successfully normalized and validated record ends with:

```text
normalization_status = normalized
validation_status = valid
validation_completed_at = non-null
```

A record that cannot be normalized ends with:

```text
normalization_status = normalization_failed
validation_status = rejected
validation_completed_at = non-null
```

A record that normalizes successfully but fails validation ends with:

```text
normalization_status = normalized
validation_status = rejected
validation_completed_at = non-null
```

A record with `validation_status = valid` must always have:

```text
normalization_status = normalized
```

No row may remain in a `pending` state after the import run reaches `validated` or `validation_failed`.

## Cardmarket Product Import

### Controlled Source Artifact

The next controlled import slice uses:

```text
data/fixtures/primal-clash/cardmarket-products.json
```

The controlled staging path is:

```text
cardmarket-products.json
→ validation and normalization
→ staging_market_products
→ validated staging run
```

The fixture contains exactly `177` Cardmarket product records.

Every record contains all seven confirmed source fields:

| Source field | Role |
| --- | --- |
| `idProduct` | Cardmarket product identifier |
| `idExpansion` | Cardmarket expansion identifier |
| `idMetacard` | Cardmarket metaproduct identifier |
| `idCategory` | Cardmarket category identifier |
| `categoryName` | Cardmarket category name |
| `name` | Raw Cardmarket product name |
| `dateAdded` | Source product creation timestamp |

No structurally optional fields were found in this controlled fixture. Each field is present in all `177` records.

### Source-to-Staging Field Mapping

| Source field | Normalization rule | `staging_market_products` target | Required for valid record |
| --- | --- | --- | ---: |
| Import context | Use the current `import_runs.import_run_id` | `import_run_id` | Yes |
| `idProduct` | Convert to trimmed non-empty text | `source_record_reference` | Yes |
| Import contract | Use controlled value `cardmarket` | `source_system` | Yes |
| `idProduct` | Convert to trimmed non-empty text | `source_product_id` | Yes |
| `idExpansion` | Convert to trimmed non-empty text | `source_expansion_id` | Yes |
| `idMetacard` | Convert to trimmed non-empty text | `source_metaproduct_id` | Yes |
| `name` | Preserve Unicode text and trim surrounding whitespace | `raw_name` | Yes |
| `idCategory` | Convert to trimmed non-empty text | `source_category_id` | Yes |
| `categoryName` | Preserve Unicode text and trim surrounding whitespace | `source_category_name` | Yes |
| `dateAdded` | Parse as a timezone-aware timestamp | `source_created_at` | Yes |
| Complete source object | Preserve without dropping fields | `raw_payload` | Yes |
| Normalized source record | Calculate a deterministic SHA-256 checksum from canonical JSON serialization | `record_checksum` | Yes |
| Importer state | Set after normalization completes | `normalization_status` | Yes |
| Validator state | Set after record-level validation completes | `validation_status` | Yes |
| Validation completion time | Populate when validation reaches a terminal state | `validation_completed_at` | Yes |

For this controlled fixture:

```text
source_record_reference = source_product_id
```

The staging identity is:

```text
(import_run_id, source_record_reference)
```

Within one import run:

- each `source_record_reference` must occur exactly once;
- each `source_product_id` must occur exactly once;
- no source product may be silently overwritten;
- duplicate source identities must fail validation.

The later production identity is:

```text
(source_system, source_product_id)
```

### Record-Level Validation Rules

A Cardmarket product staging record is valid only when all of the following are true:

- `source_record_reference` is non-empty;
- `source_system` equals `cardmarket`;
- `source_product_id` is non-empty;
- `source_expansion_id` equals `1585`;
- `source_metaproduct_id` is non-empty;
- `raw_name` is non-empty after trimming;
- `source_category_id` is non-empty;
- `source_category_name` is non-empty after trimming;
- `source_created_at` is parsed successfully;
- `raw_payload` is present;
- `record_checksum` is present;
- no duplicate `(import_run_id, source_record_reference)` exists;
- no duplicate valid `(import_run_id, source_system, source_product_id)` exists.

A source record that cannot be normalized or validated must not be silently removed or converted into a valid record.

### Online Code Card Handling

The fixture contains four valid Cardmarket source records that represent Online Code Card products:

| `idProduct` | `idMetacard` | Product name |
| --- | ---: | --- |
| `300914` | `226578` | `Online Code Card (Booster)` |
| `300919` | `226579` | `Online Code Card (Elite Trainer Box)` |
| `300971` | `226580` | `Online Code Card (Theme Deck)` |
| `300972` | `226580` | `Online Code Card (Theme Deck)` |

The controlled classification predicate is:

```text
source_category_id = '51'
AND raw_name starts with 'Online Code Card'
```

These four records are valid source records and must remain present in `staging_market_products`.

They are outside the collection scope and must not create production catalogue entities.

During the later production merge, each record must produce an `import_record_outcomes` row with:

```text
entity_type = market_product
source_system = cardmarket
source_entity_id = source_product_id
source_record_reference = source_product_id
production_entity_id = NULL
outcome_type = skipped
reason_code = online_code_card_out_of_scope
```

The recommended `reason_detail` is:

```text
Online Code Card products are outside the MVP collection scope.
```

Online Code Card records must not:

- be inserted into `market_products`;
- create card-to-market-product mappings;
- create `card_editions`;
- create `card_variants`;
- participate in imported market-price calculations;
- participate in the canonical-card `From` price;
- be counted as rejected records solely because they are outside the collection scope.

### First Persistent Staging Run Acceptance Criteria

The first persistent Cardmarket product staging run is accepted only when all of the following results are confirmed.

#### Source Counts

```text
source system: cardmarket
source expansion identifier: 1585
declared source records: 177
actual source records: 177
```

#### Normalization and Validation

```text
normalized records: 177
normalization failures: 0
valid records: 177
rejected records: 0
```

#### Persisted State

The committed transaction must contain:

```text
import_runs rows created: 1
staging_market_products rows created: 177
```

The import run must have:

```text
status = validated
total_source_records = 177
valid_source_records = 177
rejected_records = 0
staging_loaded_at IS NOT NULL
validated_at IS NOT NULL
merge_started_at IS NULL
completed_at IS NULL
```

The staging rows must have:

```text
normalization_status = normalized: 177
validation_status = valid: 177
validation_completed_at IS NOT NULL: 177
```

#### Completeness and Identity Checks

The run must produce:

```text
duplicate source_record_reference values: 0
duplicate source_product_id values: 0
missing source_product_id values: 0
missing raw_name values: 0
missing raw_payload values: 0
missing record_checksum values: 0
invalid source_system values: 0
distinct source_expansion_id values: 1
expected source_expansion_id: 1585
```

#### Scope Classification

The validated staging rows must classify as:

```text
eligible market products: 173
out-of-scope Online Code Card records: 4
```

The four out-of-scope identities must be:

```text
300914
300919
300971
300972
```

This classification is staging validation evidence. The staging importer must not create `import_record_outcomes`; those rows belong to the later production merge.

### Staging Isolation

The staging importer may modify only:

- `import_runs`;
- `staging_market_products`;
- rejected-record tables when an actual invalid source record is encountered.

It must not modify:

- `market_products`;
- `card_market_product_mappings`;
- `card_editions`;
- `card_variants`;
- `market_price_snapshots`;
- `import_record_outcomes`;
- `wishlist_items`.

A successful staging run ends at:

```text
import_runs.status = validated
```

It must not start or complete a production merge.

### Transactional Rollback Requirement

A dedicated failure-injection run must verify that the staging operation is atomic.

After an intentional failure following partial staging inserts, the database must contain:

```text
surviving import_runs rows for the failed run: 0
surviving staging_market_products rows for the failed run: 0
```

A consumed PostgreSQL sequence value is acceptable and does not indicate that a row survived the rollback.

### Expected Staging Summary

A successful importer execution should report an equivalent summary:

```text
Cardmarket product fixture validation passed
Source system: cardmarket
Source expansion ID: 1585
Source records: 177
Normalized records: 177
Valid records: 177
Rejected records: 0
Eligible market products: 173
Out-of-scope Online Code Card records: 4
Staged records: 177
Final status: validated
Production merge: not executed
```

### Later Production Projection

The later production merge will project eligible staging values as follows:

| `staging_market_products` source | `market_products` target |
| --- | --- |
| `source_system` | `source_system` |
| `source_product_id` | `source_product_id` |
| `source_expansion_id` | `source_expansion_id` |
| `source_metaproduct_id` | `source_metaproduct_id` |
| `raw_name` | `raw_name` |
| `source_category_id` | `source_category_id` |
| `source_category_name` | `source_category_name` |
| `source_created_at` | `source_created_at` |

`market_products.expansion_id` is not copied from the source fixture. It must be resolved through the existing internal Primal Clash expansion associated with Cardmarket expansion identifier `1585`.

The production merge, audit outcomes, repeated-import behaviour, and production rollback validation remain outside this staging importer implementation block.
