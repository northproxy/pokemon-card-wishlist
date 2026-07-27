# GitHub Project Draft

## Project title

Pokemon Card Wishlist

## Project description

Build a self-hosted, mobile-friendly Pokemon card catalogue with wishlist selection and CSV export. Use the project to demonstrate structured delivery, data discovery, architecture decisions, documentation, data modelling, infrastructure work, security awareness, validation, and continuous learning.

## Recommended views

### Roadmap

Group issues by milestone:

- `M0 — Discovery`
- `M1 — Repository foundation`
- `M2 — Infrastructure`
- `M3 — Data model`
- `M4 — First import`
- `M5 — Wishlist workflow`
- `M6 — Catalogue expansion`
- `M7 — MVP release`

### Board

Use these status values:

- Backlog
- Ready
- In progress
- Review
- Blocked
- Done

### Current milestone

Filter to the active milestone and sort by:

1. Priority
2. Dependency order
3. Effort

### Documentation

Filter issues with the `documentation` label.

### Risks and decisions

Filter issues with the `risk` or `decision` label.

### Data quality

Filter issues with:

- `data-quality`;
- `blocked`;
- Area = Data or Database.

## Suggested custom fields

| Field | Values |
|---|---|
| Status | Backlog, Ready, In progress, Review, Blocked, Done |
| Priority | P0, P1, P2, P3 |
| Type | Feature, Task, Bug, Research, Documentation, Decision |
| Area | Data, Database, Import, Infrastructure, UI, Security, Documentation |
| Milestone | M0, M1, M2, M3, M4, M5, M6, M7 |
| Effort | XS, S, M, L, XL |
| Learning value | Low, Medium, High |
| Risk | Low, Medium, High |

## Suggested labels

### Work type

- `feature`
- `bug`
- `documentation`
- `research`
- `decision`

### Technical area

- `data-quality`
- `database`
- `import`
- `infrastructure`
- `security`
- `ui`

### Workflow

- `mvp`
- `blocked`
- `good-first-task`
- `risk`

## Initial backlog

### M0 — Discovery

Completed or accepted:

- Inventory the available Cardmarket and Pokémon TCG Data sources.
- Document representative source fields.
- Define the canonical-card boundary.
- Accept source-scoped import keys.
- Separate canonical card, edition, language/finish variant, and market product.
- Select Primal Clash as the first vertical slice.
- Define the canonical-card `From` price as the minimum supported non-null `avg30`.

Remaining work:

- Complete the reproducible Primal Clash mapping fixture.
- Review image filenames and local image mapping feasibility.
- Classify confirmed, candidate, ambiguous, excluded, unmatched, and rejected records.
- Document Cardmarket edition and finish evidence for ambiguous products.
- Define repeated import and upsert behaviour in `ADR-008`.
- Define rejected, unmatched, and ambiguous record handling in `ADR-009`.
- Prepare the M0 discovery validation summary and exit review.

### M1 — Repository foundation

- Create the repository structure.
- Add and cross-link core documentation.
- Add issue templates.
- Add pull request template.
- Add security notes.
- Add contribution guidance.
- Add changelog.
- Add Markdown validation.
- Create GitHub Project views and fields.
- Create the initial release roadmap.

### M2 — Infrastructure

- Prepare Raspberry Pi OS.
- Connect and validate SSD.
- Install Docker.
- Create Docker Compose configuration.
- Deploy PostgreSQL.
- Deploy NocoDB.
- Configure persistent volumes.
- Configure secrets.
- Configure Tailscale.
- Test phone access.
- Document backup process.
- Test restore process.
- Document restart recovery.

### M3 — Data model

- Translate accepted catalogue concepts into a physical schema.
- Create `expansions`.
- Create canonical `cards`.
- Create `card_editions`.
- Create `card_variants`.
- Create `market_products`.
- Create card-to-market-product mapping structures.
- Create `market_price_snapshots`.
- Create `wishlist_items` referencing canonical cards.
- Create import-run tracking.
- Create rejected-record structure.
- Create unmatched- and ambiguous-mapping structures.
- Add source-scoped unique constraints.
- Add foreign keys and indexes.
- Create staging tables.
- Write migrations.
- Write the data dictionary.
- Write validation queries, including the minimum `avg30` rule.

### M4 — First import

