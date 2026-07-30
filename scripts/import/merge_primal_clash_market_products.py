"""
Script: merge_primal_clash_market_products.py

Purpose:
    Merge one validated Primal Clash Cardmarket product staging run into
    market_products. The script resolves the existing internal Primal Clash
    expansion, creates or validates its Cardmarket expansion source identifier,
    excludes Online Code Card products from production, records one audit
    outcome per staged source record, reconciles all counts, and commits the
    complete production merge in one PostgreSQL transaction.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the validated vertical slice.
    It may be replaced only by a generalized market-product merge utility that
    preserves equivalent identity, exclusion, audit, idempotency, and rollback
    guarantees.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import import_primal_clash_market_products as market_import


PRIMAL_CLASH_EXPANSION_KEY = "primal_clash"
PRIMAL_CLASH_NAME = "Primal Clash"
CATALOGUE_SOURCE_SYSTEM = "pokemon_tcg_data"
CATALOGUE_SOURCE_EXPANSION_ID = "xy5"
CARDMARKET_SOURCE_SYSTEM = "cardmarket"
CARDMARKET_SOURCE_EXPANSION_ID = "1585"

ONLINE_CODE_CARD_REASON_CODE = "online_code_card_out_of_scope"
ONLINE_CODE_CARD_REASON_DETAIL = (
    "Online Code Card products are outside the MVP collection scope."
)


@dataclass
class MergeCounts:
    inserted: int = 0
    updated: int = 0
    reactivated: int = 0
    unchanged: int = 0
    skipped: int = 0

    @property
    def production_processed(self) -> int:
        return self.inserted + self.updated + self.reactivated + self.unchanged

    @property
    def total_outcomes(self) -> int:
        return self.production_processed + self.skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge one validated Primal Clash Cardmarket product staging run "
            "into market_products."
        )
    )
    parser.add_argument(
        "--import-run-id",
        type=int,
        required=True,
        help="Validated Cardmarket product import run to merge.",
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
        raise market_import.ImportValidationError(
            f"Import run {import_run_id} does not exist."
        )

    expected_values = {
        "run_kind": market_import.RUN_KIND,
        "source_system": market_import.SOURCE_SYSTEM,
        "source_entity_type": market_import.SOURCE_ENTITY_TYPE,
        "scope_type": market_import.SCOPE_TYPE,
        "scope_reference": (
            f"{market_import.SOURCE_SYSTEM}:"
            f"{market_import.EXPECTED_EXPANSION_ID}"
        ),
        "status": "validated",
        "total_source_records": market_import.EXPECTED_RECORD_COUNT,
        "valid_source_records": market_import.EXPECTED_RECORD_COUNT,
        "rejected_records": 0,
    }
    mismatches = [
        f"{column}={run.get(column)!r}, expected {expected!r}"
        for column, expected in expected_values.items()
        if run.get(column) != expected
    ]
    if mismatches:
        raise market_import.ImportValidationError(
            "Import run is not eligible for this controlled merge: "
            + "; ".join(mismatches)
            + "."
        )

    if run.get("merge_started_at") is not None or run.get("completed_at") is not None:
        raise market_import.ImportValidationError(
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
        raise market_import.ImportValidationError(
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
                staging_market_product_id,
                source_record_reference,
                source_system,
                source_product_id,
                source_expansion_id,
                source_metaproduct_id,
                raw_name,
                source_category_id,
                source_category_name,
                source_created_at,
                raw_payload,
                record_checksum,
                normalization_status,
                validation_status,
                validation_completed_at
            FROM staging_market_products
            WHERE import_run_id = %(import_run_id)s
            ORDER BY source_product_id
            FOR UPDATE
            """,
            {"import_run_id": import_run_id},
        )
        rows = [dict(row) for row in cursor.fetchall()]

    if len(rows) != market_import.EXPECTED_RECORD_COUNT:
        raise market_import.ImportValidationError(
            f"Expected {market_import.EXPECTED_RECORD_COUNT} staging rows, "
            f"found {len(rows)}."
        )

    product_ids: set[str] = set()
    references: set[str] = set()
    code_card_ids: set[str] = set()

    for row in rows:
        product_id = row["source_product_id"]
        reference = row["source_record_reference"]

        if (
            row["source_system"] != market_import.SOURCE_SYSTEM
            or row["source_expansion_id"]
            != market_import.EXPECTED_EXPANSION_ID
            or not product_id
            or not reference
            or not row["source_metaproduct_id"]
            or not row["raw_name"]
            or not row["source_category_id"]
            or not row["source_category_name"]
            or row["raw_payload"] is None
            or not row["record_checksum"]
            or row["normalization_status"] != "normalized"
            or row["validation_status"] != "valid"
            or row["validation_completed_at"] is None
        ):
            raise market_import.ImportValidationError(
                "Staging row is incomplete or not valid: "
                f"{row['staging_market_product_id']}."
            )

        if product_id in product_ids:
            raise market_import.ImportValidationError(
                f"Duplicate staged source_product_id: {product_id}."
            )
        if reference in references:
            raise market_import.ImportValidationError(
                f"Duplicate staged source_record_reference: {reference}."
            )
        product_ids.add(product_id)
        references.add(reference)

        if is_online_code_card(row):
            code_card_ids.add(product_id)

    if code_card_ids != set(market_import.EXPECTED_CODE_CARD_IDS):
        raise market_import.ImportValidationError(
            "Online Code Card identities do not match the controlled fixture. "
            f"Expected {sorted(market_import.EXPECTED_CODE_CARD_IDS)}, "
            f"found {sorted(code_card_ids)}."
        )

    eligible_count = len(rows) - len(code_card_ids)
    if eligible_count != market_import.EXPECTED_ELIGIBLE_COUNT:
        raise market_import.ImportValidationError(
            f"Expected {market_import.EXPECTED_ELIGIBLE_COUNT} eligible "
            f"products, found {eligible_count}."
        )

    return rows


def is_online_code_card(row: dict[str, Any]) -> bool:
    return (
        row["source_category_id"] == "51"
        and row["raw_name"].startswith("Online Code Card")
    )


def resolve_primal_clash_expansion(connection: Connection[Any]) -> int:
    catalogue_identifier = fetch_one_dict(
        connection,
        """
        SELECT
            identifiers.expansion_id,
            expansions.expansion_key,
            expansions.name,
            identifiers.is_active
        FROM expansion_source_identifiers AS identifiers
        JOIN expansions
          ON expansions.expansion_id = identifiers.expansion_id
        WHERE identifiers.source_system = %(source_system)s
          AND identifiers.source_expansion_id = %(source_expansion_id)s
        FOR UPDATE OF identifiers, expansions
        """,
        {
            "source_system": CATALOGUE_SOURCE_SYSTEM,
            "source_expansion_id": CATALOGUE_SOURCE_EXPANSION_ID,
        },
    )
    if catalogue_identifier is None:
        raise market_import.ImportValidationError(
            "The existing Primal Clash catalogue source identifier "
            "'pokemon_tcg_data/xy5' could not be resolved."
        )

    if (
        catalogue_identifier["expansion_key"] != PRIMAL_CLASH_EXPANSION_KEY
        or catalogue_identifier["name"] != PRIMAL_CLASH_NAME
        or catalogue_identifier["is_active"] is not True
    ):
        raise market_import.ImportValidationError(
            "The resolved catalogue source identifier does not point to the "
            "expected active internal Primal Clash expansion."
        )

    expansion_id = int(catalogue_identifier["expansion_id"])

    cardmarket_identifier = fetch_one_dict(
        connection,
        """
        SELECT
            expansion_source_identifier_id,
            expansion_id,
            source_name,
            is_active
        FROM expansion_source_identifiers
        WHERE source_system = %(source_system)s
          AND source_expansion_id = %(source_expansion_id)s
        FOR UPDATE
        """,
        {
            "source_system": CARDMARKET_SOURCE_SYSTEM,
            "source_expansion_id": CARDMARKET_SOURCE_EXPANSION_ID,
        },
    )

    if cardmarket_identifier is None:
        connection.execute(
            """
            INSERT INTO expansion_source_identifiers (
                expansion_id,
                source_system,
                source_expansion_id,
                source_name,
                source_payload,
                is_active
            )
            VALUES (
                %(expansion_id)s,
                %(source_system)s,
                %(source_expansion_id)s,
                %(source_name)s,
                %(source_payload)s,
                TRUE
            )
            """,
            {
                "expansion_id": expansion_id,
                "source_system": CARDMARKET_SOURCE_SYSTEM,
                "source_expansion_id": CARDMARKET_SOURCE_EXPANSION_ID,
                "source_name": PRIMAL_CLASH_NAME,
                "source_payload": Jsonb(
                    {
                        "controlledImport": "primal_clash",
                        "sourceExpansionId": CARDMARKET_SOURCE_EXPANSION_ID,
                    }
                ),
            },
        )
    elif (
        int(cardmarket_identifier["expansion_id"]) != expansion_id
        or cardmarket_identifier["is_active"] is not True
    ):
        raise market_import.ImportValidationError(
            "Cardmarket expansion identifier '1585' already exists but does "
            "not resolve to the expected active Primal Clash expansion."
        )

    return expansion_id


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
        raise market_import.ImportValidationError(
            "Import run could not transition from validated to merging."
        )


