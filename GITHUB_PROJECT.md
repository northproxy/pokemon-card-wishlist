# GitHub Project Configuration

## Project title

Pokemon Card Wishlist

## Project description

Build a self-hosted, mobile-friendly Pokemon card catalogue with wishlist selection and CSV export. Use the project to demonstrate structured delivery, data discovery, architecture decisions, documentation, data modelling, infrastructure work, security awareness, validation, and continuous learning.

## Implemented views

### Roadmap

Group issues by project phase:

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

Filter items with `Area = Documentation`.

### Risks and decisions

Filter items with `Type = Decision` or `Risk = High`.

### Data quality

Filter items with `Area = Data`, `Area = Database`, or `Area = Import`.

## Implemented custom fields

| Field | Values |
|---|---|
| Status | Backlog, Ready, In progress, Review, Blocked, Done |
| Priority | P0, P1, P2, P3 |
| Type | Feature, Task, Bug, Research, Documentation, Decision |
| Area | Data, Database, Import, Infrastructure, UI, Security, Documentation |
| Project phase | M0, M1, M2, M3, M4, M5, M6, M7 |
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

**Status:** Completed and validated on 2026-07-27

Completed or accepted:

- Inventoried the available Cardmarket and Pokémon TCG Data sources.
- Documented representative source fields.
- Defined the canonical-card boundary.
- Accepted source-scoped import keys.
- Separated canonical cards, editions, language and finish variants, and market products.
- Selected Primal Clash as the first vertical slice.
- Defined the canonical-card `From` price as the minimum supported non-null `avg30`.
- Built the reproducible Primal Clash mapping fixture.
- Replaced inferred product ordering with direct Cardmarket `idProduct` evidence.
- Validated deterministic canonical-card image metadata.
- Classified Online Code Card products as excluded.
- Preserved six unlisted duplicate-like products as `unmatched_duplicate_candidate`.
- Completed the M0 discovery validation summary and exit review.

Decision status after M0:

- `ADR-008` is accepted and defines staging plus validated transactional merges for repeated imports.
- `ADR-009` is accepted and defines controlled rejected and unresolved-record review states.
- `ADR-010` is proposed and defines the backup, retention, and restore-validation strategy awaiting M2 implementation evidence.

`ADR-008` and `ADR-009` are prerequisites for the physical data model and import workflow. `ADR-010` remains a prerequisite for completing and validating the infrastructure milestone. None of these decisions invalidates the completed M0 vertical-slice discovery result.

### M1 — Repository foundation

**Status:** Completed and validated on 2026-07-27

Completed outcomes:

- Created the repository structure.
- Added and cross-linked the core project documentation.
- Added issue templates for tasks, bugs, research, and decisions.
- Added a pull request template.
- Added security notes in `SECURITY.md`.
- Added contribution guidance in `CONTRIBUTING.md`.
- Added `CHANGELOG.md` and `ROADMAP.md`.
- Added and validated Markdown checks through GitHub Actions.
- Created and published the GitHub repository.
- Configured the GitHub Project fields and views.
- Created and classified the initial M1 issue set.
- Validated the `Current milestone` view with real issues.
- Verified the public README links, workflow badge, and issue-template contact links.
- Completed the M1 exit review against `PROJECT.md`.

### M2 — Infrastructure

**Status:** Current milestone; ready to start

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

## M1 validation issue set

### 1. Configure the GitHub Project fields and views

**Type:** Task
**Project phase:** M1
**Priority:** P0
**Effort:** S

Acceptance criteria:

- the project contains the approved custom fields;
- the Roadmap, Board, Current milestone, Documentation, Risks and decisions, and Data quality views exist;
- the Current milestone view filters to `M1`;
- field values match this document;
- the configuration is verified from the published GitHub Project.

### 2. Create the initial M1 issue set

**Type:** Task
**Project phase:** M1
**Priority:** P0
**Effort:** S

Acceptance criteria:

- remaining M1 work is represented by GitHub issues;
- every issue has Type, Area, Project phase, Priority, Effort, Learning value, and Risk values;
- completed M0 research is not recreated as active work;
- issue acceptance criteria distinguish implementation from validation.

### 3. Verify published repository documentation links

**Type:** Documentation
**Project phase:** M1
**Priority:** P0
**Effort:** XS

Acceptance criteria:

- every link in `README.md` opens successfully from GitHub;
- the Markdown validation badge opens the correct workflow;
- issue-template contact links open successfully;
- no tracked document links to `docs/chatgpt_project/`;
- broken or misleading links are corrected.

### 4. Complete the M1 exit review

**Type:** Task
**Project phase:** M1
**Priority:** P0
**Effort:** S

Acceptance criteria:

- all M1 deliverables are present;
- GitHub Project configuration is validated;
- Markdown validation passes;
- repository purpose, scope, status, decisions, and next work are clear;
- planned, implemented, and validated states are consistent;
- the result is recorded in `CHANGELOG.md`, `PROJECT.md`, `ROADMAP.md`, and `LEARNING_LOG.md`.

## Example future decision issue

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
