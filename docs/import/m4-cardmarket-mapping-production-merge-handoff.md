# M4 Cardmarket Mapping Production Merge Handoff

## Project

Pokemon Card Wishlist

## Current milestone

`M4 — First import`

## Purpose

This handoff records the completed controlled Primal Clash Cardmarket mapping
pipeline and the exact next work block.

## Completed pipeline

The following path is implemented and validated:

```text
data/fixtures/primal-clash/mapping-review.csv
-> staging_market_mappings
-> card_market_mapping_cases
-> mapping_case_observations
-> mapping_candidates
-> mapping_status_history
-> card_market_product_mappings
```

## Controlled fixture state

The current Primal Clash fixture contains `177` records:

- `165` `candidate`;
- `6` `excluded`;
- `6` `unmatched_duplicate_candidate`;
- `10` candidate rows with a non-null `edition_code`.

The six excluded records are:

- four Online Code Card products that are outside MVP product scope and do not
  exist in `market_products`;
- two oversized products:
  - Cardmarket `363664`;
  - Cardmarket `363665`.

## Implemented utilities

Permanent utilities:

- `scripts/import/import_primal_clash_market_mappings.py`
- `scripts/import/fail_import_primal_clash_market_mappings.py`
- `scripts/import/validate_primal_clash_market_mapping_merge.py`
- `scripts/import/fail_merge_primal_clash_market_mappings.py`
- `scripts/import/merge_primal_clash_market_mappings.py`

## Validated staging source

First production merge source:

```text
import_run_id = 10
run_reference = primal-clash-market-mappings-dry-run-003
status before merge = validated
```

Validated staging counts:

- `177` staged;
- `177` valid;
- `0` rejected;
- `165` candidate;
- `6` excluded;
- `6` unmatched duplicate candidates;
- `10` candidate rows with edition code.

## Mapping strategy

### Candidate records

Candidate records are confirmed at canonical-card scope:

```text
current_status = confirmed
observation_status = confirmed
confirmation_scope = card
confirmation_method = direct_source_identifier
evidence_level = direct
candidate_scope = card
candidate_state = selected
card_edition_id = NULL
card_variant_id = NULL
```

No `card_editions` or `card_variants` are created automatically.

### Oversized exclusions

The two oversized products create resolved `excluded` mapping cases and
observations, but no candidate or active production mapping.

Controlled reason:

```text
oversized_card_out_of_scope
```

### Online Code Card exclusions

The four Online Code Card records cannot create mapping cases because their
products do not exist in `market_products`.

They are preserved through skipped import outcomes.

Controlled reason:

```text
online_code_card_out_of_scope
```

### Unmatched duplicate candidates

The six `unmatched_duplicate_candidate` records create resolved mapping cases
and observations without card targets, candidates, or active production
mappings.

Controlled reason:

```text
unmatched_duplicate_candidate
```

## Rollback validation

Production mapping rollback validation was completed with:

```text
scripts/import/fail_merge_primal_clash_market_mappings.py
```

The utility attempted one complete mapping chain inside a transaction and then
raised an intentional exception.

Confirmed survivors after rollback:

- mapping cases: `0`;
- observations: `0`;
- candidates: `0`;
- status history: `0`;
- production mappings: `0`;
- import outcomes: `0`.

The source run remained `validated`.

## First production merge

Run:

```text
import_run_id = 10
run_reference = primal-clash-market-mappings-dry-run-003
```

Result:

- inserted production mappings: `165`;
- unchanged production mappings: `0`;
- skipped controlled records: `12`;
- inserted mapping cases: `173`;
- inserted observations: `173`;
- inserted candidates: `165`;
- inserted status transitions: `173`;
- processed source records: `177`;
- final status: `succeeded`.

Database validation:

- mapping cases: `173`;
- observations: `173`;
- candidates: `165`;
- status history: `173`;
- active production mappings: `165`;
- run outcomes: `177`.

## Repeat production merge

Repeat staging run:

```text
import_run_id = 12
run_reference = primal-clash-market-mappings-dry-run-004
```

Repeat merge result:

- inserted production mappings: `0`;
- unchanged production mappings: `165`;
- skipped controlled records: `12`;
- inserted mapping cases: `0`;
- inserted observations: `173`;
- inserted candidates: `165`;
- inserted status transitions: `0`;
- processed source records: `177`;
- final status: `succeeded`.

Database validation after repeat merge:

- mapping cases: `173`;
- observations: `346`;
- candidates: `330`;
- status history: `173`;
- active production mappings: `165`;
- run `12` outcomes: `177`.

This confirms that production mappings and case state are idempotent while
observations and selected candidates preserve repeated import evidence.

## Commits

Relevant commits:

```text
26d8d63 Add Cardmarket mapping rollback validation
0eb3c63 Exclude oversized Cardmarket products
0a1c0a1 Add Cardmarket mapping merge rollback validation
b99ddb1 Add Cardmarket mapping pre-merge validation
3c91920 Implement Cardmarket mapping production merge
```

## GitHub Project

Use the existing Cardmarket mapping issue.

Add these commits to Evidence:

```text
0a1c0a1
b99ddb1
3c91920
```

The issue can move from `In progress` to `Review` after project documentation
and final validation evidence are updated.

Do not move it to `Done` until the documentation review and milestone exit
review are complete.

## Documentation to update

Update the coherent M4 documentation block:

- `README.md`;
- `PROJECT.md`;
- `ROADMAP.md`;
- `CHANGELOG.md`;
- `LEARNING_LOG.md`;
- relevant import documentation under `docs/import/`.

Document:

- controlled mapping counts;
- oversized and Online Code Card exclusions;
- rollback validation;
- first merge;
- repeat merge;
- final production counts;
- card-level confirmation boundary;
- deferred edition and variant classification.

## Next concrete task

Perform the documentation and evidence update for the completed Cardmarket
mapping pipeline.

Recommended order:

1. remove the two obsolete staging handoff files;
2. add this production-merge handoff;
3. update core project documentation;
4. add commits and validation results to the GitHub issue;
5. run Markdown lint and Git diff checks;
6. commit the documentation update;
7. perform the M4 mapping-block exit review.

## Recommended next chat title

```text
09 — M4 Cardmarket Mapping Documentation and Exit Review
```