- Prepare a one-expansion fixture.
- Map source fields to target fields.
- Map images.
- Implement import logic.
- Run dry-run validation.
- Import the expansion.
- Validate row counts.
- Check duplicate records.
- Record rejected items.
- Record unmatched items.
- Report missing images.
- Repeat the import and verify idempotent behaviour.
- Create the import validation report.

### M5 — Wishlist workflow

- Create catalogue table view.
- Create gallery view.
- Add search.
- Add expansion filter.
- Add metadata filters.
- Add image preview.
- Add wanted control.
- Add quantity field.
- Add notes field.
- Create Wishlist view.
- Configure CSV export.
- Protect catalogue fields from unintended editing.
- Test the complete mobile flow.
- Document NocoDB limitations.

### M6 — Catalogue expansion

- Create repeatable batch import.
- Import supported expansions.
- Produce one import summary per expansion.
- Maintain unmatched-record queue.
- Maintain rejected-record queue.
- Produce missing-image report.
- Produce duplicate and data-quality report.
- Mark unsupported expansions explicitly.

### M7 — MVP release

- Complete MVP acceptance test.
- Capture evidence screenshots.
- Create architecture diagram.
- Write setup and operating guide.
- Write demo walkthrough.
- Write release notes.
- Publish known limitations.
- Publish lessons learned.
- Verify backup and restore documentation.
- Tag version `v0.1.0`.

## First recommended Ready issues

### 1. Complete the Primal Clash mapping fixture

**Type:** Research
**Milestone:** M0
**Priority:** P0
**Effort:** M

Acceptance criteria:

- all 164 canonical `xy5` cards are present;
- all Cardmarket expansion `1585` products are represented;
- code cards are explicitly excluded;
- each mapping has a status, method, and evidence reference;
- ambiguous edition or finish mappings are not silently resolved;
- linked price records and source timestamps are preserved.

### 2. Define repeated import and upsert behaviour

**Type:** Decision
**Milestone:** M0
**Priority:** P0
**Effort:** M

Acceptance criteria:

- conflict targets use the accepted source-scoped keys;
- insert, update, unchanged, missing-from-source, and retired-source cases are defined;
- wishlist preservation rules are documented;
- repeat-import validation is specified;
- the accepted decision is recorded as `ADR-008`.

### 3. Define rejected, unmatched, and ambiguous record handling

**Type:** Decision
**Milestone:** M0
**Priority:** P0
**Effort:** M

Acceptance criteria:

- rejected, unmatched, ambiguous, candidate, confirmed, and excluded states are defined;
- each state has required evidence and review fields;
- no ambiguous mapping is silently promoted to confirmed;
- import-report requirements are documented;
- the accepted decision is recorded as `ADR-009`.

### 4. Review image naming and mapping feasibility

**Type:** Research
**Milestone:** M0
**Priority:** P1
**Effort:** M

Acceptance criteria:

- image directory structure is documented;
- naming rules are described;
- canonical-card and edition-level mapping possibilities are tested;
- missing and duplicate image risks are recorded;
- Primal Clash image coverage is reported.

## Example decision issue

### Title

Define repeated import and upsert behaviour

### Type

Decision

### Context

Repeated catalogue and price imports must update source-derived data without creating uncontrolled duplicates, deleting wishlist data, or silently retiring records that disappear from one snapshot.

### Candidate approaches

- direct upsert into production tables;
- staging followed by validated merge;
- append-only source snapshots with derived current-state tables.

### Acceptance criteria

- source-scoped conflict targets are specified;
- insert, update, unchanged, missing, and retired cases are defined;
- wishlist preservation is guaranteed;
- ambiguous mappings remain reviewable;
- repeat-import and rollback validation are defined;
- the selected approach is recorded in `DECISIONS.md` as `ADR-008`.

## Pull request checklist

- [ ] Scope of the change is clear.
- [ ] Acceptance criteria are satisfied.
- [ ] Relevant tests or validation checks passed.
- [ ] Documentation is updated.
- [ ] Database changes are reversible where practical.
- [ ] Security impact was considered.
- [ ] Data validation was performed.
- [ ] Relevant ADR or Learning Log update was prepared.
- [ ] Evidence is included where useful.
- [ ] Planned, implemented, and validated states are represented accurately.
