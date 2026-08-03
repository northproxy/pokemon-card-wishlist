# Learning Log

The purpose of this log is to show how understanding develops through concrete project work.

Entries must be:

- honest;
- concise;
- connected to completed or actively investigated work;
- clear about uncertainty;
- explicit about how learning changed the project.

Do not use this file as a generic task history. Routine progress belongs in issues, pull requests, or milestone summaries.

## When to add an entry

Add an entry when at least one of the following occurs:

- a technical assumption is confirmed or disproved;
- a meaningful mistake or blocker changes the approach;
- a new tool or concept is applied;
- an ADR is created or materially changed;
- a milestone produces a significant insight;
- validation reveals an important limitation;
- project scope or sequencing changes because of new evidence.

## Entry template

### YYYY-MM-DD — Topic

#### What I worked on

Describe the concrete task or investigation.

#### What I learned

Describe the new concept, tool, or insight.

#### What was difficult

Describe uncertainty, mistakes, blockers, or trade-offs.

#### Decision or change

Explain what changed in the project as a result.

#### Evidence

Reference the issue, ADR, validation report, command output, or file that supports the entry.

#### Next experiment

Describe the next small validation step.

---

## 2026-07-20 — Initial project framing

#### What I worked on

Defined the initial MVP goal, primary user flow, proposed stack, milestone structure, and core documentation set.

#### What I learned

The available price guide is not a complete card catalogue. Product metadata, expansion mapping, language, variants, and image relationships require separate analysis.

#### What was difficult

The largest initial uncertainty is data normalisation and record identity rather than server deployment or user-interface configuration.

#### Decision or change

The project will begin with one complete expansion as a vertical slice before attempting a full catalogue import.

The final database schema and unique import key will not be approved until representative source files have been analysed.

#### Evidence

- `MVP_SCOPE.md`
- `PROJECT.md`
- `STACK.md`
- `DECISIONS.md`

#### Next experiment

Inventory the available source files, inspect the prepared expansion list and image structure, and identify candidate stable source keys.

---

## 2026-07-25 — Separating canonical cards from marketplace variants

#### What I worked on

Compared Cardmarket product and price snapshots with Pokémon TCG Data, Cardmarket entity documentation, a scraped Primal Clash product listing, and a concrete Vulpix Version 1 / Version 2 example.

#### What I learned

A canonical set-specific card and a Cardmarket product are different entities. One canonical card, such as `xy5-20`, may have multiple editions, and each edition may have language and finish variants. Normal, reverse holo, and holo are finishes rather than edition names.

Cardmarket prices belong to market products, so a canonical-card price must be derived through explicit mappings rather than stored as if it were intrinsic card metadata.

#### What was difficult

The downloadable Cardmarket product file omits collector number, edition labels, language, and finish. Several products can therefore look identical in the reduced snapshot even when the marketplace treats them as different products. Matching by name or attack text alone is not sufficient for every record.

The Pokémon TCG Data repository is a useful structured catalogue source, but its publisher status must not be described as official without separate evidence.

#### Decision or change

Accepted the following project decisions:

- canonical cards are separate from Cardmarket products;
- imported entities use source-scoped stable identifiers;
- the conceptual hierarchy is `canonical card → edition → variant → market product`;
- initial supported market languages are English and German;
- code cards and sealed products are excluded from the MVP catalogue;
- the initial wishlist references the canonical card;
- the canonical-card price is the minimum available non-null Cardmarket `avg30` across linked English and German variants and is labelled as a `From` price.

Primal Clash was selected as the first validated vertical slice.

#### Evidence

- `ADR-005` in `DECISIONS.md`
- `ADR-006` in `DECISIONS.md`
- `ADR-007` in `DECISIONS.md`
- `ADR-011` in `DECISIONS.md`
- `MVP_SCOPE.md`
- `REVIEW_SUMMARY.md`
- Primal Clash source files and mapping analysis
- Vulpix `PRC 20` Version 1 / Version 2 example

#### Next experiment

