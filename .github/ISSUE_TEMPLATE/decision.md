---

name: Decision
about: Evaluate a significant technical or product choice and prepare an ADR
title: "decision: "
labels: "decision"
assignees: ""
-------------

## Decision required

State the specific technical, product, data, infrastructure, security, or process decision that must be made.

## Context

Describe:

* the problem;
* the relevant project constraints;
* why a decision is required now;
* what may be blocked until the decision is made.

## Milestone

Select the milestone this decision supports:

* [ ] `M0 — Discovery`
* [ ] `M1 — Repository foundation`
* [ ] `M2 — Infrastructure`
* [ ] `M3 — Data model`
* [ ] `M4 — First import`
* [ ] `M5 — Wishlist workflow`
* [ ] `M6 — Catalogue expansion`
* [ ] `M7 — MVP release`

## Related requirements

Reference relevant requirements, scope statements, ADRs, issues, or documentation.

Examples:

* `FR-10 — Data import`
* `ADR-006 — Use source-scoped identifiers as stable import keys`
* `MVP_SCOPE.md`
* `STACK.md`
* related issue or validation report

## Constraints

List the constraints that realistic alternatives must respect.

Consider:

* MVP scope;
* active milestone;
* Raspberry Pi resource limits;
* self-hosting;
* reproducibility;
* security;
* data integrity;
* backup and recovery;
* maintenance complexity;
* cost;
* validated source evidence.

## Evidence

Describe the available evidence.

Include references to:

* source files;
* fixtures;
* validation output;
* benchmark results;
* experiments;
* documentation;
* external specifications;
* prior ADRs.

Clearly separate confirmed evidence from assumptions.

## Alternatives considered

### Alternative A

Describe the approach.

#### Advantages

*

#### Disadvantages

*

#### Risks

*

#### Validation method

Describe how this alternative could be tested.

### Alternative B

Describe the approach.

#### Advantages

*

#### Disadvantages

*

#### Risks

*

#### Validation method

Describe how this alternative could be tested.

### Alternative C

Add when relevant.

#### Advantages

*

#### Disadvantages

*

#### Risks

*

#### Validation method

Describe how this alternative could be tested.

## Trade-off comparison

| Criterion         | Alternative A | Alternative B | Alternative C |
| ----------------- | ------------- | ------------- | ------------- |
| MVP fit           |               |               |               |
| Complexity        |               |               |               |
| Security          |               |               |               |
| Data integrity    |               |               |               |
| Reproducibility   |               |               |               |
| Recovery impact   |               |               |               |
| Maintenance       |               |               |               |
| Validation effort |               |               |               |

Use `Not applicable` when a criterion does not apply.

## Recommendation

State the recommended alternative and explain why it best fits the documented project constraints and available evidence.

A recommendation is not an accepted decision.

## Consequences

Describe expected positive and negative consequences.

### Positive

*

### Negative

*

### Follow-up impact

Describe required changes to:

* implementation;
* data model;
* infrastructure;
* import process;
* security controls;
* backup and restore;
* documentation;
* tests and validation;
* existing ADRs.

## Validation plan

Define how the selected approach will be evaluated.

Include:

* test or experiment;
* expected result;
* failure conditions;
* evidence to capture;
* point at which the decision should be reconsidered.

## Rollback or migration

Describe:

* how the decision could be reversed;
* migration requirements;
* compatibility consequences;
* data or configuration recovery needs.

Use `Not applicable` only when no persistent consequences exist.

## ADR preparation

* Proposed ADR identifier:
* Proposed ADR title:
* Existing ADR superseded:
* Initial ADR status: `Proposed`

An ADR may be marked `Accepted` only after explicit approval from the project owner.

## Documentation updates

* [ ] `README.md`
* [ ] `MVP_SCOPE.md`
* [ ] `PROJECT.md`
* [ ] `STACK.md`
* [ ] `DECISIONS.md`
* [ ] `GITHUB_PROJECT.md`
* [ ] `LEARNING_LOG.md`
* [ ] `CHANGELOG.md`
* [ ] Other
* [ ] No documentation update required

## Decision outcome

Complete this section only after discussion.

* Selected alternative:
* Decision status:
* Approval date:
* Approved by:
* Validation still required:
* Follow-up issues:
* ADR reference:
