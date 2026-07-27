# Contributing to Pokemon Card Wishlist

Thank you for your interest in contributing to Pokemon Card Wishlist.

This project is a self-hosted Pokemon card catalogue and wishlist MVP. It is also a public learning portfolio intended to demonstrate structured planning, data discovery, architecture decisions, implementation, validation, documentation, and incremental delivery.

## Project status

The current milestone is `M1 — Repository foundation`.

`M0 — Discovery` was completed and validated on 2026-07-27. Discovery tooling and the Primal Clash vertical-slice fixtures are validated. Application, database, and infrastructure implementation have not started.

Before contributing, review:

* [README.md](README.md)
* [MVP_SCOPE.md](MVP_SCOPE.md)
* [PROJECT.md](PROJECT.md)
* [STACK.md](STACK.md)
* [DECISIONS.md](DECISIONS.md)
* [GITHUB_PROJECT.md](GITHUB_PROJECT.md)

## Contribution principles

Contributions should follow these principles:

* Build the smallest useful version before expanding scope.
* Keep work aligned with the active milestone.
* Do not introduce out-of-scope MVP features without an approved decision.
* Preserve accepted terminology and architecture decisions.
* Do not silently resolve ambiguous source data.
* Keep source data, normalized catalogue data, import-control data, and user-generated wishlist data separate.
* Prefer simple, reproducible, free, and self-hosted solutions.
* Treat documentation and validation as part of the implementation.
* Clearly distinguish between `Proposed`, `Planned`, `Implemented`, and `Validated`.
* Never describe planned functionality as implemented or validated.

## Before starting work

Before making a change:

1. Review the relevant issue, milestone, and acceptance criteria.
2. Check whether the change is within the MVP scope.
3. Review relevant accepted or proposed ADRs in `DECISIONS.md`.
4. Identify dependencies on earlier milestones.
5. Confirm what evidence will be required to validate the result.

Do not begin work from a later milestone when an unresolved dependency from an earlier milestone blocks it.

## Branches

Use a short descriptive branch name.

Recommended formats:

```text
docs/add-security-policy
docs/update-project-status
data/validate-primal-clash-fixture
infra/add-compose-foundation
db/add-expansions-migration
fix/correct-mapping-validation
```

Avoid vague names such as:

```text
changes
updates
test
new-branch
```

## Commits

Write clear, focused commit messages.

Recommended format:

```text
<type>: <short description>
```

Common types:

* `docs`
* `data`
* `fix`
* `feat`
* `test`
* `refactor`
* `chore`
* `ci`

Examples:

```text
docs: add contribution guidelines
data: validate Primal Clash mapping counts
fix: preserve unmatched duplicate candidates
ci: add Markdown validation workflow
```

Keep unrelated changes in separate commits where practical.

## Pull requests

A pull request should:

* describe the purpose and scope of the change;
* reference the relevant issue or milestone;
* list the acceptance criteria addressed;
* explain how the change was validated;
* include relevant command output or evidence;
* identify documentation updates;
* identify security, data-quality, or recovery implications;
* clearly state what remains planned or unvalidated.

Keep pull requests small enough to review effectively.

## Pull request checklist

Before requesting review, confirm:

* [ ] The scope of the change is clear.
* [ ] The change is aligned with the active milestone.
* [ ] MVP scope was respected.
* [ ] Relevant acceptance criteria are satisfied.
* [ ] Tests or validation checks passed.
* [ ] Documentation was updated.
* [ ] Security implications were considered.
* [ ] Data-quality implications were considered.
* [ ] Database or infrastructure changes are reversible where practical.
* [ ] Required ADR updates were prepared.
* [ ] Required Learning Log updates were considered.
* [ ] Useful evidence is included.
* [ ] `Proposed`, `Planned`, `Implemented`, and `Validated` states are represented accurately.

## Documentation standards

Public repository documentation must be written in professional English.

Use consistent technical terminology across files. Keep technical identifiers in English, including:

* file and directory names;
* database tables and fields;
* variables and functions;
* API names;
* commands;
* milestones;
* issue titles;
* ADR identifiers.

Keep `README.md` as an overview and link to detailed documents instead of duplicating them.

When changing document structure or file names, update all affected cross-references.

## Architecture decisions

A significant technical or product choice should be documented as an ADR.

Before proposing an ADR:

1. Describe the context and constraint.
2. Identify realistic alternatives.
3. Compare trade-offs and consequences.
4. Recommend an approach.
5. Define how the decision will be validated.
6. Identify required follow-up work.

Do not mark an ADR as `Accepted` without explicit approval from the project owner.

When replacing an accepted ADR:

* mark the previous ADR as `Superseded`;
* reference the replacement ADR;
* explain migration or compatibility consequences.

## Data contributions

Changes involving catalogue, Cardmarket, image, or import data must preserve source traceability.

Pay particular attention to:

* source-scoped identifiers;
* canonical-card identity;
* expansion mappings;
* collector numbers;
* editions;
* languages;
* finishes;
* market-product mappings;
* image references;
* duplicate detection;
* rejected records;
* unmatched records;
* ambiguous records;
* import-run evidence;
* repeat-import behaviour.

Do not silently correct, merge, delete, or confirm ambiguous records.

Unknown or unsupported mappings must remain visible through an explicit rejected, unmatched, candidate, or ambiguous workflow.

Raw source files must not be edited to hide data-quality problems.

## Validation evidence

Validation evidence may include:

* successful script output;
* row-count summaries;
* duplicate checks;
* rejected or unmatched reports;
* fixture validation results;
* migration test output;
* backup and restore results;
* screenshots of validated user workflows;
* links to issues, ADRs, or reports.

A result should not be described as `Validated` unless reproducible evidence exists.

## Security

Do not commit:

* passwords;
* API tokens;
* private keys;
* database credentials;
* Tailscale authentication keys;
* environment files containing secrets;
* private backup archives;
* personal data that is not required by the project.

Secrets must remain outside the repository.

PostgreSQL must not be exposed directly to the public internet.

Security-sensitive findings should not be disclosed in a public issue before the reporting process in `SECURITY.md` is available.

## Definition of Done

A contribution is complete only when:

* implementation or analysis is complete;
* acceptance criteria are met;
* relevant tests or validation checks pass;
* data changes are validated;
* documentation is updated;
* security implications are considered;
* rollback or recovery implications are considered;
* required ADR or Learning Log updates are prepared;
* useful evidence is attached;
* the result is reproducible by another developer where practical.

Code completion alone does not mean that the task is done.

## Scope changes

The following are outside the approved MVP scope unless a separate decision is accepted:

* real-time market-price synchronisation;
* price-history charts or analytics beyond imported snapshots;
* automated purchasing;
* Cardmarket account integration;
* native Android or iOS applications;
* multi-user permissions;
* public user registration;
* collection-value analytics;
* automatic image recognition;
* AI card matching;
* recommendation features;
* full offline mode;
* public internet access for the MVP application.

Proposals that affect MVP scope must be discussed and recorded before implementation.