Complete a reproducible Primal Clash mapping fixture, classify confirmed and ambiguous Cardmarket mappings, and use the result to define `ADR-008` for repeated imports and `ADR-009` for rejected, unmatched, and ambiguous records.

---

## 2026-07-27 — Replacing inferred product order with direct Cardmarket IDs

#### What I worked on

Built and validated the Primal Clash mapping fixture using direct Cardmarket
`idProduct` values collected from individual product pages.

Compared all unreferenced Cardmarket products with directly mapped sibling
products sharing the same `idMetacard`.

#### What I learned

The order of products in downloadable Cardmarket snapshots is not reliable
mapping evidence.

A listing URL can be connected to a Cardmarket product deterministically by
reading the hidden `idProduct` value from the individual product page. This
removes the need to infer mappings from product ordering or semantic similarity.

The Primal Clash product fixture also contains six products that are not
referenced by any collected listing URL. Each matches a directly mapped sibling
in every inspected field except `idProduct` and `dateAdded`. The available data
supports treating them as duplicate-like unresolved source records, but does not
prove why Cardmarket created them.

#### What was difficult

The Cardmarket listing page did not expose `idProduct` directly. Individual
product pages had to be fetched separately, and rate limiting required the
collection to be resumed in several parts.

Earlier semantic matching was useful for detecting possible relationships but
could not reliably distinguish regular, full-art, and versioned products in all
cases.

The six unlisted products could not be safely mapped or deleted because the
source provides no explicit edition or finish explanation.

#### Decision or change

The Primal Clash mapping pipeline now uses direct listing URL to `idProduct`
evidence instead of product-order inference.

The validated mapping contains:

- `164` covered canonical cards;
- `167` directly mapped Cardmarket listing variants;
- `4` excluded Online Code Card products;
- `6` products classified as `unmatched_duplicate_candidate`;
- no ordinary `unmatched`, `ambiguous`, or `conflict` rows.

An `unmatched_duplicate_candidate` remains preserved as a source product record,
is not mapped to a canonical card, does not create a catalogue variant, and does
not participate in the MVP canonical-card price.

This handling was accepted in `ADR-012`.

#### Evidence

- `ADR-012` in `DECISIONS.md`
- `data/fixtures/primal-clash/mapping-review.csv`
- `scripts/discovery/build_primal_clash_mapping_review.py`
- `scripts/discovery/analyze_primal_clash_mapping_review.py`
- `scripts/discovery/analyze_primal_clash_unmatched_products.py`
- `scripts/discovery/validate_primal_clash_fixture.py`
- successful Primal Clash fixture validation output

#### Next experiment

Review the remaining M0 exit criteria and identify the next unresolved discovery
dependency before beginning the database schema.

---

## 2026-07-27 — Turning repository plans into a validated GitHub workflow

#### What I worked on

Configured the GitHub Project for `Pokemon Card Wishlist`, created the initial
M1 issue set, verified the published documentation links, and completed the
`M1 — Repository foundation` exit review.

#### What I learned

Project documentation and task tracking serve different purposes. Documents
record scope, decisions, milestone definitions, and long-lived guidance, while
GitHub issues and Project views make the current work state visible and
operational.

Custom fields such as `Status`, `Priority`, `Type`, `Area`, `Project phase`,
`Effort`, `Learning value`, and `Risk` allow the same issues to be viewed by
workflow state, current milestone, documentation area, decision risk, or data
quality without duplicating the issues.

I also learned that implementation and validation are separate states. A view or
workflow should not be marked `Done` until it has been tested with real issues
and its filters, links, and published results have been checked.

#### What was difficult

GitHub reserves some field names, including `Milestone`, so the project-specific
phase field had to be named `Project phase`. Some filters were easier to create
through the field selector than by typing them manually. Relative links that
look plausible in source files also require verification from the published
GitHub interface.

#### Decision or change

`M1 — Repository foundation` is completed and validated. The GitHub Project is
now the operational task-tracking layer, while the repository documents remain
the source of scope, decisions, milestone criteria, and portfolio evidence.