def comparable_values(row: dict[str, Any], expansion_id: int) -> dict[str, Any]:
    return {
        "source_expansion_id": row["source_expansion_id"],
        "expansion_id": expansion_id,
        "source_metaproduct_id": row["source_metaproduct_id"],
        "raw_name": row["raw_name"],
        "source_category_id": row["source_category_id"],
        "source_category_name": row["source_category_name"],
        "source_created_at": row["source_created_at"],
    }


def determine_changes(
    existing: dict[str, Any],
    desired: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for field, new_value in desired.items():
        old_value = existing[field]
        if old_value != new_value:
            changes[field] = {"from": old_value, "to": new_value}
    return changes


def record_outcome(
    connection: Connection[Any],
    *,
    import_run_id: int,
    row: dict[str, Any],
    outcome_type: str,
    production_entity_id: int | None,
    reason_code: str | None = None,
    reason_detail: str | None = None,
    change_summary: dict[str, Any] | None = None,
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
            'market_product',
            %(source_system)s,
            %(source_entity_id)s,
            %(source_record_reference)s,
            %(production_entity_id)s,
            %(outcome_type)s,
            %(reason_code)s,
            %(reason_detail)s,
            %(change_summary)s
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
            "change_summary": (
                Jsonb(change_summary) if change_summary is not None else None
            ),
        },
    )


