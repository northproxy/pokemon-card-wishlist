# M4 First Import — Canonical Catalogue Handoff

## Purpose

This document records the work completed during the first implementation block of `M4 — First import`.

The completed scope covers the Primal Clash canonical catalogue path:

```text
canonical-cards.json
→ validation and normalization
→ staging_cards
→ production catalogue merge
→ repeat-import validation
```

Cardmarket products, market mappings, market prices, excluded products, unmatched duplicate candidates, and the runtime canonical-card `From` price remain outside this completed block.

## Starting State

The previous milestone, `M3 — Data model`, was formally closed before this work began.

Confirmed starting conditions:

- the PostgreSQL physical schema was implemented and locally validated;
- `21` project tables existed;
- `17` reversible dbmate migrations were applied;
- `dbmate status` reported `Applied: 17` and `Pending: 0`;
- schema-wide validation passed;
- Primal Clash fixtures were validated;
- Primal Clash had not yet been imported into PostgreSQL;
- the import pipeline had not yet been implemented.

Validated canonical-card fixture expectations:

- source system: `pokemon_tcg_data`;
- source expansion ID: `xy5`;
- expected canonical cards: `164`;
- image metadata present for all `164` cards.

## Controlled Import Slice

The first controlled import slice was deliberately restricted to canonical Primal Clash cards.

```text
data/fixtures/primal-clash/canonical-cards.json
→ import_runs
→ staging_cards
```

The first dry run did not modify production catalogue, market, mapping, price, or wishlist tables.

### Production tables excluded from the initial staging slice

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

## Source-to-Target Documentation

Created:

```text
docs/import/primal-clash-source-to-target.md
```

The document records:

- the controlled canonical-card source artifact;
- the fixture envelope;
- source-to-`staging_cards` field mapping;
- raw payload preservation;
- the later staging-to-production projection;
- import-run lifecycle;
- staging state lifecycle;
- record-level validation rules;
- dry-run isolation requirements;
- acceptance criteria.

### Confirmed fixture shape

Top-level fields:

- `sourceFile`;
- `sourceSystem`;
- `setId`;
- `recordCount`;
- `records`.

Representative card fields:

- `id`;
- `name`;
- `supertype`;
- `subtypes`;
- `hp`;
- `types`;
- `evolvesTo`;
- `attacks`;
- `weaknesses`;
- `retreatCost`;
- `convertedRetreatCost`;
- `number`;
- `artist`;
- `rarity`;
- `flavorText`;
- `nationalPokedexNumbers`;
- `legalities`;
- `images`.

The first import projection uses dedicated staging columns for source identity, collector number, name, rarity, and image URLs. The complete card object is preserved in `raw_payload`.

## PostgreSQL Driver

Installed and validated Psycopg 3:

```text
psycopg 3.3.4
```

Created:

```text
requirements.txt
```

with:

```text
psycopg[binary]==3.3.4
```

Validation command:

```powershell
python -m pip install -r requirements.txt
```

Result:

```text
Requirement already satisfied
```

## Database Connection

PostgreSQL is exposed locally through:

```text
127.0.0.1:5432
```

Connection settings used:

```text
POSTGRES_DB=pokemon_wishlist
POSTGRES_USER=pokemon_app
```

The password remained outside the repository and was read from `.env`.

A session-scoped connection URL was set in PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://pokemon_app:<PASSWORD>@127.0.0.1:5432/pokemon_wishlist"
```

Connection validation:

```powershell
python -c "import os, psycopg; conn = psycopg.connect(os.environ['DATABASE_URL']); print(conn.execute('SELECT current_database(), current_user').fetchone()); conn.close()"
```

Confirmed result:

```text
('pokemon_wishlist', 'pokemon_app')
```

The database was also inspected successfully through DBeaver.

## Canonical Catalogue Staging Importer

Created:

```text
scripts/import/import_primal_clash_catalogue.py
```

### Responsibilities

The script:

- reads `canonical-cards.json`;
- validates the fixture envelope;
- verifies the expected source system, set ID, and record count;
- calculates the source artifact SHA-256 checksum;
- normalizes all canonical card records;
- extracts small and large image URLs;
- preserves each complete source record in `raw_payload`;
- calculates deterministic per-record checksums;
- validates source identities and image URL patterns;
- creates one `import_runs` row;
- inserts records into `staging_cards`;
- validates persisted counts and states;
- advances the run lifecycle:
  - `created`;
  - `staging_loaded`;
  - `validated`;
- commits a persistent validated staging run;
- does not perform a production merge.

### Source artifact checksum

```text
5459b8982782a31829526e8fb7eb76cbfb18d09c092034505be77cfe9a2b5110
```

### Local fixture validation result

```text
Primal Clash catalogue fixture validation passed
Source file: xy5.json
Source system: pokemon_tcg_data
Set ID: xy5
Record count: 164
Normalized records: 164
Valid records: 164
Rejected records: 0
```

## First Persistent Staging Run

Command:

```powershell
python scripts/import/import_primal_clash_catalogue.py `
  --run-reference primal-clash-catalogue-dry-run-001 `
  --importer-version m4-first-import-v1
