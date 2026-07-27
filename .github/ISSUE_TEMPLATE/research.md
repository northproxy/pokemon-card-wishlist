---

name: Research
about: Investigate an open question using explicit evidence, assumptions, risks, and validation
title: "research: "
labels: "research"
assignees: ""
-------------

## Research question

State the specific question this investigation must answer.

The question should be narrow enough to produce a concrete conclusion, recommendation, validation result, or follow-up decision.

## Context

Explain:

* why this investigation is needed;
* which milestone or task depends on it;
* what is currently known;
* what remains uncertain;
* what may be blocked until the research is complete.

## Milestone

Select the milestone this research supports:

* [ ] `M0 — Discovery`
* [ ] `M1 — Repository foundation`
* [ ] `M2 — Infrastructure`
* [ ] `M3 — Data model`
* [ ] `M4 — First import`
* [ ] `M5 — Wishlist workflow`
* [ ] `M6 — Catalogue expansion`
* [ ] `M7 — MVP release`

## Related requirements and decisions

Reference relevant requirements, ADRs, issues, fixtures, reports, or project documents.

Examples:

* `FR-04 — Card image`
* `FR-10 — Data import`
* `FR-11 — Import validation`
* `ADR-005 — Separate canonical cards from Cardmarket products`
* `ADR-006 — Use source-scoped identifiers as stable import keys`
* `MVP_SCOPE.md`
* `STACK.md`
* related issue or pull request

## Scope

### Included

Describe what will be investigated.

### Not included

Describe related topics that are intentionally excluded from this investigation.

## Current evidence

List the evidence already available.

Examples:

* source files;
* raw records;
* fixtures;
* validation reports;
* documentation;
* command output;
* sample data;
* external specifications;
* observed application behaviour.

Clearly distinguish:

* confirmed facts;
* assumptions;
* hypotheses;
* unresolved gaps.

## Research method

Describe the investigation approach.

Possible methods include:

* inspecting representative source records;
* comparing multiple source files;
* running validation scripts;
* building a focused fixture;
* testing a reproducible scenario;
* reviewing official documentation;
* comparing technical alternatives;
* measuring resource usage;
* testing import or mapping behaviour;
* validating results against acceptance criteria.

## Input data

List all source files, fixtures, systems, sample records, or documentation required for the investigation.

Include relevant paths or identifiers where practical.

## Expected output

Describe the concrete artifacts this research should produce.

Examples:

* research summary;
* validation report;
* fixture;
* comparison table;
* script;
* data-quality report;
* recommended approach;
* proposed ADR;
* follow-up issues;
* documentation update.

## Acceptance criteria

* [ ] The research question is answered or the remaining gap is explicitly documented.
* [ ] Evidence is sufficient to support the conclusion.
* [ ] Confirmed facts are separated from assumptions and inference.
* [ ] Representative real data is used where the question concerns source data.
* [ ] Ambiguous or unsupported findings are not silently resolved.
* [ ] Reproduction steps are documented.
* [ ] Relevant risks and limitations are recorded.
* [ ] Required follow-up work is identified.
* [ ] Documentation is updated where necessary.
* [ ] The result is not described as `Validated` without reproducible evidence.

Add research-specific acceptance criteria below:

* [ ]
* [ ]

## Findings

Record the investigation results.

### Confirmed findings

List conclusions directly supported by evidence.

### Unsupported assumptions

List assumptions that were disproved or could not be confirmed.

### Remaining uncertainty

Describe unresolved questions, missing evidence, or limitations.

## Data-quality impact

Describe any implications for:

* source-scoped identifiers;
* canonical-card identity;
* expansion mapping;
* collector numbers;
* editions;
* languages;
* finishes;
* market-product mappings;
* price snapshots;
* image references;
* duplicate detection;
* rejected records;
* unmatched records;
* ambiguous records;
* import validation;
* wishlist-data preservation.

Use `Not applicable` when the research has no data-quality impact.

## Security impact

Describe any implications for:

* credentials or secrets;
* network exposure;
* container configuration;
* permissions;
* imported or exported data;
* dependency versions;
* backup and restore;
* data integrity or availability.

Use `Not applicable` when there is no security impact.

## Risks and limitations

Describe risks such as:

* incomplete source data;
* unrepresentative samples;
* unavailable external evidence;
* rate limiting;
* unstable external pages;
* inferred rather than direct mappings;
* version-specific behaviour;
* hardware limitations;
* conclusions that may not generalise beyond the tested vertical slice.

## Recommendation

State the recommended next action based on the findings.

Clearly distinguish a recommendation from an accepted decision.

## Validation and evidence

List the evidence that confirms the research result.

Examples:

```text
Paste relevant command output or validation summaries here.
```

Also reference:

* scripts;
* fixtures;
* reports;
* affected source records;
* screenshots;
* benchmark output;
* documentation;
* commits or pull requests.

## Follow-up actions

List concrete work created by the research.

* [ ] Create or update an ADR.
* [ ] Create an implementation issue.
* [ ] Extend the fixture.
* [ ] Add permanent validation.
* [ ] Update project documentation.
* [ ] Record a Learning Log entry.
* [ ] Revisit the question when richer evidence becomes available.
* [ ] Other:

## Documentation updates

* [ ] `README.md`
* [ ] `MVP_SCOPE.md`
* [ ] `PROJECT.md`
* [ ] `STACK.md`
* [ ] `DECISIONS.md`
* [ ] `GITHUB_PROJECT.md`
* [ ] `LEARNING_LOG.md`
* [ ] `REVIEW_SUMMARY.md`
* [ ] `CHANGELOG.md`
* [ ] `docs/discovery/`
* [ ] Other
* [ ] No documentation update required

## Completion status

At completion, classify the result:

* Proposed:
* Planned:
* Implemented:
* Validated:

## Research conclusion

Complete this section before closing the issue.

* Question answered:
* Main conclusion:
* Evidence location:
* Remaining uncertainty:
* Decision required:
* Follow-up issues:
