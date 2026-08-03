# Primal Clash Source-to-Target Mapping

## Status

Implemented and validated for the controlled Primal Clash canonical-card, Cardmarket product, mapping, and price paths. Edition and variant derivation remains incomplete.

## Controlled Slice

The first controlled import slice covers canonical Primal Clash card records only.

```text
data/fixtures/primal-clash/canonical-cards.json
â†’ import_runs
â†’ staging_cards
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

- the top-level payload is not a JSON object;
- `records` is not a JSON array;
- `recordCount` is not an integer;
- `recordCount` does not equal the number of elements in `records`;
- `sourceSystem` is missing or unsupported;
- `setId` is missing or does not match the controlled import scope.

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

- `supertype`;
- `subtypes`;
- `hp`;
- `types`;
- `evolvesTo`;
- `attacks`;
- `weaknesses`;
- `retreatCost`;
- `convertedRetreatCost`;
- `artist`;
- `flavorText`;
- `nationalPokedexNumbers`;
- `legalities`;
- the complete `images` object.

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

- `source_record_reference` is non-empty;
- `source_system` equals `pokemon_tcg_data`;
- `source_card_id` is non-empty;
- `source_expansion_id` equals `xy5`;
- `collector_number` is non-empty;
- `name` is non-empty;
- `raw_payload` is present;
- `image_small_url` is non-empty;
- `image_large_url` is non-empty;
- both image references use HTTPS;
- both image references use the expected `images.pokemontcg.io` host;
- `image_small_url` matches the expected `xy5/<collector-number>.png` pattern;
- `image_large_url` matches the expected `xy5/<collector-number>_hires.png` pattern;
- no duplicate `(import_run_id, source_record_reference)` exists;
- no duplicate valid `(import_run_id, source_system, source_card_id)` exists.

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

- `import_runs`;
- `staging_cards`;
- rejected-record tables when an actual invalid source record is encountered.

The following tables must have identical row counts before and after the dry run:

- `expansions`;
- `expansion_source_identifiers`;
- `cards`;
- `card_editions`;
- `card_variants`;
- `market_products`;
- `card_market_product_mappings`;
- `market_price_snapshots`;
- `card_market_mapping_cases`;
- `mapping_case_observations`;
- `mapping_candidates`;
- `mapping_status_history`;
- `wishlist_items`;
- `import_record_outcomes`.

## First Dry-Run Acceptance Criteria

The first controlled slice is accepted when:

- exactly one catalogue import run is created;
- the run scope identifies `pokemon_tcg_data:xy5`;
- the importer reads exactly `164` source records;
- exactly `164` rows are inserted into `staging_cards`;
- every source record is represented once;
- all staging rows belong to the same import run;
- all `164` records reach a valid terminal validation state;
- no staging row remains in `pending` normalization or validation state;
- no rejected source records are created;
- all image references are present and valid;
- run-level counts reconcile with staging and rejection counts;
- no production, market, mapping, price, or wishlist table changes;
- the existing permanent Primal Clash fixture validator continues to pass.

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
â†’ staging_loaded
â†’ validated
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

- populate `failure_code`;
- optionally populate `failure_detail`;
- populate `completed_at`;
- never populate `merge_started_at`;
- never modify production tables.

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
â†’ validation and normalization
â†’ staging_market_products
â†’ validated staging run
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

The Cardmarket product production merge is implemented and validated.

Validated results:

- first merge: `173` inserted market products and `4` skipped Online Code Card records;
- repeated merge: `173` unchanged market products and `4` skipped Online Code Card records;
- final active production products: `173`;
- duplicate production source identities: `0`;
- Online Code Card products in production: `0`;
- one reconciled `import_record_outcomes` row per source record and production run.

## Cardmarket Price Import

### Controlled Source Artifact

The controlled Cardmarket price path uses:

```text
data/fixtures/primal-clash/cardmarket-prices.json
```

The implemented and validated pipeline is:

```text
cardmarket-prices.json
â†’ validation and normalization
â†’ staging_market_prices
â†’ market_price_snapshots
â†’ runtime canonical-card From price
```

The fixture was prepared from:

```text
price_guide_6.json
```

The fixture envelope contains:

| Source field | Expected value or role |
| --- | --- |
| `sourceFile` | Original source artifact reference |
| `sourceSystem` | Controlled value `cardmarket` |
| `sourceCreatedAt` | File-level source snapshot timestamp |
| `expansionId` | Controlled Cardmarket expansion identifier `1585` |
| `recordCount` | Declared source record count |
| `records` | Cardmarket price source records |

The validated fixture metadata is:

```text
sourceFile = price_guide_6.json
sourceSystem = cardmarket
sourceCreatedAt = 2026-07-26T02:44:32+0200
expansionId = 1585
recordCount = 177
```

The normalized UTC source snapshot timestamp is:

```text
2026-07-26T00:44:32+00:00
```

All `177` records share this file-level source snapshot timestamp.

### Source Fields and Controlled Currency

Each source record contains:

| Source field | Role |
| --- | --- |
| `idProduct` | Cardmarket product identifier |
| `avg30` | Cardmarket 30-day average |
| `avg30-holo` | Additional Cardmarket holo 30-day average when present |

The fixture does not contain a currency field. The controlled import contract assigns:

```text
currency_code = EUR
```

This assignment is specific to the validated Cardmarket fixture contract and must not be inferred for unrelated sources.

Validated value distribution:

```text
source records: 177
records with avg30: 177
records with avg30-holo: 169
records without avg30-holo: 8
```

### Source-to-Staging Field Mapping

| Source value | Normalization rule | `staging_market_prices` target | Required for valid record |
| --- | --- | --- | ---: |
| Import context | Use the current `import_runs.import_run_id` | `import_run_id` | Yes |
| `idProduct` plus stable artifact context | Build `cardmarket-prices.json#idProduct=<id>` | `source_record_reference` | Yes |
| Import contract | Use controlled value `cardmarket` | `source_system` | Yes |
| `idProduct` | Convert to trimmed non-empty text | `source_product_id` | Yes |
| Top-level `sourceCreatedAt` | Parse as timezone-aware timestamp and normalize to UTC | `source_snapshot_at` | Yes |
| Import contract | Use controlled value `EUR` | `currency_code` | Yes |
| `avg30` source value | Preserve a deterministic text representation | `avg30_raw` | Yes for this fixture |
| `avg30` source value | Parse as non-negative `numeric(12,4)` | `avg30` | Yes for this fixture |
| `avg30-holo` source value | Preserve a deterministic text representation or `NULL` | `avg30_holo_raw` | No |
| `avg30-holo` source value | Parse as non-negative `numeric(12,4)` or `NULL` | `avg30_holo` | No |
| Complete source object | Preserve without dropping fields | `raw_payload` | Yes |
| Normalized source record | Calculate deterministic SHA-256 from canonical JSON | `record_checksum` | Yes |
| Importer state | Set after normalization completes | `normalization_status` | Yes |
| Validator state | Set after validation completes | `validation_status` | Yes |
| Validation completion time | Populate for the terminal validation state | `validation_completed_at` | Yes |

