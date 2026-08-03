"""
Script: merge_primal_clash_market_prices.py

Purpose:
    Merge one validated Primal Clash Cardmarket price staging run into
    market_price_snapshots. The script resolves eligible Cardmarket products,
    excludes the controlled Online Code Card records, preserves append-only
    snapshot identity, records one audit outcome per staged source record,
    reconciles all counts, and commits the complete merge in one PostgreSQL
    transaction.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the validated vertical slice.
    It may be replaced only by a generalized market-price merge utility that
    preserves equivalent snapshot identity, exclusion, audit, idempotency,
    conflict-detection, and rollback guarantees.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

import import_primal_clash_market_prices as price_import


EXPECTED_ELIGIBLE_COUNT = 173
EXPECTED_SKIPPED_COUNT = 4
EXPECTED_ONLINE_CODE_CARD_IDS = frozenset(
    {"300914", "300919", "300971", "300972"}
)
ONLINE_CODE_CARD_REASON_CODE = "online_code_card_out_of_scope"
ONLINE_CODE_CARD_REASON_DETAIL = (
    "Online Code Card products are outside the MVP collection scope."
)
SNAPSHOT_CONFLICT_REASON_CODE = "market_price_snapshot_identity_conflict"


@dataclass
class MergeCounts:
    inserted: int = 0
    unchanged: int = 0
    skipped: int = 0

    @property
    def production_processed(self) -> int:
        return self.inserted + self.unchanged

    @property
    def total_outcomes(self) -> int:
        return self.production_processed + self.skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge one validated Primal Clash Cardmarket price staging run "
            "into market_price_snapshots."
        )
    )
    parser.add_argument(
        "--import-run-id",
        type=int,
        required=True,
        help="Validated Cardmarket price import run to merge.",
    )
    return parser.parse_args()


def fetch_one_dict(
    connection: Connection[Any],
    query: str,
    parameters: dict[str, Any],
) -> dict[str, Any] | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, parameters)
        row = cursor.fetchone()
    return dict(row) if row is not None else None


def fetch_scalar(
    connection: Connection[Any],
    query: str,
    parameters: dict[str, Any],
) -> int:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise RuntimeError("Validation query returned no row.")
    return int(row[0])


def lock_and_validate_import_run(
    connection: Connection[Any],
    import_run_id: int,
) -> dict[str, Any]:
    run = fetch_one_dict(
        connection,
        """
        SELECT *
        FROM import_runs
        WHERE import_run_id = %(import_run_id)s
        FOR UPDATE
        """,
        {"import_run_id": import_run_id},
    )
    if run is None:
        raise price_import.ImportValidationError(
            f"Import run {import_run_id} does not exist."
        )

    expected_values = {
        "run_kind": price_import.RUN_KIND,
        "source_system": price_import.SOURCE_SYSTEM,
        "source_entity_type": price_import.SOURCE_ENTITY_TYPE,
        "scope_type": price_import.SCOPE_TYPE,
        "scope_reference": (
            f"{price_import.SOURCE_SYSTEM}:"
            f"{price_import.EXPECTED_EXPANSION_ID}"
        ),
        "status": "validated",
        "total_source_records": price_import.EXPECTED_RECORD_COUNT,
        "valid_source_records": price_import.EXPECTED_RECORD_COUNT,
        "rejected_records": 0,
    }
    mismatches = [
        f"{column}={run.get(column)!r}, expected {expected!r}"
        for column, expected in expected_values.items()
        if run.get(column) != expected
    ]
    if mismatches:
        raise price_import.ImportValidationError(
            "Import run is not eligible for this controlled merge: "
            + "; ".join(mismatches)
            + "."
        )

    if run.get("merge_started_at") is not None or run.get("completed_at") is not None:
        raise price_import.ImportValidationError(
            "Import run already contains merge lifecycle timestamps."
        )

    existing_outcomes = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_record_outcomes
        WHERE import_run_id = %(import_run_id)s
        """,
        {"import_run_id": import_run_id},
    )
    if existing_outcomes != 0:
        raise price_import.ImportValidationError(
            f"Import run already has {existing_outcomes} record outcomes."
        )

    return run


def load_and_validate_staging_rows(
    connection: Connection[Any],
    import_run_id: int,
) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
                staging_market_price_id,
                source_record_reference,
                source_system,
                source_product_id,
                source_snapshot_at,
                currency_code,
                avg30_raw,
                avg30,
                avg30_holo_raw,
                avg30_holo,
                raw_payload,
                record_checksum,
                normalization_status,
                validation_status,
                validation_completed_at
            FROM staging_market_prices
            WHERE import_run_id = %(import_run_id)s
            ORDER BY source_product_id
            FOR UPDATE
            """,
            {"import_run_id": import_run_id},
        )
        rows = [dict(row) for row in cursor.fetchall()]

    if len(rows) != price_import.EXPECTED_RECORD_COUNT:
        raise price_import.ImportValidationError(
            f"Expected {price_import.EXPECTED_RECORD_COUNT} staging rows, "
            f"found {len(rows)}."
        )

    product_ids: set[str] = set()
    references: set[str] = set()
    snapshot_values: set[Any] = set()

    for row in rows:
        product_id = row["source_product_id"]
        reference = row["source_record_reference"]
        snapshot_at = row["source_snapshot_at"]

        if (
            row["source_system"] != price_import.SOURCE_SYSTEM
            or not product_id
            or not reference
            or snapshot_at is None
            or row["currency_code"] != price_import.CURRENCY_CODE
            or row["avg30"] is None
            or row["raw_payload"] is None
            or not row["record_checksum"]
            or row["normalization_status"] != "normalized"
            or row["validation_status"] != "valid"
            or row["validation_completed_at"] is None
        ):
            raise price_import.ImportValidationError(
                "Staging row is incomplete or not valid: "
                f"{row['staging_market_price_id']}."
            )

        if product_id in product_ids:
            raise price_import.ImportValidationError(
                f"Duplicate staged source_product_id: {product_id}."
            )
        if reference in references:
            raise price_import.ImportValidationError(
                f"Duplicate staged source_record_reference: {reference}."
            )

        product_ids.add(product_id)
        references.add(reference)
        snapshot_values.add(snapshot_at)

    if len(snapshot_values) != 1:
        raise price_import.ImportValidationError(
            f"Expected one controlled source snapshot timestamp, found "
            f"{len(snapshot_values)}."
        )

    return rows


def mark_merge_started(
    connection: Connection[Any],
    import_run_id: int,
) -> None:
    result = connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'merge_started',
            merge_started_at = CURRENT_TIMESTAMP
        WHERE import_run_id = %(import_run_id)s
          AND status = 'validated'
        """,
        {"import_run_id": import_run_id},
    )
    if result.rowcount != 1:
        raise price_import.ImportValidationError(
            "Import run could not transition from validated to merge_started."
        )


def resolve_market_product(
    connection: Connection[Any],
    source_product_id: str,
) -> dict[str, Any] | None:
    return fetch_one_dict(
        connection,
        """
        SELECT
            market_product_id,
            source_system,
            source_product_id,
            source_expansion_id,
            is_active
        FROM market_products
        WHERE source_system = %(source_system)s
          AND source_product_id = %(source_product_id)s
        FOR UPDATE
        """,
        {
            "source_system": price_import.SOURCE_SYSTEM,
            "source_product_id": source_product_id,
        },
    )