def merge_one_product(
    connection: Connection[Any],
    *,
    import_run_id: int,
    expansion_id: int,
    row: dict[str, Any],
    counts: MergeCounts,
) -> None:
    if is_online_code_card(row):
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

    existing = fetch_one_dict(
        connection,
        """
        SELECT
            market_product_id,
            source_system,
            source_product_id,
            source_expansion_id,
            expansion_id,
            source_metaproduct_id,
            raw_name,
            source_category_id,
            source_category_name,
            source_created_at,
            is_active,
            retired_at
        FROM market_products
        WHERE source_system = %(source_system)s
          AND source_product_id = %(source_product_id)s
        FOR UPDATE
        """,
        {
            "source_system": row["source_system"],
            "source_product_id": row["source_product_id"],
        },
    )

    desired = comparable_values(row, expansion_id)

    if existing is None:
        inserted = connection.execute(
            """
            INSERT INTO market_products (
                source_system,
                source_product_id,
                source_expansion_id,
                expansion_id,
                source_metaproduct_id,
                raw_name,
                source_category_id,
                source_category_name,
                source_created_at,
                is_active,
                retired_at
            )
            VALUES (
                %(source_system)s,
                %(source_product_id)s,
                %(source_expansion_id)s,
                %(expansion_id)s,
                %(source_metaproduct_id)s,
                %(raw_name)s,
                %(source_category_id)s,
                %(source_category_name)s,
                %(source_created_at)s,
                TRUE,
                NULL
            )
            RETURNING market_product_id
            """,
            {
                "source_system": row["source_system"],
                "source_product_id": row["source_product_id"],
                **desired,
            },
        ).fetchone()
        if inserted is None:
            raise RuntimeError("Database did not return market_product_id.")

        market_product_id = int(inserted[0])
        record_outcome(
            connection,
            import_run_id=import_run_id,
            row=row,
            outcome_type="inserted",
            production_entity_id=market_product_id,
        )
        counts.inserted += 1
        return

    market_product_id = int(existing["market_product_id"])
    changes = determine_changes(existing, desired)

    if existing["is_active"] is not True:
        connection.execute(
            """
            UPDATE market_products
            SET
                source_expansion_id = %(source_expansion_id)s,
                expansion_id = %(expansion_id)s,
                source_metaproduct_id = %(source_metaproduct_id)s,
                raw_name = %(raw_name)s,
                source_category_id = %(source_category_id)s,
                source_category_name = %(source_category_name)s,
                source_created_at = %(source_created_at)s,
                is_active = TRUE,
                retired_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE market_product_id = %(market_product_id)s
            """,
            {"market_product_id": market_product_id, **desired},
        )
        changes["is_active"] = {"from": existing["is_active"], "to": True}
        changes["retired_at"] = {"from": existing["retired_at"], "to": None}
        record_outcome(
            connection,
            import_run_id=import_run_id,
            row=row,
            outcome_type="reactivated",
            production_entity_id=market_product_id,
            change_summary=changes,
        )
        counts.reactivated += 1
        return

    if changes:
        connection.execute(
            """
            UPDATE market_products
            SET
                source_expansion_id = %(source_expansion_id)s,
                expansion_id = %(expansion_id)s,
                source_metaproduct_id = %(source_metaproduct_id)s,
                raw_name = %(raw_name)s,
                source_category_id = %(source_category_id)s,
                source_category_name = %(source_category_name)s,
                source_created_at = %(source_created_at)s,
                updated_at = CURRENT_TIMESTAMP
            WHERE market_product_id = %(market_product_id)s
            """,
            {"market_product_id": market_product_id, **desired},
        )
        record_outcome(
            connection,
            import_run_id=import_run_id,
            row=row,
            outcome_type="updated",
            production_entity_id=market_product_id,
            change_summary=changes,
        )
        counts.updated += 1
        return

    record_outcome(
        connection,
        import_run_id=import_run_id,
        row=row,
        outcome_type="unchanged",
        production_entity_id=market_product_id,
    )
    counts.unchanged += 1


