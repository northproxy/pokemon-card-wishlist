# Technical Stack

## Status

This document distinguishes the locally implemented development stack from the still-proposed Raspberry Pi MVP deployment.

The following are implemented and locally validated:

- GitHub repository and project workflow;
- GitHub Actions Markdown validation;
- WSL 2 and Docker Desktop development environment;
- PostgreSQL 17 accessed only through `127.0.0.1`;
- dbmate migration workflow;
- physical PostgreSQL schema with `21` project tables and `17` applied migrations;
- executable schema validation through `scripts/database/validate_schema.sql`.

The following remain proposed or planned for infrastructure and application milestones:

- Raspberry Pi OS deployment;
- SSD-backed persistent Docker volumes;
- NocoDB;
- Tailscale private access;
- production backup and restore;
- restart recovery validation;
- mobile wishlist workflow.

The physical schema is documented in `docs/database/data-model.md`. Primal Clash import logic and runtime import validation remain part of `M4 — First import`.

## Recommended MVP stack

| Layer | Technology | Reason | Status |
|---|---|---|---|
| Hardware | Raspberry Pi 4 or 5 | Low-cost self-hosted server | Proposed |
| Operating system | Raspberry Pi OS Lite 64-bit | Stable, lightweight, and well supported | Proposed |
| Primary storage | USB-connected SSD | More suitable than microSD for database, images, and backups | Proposed |
| Containers | Docker and Docker Compose | Reproducible deployment and simpler service management | Proposed |
| Database | PostgreSQL 17 | Relational integrity, mature backup tools, and future extensibility | Implemented and locally validated for development; Raspberry Pi deployment planned |
| Admin and UI | NocoDB | Fast mobile-friendly catalogue and wishlist workflow without a custom frontend | Proposed |
| Remote access | Tailscale | Private access without public port forwarding | Proposed |
| Image storage | Local SSD filesystem | Simple and inexpensive for the MVP | Proposed |
| Reverse proxy | Caddy, only if later required | Optional HTTPS and routing layer | Deferred |
| Database backup | `pg_dump` | Portable logical backup | Proposed |
| File backup | Encrypted archive or file-level copy | Covers images and configuration | Proposed |
| Repository | GitHub | Version control, documentation, issues, and project tracking | Implemented |
| CI | GitHub Actions | Markdown checks first; automated tests later | Implemented and validated for Markdown |

## Architecture summary

The proposed deployment model is:

```text
Mobile phone
    |
Tailscale private network
    |
Raspberry Pi
    |
Docker Compose
    |-- NocoDB
    |-- PostgreSQL
    |-- image storage on SSD
```

PostgreSQL must not be exposed directly to the public internet.

## Why PostgreSQL instead of SQLite

SQLite remains suitable for a local proof of concept, but PostgreSQL is preferred for the MVP because:

- NocoDB integrates naturally with it;
- relational constraints are clearer;
- concurrent access is safer;
- backup and restore workflows are mature;
- repeated imports and staging workflows are easier to structure;
- future API or multi-user work would require fewer architectural changes.

The trade-off is higher operational complexity.

## Why NocoDB for the MVP

NocoDB is proposed because it can provide:

- mobile browser access;
- table and gallery views;
- filters and saved views;
- checkbox fields;
- relationships between tables;
- CSV import and export;
- basic authentication;
- rapid validation of the data model and user workflow.

The main trade-offs are:

- limited control over mobile UX;
- possible dependence on NocoDB-specific behaviour;
- possible migration to a custom frontend later.

The complete mobile flow must be validated with one full expansion before this decision is accepted.

## Implemented physical data model

The accepted conceptual boundaries have been implemented as a normalized PostgreSQL schema. The authoritative table-level definitions, controlled values, constraints, indexes, lifecycle rules, and migration order are maintained in `docs/database/data-model.md`.

The schema contains `21` project tables across these responsibilities:

- catalogue foundation: `expansions`, `expansion_source_identifiers`, `cards`, `card_editions`, and `card_variants`;
- market catalogue and pricing: `market_products`, `card_market_product_mappings`, and `market_price_snapshots`;
- import lifecycle and staging: `import_runs`, `staging_cards`, `staging_market_products`, `staging_market_prices`, and `staging_market_mappings`;
- import audit and rejection handling: `import_record_outcomes`, `rejected_source_records`, and `rejected_source_record_reasons`;
- mapping review: `card_market_mapping_cases`, `mapping_case_observations`, `mapping_candidates`, and `mapping_status_history`;
- user-generated data: `wishlist_items`.

The schema preserves the accepted hierarchy:

```text
canonical card
    → edition
        → language/finish variant
            → Cardmarket market product
                → price snapshot
```

Implemented boundaries include:

- source-scoped identity for canonical catalogue records and market products;
- separation of production data from permissive staging records;
- controlled rejected and unresolved mapping workflows;
- append-only market price snapshots;
- one active production mapping per market product;
- canonical-card wishlist ownership independent from staging, language, finish, edition, and price data;
- lifecycle and referential-integrity constraints designed to preserve audit history and wishlist data.

The schema is implemented through `17` reversible dbmate migrations. Local validation confirms `21` project tables, `22` total `public` tables including `schema_migrations`, no pending migrations, successful rollback and reapply checks, and a passing schema-wide validation script.

This validation covers schema structure and database invariants. It does not yet validate the Primal Clash source-to-target transformation, transactional merge behaviour on real records, repeat-import idempotency, rejected or unresolved outcomes from real import runs, or the runtime canonical-card `From` price query. Those are `M4 — First import` responsibilities.

## Storage recommendation

Use a USB-connected SSD rather than relying only on microSD.

The SSD should contain:

- PostgreSQL data;
- card images;
- Docker persistent volumes;
- configuration backups;
- database backups.

Backups should also be copied to a separate location. A backup stored only on the same SSD does not protect against device or disk failure.

## Security baseline

- Do not expose PostgreSQL to the public internet.
- Prefer Tailscale for private access.
- Use strong unique credentials.
- Store secrets outside the repository.
- Keep the operating system and container images updated.
- Restrict file and database permissions.
- Back up PostgreSQL, images, and configuration.
- Test restoration, not only backup creation.
- Document the actual network exposure.