The current milestone advances to `M2 — Infrastructure`. Infrastructure work
will continue one documented, reversible, and validated action at a time.

#### Evidence

- configured GitHub Project fields and views;
- four classified M1 GitHub issues;
- validated `Current milestone` view;
- verified README documentation links;
- verified Markdown validation workflow badge;
- verified issue-template contact links;
- successful GitHub Actions Markdown validation;
- clean Git working tree and synchronised `main` branch;
- M1 deliverable-presence check against `PROJECT.md`.

#### Next experiment

Select the first M2 infrastructure task, confirm its dependencies and rollback
path, and begin with one reproducible action on the target Raspberry Pi or its
prepared environment.

---

## 2026-07-28 — Building a reproducible local PostgreSQL workflow

#### What I worked on

Prepared Windows for local PostgreSQL development using WSL 2, Ubuntu 24.04,
Docker Desktop, DBeaver Community, a PostgreSQL 17 container, and `dbmate`
running through Docker Compose.

Created a local `.env`, a safe `.env.example`, a Compose service for PostgreSQL,
a tools profile for `dbmate`, a tracked `db/migrations/` directory, and an
automatically generated `db/schema.sql`.

#### What I learned

Docker Desktop can expose the same Linux Docker engine to both Windows
PowerShell and a WSL distribution. PostgreSQL can therefore remain isolated in a
container while DBeaver connects through a local-only host port.

Inside a Docker network, one container connects to another by Compose service
name such as `postgres`, not by `localhost`. I also learned that `dbmate` reads
`DATABASE_URL`, creates its own `schema_migrations` table, and can generate a
schema dump after migration changes.

A migration workflow is not validated merely because a migration can be
created. Applying a migration, checking its status, rolling it back, and
confirming the final schema state are separate validation steps.

#### What was difficult

Port `5432` was initially occupied by a separately installed PostgreSQL 18
Windows service. Identifying the listener required tracing the process from
`postgres.exe` to `pg_ctl.exe` and then to the `postgresql-x64-18` service.

The initial `.env` was written with a UTF-8 byte-order mark. Docker Compose
accepted it, but `dbmate` rejected the invisible leading character. The file had
to be rewritten as UTF-8 without BOM.

The repository-wide `*.sql` ignore rule also hid both migration files and
`db/schema.sql`. Explicit exceptions were required so executable migrations
could be version-controlled without allowing arbitrary SQL dumps into Git.

#### Decision or change

Local database development now uses PostgreSQL 17 and `dbmate` exclusively
through Docker Compose. PostgreSQL Server and `dbmate` are not project
dependencies installed directly in Windows.

The PostgreSQL container binds to `127.0.0.1:5432`, secrets remain in the
ignored `.env`, and `.env.example` documents the required variables without
containing credentials.

The unrelated Windows PostgreSQL 18 service was stopped and its automatic
startup disabled to prevent a recurring local port conflict. It was not
uninstalled and its data was not deleted.

This validates the local development workflow only. Raspberry Pi deployment,
persistent SSD storage, NocoDB, private access, backup, restore, and restart
recovery remain separate infrastructure work.

#### Evidence

- commit `042d92b` (`Add local PostgreSQL development setup`);
- `compose.yaml`;
- `.env.example`;
- `db/schema.sql`;
- `db/migrations/.gitkeep`;
- `docs/database/local-postgresql-development-setup.md`;
- successful `docker run --rm hello-world`;
- successful PostgreSQL health check and `psql` query;
- successful DBeaver connection test;
- successful `dbmate` `new`, `up`, `status`, and `down` commands;
- final migration status: `Applied: 0`, `Pending: 0`.

#### Next experiment

Create the first real PostgreSQL migration from the accepted physical data-model
requirements, then validate constraints, indexes, rollback behavior, and schema
output against executable database checks.

---

## 2026-07-29 — Turning the conceptual model into validated migrations

#### What I worked on