```

Result:

```text
Import run ID: 1
Run reference: primal-clash-catalogue-dry-run-001
Staged records: 164
Valid records: 164
Rejected records: 0
Final status: validated
Production merge: not executed
```

### SQL validation

Confirmed:

- `status = validated`;
- `total_source_records = 164`;
- `valid_source_records = 164`;
- `rejected_records = 0`;
- `staging_loaded_at` populated;
- `validated_at` populated;
- `merge_started_at = NULL`;
- `completed_at = NULL`;
- `164` staging rows;
- `164` valid staging rows;
- `0` rejected staging rows;
- `0` incomplete staging rows;
- `0` duplicate source identities;
- all checked production tables remained empty.

## Transactional Rollback Validation

Created:

```text
scripts/import/fail_import_primal_clash_catalogue.py
```

### Purpose

The script intentionally:

1. creates an import run inside a transaction;
2. inserts a controlled number of staging rows;
3. raises an intentional exception;
4. verifies that the transaction rolled back completely.

Command:

```powershell
python scripts/import/fail_import_primal_clash_catalogue.py `
  --run-reference primal-clash-catalogue-rollback-test-001 `
  --importer-version m4-first-import-v1 `
  --fail-after-records 10
```

Confirmed result:

```text
Expected failure triggered: Intentional rollback validation failure after 10 staging records.
Transactional rollback validation passed
Attempted import run ID: 2
Run reference: primal-clash-catalogue-rollback-test-001
Surviving import runs: 0
Surviving staging rows: 0
```

The missing sequence value `2` is expected PostgreSQL sequence behaviour and does not indicate a surviving row.

## Repeat Staging Import

Command:

```powershell
python scripts/import/import_primal_clash_catalogue.py `
  --run-reference primal-clash-catalogue-dry-run-002 `
  --importer-version m4-first-import-v1
```

Result:

```text
Import run ID: 3
Run reference: primal-clash-catalogue-dry-run-002
Staged records: 164
Valid records: 164
Rejected records: 0
Final status: validated
Production merge: not executed
```

### Repeat staging validation

Confirmed for runs `1` and `3`:

- both had status `validated` before their production merges;
- both used the same source artifact checksum;
- each contained exactly `164` staging rows;
- each reported `164` valid and `0` rejected records;
- duplicate source identities within each run: `0`;
- production tables remained unchanged during staging.

This validates repeatable staging snapshots. It does not by itself prove production idempotency.

## Production Catalogue Merge

Created:

```text
scripts/import/merge_primal_clash_catalogue.py
```

### Responsibilities

The script:

- accepts a validated `import_run_id`;
- locks and verifies the selected run;
- verifies the controlled fixture checksum and scope;
- validates persisted staging rows;
- refuses runs with pending, rejected, duplicate, or incomplete records;
- creates or resolves the internal Primal Clash expansion;
- creates or resolves the Pokémon TCG Data source identifier;
- merges cards by production identity:
  - `(source_system, source_card_id)`;
- records one `import_record_outcomes` row per staged card;
- distinguishes:
  - `inserted`;
  - `updated`;
  - `unchanged`;
  - `reactivated`;
- validates production and outcome counts;
- completes the import run as `succeeded`;
- executes the complete merge in one PostgreSQL transaction.

### Expansion bootstrap

Confirmed production values:

```text
expansion_key = primal_clash
name = Primal Clash
source_system = pokemon_tcg_data
source_expansion_id = xy5
source_name = Primal Clash
```

The generated `expansion_id` was `2`. Sequence gaps are valid and are not treated as errors.

## First Production Merge

Command:

```powershell
python scripts/import/merge_primal_clash_catalogue.py `
  --import-run-id 1