def record_outcome(
    connection: Connection[Any],
    *,
    import_run_id: int,
    row: dict[str, Any],
    outcome_type: str,
    production_entity_id: int | None,
    reason_code: str | None = None,
    reason_detail: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO import_record_outcomes (
            import_run_id,
            entity_type,
            source_system,
            source_entity_id,
            source_record_reference,
            production_entity_id,
            outcome_type,
            reason_code,
            reason_detail,
            change_summary
        )
        VALUES (
            %(import_run_id)s,
            'market_price_snapshot',
            %(source_system)s,
            %(source_entity_id)s,
            %(source_record_reference)s,
            %(production_entity_id)s,
            %(outcome_type)s,
            %(reason_code)s,
            %(reason_detail)s,
            NULL
        )
        """,
        {
            "import_run_id": import_run_id,
            "source_system": row["source_system"],
            "source_entity_id": row["source_product_id"],
            "source_record_reference": row["source_record_reference"],
            "production_entity_id": production_entity_id,
            "outcome_type": outcome_type,
            "reason_code": reason_code,
            "reason_detail": reason_detail,
        },
    )


def normalize_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def existing_snapshot_matches(
    existing: dict[str, Any],
    row: dict[str, Any],
) -> bool:
    return (
        existing["currency_code"] == row["currency_code"]
        and normalize_decimal(existing["avg30"]) == normalize_decimal(row["avg30"])
        and normalize_decimal(existing["avg30_holo"])
        == normalize_decimal(row["avg30_holo"])
        and existing["source_record_reference"] == row["source_record_reference"]
        and existing["record_checksum"] == row["record_checksum"]
    )


def merge_one_price(
    connection: Connection[Any],
    *,
    import_run_id: int,
    row: dict[str, Any],
    counts: MergeCounts,
) -> None:
    source_product_id = row["source_product_id"]
    market_product = resolve_market_product(connection, source_product_id)

    if market_product is None:
        if source_product_id not in EXPECTED_ONLINE_CODE_CARD_IDS:
            raise price_import.ImportValidationError(
                "No production market product exists for unexpected price "
                f"record {source_product_id}."
            )
        record_outcome(
            connection,
            import_run_id=import_run_id,
            row=row,
            outcome_type="skipped",
            production_entity_id=None,
            reason_code=ONLINE_CODE_CARD_REASON_CODE,
            reason_detail=ONLINE_CODE_CARD_REASON_DETAIL,
        )
        counts.skipped += 1
        return

    if source_product_id in EXPECTED_ONLINE_CODE_CARD_IDS:
        raise price_import.ImportValidationError(
            f"Online Code Card product {source_product_id} unexpectedly exists "
            "in market_products."
        )
    if market_product["is_active"] is not True:
        raise price_import.ImportValidationError(
            f"Market product {source_product_id} is inactive."
        )
    if market_product["source_expansion_id"] != price_import.EXPECTED_EXPANSION_ID:
        raise price_import.ImportValidationError(
            f"Market product {source_product_id} is outside Cardmarket "
            f"expansion {price_import.EXPECTED_EXPANSION_ID}."
        )

    market_product_id = int(market_product["market_product_id"])
    existing = fetch_one_dict(
        connection,
        """
        SELECT
            market_price_snapshot_id,
            market_product_id,
            import_run_id,
            source_snapshot_at,
            currency_code,
            avg30,
            avg30_holo,
            source_record_reference,
            record_checksum
        FROM market_price_snapshots
        WHERE market_product_id = %(market_product_id)s
          AND source_snapshot_at = %(source_snapshot_at)s
        FOR UPDATE
        """,
        {
            "market_product_id": market_product_id,
            "source_snapshot_at": row["source_snapshot_at"],
        },
    )

    if existing is not None:
        snapshot_id = int(existing["market_price_snapshot_id"])
        if not existing_snapshot_matches(existing, row):
            raise price_import.ImportValidationError(
                f"{SNAPSHOT_CONFLICT_REASON_CODE}: product "
                f"{source_product_id} already has a different snapshot at "
                f"{row['source_snapshot_at'].isoformat()}."
            )

        record_outcome(
            connection,
            import_run_id=import_run_id,
            row=row,
            outcome_type="unchanged",
            production_entity_id=snapshot_id,
        )
        counts.unchanged += 1
        return

    inserted = connection.execute(
        """
        INSERT INTO market_price_snapshots (
            market_product_id,
            import_run_id,
            source_snapshot_at,
            currency_code,
            avg30,
            avg30_holo,
            source_record_reference,
            record_checksum
        )
        VALUES (
            %(market_product_id)s,
            %(import_run_id)s,
            %(source_snapshot_at)s,
            %(currency_code)s,
            %(avg30)s,
            %(avg30_holo)s,
            %(source_record_reference)s,
            %(record_checksum)s
        )
        RETURNING market_price_snapshot_id
        """,
        {
            "market_product_id": market_product_id,
            "import_run_id": import_run_id,
            "source_snapshot_at": row["source_snapshot_at"],
            "currency_code": row["currency_code"],
            "avg30": row["avg30"],
            "avg30_holo": row["avg30_holo"],
            "source_record_reference": row["source_record_reference"],
            "record_checksum": row["record_checksum"],
        },
    ).fetchone()
    if inserted is None:
        raise RuntimeError("Database did not return market_price_snapshot_id.")

    record_outcome(
        connection,
        import_run_id=import_run_id,
        row=row,
        outcome_type="inserted",
        production_entity_id=int(inserted[0]),
    )
    counts.inserted += 1


def validate_merged_state(
    connection: Connection[Any],
    *,
    import_run_id: int,
    rows: list[dict[str, Any]],
    counts: MergeCounts,
) -> None:
    if counts.production_processed != EXPECTED_ELIGIBLE_COUNT:
        raise price_import.ImportValidationError(
            "Production outcome count does not reconcile: "
            f"{counts.production_processed} processed, expected "
            f"{EXPECTED_ELIGIBLE_COUNT}."
        )
    if counts.skipped != EXPECTED_SKIPPED_COUNT:
        raise price_import.ImportValidationError(
            f"Skipped count is {counts.skipped}, expected "
            f"{EXPECTED_SKIPPED_COUNT}."
        )
    if counts.total_outcomes != price_import.EXPECTED_RECORD_COUNT:
        raise price_import.ImportValidationError(
            f"Total outcomes are {counts.total_outcomes}, expected "
            f"{price_import.EXPECTED_RECORD_COUNT}."
        )

    source_snapshot_at = rows[0]["source_snapshot_at"]
    snapshot_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM market_price_snapshots AS snapshots
        JOIN market_products AS products
          ON products.market_product_id = snapshots.market_product_id
        WHERE products.source_system = 'cardmarket'
          AND products.source_expansion_id = '1585'
          AND snapshots.source_snapshot_at = %(source_snapshot_at)s
        """,
        {"source_snapshot_at": source_snapshot_at},
    )
    if snapshot_count != EXPECTED_ELIGIBLE_COUNT:
        raise price_import.ImportValidationError(
            f"Production contains {snapshot_count} snapshots for the "
            f"controlled source timestamp, expected {EXPECTED_ELIGIBLE_COUNT}."
        )

    duplicate_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT market_product_id, source_snapshot_at
            FROM market_price_snapshots
            GROUP BY market_product_id, source_snapshot_at
            HAVING COUNT(*) > 1
        ) AS duplicates
        """,
        {},
    )
    if duplicate_count != 0:
        raise price_import.ImportValidationError(
            f"Found {duplicate_count} duplicate snapshot identity groups."
        )

    outcome_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_record_outcomes
        WHERE import_run_id = %(import_run_id)s
          AND entity_type = 'market_price_snapshot'
        """,
        {"import_run_id": import_run_id},
    )
    if outcome_count != price_import.EXPECTED_RECORD_COUNT:
        raise price_import.ImportValidationError(
            f"Recorded {outcome_count} price outcomes, expected "
            f"{price_import.EXPECTED_RECORD_COUNT}."
        )

    skipped_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_record_outcomes
        WHERE import_run_id = %(import_run_id)s
          AND entity_type = 'market_price_snapshot'
          AND outcome_type = 'skipped'
          AND reason_code = %(reason_code)s
          AND production_entity_id IS NULL
        """,
        {
            "import_run_id": import_run_id,
            "reason_code": ONLINE_CODE_CARD_REASON_CODE,
        },
    )
    if skipped_count != EXPECTED_SKIPPED_COUNT:
        raise price_import.ImportValidationError(
            f"Recorded {skipped_count} controlled skipped outcomes, expected "
            f"{EXPECTED_SKIPPED_COUNT}."
        )


def complete_import_run(
    connection: Connection[Any],
    *,
    import_run_id: int,
    counts: MergeCounts,
) -> None:
    result = connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'succeeded',
            completed_at = CURRENT_TIMESTAMP,
            inserted_records = %(inserted_records)s,
            updated_records = 0,
            unchanged_records = %(unchanged_records)s,
            missing_records = 0,
            retired_records = 0
        WHERE import_run_id = %(import_run_id)s
          AND status = 'merge_started'
        """,
        {
            "import_run_id": import_run_id,
            "inserted_records": counts.inserted,
            "unchanged_records": counts.unchanged,
        },
    )
    if result.rowcount != 1:
        raise price_import.ImportValidationError(
            "Import run could not transition from merge_started to succeeded."
        )