Translated the accepted conceptual data model into `17` incremental PostgreSQL
migrations using `dbmate`. The migrations created `21` project tables for the
catalogue hierarchy, market products and prices, import staging and audit data,
mapping review history, production mappings, and wishlist data.

Applied each migration against PostgreSQL 17, inspected the resulting tables,
constraints, and indexes, and validated rollback and repeated application. I
also created `scripts/database/validate_schema.sql` as a permanent executable
schema-wide validation utility.

#### What I learned

A conceptual data model is not implementation-ready until table order, cyclic
foreign-key dependencies, composite hierarchy keys, controlled values, partial
unique indexes, and rollback behavior are expressed in executable SQL.

Small migrations made dependency problems easier to detect and recover from.
For example, the mapping review chain required a later foreign key from
`card_market_mapping_cases` to `mapping_case_observations`, and composite foreign
keys required explicit hierarchy uniqueness on parent tables.

I also learned that database-level constraints and schema-wide validation serve
different purposes. Constraints reject invalid individual writes, while the
validation script checks cross-table invariants such as confirmed mapping cases
having exactly one active production mapping and price snapshots belonging to
compatible successful import runs.

#### What was difficult

The mapping domain contains several intentional dependency cycles and
polymorphic audit relationships. These could not be represented safely by
creating all tables in one large SQL file or by adding every foreign key at the
first possible moment.

Running `dbmate` directly inside WSL also required a WSL-local installation and
a `DATABASE_URL` built from the ignored `.env`. Repository-wide `git diff
--check` output was initially noisy because unrelated files still used Windows
line endings, so migration checks had to be scoped to the files being changed.

#### Decision or change

The physical PostgreSQL schema is now implemented and locally validated. The
final local state is:

- `17` applied migrations;
- `0` pending migrations;
- `21` project tables;
- `22` total public tables including `schema_migrations`;
- successful rollback and reapplication of every migration or migration package;
- successful schema-wide validation.

This completes schema creation, but it does not yet validate the import pipeline,
repeat-import merge behavior with real data, runtime `From` price calculation,
or the user-facing wishlist workflow.

#### Evidence

- `db/migrations/`;
- `docs/database/data-model.md`;
- `scripts/database/validate_schema.sql`;
- `dbmate status` showing `Applied: 17` and `Pending: 0`;
- PostgreSQL table inventory showing `21` project tables;
- successful migration rollback and reapplication output;
- validation output: `schema validation passed`.

#### Next experiment

Prepare a controlled Primal Clash bootstrap dataset and execute the first staged
import path through validation and transactional merge without creating
uncontrolled duplicates or modifying wishlist-owned data.

---

## 2026-07-30 — Validating staged Cardmarket product imports with real source conditions

#### What I worked on

Implemented and validated the controlled Primal Clash Cardmarket product path from
`cardmarket-products.json` through `staging_market_products` to
`market_products`. The work included deterministic normalization, persistent
staging snapshots, a controlled partial-write rollback test, production merges,
per-record audit outcomes, and a repeated idempotency run.

#### What I learned

Real source data can expose a normalization rule without exposing a schema
problem. Cardmarket uses `0000-00-00 00:00:00` as a missing-value sentinel. The
correct boundary is to normalize it to `NULL` before PostgreSQL timestamp parsing,
while preserving the original value in `raw_payload`. The existing nullable
`source_created_at` column already represented this condition correctly.

I also learned that a valid staging record is not automatically an eligible
production record. The four Online Code Card products are structurally valid and
remain auditable, but they are outside MVP collection scope. Recording them as
`skipped` with a controlled reason preserves evidence without polluting production
catalogue data.

Repeated imports are best validated at several layers: identical artifact
checksums, independent staging snapshots, production uniqueness, unchanged-record
detection, and one reconciled audit outcome per source record.

#### What was difficult

The first production merge attempt used the lifecycle value `merging`, while the
physical schema requires `merge_started`. PostgreSQL rejected the transaction and
rolled back all status, production, and outcome changes. This was an importer bug,
not evidence that the schema needed to change.

