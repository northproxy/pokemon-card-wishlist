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
