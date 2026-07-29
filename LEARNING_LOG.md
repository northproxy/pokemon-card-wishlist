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