Timestamp interpretation also has a limitation: the importer treats timezone-naive
real source timestamps as UTC deterministically, but the fixture alone does not
prove Cardmarket's original timezone semantics.

#### Decision or change

The Cardmarket product import now uses the lifecycle
`validated → merge_started → succeeded`. The source timestamp sentinel is
normalized to `NULL`, Online Code Card products are recorded as explicit skipped
outcomes, and no schema migration is introduced unless a later import confirms a
real modelling problem.

The active M4 work now moves to `cardmarket-mappings.json`, while the validated
product path remains stable.

#### Evidence

- `scripts/import/import_primal_clash_market_products.py`;
- `scripts/import/fail_import_primal_clash_market_products.py`;
- `scripts/import/merge_primal_clash_market_products.py`;
- `docs/import/primal-clash-source-to-target.md`;
- staging runs `4` and `6`;
- controlled rollback attempt consuming run sequence value `5`;
- first merge outcomes: `173` inserted and `4` skipped;
- repeat merge outcomes: `173` unchanged and `4` skipped;
- final production state: `173` active products and `0` duplicate source identities.

#### Next experiment

Inspect the controlled Cardmarket mapping fixture and define the exact staging and
production handling for confirmed mappings, six
`unmatched_duplicate_candidate` records, and four Online Code Card exclusions.

---

## 2026-07-31 — Preserving mapping state and repeated import evidence

#### What I worked on

Implemented and validated the controlled Primal Clash Cardmarket mapping path
from `staging_market_mappings` through mapping cases, observations, selected
candidates, status history, and active `card_market_product_mappings`. The work
included read-only pre-merge reconciliation, intentional transactional rollback,
a first production merge, and a repeated production merge.

#### What I learned

Idempotency does not mean that every table remains unchanged. Persistent current
state should remain stable, while event and evidence tables may legitimately grow.
In the repeated mapping merge, mapping cases, active mappings, and status history
remained unchanged, but a new observation and selected candidate were stored for
each eligible repeated source record.

I also learned that source classification and production eligibility are separate.
The four Online Code Card rows remain valid staged and audited records even though
they cannot create mapping cases because their products are intentionally absent
from `market_products`. Oversized and duplicate-like products can create resolved
review cases without creating active canonical-card mappings.

#### What was difficult

The mapping pipeline spans several tables with different responsibilities and
constraints. A correct transaction had to create a complete initial chain, update
the case's source observation, create an active mapping only for confirmed rows,
and reconcile one outcome for every one of the `177` source records.

The repeat behavior also required a clear distinction between a real state
transition and supporting evidence. Repeated identical input must not add another
status transition, but it should remain auditable as a new accepted observation.

#### Decision or change

Candidate rows are confirmed only at canonical-card scope using direct source
identifier evidence. Edition codes are preserved as evidence but do not
automatically create editions or variants. Oversized products are resolved as
`excluded`; duplicate-like products remain
`unmatched_duplicate_candidate`; Online Code Cards produce skipped outcomes.

The active M4 work now advances to Cardmarket price staging, price snapshots, and
runtime minimum non-null `avg30` `From` price validation.

#### Evidence

- `scripts/import/validate_primal_clash_market_mapping_merge.py`;
- `scripts/import/fail_merge_primal_clash_market_mappings.py`;
- `scripts/import/merge_primal_clash_market_mappings.py`;
- `docs/import/m4-cardmarket-mapping-production-merge-handoff.md`;
- first production mapping merge run `10`;
- repeated production mapping merge run `12`;
- first merge: `165` inserted mappings and `12` skipped outcomes;
- repeat merge: `165` unchanged mappings and `12` skipped outcomes;
- final cumulative state: `173` cases, `346` observations, `330` candidates,
  `173` status-history rows, and `165` active production mappings;
- commits `0a1c0a1`, `b99ddb1`, `3c91920`, and `28f4eda`.

#### Next experiment

