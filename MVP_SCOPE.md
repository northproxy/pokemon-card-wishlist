# MVP Scope

## Product vision

Create a self-hosted Pokemon card catalogue that allows a collector to browse cards, mark cards of interest, maintain a simple wishlist, and export the selected records to CSV.

The MVP must remain simple enough to build and operate on a Raspberry Pi while preserving a clean foundation for future collection-management features.

## Target user

The initial target user is a single Pokemon card collector who wants to:

- browse an imported card catalogue;
- filter cards by expansion and available card properties;
- inspect card images;
- select cards from a mobile phone;
- record wanted quantity and optional notes;
- export the current selection as a wishlist.

## Primary user journey

1. Open the application in a mobile browser.
2. Browse or search imported cards.
3. Filter by expansion and available metadata.
4. Preview card details and image.
5. Mark or unmark a card as wanted.
6. Set wanted quantity and optional notes.
7. Open a filtered Wishlist view.
8. Export selected cards to CSV.

## In scope

### Catalogue

- Import card records from prepared source files.
- Store expansions and catalogue records.
- Preserve relevant external source identifiers.
- Store one image reference per catalogue record.
- Represent canonical cards separately from editions, language/finish variants, and Cardmarket market products.
- Support English and German market variants.
- Preserve Cardmarket edition codes and human-readable edition names when available.
- Display the minimum available Cardmarket `avg30` across linked English and German variants as a `From` price.
- Track unmatched, rejected, and ambiguous records during import.

### User interface

- Mobile-friendly browser access.
- Table and/or gallery views.
- Search by card name.
- Filters for expansion and available metadata.
- Card-image preview.
- Wishlist selection control.
- Quantity and notes fields.
- Dedicated filtered Wishlist view.

### Export

Export selected records to CSV.

The export must include, where available:

- card name;
- expansion;
- collector number;
- variant;
- language;
- quantity;
- notes;
- external product identifier;
- minimum available 30-day average price, where available.

### Data import and validation

- Documented import process.
- Repeatable imports.
- Idempotent behaviour where practical.
- Duplicate detection.
- Rejected and unmatched record handling.
- Import summary or validation report.

### Infrastructure

- Self-hosted deployment on Raspberry Pi.
- Docker-based setup.
- Persistent storage on SSD.
- Secure private remote access.
- Automated or scheduled database backup.
- Documented and tested restore procedure.

### Documentation

- `README.md`;
- `MVP_SCOPE.md`;
- `PROJECT.md`;
- `STACK.md`;
- `DECISIONS.md`;
- `GITHUB_PROJECT.md`;
- `LEARNING_LOG.md`;
- setup and operating documentation;
- validation evidence;
- release notes and known limitations.

## Out of scope for MVP

- Price-history charts and analytics beyond retaining imported price snapshots.
- Automated purchasing.
- Cardmarket account integration.
- Native Android or iOS application.
- Multi-user permissions.
- Public user registration.
- Collection-value analytics.
- Automatic image recognition.
- AI card matching.
- Recommendation engine.
- Real-time synchronisation with external sources.
- Full offline mode.
- Public internet access for the MVP application.
- Custom frontend development unless NocoDB is proven insufficient for the core workflow.

## Functional requirements

### FR-01 — Catalogue browsing

The user can view all successfully imported catalogue records.

### FR-02 — Search

The user can search imported records by card name.

### FR-03 — Filtering

The user can filter records by expansion and other available metadata.

### FR-04 — Card image

The user can open or preview the image associated with a catalogue record.

### FR-05 — Wishlist selection

The user can mark and unmark a catalogue record as wanted.

### FR-06 — Wishlist metadata

The user can set wanted quantity and optional notes.

### FR-07 — Wishlist view

The user can view only records currently marked as wanted.

### FR-08 — Export

The user can export the current wishlist to CSV.

### FR-09 — Mobile access

The complete primary user journey works in a mobile browser.

### FR-10 — Data import

An administrator can import or update catalogue data through a documented process.

### FR-11 — Import validation

Each import produces enough evidence to verify row counts, duplicates, rejected records, unmatched records, and missing images.

### FR-12 — Informational market price

For a canonical card with mapped Cardmarket products, the application can display the minimum non-null `avg30` among supported English and German editions and variants. The value is labelled as a `From` price and as a 30-day average.

## Non-functional requirements

- The application should remain usable over a typical home internet connection.
- Catalogue and wishlist data must survive container restarts.
- The system must recover after a Raspberry Pi restart.
- Backups must be restorable.
- PostgreSQL must not be exposed directly to the public internet.
- Secrets must remain outside the repository.
- The system should be understandable by another developer from repository documentation.
- Data imports should be repeatable and idempotent where practical.
- Planned, implemented, and validated functionality must be clearly distinguished in documentation.

## MVP acceptance criteria

The MVP is accepted when:

- one complete expansion has been imported and validated;
- imported cards are visible from a phone;
- associated images are accessible;
- search and expansion filtering work;
- wishlist selections persist;
- quantity and notes persist;
- the Wishlist view works;
- selected records can be exported to CSV;
- mapped cards display the validated minimum `avg30` rule or clearly show that no price is available;
- repeated import does not create uncontrolled duplicates;
- rejected and unmatched records are reported;
- the application starts successfully after a Raspberry Pi restart;
- backup and restore have been documented and tested;
- major technical decisions are recorded as ADRs;
- known limitations are published.