The staging identity is:

```text
(import_run_id, source_record_reference)
```

Within one import run:

- every source record must be represented exactly once;
- each `source_record_reference` must be unique;
- each `source_product_id` must be unique;
- raw and normalized values must both remain available;
- no invalid or out-of-scope record may disappear silently.

### Fixture and Record Validation

The complete fixture must fail before staging when:

- the top-level payload is not a JSON object;
- `records` is not a JSON array;
- `recordCount` is not an integer;
- `recordCount` does not equal the number of records;
- `recordCount` is not `177`;
- `sourceSystem` is not `cardmarket`;
- `expansionId` is not `1585`;
- `sourceCreatedAt` is missing or cannot be parsed deterministically;
- duplicate `idProduct` values exist.

A normalized record is valid only when:

- `source_record_reference` is non-empty;
- `source_system` equals `cardmarket`;
- `source_product_id` is non-empty;
- `source_snapshot_at` is present;
- `currency_code` equals `EUR`;
- `avg30` and `avg30_holo`, when present, are non-negative;
- at least one normalized price value is non-null;
- normalized values fit `numeric(12,4)`;
- `raw_payload` is present;
- `record_checksum` is present;
- normalization and validation reach terminal states.

The validated fixture produced:

```text
normalized records: 177
valid records: 177
rejected records: 0
duplicate source_product_id values: 0
```