Inspect the controlled Primal Clash Cardmarket price fixture, define the exact
staging and snapshot merge contract, and validate the minimum supported non-null
English or German `avg30` rule for the canonical-card `From` price.

---

## 2026-08-03 — Validating append-only market price snapshots and runtime aggregation

#### What I worked on

Implemented and validated the controlled Primal Clash Cardmarket price path from
`cardmarket-prices.json` through `staging_market_prices` to append-only
`market_price_snapshots`, then validated the runtime canonical-card `From` price.

The work included deterministic normalization, persistent staging, staging
rollback, production rollback, first and repeated production merges, complete
per-record audit outcomes, and a permanent SQL validator for the runtime
aggregation rule.

#### What I learned

Idempotency for append-only snapshot data differs from idempotency for mutable
current-state data. Reimporting the same source snapshot must not create another
snapshot row or update the existing row. It should preserve the original
historical record and classify the repeated source record as `unchanged`.

I also learned that runtime pricing should not read arbitrary snapshot rows
directly. It must first select the latest eligible snapshot per active market
product from a successful import run, then aggregate across active canonical-card
mappings with `MIN(avg30)`.

Audit completeness remains independent from production row creation. All `177`
source records produced outcomes even though only `173` eligible products created
or matched production snapshots and `4` Online Code Card records were skipped.

#### What was difficult

The price fixture provides one file-level timestamp rather than a timestamp on
each record, and it does not contain a currency field. The importer therefore
needed an explicit controlled contract: apply the normalized file timestamp to
all rows and assign `EUR` without pretending that the source supplied either
value per record.

The current fixture also does not exercise the no-price branch because every
mapped Primal Clash card has at least one non-null `avg30`. The SQL semantics
support a missing result, but that behaviour is not proven by this fixture alone.

#### Decision or change

Cardmarket price snapshots are now treated as append-only production evidence
with identity:

```text
(market_product_id, source_snapshot_at)
```

An identical repeated snapshot produces `unchanged`; conflicting values for the
same identity must fail rather than overwrite history.

The runtime canonical-card price is validated as the minimum non-null `avg30`
from the latest eligible successful snapshot for each active mapped product. The
result is labelled `From` and `30-day average`, and `avg30_holo` is excluded from
the MVP formula.

#### Evidence

- `scripts/import/import_primal_clash_market_prices.py`;
- `scripts/import/fail_import_primal_clash_market_prices.py`;
- `scripts/import/merge_primal_clash_market_prices.py`;
- `scripts/import/fail_merge_primal_clash_market_prices.py`;
- `scripts/database/validate_primal_clash_from_prices.sql`;
- staging and first production run `13`;
- repeated staging and production run `15`;
- first merge: `173` inserted snapshots and `4` skipped outcomes;
- repeat merge: `173` unchanged snapshots, `0` inserted snapshots, and `4`
  skipped outcomes;
- final production state: `173` snapshots and `0` duplicate identities;
- runtime validation: `165` active mapped products and `164` canonical cards
  with a `From` price;
- implementation commit `5b49bda`.

#### Next experiment

Complete the M4 documentation and validation report, then decide whether edition
and variant derivation belongs in the current milestone or should be explicitly
deferred without blocking the validated canonical-card price path.

---

## 2026-08-03 — Deferring derivation when evidence proves only card scope

#### What I worked on

Reviewed every Primal Clash mapping row containing a Cardmarket edition code and
validated whether the available evidence supports card-, edition-, or
variant-level production records.

The review covered `12` edition-code rows: `10` candidate mappings and `2`
excluded oversized products. I also checked the production counts and reran the
permanent runtime canonical-card price validator.

#### What I learned

A source label that looks like an edition code is not automatically a stable
catalogue edition identity. The values `V1` and `V2` occur in different contexts:
multiple products for one canonical card, separate canonical cards with different
collector numbers, and excluded oversized products.

Direct `idProduct` evidence can prove the relationship between a canonical card
and a Cardmarket product without proving the product's edition, language, or
finish. Production data should therefore be created only at the most specific
scope supported by evidence.

#### What was difficult