def main() -> int:
    args = parse_args()
    if args.import_run_id < 1:
        raise price_import.ImportValidationError(
            "--import-run-id must be a positive integer."
        )

    database_url = price_import.get_database_url()
    counts = MergeCounts()

    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            run = lock_and_validate_import_run(connection, args.import_run_id)
            staging_rows = load_and_validate_staging_rows(
                connection, args.import_run_id
            )
            mark_merge_started(connection, args.import_run_id)

            for row in staging_rows:
                merge_one_price(
                    connection,
                    import_run_id=args.import_run_id,
                    row=row,
                    counts=counts,
                )

            validate_merged_state(
                connection,
                import_run_id=args.import_run_id,
                rows=staging_rows,
                counts=counts,
            )
            complete_import_run(
                connection,
                import_run_id=args.import_run_id,
                counts=counts,
            )

    print("Primal Clash Cardmarket price production merge committed")
    print(f"Import run ID: {args.import_run_id}")
    print(f"Run reference: {run['run_reference']}")
    print(f"Source snapshot at: {staging_rows[0]['source_snapshot_at'].isoformat()}")
    print(f"Inserted market price snapshots: {counts.inserted}")
    print(f"Unchanged market price snapshots: {counts.unchanged}")
    print(f"Skipped Online Code Card records: {counts.skipped}")
    print(f"Processed source records: {counts.total_outcomes}")
    print("Final status: succeeded")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (price_import.ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
