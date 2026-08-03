# M4 First Import Exit Review

## Document status

- Milestone: `M4 — First import`
- Review status: Completed
- Completion date: 2026-08-03
- Validated expansion: Primal Clash
- Pokémon TCG Data set: `xy5`
- Cardmarket expansion ID: `1585`
- Validation scope: Canonical-card import vertical slice

## Purpose

This document records the formal exit review for `M4 — First import`.

It evaluates the implemented and validated Primal Clash import against the
milestone exit criteria defined in `PROJECT.md` and `ROADMAP.md`.

Detailed implementation, reconciliation, rollback, repeat-import, mapping,
pricing, image, and limitation evidence is maintained in:

```text
docs/import/primal-clash-import-validation-report.md
```

This exit review does not replace that report. It records the milestone-level
decision based on the completed validation evidence.

## Reviewed evidence

The exit review considered:

- the M4 goal, deliverables, and exit criteria in `PROJECT.md`;
- the M4 milestone status and exit condition in `ROADMAP.md`;
- the import and validation requirements in `MVP_SCOPE.md`;
- the accepted import, mapping, pricing, and scope decisions in
  `DECISIONS.md`;
- the consolidated Primal Clash import validation report;
- permanent database and runtime validation utilities;
- recorded import-run and rollback evidence;
- the final controlled production state.

## Final validated production state

| Object or result                           | Final count |
| ------------------------------------------ | ----------: |
| Active canonical cards                     |       `164` |
| Active Cardmarket market products          |       `173` |
| Active canonical-card mappings             |       `165` |
| Market price snapshots                     |       `173` |
| Canonical cards with runtime `From` prices |       `164` |
| `card_editions`                            |         `0` |
| `card_variants`                            |         `0` |
| Duplicate market-product source identities |         `0` |
| Duplicate price-snapshot identities        |         `0` |
| Online Code Card products in production    |         `0` |

The controlled source scope contains:

- `164` canonical-card records;
- `177` Cardmarket product records;
- `177` Cardmarket mapping records;
- `177` Cardmarket price records.

Every source record is represented through one of the accepted outcomes:

- imported;
- unchanged on repeated import;
- explicitly skipped;
- preserved as a resolved exclusion;
- preserved as `unmatched_duplicate_candidate`.

No source discrepancy is silently discarded.

## Exit-criteria assessment

### Selected expansion is imported completely or discrepancies are documented

**Status: Pass**

Primal Clash is imported completely at the supported canonical-card scope.

The final controlled result includes:

- `164` active canonical cards;
- `173` active Cardmarket products;
- `165` active canonical-card mappings;
- `173` append-only market price snapshots;
- runtime `From` prices for all `164` canonical cards.

All records outside the accepted production mapping scope remain explicitly
classified:

- `4` Online Code Card records are preserved as skipped outcomes;
- `2` oversized products are preserved as resolved exclusions;
- `6` products remain preserved as `unmatched_duplicate_candidate`;
- ordinary `unmatched` mappings: `0`;
- `ambiguous` mappings: `0`;
- mapping conflicts: `0`;
- rejected source records: `0`.

### Image mapping is validated

**Status: Pass**

Image validation confirmed:

- `164` canonical cards with small image URLs;
- `164` canonical cards with large image URLs;
- `0` missing small image URLs;
- `0` missing large image URLs;
- `164` unique small image URLs;
- `164` unique large image URLs;
- `328` local PNG files;
- `0` remaining partial download files.

The repeated image download completed with no new downloads, failures, invalid
records, or missing-image records.

### Repeated import does not create uncontrolled duplicates

**Status: Pass**

Repeated import behaviour was validated separately for current-state,
evidence-history, and append-only data.

The repeated canonical-card import created no duplicate canonical-card
identities.

The repeated Cardmarket product merge produced:

```text
173 unchanged
4 skipped
0 uncontrolled inserts
```

The repeated mapping merge produced:

```text
165 unchanged active mappings
12 skipped outcomes
0 new mapping cases
0 new active mappings
0 new status transitions
```