The accepted conceptual hierarchy includes editions and language and finish
variants, while the current vertical-slice sources do not provide enough metadata
to populate those entities safely. Populating the tables would make the model
look more complete, but would require guessed values and make later correction
more difficult.

#### Decision or change

Accepted `ADR-013 — Defer automatic edition and variant derivation`.

The Primal Clash import remains at canonical-card mapping scope. Edition codes
are preserved as evidence, but automatic `card_editions` and `card_variants`
creation is deferred until a controlled source or review process proves edition
identity, language, and finish.

The empty production tables are treated as a documented limitation rather than
an import failure.

#### Evidence

- `12` mapping rows with edition codes;
- `10` candidate rows confirmed only at card scope;
- `2` excluded oversized rows;
- `0` edition-scope candidate mappings;
- `0` variant-scope candidate mappings;
- `card_editions`: `0`;
- `card_variants`: `0`;
- active `card_market_product_mappings`: `165`;
- `market_price_snapshots`: `173`;
- canonical cards with runtime `From` prices: `164`;
- runtime validation result:
  `Primal Clash runtime From price validation passed`;
- `ADR-013` in `DECISIONS.md`.

#### Next experiment

Prepare the consolidated Primal Clash import validation report and verify the
remaining M4 exit criteria without claiming unsupported edition or variant
coverage.

## 2026-08-03 — Closing a milestone at the evidence-supported scope

#### What I worked on

Consolidated the complete Primal Clash import evidence, reviewed the result
against the formal `M4 — First import` exit criteria, and prepared the milestone
exit review.

The review covered canonical cards, Cardmarket products, mapping evidence,
append-only prices, runtime aggregation, local images, repeated imports,
transaction rollback, unresolved records, and the accepted edition and variant
scope limitation.

#### What I learned

A milestone can be complete without every table in the conceptual model being
populated, provided the implemented scope is explicit, the missing data is not
invented, and the formal exit criteria are satisfied.

Idempotency also has different meanings across the model. Stable current-state
entities should remain unchanged, evidence tables may receive new observations,
and append-only snapshots must reject or classify an identical identity without
overwriting history.

A documented limitation is different from a blocker. Empty edition and variant
tables would be a blocker only if M4 claimed validated edition- or
variant-specific workflows. They do not block the validated canonical-card
import and price path accepted under `ADR-013`.

#### What was difficult

The main challenge was separating M4 completion from complete MVP completion.
The import vertical slice is validated, while NocoDB, mobile access, wishlist
interaction, CSV export, Raspberry Pi deployment, backup, and restore remain
unimplemented.

It was also necessary to avoid treating complete price coverage in the current
fixture as proof of the user-facing no-price branch. The SQL semantics support a
missing result, but the fixture does not independently exercise that case.

#### Decision or change

`M4 — First import` is completed and validated on 2026-08-03 at canonical-card
scope.

The validated final state is:

- `164` active canonical cards;
- `173` active Cardmarket market products;
- `165` active canonical-card mappings;
- `173` append-only market price snapshots;
- `164` canonical cards with runtime `From` prices;
- `0` `card_editions` and `0` `card_variants` by design under `ADR-013`.

No known limitation blocks formal M4 completion. The active project focus
returns to `M2 — Infrastructure` before the mobile wishlist workflow is
validated.

#### Evidence

- `docs/import/primal-clash-import-validation-report.md`;
- `docs/import/m4-first-import-exit-review.md`;
- validation report commit `423d6a2`;
- `ADR-013` in `DECISIONS.md`;
- product import runs `4` and `6`;
- mapping production runs `10` and `12`;
- price import runs `13` and `15`;
- `scripts/database/validate_schema.sql`;
- `scripts/database/validate_primal_clash_from_prices.sql`.

#### Next experiment

Resume `M2 — Infrastructure` with one reproducible deployment block and validate
the Raspberry Pi, SSD, Docker Compose, PostgreSQL, and NocoDB dependency chain
before claiming the mobile wishlist workflow is ready.
