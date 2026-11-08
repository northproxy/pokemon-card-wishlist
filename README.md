# Pokemon Card Wishlist

A self-hosted, mobile-friendly MVP for browsing a structured Pokemon card catalogue, selecting wanted cards, viewing an informational market reference price, and exporting the selection as a CSV wishlist.

The project is also a public learning portfolio. It is intended to demonstrate structured project planning, data discovery, architecture decisions, data modelling, infrastructure work, security awareness, validation, documentation, and incremental delivery.

[![Markdown validation](https://github.com/northproxy/pokemon-card-wishlist/actions/workflows/markdown.yml/badge.svg)](https://github.com/northproxy/pokemon-card-wishlist/actions/workflows/markdown.yml)

## Project status

**Current milestone:** `M2 — Infrastructure`

`M0 — Discovery` and `M1 — Repository foundation` were completed and validated on 2026-07-27. `M3 — Data model` was implemented and locally validated on 2026-07-29. `M4 — First import` was completed and validated on 2026-08-03.

The physical PostgreSQL schema contains `21` project tables implemented through `17` incremental `dbmate` migrations. The controlled Primal Clash import is complete at canonical-card scope, including staging, validation, transactional merges, rollback tests, repeated-import behaviour, audit evidence, image coverage, Cardmarket mappings, append-only price snapshots, and runtime `From` pricing.

A second, catalogue-only expansion, **30th Celebration: Classic Collection** (`me55c`), was imported and locally validated in November 2026. Its validated production result is `30` active canonical cards in expansion ID `3` (import run ID `16`), with `60` PNG images downloaded under `images/raw/me55c/` and no download failures. The `me55c` canonical fixture and dedicated staging and merge scripts are tracked in the repository. Cardmarket products, mappings, pricing, and repeat-import/rollback validation have **not** been completed for `me55c`; this does not change the completed Primal Clash M4 evidence or the current M2 priority.

The validated vertical slice includes:

- Pokémon TCG Data set: `xy5`;
- Cardmarket expansion: `1585`;
- expansion name: Primal Clash;
- `164` canonical cards imported and active;
- `173` eligible Cardmarket products imported and active;
- `165` active card-level Cardmarket mappings;
- `173` append-only Cardmarket price snapshots;
- `164` canonical cards with a validated runtime `From` price;
- `4` Online Code Card records preserved through skipped audit outcomes;
- `2` oversized products preserved as resolved exclusions;
- `6` unlisted products preserved as `unmatched_duplicate_candidate`;
- `0` duplicate market-product source identities;
- `0` duplicate market-price snapshot identities;
- no ambiguous, conflicting, or ordinary unmatched mapping rows.

`ADR-013` is accepted: automatic edition and variant derivation is deferred because the current evidence proves only canonical-card-level mappings. The Primal Clash production state therefore intentionally contains `0` `card_editions` and `0` `card_variants`. This is a documented limitation and does not invalidate the completed M4 import or runtime pricing result.

The consolidated evidence is available in the [Primal Clash import validation report](docs/import/primal-clash-import-validation-report.md) and the [M4 first-import exit review](docs/import/m4-first-import-exit-review.md).

The current priority is to resume `M2 — Infrastructure`: Raspberry Pi deployment, SSD-backed persistence, NocoDB, private access, backup, restore, and restart recovery remain planned and unvalidated. The application and wishlist workflow have not started.

## Project goals

- Build a searchable catalogue of Pokemon cards.
- Preserve canonical card identity independently from marketplace products.
- Support English and German market variants.
- Provide a mobile-friendly browser workflow.
- Allow a user to mark cards as wanted.
- Store optional quantity and notes.
- Display a clearly labelled informational `From` price based on Cardmarket `avg30`.
- Provide a filtered Wishlist view.
- Export selected cards to CSV.
- Run the MVP on a Raspberry Pi.
- Keep deployment and recovery procedures reproducible.
- Document decisions, risks, trade-offs, validation, and lessons learned.

## MVP catalogue model

The accepted conceptual hierarchy is:

```text
canonical card → edition → language/finish variant → market product → price snapshot
```

The initial wishlist references the canonical card, for example `xy5-20`. Edition- and variant-specific wishlist selection is planned for a later version.

## MVP user flow

1. Open the application on a phone.
2. Browse or search the catalogue.
3. Filter cards by expansion and available metadata.
4. View card information, image, and informational `From` price where available.
5. Mark cards as wanted.
6. Set quantity and optional notes.
7. Open the Wishlist view.
8. Export selected cards to CSV.

## Proposed MVP stack

- Raspberry Pi 4 or 5
- Raspberry Pi OS Lite 64-bit
- Docker and Docker Compose
- PostgreSQL
- NocoDB
- Tailscale
- USB-connected SSD
- GitHub and GitHub Actions

The application and infrastructure stack choices remain proposed until the corresponding ADRs are accepted and validated. GitHub is implemented as the repository platform, and GitHub Actions Markdown validation is implemented and validated.

## Delivery approach

The project follows a milestone-based approach:

- `M0 — Discovery`
- `M1 — Repository foundation`
- `M2 — Infrastructure`
- `M3 — Data model`
- `M4 — First import`
- `M5 — Wishlist workflow`
- `M6 — Catalogue expansion`
- `M7 — MVP release`

Primal Clash is the validated discovery vertical slice and will remain the first implementation target. Full catalogue import is intentionally deferred until the implemented vertical slice is validated.

## Documentation

- [MVP Scope](MVP_SCOPE.md)
- [Project Plan](PROJECT.md)
- [Release Roadmap](ROADMAP.md)
- [Technical Stack](STACK.md)
- [Architecture Decision Log](DECISIONS.md)
- [GitHub Project Draft](GITHUB_PROJECT.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Learning Log](LEARNING_LOG.md)
- [Discovery Documentation](docs/discovery/README.md)
- [Local PostgreSQL development setup](docs/database/local-postgresql-development-setup.md)
- [PostgreSQL data model](docs/database/data-model.md)
- [Executable schema validation](scripts/database/validate_schema.sql)
- [Primal Clash source-to-target contract](docs/import/primal-clash-source-to-target.md)
- [Primal Clash import validation report](docs/import/primal-clash-import-validation-report.md)
- [M4 first-import exit review](docs/import/m4-first-import-exit-review.md)
- [Image download utilities](scripts/images/README.md)

## Success criteria

The MVP is complete when:

- Primal Clash has been imported and validated as a complete vertical slice;
- cards and images are usable from a phone;
- search and expansion filtering work;
- wishlist selections persist;
- quantity and notes can be stored;
- mapped cards display the validated minimum non-null `avg30` rule or clearly show that no price is available;
- selected cards can be exported to CSV;
- repeated import does not create uncontrolled duplicates;
- rejected, unmatched, and ambiguous records are reported;
- the application recovers after a Raspberry Pi restart;
- backup and restore have been documented and tested;
- major technical decisions are recorded;
- the repository clearly distinguishes proposed, implemented, and validated work.

## Scope boundary

The MVP includes imported Cardmarket price snapshots only to display the minimum available English or German `avg30` as a clearly labelled `From` price.

The MVP does not include real-time price synchronisation, price-history charts or analytics, automated purchasing, Cardmarket account integration, a native mobile application, multi-user access, public registration, collection-value analytics, image recognition, AI matching, recommendation features, real-time external synchronisation, or full offline support.
