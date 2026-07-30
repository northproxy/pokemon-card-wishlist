# M4 First Import — Cardmarket Products Handoff

## Purpose

This document records the work completed during the Cardmarket product import block of `M4 — First import`.

The completed scope covers:

```text
cardmarket-products.json
→ validation and normalization
→ staging_market_products
→ transactional rollback validation
→ repeat staging validation
→ market_products production merge
→ repeat production merge
→ audit outcome validation
```

The next import block is:

```text
cardmarket-mappings.json
→ staging_market_mappings
→ card_market_product_mappings
```

Do not return to schema design unless the mapping import reveals a confirmed schema problem.

## Starting State

The canonical Primal Clash catalogue path had already been implemented and validated before this block began.

Confirmed production state at the start:

- one internal Primal Clash expansion existed;
- `pokemon_tcg_data / xy5` resolved to that expansion;
- `164` canonical Primal Clash cards existed;
- all `164` cards were active;
- repeated canonical-card production import was idempotent;
- `market_products` was empty.

## Controlled Source Artifact

The Cardmarket product fixture is:

```text
data/fixtures/primal-clash/cardmarket-products.json
```

Confirmed fixture properties:

```text
source file: products_singles_6.json
source system: cardmarket
source expansion ID: 1585
record count: 177
```

Every source record contains all seven fields:

- `idProduct`;
- `idExpansion`;
- `idMetacard`;
- `idCategory`;
- `categoryName`;
- `name`;
- `dateAdded`.

No structurally optional fields were found within this controlled fixture.

## Source-to-Staging Mapping

The confirmed mapping is:

| Source field | `staging_market_products` column | Normalization |
|---|---|---|
| `idProduct` | `source_product_id` | Convert to trimmed non-empty text |
| `idExpansion` | `source_expansion_id` | Convert to trimmed non-empty text |
| `idMetacard` | `source_metaproduct_id` | Convert to trimmed non-empty text |
| `name` | `raw_name` | Trim surrounding whitespace |
| `idCategory` | `source_category_id` | Convert to trimmed non-empty text |
| `categoryName` | `source_category_name` | Trim surrounding whitespace |
| `dateAdded` | `source_created_at` | Parse real timestamps; convert the source sentinel to `NULL` |
| Complete source object | `raw_payload` | Preserve as JSONB |

Importer-generated values:

| Column | Value |
|---|---|
| `source_record_reference` | `cardmarket-products.json#idProduct=<idProduct>` |
| `source_system` | `cardmarket` |
| `record_checksum` | Deterministic SHA-256 checksum |
| `normalization_status` | `normalized` |
| `validation_status` | `valid` |
| `validation_completed_at` | Populated at validation completion |

## Source Timestamp Finding

The first importer execution exposed a real source-data condition:

```text
dateAdded = 0000-00-00 00:00:00
```

This value is not a valid timestamp. It is a source missing-value sentinel.

Confirmed fixture distribution:

```text
missing-value sentinel records: 164
real timestamp records: 13
```

The accepted normalization rule is:

```text
0000-00-00 00:00:00 → NULL
valid dateAdded value → parsed timestamptz
```

The physical schema already allowed `source_created_at` to be `NULL`, so no schema change was required.

The importer deterministically interprets timezone-naive real timestamps as UTC. PostgreSQL displays them according to the session timezone. This confirms importer behaviour but does not independently prove the original Cardmarket timezone semantics.

## Online Code Card Scope Handling

Four valid source records are Online Code Card products:

| `idProduct` | `idMetacard` | Product |
|---|---:|---|
| `300914` | `226578` | `Online Code Card (Booster)` |
| `300919` | `226579` | `Online Code Card (Elite Trainer Box)` |
| `300971` | `226580` | `Online Code Card (Theme Deck)` |
| `300972` | `226580` | `Online Code Card (Theme Deck)` |

The controlled classification predicate is:

```text
source_category_id = '51'
AND raw_name starts with 'Online Code Card'
```

Accepted handling:

- all four records remain valid staging records;
- they are not rejected;
- they are not inserted into `market_products`;
- they do not participate in mappings, editions, variants, prices, or the canonical-card `From` price;
- each production merge records an audit outcome with:

```text
entity_type = market_product
outcome_type = skipped
reason_code = online_code_card_out_of_scope
production_entity_id = NULL
```

Reason detail:

```text
Online Code Card products are outside the MVP collection scope.
```

The controlled classification counts are:

```text
eligible market products: 173
out-of-scope Online Code Card records: 4
```

## Schema Review Result

The actual columns and constraints of these tables were inspected:

- `staging_market_products`;
- `market_products`;
- `import_record_outcomes`.

Confirmed conclusions:

- all seven source fields have direct staging targets;
- staging supports raw JSON, record checksums, normalization state, validation state, and validation timestamps;
- production identity is protected by:

```text
UNIQUE (source_system, source_product_id)
```

- `import_record_outcomes` already supports `outcome_type = skipped`;
- a skipped outcome requires a non-null `reason_code`;
- no schema migration was required.

## Documentation Update

Updated:

```text
docs/import/primal-clash-source-to-target.md
```

The Cardmarket product section records:

- controlled fixture contract;
- source-to-staging mapping;
- validation rules;
- timestamp sentinel handling;
- Online Code Card classification;
- staging acceptance criteria;
- rollback requirements;
- production projection;
- audit outcome rules.

## Cardmarket Product Staging Importer

Created:

```text
scripts/import/import_primal_clash_market_products.py
```

### Responsibilities

The importer:

- reads the controlled fixture;
- validates the top-level envelope;
- requires `cardmarket / 1585`;
- requires exactly `177` source records;
- verifies all seven required fields;
- normalizes identifiers and names;
- preserves Unicode;
- converts `164` missing timestamp sentinels to `NULL`;
- parses `13` real timestamps;
- preserves each complete source record in `raw_payload`;
- calculates deterministic record checksums;
- rejects duplicate source identities;
- validates the four exact Online Code Card identities;
- creates one `import_runs` row;
- inserts all `177` records into `staging_market_products`;
- validates persisted counts and terminal states;
- advances the lifecycle:

```text
created
→ staging_loaded
→ validated
```

- commits one persistent staging snapshot;
- does not execute a production merge.

## First Persistent Staging Run

Command:

```powershell
python scripts/import/import_primal_clash_market_products.py `
  --run-reference primal-clash-market-products-dry-run-001 `
  --importer-version m4-first-import-v1
```

Confirmed result:

```text
Import run ID: 4
Source records: 177
Normalized records: 177
Valid records: 177
Rejected records: 0
Eligible market products: 173
Out-of-scope Online Code Card records: 4
Missing source timestamps normalized to NULL: 164
Parsed source timestamps: 13
Staged records: 177
Final status: validated
Production merge: not executed
```

### SQL validation

Confirmed for run `4`:

- `status = validated`;
- `total_source_records = 177`;
- `valid_source_records = 177`;
- `rejected_records = 0`;
- `staging_loaded_at` populated;
- `validated_at` populated;
- `merge_started_at = NULL`;
- `completed_at = NULL`;
- `177` staged rows;
- `177` normalized rows;
- `177` valid rows;
- `0` pending rows;
- `0` missing validation timestamps;
- `0` duplicate `source_record_reference` values;
- `0` duplicate `source_product_id` values;
- `0` missing required staging values;
- one distinct source expansion ID: `1585`;
- `164` null source timestamps;
- `13` parsed source timestamps;
- exact Online Code Card identities matched;
- `173` eligible records;
- `4` out-of-scope records;
- `market_products` remained empty.

## Transactional Rollback Validation

Created:

```text
scripts/import/fail_import_primal_clash_market_products.py
```

### Purpose

The script:

1. loads and validates the controlled fixture;
2. creates an import run inside one transaction;
3. inserts a controlled partial set of staging rows;
4. raises an intentional exception;
5. verifies complete rollback in a new connection.

Command:

```powershell
python scripts/import/fail_import_primal_clash_market_products.py `
  --run-reference primal-clash-market-products-rollback-test-001 `
  --importer-version m4-first-import-v1 `
  --fail-after-records 10
```

Confirmed result:

```text
Expected failure triggered after 10 staging records
Attempted import run ID: 5
Surviving import runs: 0
Surviving staging rows: 0
```

The consumed PostgreSQL sequence value `5` is expected and does not indicate that a row survived the rollback.

## Repeat Staging Import

Command:

```powershell
python scripts/import/import_primal_clash_market_products.py `
  --run-reference primal-clash-market-products-dry-run-002 `
  --importer-version m4-first-import-v1
```

Confirmed result:

```text
Import run ID: 6
Staged records: 177
Valid records: 177
Rejected records: 0
Eligible market products: 173
Out-of-scope Online Code Card records: 4
Missing source timestamps normalized to NULL: 164
Parsed source timestamps: 13
Final status: validated
Production merge: not executed
```

### Repeat staging validation

Runs `4` and `6` both had:

```text
status: validated
artifact checksum:
bab3dca68cb0644e9fb755554d565fd662637f7ad39466534f93fac79bfe4b19
staged rows: 177
normalized rows: 177
valid rows: 177
rejected rows: 0
missing source timestamps: 164
Online Code Card records: 4
```

This validates repeatable, independent staging snapshots.

## Cardmarket Product Production Merge

Created:

```text
scripts/import/merge_primal_clash_market_products.py
```

### Responsibilities

The merge script:

- accepts one validated Cardmarket product import run;
- locks the selected import run;
- locks and validates all `177` staging rows;
- refuses incomplete, duplicate, rejected, or previously merged runs;
- resolves the existing internal Primal Clash expansion through:

```text
pokemon_tcg_data / xy5
```

- creates or validates the second expansion source identifier:

```text
cardmarket / 1585
```

- ensures both source identifiers resolve to the same internal expansion;
- inserts, updates, reactivates, or compares `173` eligible market products;
- skips the four Online Code Card records;
- records one `import_record_outcomes` row per staged record;
- validates production and outcome counts;
- advances the merge lifecycle;
- commits the complete merge atomically.

### Merge lifecycle bug found and fixed

The first merge attempt used the incorrect status:

```text
merging
```

The physical schema requires:

```text
merge_started
```

The failed transaction violated `import_runs_failure_fields_check`.

Confirmed rollback after the failed attempt:

```text
run 4 status: validated
merge_started_at: NULL
completed_at: NULL
market_products: 0
outcomes for run 4: 0
```

The implementation was corrected to use:

```text
validated
→ merge_started
→ succeeded
```

This was an implementation bug, not a schema problem.

## First Production Merge

Command:

```powershell
python scripts/import/merge_primal_clash_market_products.py `
  --import-run-id 4
```

Confirmed result:

```text
Primal Clash Cardmarket product production merge committed
Import run ID: 4
Expansion ID: 2
Inserted market products: 173
Updated market products: 0
Reactivated market products: 0
Unchanged market products: 0
Skipped Online Code Card records: 4
Processed source records: 177
Final status: succeeded
```

### First production validation

Confirmed:

```text
run status: succeeded
inserted_records: 173
updated_records: 0
unchanged_records: 0
missing_records: 0
retired_records: 0
```

Production state:

```text
market products: 173
active market products: 173
inactive market products: 0
duplicate source identities: 0
Online Code Card products in production: 0
missing source timestamps: 164
parsed source timestamps: 9
```

Only `9` real timestamps exist in production because the other four real timestamps belong to the excluded Online Code Card records.

Audit outcomes:

```text
inserted: 173
skipped: 4
total: 177
```

Exact skipped identities:

```text
300914
300919
300971
300972
```

All skipped outcomes have:

```text
reason_code = online_code_card_out_of_scope
production_entity_id = NULL
```

The Cardmarket source identifier was confirmed as:

```text
expansion_id: 2
source_system: cardmarket
source_expansion_id: 1585
source_name: Primal Clash
is_active: true
expansion_key: primal_clash
name: Primal Clash
```

## Repeat Production Merge

Command:

```powershell
python scripts/import/merge_primal_clash_market_products.py `
  --import-run-id 6