### Price Staging Import Run Contract

The permanent staging importer is:

```text
scripts/import/import_primal_clash_market_prices.py
```

It creates an `import_runs` record with the controlled values:

| Column | Value |
| --- | --- |
| `run_kind` | `market_prices` |
| `source_system` | `cardmarket` |
| `source_entity_type` | `market_price` |
| `source_artifact_reference` | `data/fixtures/primal-clash/cardmarket-prices.json` |
| `scope_type` | `expansion` |
| `scope_reference` | `cardmarket:1585` |
| `is_authoritative` | `true` |
| Initial `status` | `created` |

The staging lifecycle is:

```text
created
â†’ staging_loaded
â†’ validated
```

A successful staging run must contain:

```text
total_source_records = 177
valid_source_records = 177
rejected_records = 0
staging_market_prices rows = 177
merge_started_at IS NULL
completed_at IS NULL
```

The staging importer must not write:

- `market_price_snapshots`;
- `import_record_outcomes`;
- `market_products`;
- `card_market_product_mappings`;
- catalogue hierarchy tables;
- `wishlist_items`.

Validated staging runs:

```text
13  primal-clash-market-prices-dry-run-001
15  primal-clash-market-prices-dry-run-002
```

Each run staged `177` valid rows with `0` rejected records.

### Staging Transactional Rollback

The permanent failure-injection utility is:

```text
scripts/import/fail_import_primal_clash_market_prices.py
```

It creates an import run and one staged record inside a transaction, raises an intentional exception, and verifies rollback through a new database connection.

Validated rollback evidence:

```text
attempted import run ID: 14
attempted staged records: 1
surviving matching import runs: 0
final committed staging row count: 177
```

A consumed PostgreSQL sequence value is acceptable and does not indicate that a row survived rollback.

### Staging-to-Production Projection

The permanent production merge utility is:

```text
scripts/import/merge_primal_clash_market_prices.py
```

Eligible staging rows project as follows:

| `staging_market_prices` source | `market_price_snapshots` target |
| --- | --- |
| Resolved `source_product_id` | `market_product_id` |
| `import_run_id` | `import_run_id` |
| `source_snapshot_at` | `source_snapshot_at` |
| `currency_code` | `currency_code` |
| `avg30` | `avg30` |
| `avg30_holo` | `avg30_holo` |
| `source_record_reference` | `source_reference` |

The merge must resolve the existing production product through:

```text
market_products.source_system = cardmarket
market_products.source_product_id = staging_market_prices.source_product_id
```

An eligible record must resolve to an active Primal Clash production product.

The production snapshot identity is:

```text
(market_product_id, source_snapshot_at)
```

`market_price_snapshots` is append-only:

- a new identity creates an `inserted` snapshot;
- an identical existing identity and values produces an `unchanged` outcome;
- an existing identity with conflicting values must fail the controlled merge;
- an existing historical snapshot must never be updated or deleted.

### Out-of-Scope Price Records

The price fixture contains records for the same four Online Code Card product identities excluded from `market_products`:

```text
300914
300919
300971
300972
```

These records are valid source records and remain present in `staging_market_prices`.

During production merge they must produce:

```text
entity_type = market_price_snapshot
source_system = cardmarket
source_entity_id = source_product_id
production_entity_id = NULL
outcome_type = skipped
reason_code = online_code_card_out_of_scope
```

They must not create:

- `market_products`;
- `market_price_snapshots`;
- canonical-card mappings;
- runtime canonical-card prices.

