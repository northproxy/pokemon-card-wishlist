# Pokemon Card Wishlist

A self-hosted, mobile-friendly MVP for browsing a structured Pokemon card catalogue, selecting wanted cards, viewing an informational market reference price, and exporting the selection as a CSV wishlist.

The project is also a public learning portfolio. It is intended to demonstrate structured project planning, data discovery, architecture decisions, data modelling, infrastructure work, security awareness, validation, documentation, and incremental delivery.

[![Markdown validation](https://github.com/northproxy/pokemon-card-wishlist/actions/workflows/markdown.yml/badge.svg)](https://github.com/northproxy/pokemon-card-wishlist/actions/workflows/markdown.yml)

## Project status

**Current milestone:** `M2 — Infrastructure`

`M0 — Discovery` and `M1 — Repository foundation` were completed and validated on 2026-07-27.

Discovery tooling, the Primal Clash vertical-slice fixtures, the repository foundation, the GitHub Project workflow, and Markdown validation are validated. Application, database, and infrastructure implementation have not started.

The current priority is to prepare and execute the first validated `M2 — Infrastructure` task without bypassing unresolved security, storage, backup, or recovery dependencies.

The first validated vertical slice is:

* Pokémon TCG Data set: `xy5`;
* Cardmarket expansion: `1585`;
* expansion name: Primal Clash;
* `164` canonical cards covered;
* `167` Cardmarket listing variants mapped through direct `idProduct` evidence;
* `6` unlisted products preserved as `unmatched_duplicate_candidate`;
* `4` Online Code Card products excluded from MVP catalogue scope;
* no ambiguous, conflicting, or ordinary unmatched mapping rows remaining.

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