Additional mapping observations and selected-candidate evidence were preserved
as expected without changing stable production state.

The repeated Cardmarket price merge produced:

```text
173 unchanged snapshots
0 inserted snapshots
4 skipped outcomes
```

No duplicate `(market_product_id, source_snapshot_at)` identities were created.

### Rejected and unmatched records remain visible

**Status: Pass**

No rejected source records exist in the controlled Primal Clash fixture.

Expected exclusions and unresolved records remain visible through controlled
audit and review structures.

The final unresolved and exclusion state includes:

- `4` Online Code Card skipped outcomes;
- `2` resolved oversized exclusions;
- `6` `unmatched_duplicate_candidate` records.

The unresolved duplicate candidates remain valid market products but:

- do not create canonical-card mappings;
- do not create editions or variants;
- do not participate in canonical-card pricing.

### Import evidence is stored

**Status: Pass**

The implemented import workflow preserves:

- import runs;
- persistent staging records;
- per-record import outcomes;
- rejected-record structures;
- mapping cases;
- mapping observations;
- mapping candidates;
- mapping status history;
- active production mappings;
- append-only market price snapshots;
- rollback evidence;
- repeat-import evidence;
- permanent executable validation scripts;
- the consolidated validation report.

Every production run reconciles its declared source scope through controlled
per-record outcomes.

## Additional validation results

The following results strengthen the formal M4 completion decision.

### Production mappings match the accepted fixture

**Status: Pass**

The accepted fixture and production state contain:

```text
165 active canonical-card mappings
```

No unresolved or excluded product contributes an active mapping.

### Informational pricing matches the accepted rule

**Status: Pass**

The permanent runtime validator confirms the accepted pricing path:

```text
canonical card
→ active canonical-card mapping
→ active Cardmarket market product
→ latest eligible successful price snapshot
→ MIN(avg30)
```

Validation confirmed:

```text
165 active mapped market products
164 canonical cards with a runtime From price
```

The runtime value excludes `avg30_holo` and is suitable for the labels:

```text
From
30-day average
```

### Controlled failures leave no partial accepted production state

**Status: Pass**

Controlled rollback validation covered:

- Cardmarket product staging failure after a partial write;
- Cardmarket mapping production failure after one complete mapping chain;
- Cardmarket price staging failure after a partial write;
- Cardmarket price production failure after one snapshot and one audit outcome.

Each failure left the previous accepted production state unchanged and preserved
the ability to execute a subsequent valid run.

### Unsupported edition or variant data is not invented

**Status: Pass**

`ADR-013 — Defer automatic edition and variant derivation` is accepted.

The controlled source evidence proves canonical-card-to-market-product
relationships but does not prove complete:

- edition identity;
- language;
- finish;
- default edition semantics.

The current production state therefore intentionally contains:

```text
card_editions = 0
card_variants = 0
```

This is a documented source-evidence limitation, not an import failure.

## Blocking limitations assessment

No known limitation blocks formal completion of `M4 — First import`.

The following limitations remain accepted and documented.

### Edition and variant classification

Edition-, language-, and finish-specific production data is not yet available.

This prevents claims of validated:

- edition filtering;
- language filtering;
- finish filtering;
- edition-specific wishlist selection;
- variant-specific wishlist selection;
- complete edition, language, or finish values in CSV export.

This work requires a later controlled classification source or review process.

### Runtime no-price branch

All `164` controlled Primal Clash canonical cards currently have at least one
eligible non-null `avg30`.

The fixture therefore does not independently exercise a canonical card without
an available runtime price.

The current SQL semantics allow no price result, but that branch requires a
separate controlled validation case before the user-facing no-price behaviour is
claimed as validated.

### Cardmarket source timestamp semantics

Timezone-naive source timestamps are normalized deterministically by the
importer.

The fixture does not independently prove the original Cardmarket timezone
semantics.

### Application workflow

The following remain outside M4 and belong to `M5 — Wishlist workflow`:

- NocoDB configuration;
- catalogue browsing;
- search;
- filters;
- application image preview;
- wishlist selection;
- wanted quantity and notes;
- Wishlist view;
- CSV export;
- mobile browser validation.

### Infrastructure

The following remain outside M4 and belong to infrastructure work:

- Raspberry Pi deployment;
- SSD-backed production persistence;
- NocoDB deployment;
- private Tailscale access;
- backup scheduling;
- restore validation;
- Raspberry Pi restart recovery.

### Broader catalogue coverage

Only Primal Clash is validated as the implementation vertical slice.

Additional expansion imports remain part of
`M6 — Catalogue expansion`.

## Milestone decision

`M4 — First import` satisfies its formal exit criteria.

The milestone is therefore:

```text
Status: Completed and validated
Completion date: 2026-08-03
Validated scope: Primal Clash canonical-card import vertical slice
Blocking limitations: None
```

The milestone completion does not claim that the complete MVP is validated.

It confirms that one complete expansion has passed the supported import,
mapping, image, pricing, repeated-import, audit, and rollback requirements at
canonical-card scope.

## Required project-status updates

Formal completion of M4 must be reflected consistently in:

- `PROJECT.md`;
- `ROADMAP.md`;
- `README.md`;
- `CHANGELOG.md`;
- `LEARNING_LOG.md`;
- the active GitHub Project issue.

The update must:

- mark `M4 — First import` as completed and validated on 2026-08-03;
- remove statements that the consolidated validation report or exit review
  remains incomplete;
- preserve the accepted limitations under `ADR-013`;
- move the active project focus to the next approved work block;
- avoid describing M5, infrastructure, or broader catalogue work as completed.

## GitHub issue evidence

The M4 exit-review issue should record:

- this exit-review document;
- `docs/import/primal-clash-import-validation-report.md`;
- validation report commit `423d6a2`;
- the documentation commit containing the formal milestone update;
- product import runs `4` and `6`;
- mapping production runs `10` and `12`;
- price import runs `13` and `15`;
- final production counts;
- permanent validation script results;
- the accepted `ADR-013` limitation;
- confirmation that repository documentation is consistent;
- confirmation that the working tree is clean after the final commit.

The issue may move to `Done` after the required documentation updates are
committed and the recorded evidence is complete.

## Evidence index

### Consolidated validation report

- `docs/import/primal-clash-import-validation-report.md`

### Architecture decisions

- `ADR-005 — Separate canonical cards from Cardmarket products`
- `ADR-006 — Use source-scoped identifiers as stable import keys`
- `ADR-008 — Use staging and validated transactional merges for repeated imports`
- `ADR-009 — Preserve rejected and unresolved import records through controlled review states`
- `ADR-011 — Display the minimum 30-day average as the canonical card price`
- `ADR-012 — Preserve unlisted duplicate-like Cardmarket products as unmatched candidates`
- `ADR-013 — Defer automatic edition and variant derivation`

### Permanent validation utilities

- `scripts/database/validate_schema.sql`
- `scripts/database/validate_primal_clash_from_prices.sql`
- `scripts/images/download_card_images.py`

### Relevant commits

- `ad3a2d9` — Add repeatable card image download workflow
- `5b49bda` — Implement Cardmarket price import pipeline
- `e3d2a53` — Document Cardmarket price import validation
- `b19b0b0` — Document edition and variant derivation deferral
- `423d6a2` — Add Primal Clash import validation report

## Conclusion

The Primal Clash vertical slice provides sufficient implementation and
validation evidence to close `M4 — First import`.

The completed milestone demonstrates:

- complete controlled source reconciliation;
- repeatable staged imports;
- transactional production merges;
- explicit exclusions and unresolved-record handling;
- stable current production identities;
- append-only market price evidence;
- runtime canonical-card `From` pricing;
- deterministic image coverage;
- rollback safety;
- honest documentation of unsupported edition and variant scope.

No current limitation requires M4 to remain open.