The two oversized mapped-source exclusions and six `unmatched_duplicate_candidate` products remain active market products with imported snapshots when they are eligible production products. They do not affect canonical-card runtime prices because they do not have active canonical-card mappings.

### Production Merge Lifecycle and Audit Contract

The production lifecycle is:

```text
validated
â†’ merge_started
â†’ succeeded
```

The complete merge runs inside one PostgreSQL transaction.

Each of the `177` staged source records must produce exactly one `import_record_outcomes` row:

- `inserted` for a newly stored production snapshot;
- `unchanged` for an identical existing production snapshot;
- `skipped` for a controlled out-of-scope Online Code Card record;
- controlled failure rather than silent overwrite for a conflicting existing snapshot identity.

Run summary counts must reconcile with all `177` source records.

### Production Merge Transactional Rollback

The permanent failure-injection utility is:

```text
scripts/import/fail_merge_primal_clash_market_prices.py
```

It transitions a validated run to `merge_started`, inserts one production snapshot and one audit outcome inside a transaction, raises an intentional exception, and verifies complete rollback through a new connection.

Validated rollback evidence for run `13`:

```text
attempted source product ID: 273532
attempted price snapshot ID: 1
surviving price snapshots: 0
surviving run outcomes: 0
final import run status: validated
```

The run's `merge_started_at` and `completed_at` values remained `NULL`.

### First and Repeated Production Merge Results

First production merge:

```text
import run ID: 13
run reference: primal-clash-market-prices-dry-run-001
inserted snapshots: 173
unchanged snapshots: 0
skipped Online Code Card records: 4
processed source records: 177
final status: succeeded
```

Repeated production merge of the identical fixture and source snapshot:

```text
import run ID: 15
run reference: primal-clash-market-prices-dry-run-002
inserted snapshots: 0
unchanged snapshots: 173
skipped Online Code Card records: 4
processed source records: 177
final status: succeeded
```

Final production state:

```text
market_price_snapshots: 173
duplicate snapshot identities: 0
```

The repeated import preserves the original snapshots and records unchanged outcomes without creating duplicate production rows.

### Runtime Canonical-Card From Price

The permanent validator is:

```text
scripts/database/validate_primal_clash_from_prices.sql
```

The runtime rule is defined by `ADR-011` and `FR-12`.

For each active market product, select its latest eligible snapshot from a successful import run. Then calculate one canonical-card value from active canonical-card mappings:

```sql
MIN(avg30)
```

Runtime eligibility requires:

- an active `card_market_product_mappings` row;
- an active canonical `cards` row;
- an active Cardmarket `market_products` row;
- a snapshot linked to an `import_runs.status = 'succeeded'` run;
- `currency_code = 'EUR'`;
- non-null `avg30`.

The initial MVP formula must not use `avg30_holo`.

The result is informational and must be labelled:

```text
display prefix: From
display label: 30-day average
```

Validated runtime result:

```text
Primal Clash runtime From price validation passed
Price snapshots: 173
Active mapped market products: 165
Canonical cards with From prices: 164
```

Representative results:

```text
xy5-1  Weedle    From EUR 0.1400
xy5-2  Kakuna    From EUR 0.1800
xy5-3  Beedrill  From EUR 0.7500
xy5-8  Sceptile  From EUR 2.6900
xy5-9  Sceptile  From EUR 10.2200
```

The canonical-card query returns no price when no eligible non-null `avg30` exists. Every mapped canonical card in the current fixture has at least one eligible non-null `avg30`, so the no-price branch is defined by query semantics but is not represented by this fixture.

### Known Limitations

- The fixture provides one file-level source snapshot timestamp for all `177` records.
- The fixture does not provide currency; the controlled contract assigns `EUR`.
- The fixture contains `avg30-holo`, but the MVP runtime formula excludes it.
- Imported Cardmarket values are informational snapshots, not real-time prices or purchase quotes.
- Language, edition, and finish must not be inferred from price values.
- Edition and variant creation remains a separate M4 work block.
- The current fixture does not exercise the runtime no-price branch.
