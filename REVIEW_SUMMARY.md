# Documentation Review Summary

The seven core project documents were reviewed and updated.

## Main corrections

- Standardised the project name as `Pokemon Card Wishlist`.
- Removed the accented character from the technical project name.
- Standardised milestone names as `M0` through `M7`.
- Clarified that application and database implementation have not started, while discovery tooling and validated fixtures are already in progress.
- Marked the stack and ADRs as proposed rather than implemented.
- Removed README ambiguity between Tailscale and Cloudflare Tunnel.
- Removed README ambiguity between local and object storage.
- Added explicit distinction between Proposed, Planned, Implemented, and Validated.
- Added rejected, unmatched, missing-image, and import-validation requirements.
- Added repeat-import and idempotency validation.
- Strengthened backup requirements to include database, images, and configuration.
- Clarified that same-device backups do not protect against disk failure.
- Expanded the planned ADR list.
- Added evidence requirements to the Learning Log.
- Added a minimal Ready backlog for M0.
- Added import-run tracking and data-quality workflows to the plan.

## Discovery decisions accepted on 2026-07-25

Evidence from Pokémon TCG Data, Cardmarket downloadable files, Cardmarket entity documentation, the Primal Clash Cardmarket listing, and the Vulpix edition example supports the following accepted decisions:

- a canonical card is separate from a Cardmarket market product;
- external entities use source-scoped stable identifiers;
- the model separates canonical card, edition, language/finish variant, and market product;
- the initial supported languages are English and German;
- code cards and sealed products are excluded from the MVP catalogue;
- the initial wishlist references the canonical card;
- edition- and variant-specific wishlist selection is deferred;
- the displayed canonical-card price is the minimum available Cardmarket `avg30` among linked English and German variants.

## Primal Clash mapping validated on 2026-07-27

The Primal Clash vertical-slice mapping was rebuilt using direct Cardmarket
`idProduct` values collected from individual product pages rather than inferred
product ordering.

Validated results:

- `164` canonical cards are covered;
- `167` Cardmarket listing variants are mapped through direct `idProduct`
  evidence;
- no canonical card has ambiguous mapping rows;
- no Cardmarket product is referenced by multiple canonical cards;
- `4` Online Code Card products remain explicitly excluded from MVP scope;
- `6` unlisted duplicate-like Cardmarket products are preserved as
  `unmatched_duplicate_candidate`;
- no ordinary `unmatched`, `ambiguous`, or `conflict` rows remain.

The six `unmatched_duplicate_candidate` records match directly mapped sibling
products in every inspected field except `idProduct` and `dateAdded`. They remain
preserved as source evidence, are not mapped to canonical cards, do not create
catalogue variants, and do not participate in the MVP canonical-card price.

The permanent Primal Clash validation script now checks fixture structure,
declared record counts, mapping-status counts, canonical-card coverage, unique
Cardmarket product coverage, exclusions, duplicate candidates, and the absence
of unresolved statuses.

## Primal Clash image mapping validated on 2026-07-27

The canonical-card fixture provides deterministic image metadata for every
Primal Clash card.

Validated results:

- all `164` canonical cards have a small image URL;
- all `164` canonical cards have a large image URL;
- all small image URLs are unique;
- all large image URLs are unique;
- no image metadata is missing;
- all URLs use HTTPS and the expected `images.pokemontcg.io` host;
- all URL paths match the expected set-code and collector-number pattern.

For example, canonical card `xy5-1` maps deterministically to:

- small image path: `/xy5/1.png`;
- large image path: `/xy5/1_hires.png`.

This validates image mapping feasibility at the source-metadata level without
matching by card name.

The validation does not yet confirm remote file availability, image dimensions,
download behaviour, local filename conventions, licensing conditions, local
storage, backup, or restore. Those remain implementation and validation work
for later milestones.

## Important unresolved decisions

The following remain intentionally unresolved:

- final physical database schema and controlled-value implementation;
- exact staging, evidence, review-history, and merge-result table structures;
- handling of future Cardmarket products whose differences exceed
  `idProduct` and `dateAdded`, or which lack a directly mapped sibling;
- final acceptance of NocoDB, PostgreSQL, Tailscale, and local image storage;
- the concrete external backup location, schedule, scripts, retention cleanup,
  and restore-test evidence required to validate `ADR-010`.

`ADR-008` and `ADR-009` are accepted and now define the repeated-import and
unresolved-record boundaries for `M3 — Data model`. `ADR-010` is proposed and
must remain unvalidated until the backup and restore process is implemented and
a complete clean restore test passes during `M2 — Infrastructure`. The Primal
Clash direct-ID mapping and its six `unmatched_duplicate_candidate` records are
no longer unresolved.