```

Result:

```text
Primal Clash catalogue production merge committed
Import run ID: 1
Run reference: primal-clash-catalogue-dry-run-001
Expansion ID: 2
Inserted cards: 164
Updated cards: 0
Reactivated cards: 0
Unchanged cards: 0
Processed cards: 164
Final status: succeeded
```

### First merge validation

Confirmed:

```text
status = succeeded
inserted_records = 164
updated_records = 0
unchanged_records = 0
missing_records = 0
retired_records = 0
```

Production state:

```text
expansions = 1 Primal Clash expansion
cards_total = 164
active_cards = 164
missing_image_references = 0
duplicate_source_identities = 0
```

Audit outcomes:

```text
inserted = 164
```

## Repeat Production Merge

Command:

```powershell
python scripts/import/merge_primal_clash_catalogue.py `
  --import-run-id 3
```

Result:

```text
Primal Clash catalogue production merge committed
Import run ID: 3
Run reference: primal-clash-catalogue-dry-run-002
Expansion ID: 2
Inserted cards: 0
Updated cards: 0
Reactivated cards: 0
Unchanged cards: 164
Processed cards: 164
Final status: succeeded
```

### Production idempotency validation

Confirmed:

```text
run 1:
  inserted = 164
  updated = 0
  unchanged = 0

run 3:
  inserted = 0
  updated = 0
  unchanged = 164
```

Final production state:

```text
cards_total = 164
active_cards = 164
duplicate_source_identities = 0
```

Audit outcomes:

```text
run 1: inserted = 164
run 3: unchanged = 164
```

This proves that an identical repeated production import does not create uncontrolled card duplicates.

## Confirmed Results

The following canonical catalogue path is now implemented and validated:

```text
fixture envelope validation
→ record normalization
→ image-reference extraction
→ persistent PostgreSQL staging
→ staging count and uniqueness validation
→ repeat staging
→ partial-write rollback
→ expansion bootstrap
→ production card insertion
→ import outcome recording
→ repeated production merge
→ unchanged-record detection
→ production duplicate prevention
```

Confirmed counts:

- source canonical cards: `164`;
- normalized cards: `164`;
- valid cards: `164`;
- rejected cards: `0`;
- first production insert: `164`;
- repeated production insert: `0`;
- repeated unchanged cards: `164`;
- active production cards: `164`;
- missing image references: `0`;
- duplicate production identities: `0`.

## Important Limitations

This work does not complete all of `M4 — First import`.

Not yet implemented or validated:

- Cardmarket product staging and production merge;
- `177` Cardmarket products;
- excluded Online Code Card workflow;
- six `unmatched_duplicate_candidate` products;
- Cardmarket mapping staging and merge;
- `167` confirmed candidate product mappings;
- card editions and variants produced from market data;
- Cardmarket price staging;
- `177` market price records;
- `market_price_snapshots`;
- runtime canonical-card minimum non-null `avg30` `From` price query;
- real rejected-record persistence using invalid fixture data;
- missing and retirement behaviour for authoritative catalogue snapshots;
- production merge rollback through a dedicated failure-injection test;
- a complete M4 import validation report;
- M4 documentation and repository-wide exit validation;
- wishlist application workflow.

## Files Created or Updated

Created during this work:

```text
docs/import/primal-clash-source-to-target.md
requirements.txt
scripts/import/import_primal_clash_catalogue.py
scripts/import/fail_import_primal_clash_catalogue.py
scripts/import/merge_primal_clash_catalogue.py
```

Local Python dependency added:

```text
psycopg[binary]==3.3.4
```

## Current Database State

Relevant confirmed rows:

```text
import_runs:
- run 1: succeeded
- run 3: succeeded

staging_cards:
- 164 rows for run 1
- 164 rows for run 3

expansions:
- 1 Primal Clash expansion

expansion_source_identifiers:
- pokemon_tcg_data / xy5

cards:
- 164 active Primal Clash cards

import_record_outcomes:
- run 1: 164 inserted
- run 3: 164 unchanged
```

The rollback test run did not survive, but its attempted sequence ID was `2`.

## Recommended Next Block

Continue `M4 — First import` with Cardmarket products:

```text
data/fixtures/primal-clash/cardmarket-products.json
→ staging_market_products
→ market_products
```

The next work should begin by:

1. inspecting the actual fixture fields in `cardmarket-products.json`;
2. inspecting actual columns and constraints in:
   - `staging_market_products`;
   - `market_products`;
3. documenting the exact source-to-staging mapping;
4. defining the handling of the four excluded Online Code Card products;
5. defining staging and production acceptance criteria;
6. implementing persistent staging, rollback, merge, and repeat-import validation.

Do not return to schema design unless the real Cardmarket import reveals a confirmed schema problem.