```

Confirmed result:

```text
Primal Clash Cardmarket product production merge committed
Import run ID: 6
Expansion ID: 2
Inserted market products: 0
Updated market products: 0
Reactivated market products: 0
Unchanged market products: 173
Skipped Online Code Card records: 4
Processed source records: 177
Final status: succeeded
```

### Idempotency validation

Final reconciliation:

```text
run 4:
  inserted outcomes: 173
  skipped outcomes: 4
  total outcomes: 177

run 6:
  unchanged outcomes: 173
  skipped outcomes: 4
  total outcomes: 177
```

Final production state remained:

```text
market products total: 173
active market products: 173
inactive market products: 0
missing source timestamps: 164
parsed source timestamps: 9
duplicate source identities: 0
Online Code Card products in production: 0
```

This proves that an identical repeated Cardmarket product import does not create uncontrolled duplicates or unnecessary updates.

## Confirmed Results

The following Cardmarket product path is now implemented and validated:

```text
fixture envelope validation
→ record normalization
→ timestamp sentinel handling
→ Unicode preservation
→ deterministic record checksums
→ persistent PostgreSQL staging
→ staging count and uniqueness validation
→ Online Code Card classification
→ repeat staging snapshots
→ partial-write rollback
→ internal expansion resolution
→ Cardmarket expansion identifier creation
→ production market-product insertion
→ skipped out-of-scope outcome recording
→ complete per-record audit outcomes
→ repeated production merge
→ unchanged-record detection
→ production duplicate prevention
```

Confirmed counts:

```text
source records: 177
valid staging records: 177
rejected records: 0
eligible products: 173
Online Code Card records: 4
first production insert: 173
repeat production insert: 0
repeat unchanged: 173
active production products: 173
duplicate production identities: 0
Online Code Card products in production: 0
```

## Files Created or Updated

Created:

```text
scripts/import/import_primal_clash_market_products.py
scripts/import/fail_import_primal_clash_market_products.py
scripts/import/merge_primal_clash_market_products.py
```

Updated:

```text
docs/import/primal-clash-source-to-target.md
```

## Current Database State

Relevant confirmed rows:

```text
import_runs:
- run 1: canonical catalogue merge succeeded
- run 3: repeat canonical catalogue merge succeeded
- run 4: Cardmarket product merge succeeded
- run 6: repeat Cardmarket product merge succeeded

staging_market_products:
- 177 rows for run 4
- 177 rows for run 6

expansion_source_identifiers:
- pokemon_tcg_data / xy5
- cardmarket / 1585

market_products:
- 173 active Primal Clash Cardmarket products
- 0 Online Code Card products

import_record_outcomes:
- run 4: 173 inserted, 4 skipped
- run 6: 173 unchanged, 4 skipped
```

Rollback-test run `5` did not survive, but its sequence value was consumed.

## Important Limitations

This work does not complete all of `M4 — First import`.

Not yet implemented or validated:

- Cardmarket mapping staging;
- production card-to-market-product mappings;
- handling of the six `unmatched_duplicate_candidate` products in the mapping import;
- mapping-related unresolved and excluded audit outcomes;
- card editions and variants produced from market mappings;
- Cardmarket price staging;
- market price snapshots;
- the canonical-card minimum non-null `avg30` `From` price query;
- dedicated production merge failure injection for Cardmarket products;
- a complete M4 import validation report;
- final M4 documentation and repository-wide exit validation.

## Recommended Next Block

Continue `M4 — First import` with Cardmarket mappings:

```text
cardmarket-mappings.json
→ staging_market_mappings
→ card_market_product_mappings
```

Begin by:

1. locating and inspecting the actual mapping fixture path, envelope, and fields;
2. inspecting the actual columns and constraints of:
   - `staging_market_mappings`;
   - `card_market_product_mappings`;
3. confirming mapping statuses and record counts;
4. defining the exact source-to-staging mapping;
5. defining handling for:
   - confirmed mappings;
   - `unmatched_duplicate_candidate`;
   - Online Code Card exclusions;
6. defining acceptance criteria for the first persistent mapping staging run.
