---

name: Bug report
about: Report reproducible incorrect behaviour in implemented project work
title: "bug: "
labels: "bug"
assignees: ""
-------------

## Summary

Describe the incorrect behaviour clearly and concisely.

Do not use this template for functionality that is only `Proposed` or `Planned` and has not yet been implemented.

## Affected milestone

Select the milestone in which the affected functionality belongs:

* [ ] `M0 — Discovery`
* [ ] `M1 — Repository foundation`
* [ ] `M2 — Infrastructure`
* [ ] `M3 — Data model`
* [ ] `M4 — First import`
* [ ] `M5 — Wishlist workflow`
* [ ] `M6 — Catalogue expansion`
* [ ] `M7 — MVP release`

## Affected component

Select or describe the affected area:

* [ ] Documentation
* [ ] Discovery data
* [ ] Fixture or validation script
* [ ] Import pipeline
* [ ] Database
* [ ] Infrastructure
* [ ] NocoDB or user interface
* [ ] Wishlist workflow
* [ ] CSV export
* [ ] Security
* [ ] Backup or restore
* [ ] Other

## Current status

Classify the affected functionality:

* [ ] `Implemented`
* [ ] `Validated`
* [ ] Status is unclear or inconsistent in documentation

## Environment

Provide relevant environment details.

Examples:

* operating system;
* Python version;
* Docker version;
* PostgreSQL version;
* NocoDB version;
* Raspberry Pi model;
* browser and device;
* commit or branch.

Use `Not applicable` for documentation-only defects.

## Preconditions

Describe any data, configuration, services, or repository state required before reproducing the issue.

## Steps to reproduce

1.
2.
3.

## Expected behaviour

Describe what should happen according to the documented requirement, ADR, acceptance criterion, or validated behaviour.

## Actual behaviour

Describe what happened instead.

## Evidence

Include relevant evidence with secrets and private data removed.

Examples:

```text
Paste command output, validation errors, or logs here.
```

Other useful evidence may include:

* screenshots;
* failing test output;
* validation reports;
* affected row counts;
* sample record identifiers;
* links to requirements or ADRs.

## Frequency

Select one:

* [ ] Always
* [ ] Intermittent
* [ ] Occurred once
* [ ] Unknown

## Data-quality impact

Describe whether the issue may affect:

* canonical-card identity;
* source-scoped identifiers;
* editions, languages, or finishes;
* Cardmarket mappings;
* price aggregation;
* rejected, unmatched, ambiguous, or duplicate-like records;
* wishlist data;
* exported CSV;
* validation counts.

Use `No known data-quality impact` when applicable.

## Security impact

Describe any possible impact on:

* secrets or credentials;
* network exposure;
* permissions;
* imported or exported data;
* backup files;
* authentication;
* data integrity or availability.

Do not include sensitive exploit details in a public issue. Follow `SECURITY.md` when the issue may be a vulnerability.

## Workaround

Describe any temporary workaround.

Use `None known` when no workaround exists.

## Possible cause

Describe any suspected cause, clearly marking it as an assumption until confirmed.

## Acceptance criteria for the fix

* [ ] The defect is reproducible before the fix.
* [ ] The root cause is identified or documented.
* [ ] The fix does not introduce uncontrolled scope changes.
* [ ] Relevant tests or validation checks pass.
* [ ] Regression coverage is added where practical.
* [ ] Data integrity is verified.
* [ ] Security implications are reviewed.
* [ ] Documentation is corrected where required.
* [ ] `CHANGELOG.md` is updated when the change is notable.
* [ ] Evidence confirms the corrected behaviour.
* [ ] The result is not marked `Validated` without reproducible evidence.

## Rollback or recovery

Describe how the fix can be reverted and how affected data or configuration can be recovered if necessary.

## Related references

Add links or references to:

* related issues;
* pull requests;
* requirements;
* ADRs;
* validation reports;
* affected files.
