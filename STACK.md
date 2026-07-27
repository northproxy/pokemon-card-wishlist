# Technical Stack

## Status

This document describes the **proposed MVP stack**. Individual technology choices remain provisional until their ADRs are accepted and validated. The catalogue identity model and source-key strategy have already been accepted in `ADR-005`, `ADR-006`, `ADR-007`, and `ADR-011`.

## Recommended MVP stack

| Layer | Technology | Reason | Status |
|---|---|---|---|
| Hardware | Raspberry Pi 4 or 5 | Low-cost self-hosted server | Proposed |
| Operating system | Raspberry Pi OS Lite 64-bit | Stable, lightweight, and well supported | Proposed |
| Primary storage | USB-connected SSD | More suitable than microSD for database, images, and backups | Proposed |
| Containers | Docker and Docker Compose | Reproducible deployment and simpler service management | Proposed |
| Database | PostgreSQL | Relational integrity, mature backup tools, and future extensibility | Proposed |
| Admin and UI | NocoDB | Fast mobile-friendly catalogue and wishlist workflow without a custom frontend | Proposed |
| Remote access | Tailscale | Private access without public port forwarding | Proposed |
| Image storage | Local SSD filesystem | Simple and inexpensive for the MVP | Proposed |
| Reverse proxy | Caddy, only if later required | Optional HTTPS and routing layer | Deferred |
| Database backup | `pg_dump` | Portable logical backup | Proposed |
| File backup | Encrypted archive or file-level copy | Covers images and configuration | Proposed |
| Repository | GitHub | Version control, documentation, issues, and project tracking | Proposed |
| CI | GitHub Actions | Markdown checks first; automated tests later | Proposed |

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

## Accepted conceptual data model

The final physical schema remains a task for `M3 — Data model`, but discovery has established the following entity boundaries:

```text
canonical card
    → edition
        → language/finish variant
            → Cardmarket market product
                → price snapshot
```

### Catalogue data

Expected entities:

- `expansions`;
- `cards` for canonical set-specific cards;
- `card_editions`;
- `card_variants`;
- source identifiers and source mappings;
- image references.

A canonical card is identified by a source-scoped key such as `('pokemon_tcg_data', 'xy5-20')`. Language and finish do not create additional canonical cards.

### Market data

Expected entities:

- `market_products`;
- `card_market_product_mappings`;
- `market_price_snapshots`.

A Cardmarket product is identified independently by a source-scoped key such as `('cardmarket', '273532')`. A canonical card may map to zero, one, or many market products.

Mapping records should preserve at least:

- mapping status;
- mapping method;
- confidence or evidence level;
- unresolved edition or finish details;
- raw source identifiers.

Price snapshots remain attached to market products. The canonical-card display price is a derived value: the minimum non-null Cardmarket `avg30` among linked English and German editions and variants.

### User-generated data

Expected entities:

- `wishlist_items`;
- wanted quantity;
- notes;
- later optional edition and variant preferences.

The MVP wishlist references the canonical card. Edition- and variant-specific selection is deferred.

### Import-control data

Expected entities:

- import runs;
- staging records;
- rejected records;
- unmatched records;
- ambiguous mappings;
- validation summaries.

Unknown or ambiguous source data must not be silently corrected.

## Preliminary entity sketches

These are conceptual sketches, not final database definitions.

### `cards`

| Field | Notes |
|---|---|
| internal primary key | Implementation choice remains open |
| `source_system` | Canonical catalogue source |
| `source_card_id` | For example `xy5-20` |
| `expansion_id` | Internal relationship to `expansions` |
| `collector_number` | Stored as text |
| `name` | Canonical display name |
| `rarity` | Optional source metadata |
| image reference | Local path or internal URL |

Required uniqueness: `(source_system, source_card_id)`.

### `card_editions`

| Field | Notes |
|---|---|
| `card_id` | Links to the canonical card |
| source edition code | For example `V1` or `V2` |
| display name | For example `Standard` or `Build-A-Bear Workshop` |
| source evidence | URL, source record, or mapping reference |

### `card_variants`

| Field | Notes |
|---|---|
| `edition_id` | Links to an edition |
| language | Initially English or German |
| finish | Normal, reverse holo, holo, or controlled `other` |
| mapping status | Confirmed, candidate, ambiguous, or excluded |

### `market_products`

| Field | Notes |
|---|---|
| `source_system` | `cardmarket` |
| `source_product_id` | Cardmarket `idProduct` |
| source expansion ID | Cardmarket `idExpansion` |
| source metaproduct ID | Preserved when available |
| raw product name | Preserved exactly from source |

Required uniqueness: `(source_system, source_product_id)`.

### `market_price_snapshots`

| Field | Notes |
|---|---|
| `market_product_id` | Links to one market product |
| snapshot timestamp | Source snapshot time |
| `avg30` | Non-foil 30-day average when available |
| `avg30_holo` | Foil/holo 30-day average when available |
| currency | Must be stored explicitly |

### `wishlist_items`

| Field | Notes |
|---|---|
| `card_id` | Links to the canonical card |
| wanted state | Boolean or presence-based design remains open |
| quantity | Default 1; must be positive |
| notes | Optional |
| edition preference | Deferred for the initial UI |
| variant preference | Deferred for the initial UI |

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