def validate_merged_state(
    connection: Connection[Any],
    *,
    import_run_id: int,
    expansion_id: int,
    counts: MergeCounts,
) -> None:
    if counts.production_processed != market_import.EXPECTED_ELIGIBLE_COUNT:
        raise market_import.ImportValidationError(
            "Production outcome count does not reconcile: "
            f"{counts.production_processed} processed, expected "
            f"{market_import.EXPECTED_ELIGIBLE_COUNT}."
        )
    if counts.skipped != market_import.EXPECTED_CODE_CARD_COUNT:
        raise market_import.ImportValidationError(
            f"Skipped count is {counts.skipped}, expected "
            f"{market_import.EXPECTED_CODE_CARD_COUNT}."
        )
    if counts.total_outcomes != market_import.EXPECTED_RECORD_COUNT:
        raise market_import.ImportValidationError(
            f"Total outcomes are {counts.total_outcomes}, expected "
            f"{market_import.EXPECTED_RECORD_COUNT}."
        )

    production_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM market_products
        WHERE source_system = 'cardmarket'
          AND source_expansion_id = '1585'
          AND expansion_id = %(expansion_id)s
        """,
        {"expansion_id": expansion_id},
    )
    if production_count != market_import.EXPECTED_ELIGIBLE_COUNT:
        raise market_import.ImportValidationError(
            f"Production contains {production_count} Primal Clash Cardmarket "
            f"products, expected {market_import.EXPECTED_ELIGIBLE_COUNT}."
        )

    code_cards_in_production = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM market_products
        WHERE source_system = 'cardmarket'
          AND source_product_id = ANY(%(code_card_ids)s)
        """,
        {"code_card_ids": list(market_import.EXPECTED_CODE_CARD_IDS)},
    )
    if code_cards_in_production != 0:
        raise market_import.ImportValidationError(
            f"Found {code_cards_in_production} Online Code Card products in "
            "market_products."
        )

    outcome_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_record_outcomes
        WHERE import_run_id = %(import_run_id)s
          AND entity_type = 'market_product'
        """,
        {"import_run_id": import_run_id},
    )
    if outcome_count != market_import.EXPECTED_RECORD_COUNT:
        raise market_import.ImportValidationError(
            f"Recorded {outcome_count} market-product outcomes, expected "
            f"{market_import.EXPECTED_RECORD_COUNT}."
        )

    skipped_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_record_outcomes
        WHERE import_run_id = %(import_run_id)s
          AND entity_type = 'market_product'
          AND outcome_type = 'skipped'
          AND reason_code = %(reason_code)s
          AND production_entity_id IS NULL
        """,
        {
            "import_run_id": import_run_id,
            "reason_code": ONLINE_CODE_CARD_REASON_CODE,
        },
    )
    if skipped_count != market_import.EXPECTED_CODE_CARD_COUNT:
        raise market_import.ImportValidationError(
            f"Recorded {skipped_count} controlled skipped outcomes, expected "
            f"{market_import.EXPECTED_CODE_CARD_COUNT}."
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
            updated_records = %(updated_records)s,
            unchanged_records = %(unchanged_records)s,
            missing_records = 0,
            retired_records = 0
        WHERE import_run_id = %(import_run_id)s
          AND status = 'merge_started'
        """,
        {
            "import_run_id": import_run_id,
            "inserted_records": counts.inserted,
            "updated_records": counts.updated + counts.reactivated,
            "unchanged_records": counts.unchanged,
        },
    )
    if result.rowcount != 1:
        raise market_import.ImportValidationError(
            "Import run could not transition from merge_started to succeeded."
        )


def main() -> int:
    args = parse_args()
    if args.import_run_id < 1:
        raise market_import.ImportValidationError(
            "--import-run-id must be a positive integer."
        )

    database_url = market_import.get_database_url()
    counts = MergeCounts()

    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            run = lock_and_validate_import_run(connection, args.import_run_id)
            staging_rows = load_and_validate_staging_rows(
                connection, args.import_run_id
            )
            expansion_id = resolve_primal_clash_expansion(connection)
            mark_merge_started(connection, args.import_run_id)

            for row in staging_rows:
                merge_one_product(
                    connection,
                    import_run_id=args.import_run_id,
                    expansion_id=expansion_id,
                    row=row,
                    counts=counts,
                )

            validate_merged_state(
                connection,
                import_run_id=args.import_run_id,
                expansion_id=expansion_id,
                counts=counts,
            )
            complete_import_run(
                connection,
                import_run_id=args.import_run_id,
                counts=counts,
            )

    print("Primal Clash Cardmarket product production merge committed")
    print(f"Import run ID: {args.import_run_id}")
    print(f"Run reference: {run['run_reference']}")
    print(f"Expansion ID: {expansion_id}")
    print(f"Inserted market products: {counts.inserted}")
    print(f"Updated market products: {counts.updated}")
    print(f"Reactivated market products: {counts.reactivated}")
    print(f"Unchanged market products: {counts.unchanged}")
    print(f"Skipped Online Code Card records: {counts.skipped}")
    print(f"Processed source records: {counts.total_outcomes}")
    print("Final status: succeeded")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (market_import.ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
