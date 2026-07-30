"""
Script: merge_primal_clash_market_mappings.py

Purpose:
    Validate one staged Primal Clash Cardmarket mapping run before production
    merge implementation. This phase reads import and production identities,
    reconciles all controlled mapping categories, and performs no database
    writes.

Lifecycle:
    Transitional implementation phase of a permanent project utility.

Removal:
    Replace this read-only phase with the validated transactional production
    merge only after identity resolution, controlled category counts, and
    rollback behaviour have been confirmed.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

import import_primal_clash_market_mappings as mapping_import


ONLINE_CODE_CARD_PRODUCT_IDS = frozenset(
    {
        "300914",
        "300919",
        "300971",
        "300972",
    }
)

OVERSIZED_PRODUCT_IDS = frozenset(
    {
        "363664",
        "363665",
    }
)


@dataclass(frozen=True)
class ValidationCounts:
    staged: int
    candidates: int
    excluded: int
    unmatched_duplicate_candidates: int
    resolved_candidate_products: int
    resolved_candidate_cards: int
    resolved_oversized_products: int
    resolved_unmatched_products: int
    missing_online_code_products: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read and validate one staged Primal Clash Cardmarket mapping run "
            "without writing to production tables."
        )
    )
    parser.add_argument(
        "--import-run-id",
        type=int,
        required=True,
        help="Validated Cardmarket mapping import run to inspect.",
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


def load_import_run(
    connection: Connection[Any],
    import_run_id: int,
) -> dict[str, Any]:
    run = fetch_one_dict(
        connection,
        """
        SELECT *
        FROM import_runs
        WHERE import_run_id = %(import_run_id)s
        """,
        {"import_run_id": import_run_id},
    )
    if run is None:
        raise mapping_import.ImportValidationError(
            f"Import run {import_run_id} does not exist."
        )

    expected_values = {
        "run_kind": mapping_import.RUN_KIND,
        "source_system": mapping_import.SOURCE_SYSTEM,
        "source_entity_type": mapping_import.SOURCE_ENTITY_TYPE,
        "scope_type": mapping_import.SCOPE_TYPE,
        "scope_reference": (
            f"{mapping_import.SOURCE_SYSTEM}:"
            f"{mapping_import.EXPECTED_EXPANSION_ID}"
        ),
        "status": "validated",
        "total_source_records": mapping_import.EXPECTED_RECORD_COUNT,
        "valid_source_records": mapping_import.EXPECTED_RECORD_COUNT,
        "rejected_records": 0,
    }

    mismatches = [
        f"{column}={run.get(column)!r}, expected {expected!r}"
        for column, expected in expected_values.items()
        if run.get(column) != expected
    ]
    if mismatches:
        raise mapping_import.ImportValidationError(
            "Import run is not eligible for the controlled merge: "
            + "; ".join(mismatches)
            + "."
        )

    if run.get("merge_started_at") is not None or run.get("completed_at") is not None:
        raise mapping_import.ImportValidationError(
            "Import run already contains merge lifecycle timestamps."
        )

    return run


def load_staging_rows(
    connection: Connection[Any],
    import_run_id: int,
) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
                source_record_reference,
                market_source_system,
                source_product_id,
                catalogue_source_system,
                source_card_id,
                source_edition_code,
                proposed_status,
                confirmation_scope,
                confirmation_method,
                evidence_level,
                evidence_reference,
                evidence_payload,
                raw_payload,
                record_checksum,
                normalization_status,
                validation_status,
                validation_completed_at
            FROM staging_market_mappings
            WHERE import_run_id = %(import_run_id)s
            ORDER BY source_product_id
            """,
            {"import_run_id": import_run_id},
        )
        return [dict(row) for row in cursor.fetchall()]


def validate_staging_rows(
    rows: list[dict[str, Any]],
) -> None:
    if len(rows) != mapping_import.EXPECTED_RECORD_COUNT:
        raise mapping_import.ImportValidationError(
            f"Expected {mapping_import.EXPECTED_RECORD_COUNT} staging rows, "
            f"found {len(rows)}."
        )

    references: set[str] = set()
    product_ids: set[str] = set()
    status_counts = {
        "candidate": 0,
        "excluded": 0,
        "unmatched_duplicate_candidate": 0,
    }
    candidate_with_edition_code = 0

    for row in rows:
        reference = row["source_record_reference"]
        product_id = row["source_product_id"]
        status = row["proposed_status"]

        if (
            row["market_source_system"] != mapping_import.SOURCE_SYSTEM
            or not reference
            or not product_id
            or status not in mapping_import.ALLOWED_MAPPING_STATUSES
            or row["evidence_reference"] is None
            or row["evidence_payload"] is None
            or row["raw_payload"] is None
            or not row["record_checksum"]
            or row["normalization_status"] != "normalized"
            or row["validation_status"] != "valid"
            or row["validation_completed_at"] is None
            or row["confirmation_scope"] is not None
            or row["confirmation_method"] is not None
            or row["evidence_level"] is not None
        ):
            raise mapping_import.ImportValidationError(
                f"Invalid staged mapping row: {reference!r}."
            )

        if reference in references:
            raise mapping_import.ImportValidationError(
                f"Duplicate source_record_reference: {reference}."
            )
        if product_id in product_ids:
            raise mapping_import.ImportValidationError(
                f"Duplicate source_product_id: {product_id}."
            )
        references.add(reference)
        product_ids.add(product_id)

        if status == "candidate":
            if (
                row["catalogue_source_system"]
                != mapping_import.CATALOGUE_SOURCE_SYSTEM
                or not row["source_card_id"]
            ):
                raise mapping_import.ImportValidationError(
                    f"Candidate row {reference!r} has no canonical-card identity."
                )
            if row["source_edition_code"] is not None:
                candidate_with_edition_code += 1
        elif (
            row["catalogue_source_system"] is not None
            or row["source_card_id"] is not None
        ):
            raise mapping_import.ImportValidationError(
                f"Non-candidate row {reference!r} has a card target."
            )

        status_counts[status] += 1

    expected_counts = {
        "candidate": mapping_import.EXPECTED_CANDIDATE_COUNT,
        "excluded": mapping_import.EXPECTED_EXCLUDED_COUNT,
        "unmatched_duplicate_candidate": (
            mapping_import.EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT
        ),
    }
    if status_counts != expected_counts:
        raise mapping_import.ImportValidationError(
            f"Status counts are {status_counts}, expected {expected_counts}."
        )

    if (
        candidate_with_edition_code
        != mapping_import.EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT
    ):
        raise mapping_import.ImportValidationError(
            "Candidate rows with edition code are "
            f"{candidate_with_edition_code}, expected "
            f"{mapping_import.EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT}."
        )

    excluded_ids = {
        row["source_product_id"]
        for row in rows
        if row["proposed_status"] == "excluded"
    }
    expected_excluded_ids = ONLINE_CODE_CARD_PRODUCT_IDS | OVERSIZED_PRODUCT_IDS
    if excluded_ids != expected_excluded_ids:
        raise mapping_import.ImportValidationError(
            "Excluded product identities do not match the controlled fixture."
        )


def resolve_identities(
    connection: Connection[Any],
    rows: list[dict[str, Any]],
) -> ValidationCounts:
    resolved_candidate_products = 0
    resolved_candidate_cards = 0
    resolved_oversized_products = 0
    resolved_unmatched_products = 0
    missing_online_code_products = 0

    for row in rows:
        product = fetch_one_dict(
            connection,
            """
            SELECT market_product_id, is_active
            FROM market_products
            WHERE source_system = %(source_system)s
              AND source_product_id = %(source_product_id)s
            """,
            {
                "source_system": row["market_source_system"],
                "source_product_id": row["source_product_id"],
            },
        )

        status = row["proposed_status"]
        product_id = row["source_product_id"]

        if status == "candidate":
            if product is None or product["is_active"] is not True:
                raise mapping_import.ImportValidationError(
                    f"Candidate market product {product_id} is missing or inactive."
                )
            resolved_candidate_products += 1

            card = fetch_one_dict(
                connection,
                """
                SELECT card_id, is_active
                FROM cards
                WHERE source_system = %(source_system)s
                  AND source_card_id = %(source_card_id)s
                """,
                {
                    "source_system": row["catalogue_source_system"],
                    "source_card_id": row["source_card_id"],
                },
            )
            if card is None or card["is_active"] is not True:
                raise mapping_import.ImportValidationError(
                    "Candidate canonical card is missing or inactive: "
                    f"{row['source_card_id']}."
                )
            resolved_candidate_cards += 1
            continue

        if status == "excluded":
            if product_id in ONLINE_CODE_CARD_PRODUCT_IDS:
                if product is not None:
                    raise mapping_import.ImportValidationError(
                        f"Online Code Card {product_id} unexpectedly exists "
                        "in market_products."
                    )
                missing_online_code_products += 1
                continue

            if product_id in OVERSIZED_PRODUCT_IDS:
                if product is None or product["is_active"] is not True:
                    raise mapping_import.ImportValidationError(
                        f"Oversized product {product_id} is missing or inactive."
                    )
                resolved_oversized_products += 1
                continue

        if status == "unmatched_duplicate_candidate":
            if product is None or product["is_active"] is not True:
                raise mapping_import.ImportValidationError(
                    f"Unmatched duplicate product {product_id} is missing "
                    "or inactive."
                )
            resolved_unmatched_products += 1

    return ValidationCounts(
        staged=len(rows),
        candidates=sum(row["proposed_status"] == "candidate" for row in rows),
        excluded=sum(row["proposed_status"] == "excluded" for row in rows),
        unmatched_duplicate_candidates=sum(
            row["proposed_status"] == "unmatched_duplicate_candidate"
            for row in rows
        ),
        resolved_candidate_products=resolved_candidate_products,
        resolved_candidate_cards=resolved_candidate_cards,
        resolved_oversized_products=resolved_oversized_products,
        resolved_unmatched_products=resolved_unmatched_products,
        missing_online_code_products=missing_online_code_products,
    )


def validate_counts(counts: ValidationCounts) -> None:
    expected_values = {
        "staged": mapping_import.EXPECTED_RECORD_COUNT,
        "candidates": mapping_import.EXPECTED_CANDIDATE_COUNT,
        "excluded": mapping_import.EXPECTED_EXCLUDED_COUNT,
        "unmatched_duplicate_candidates": (
            mapping_import.EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT
        ),
        "resolved_candidate_products": mapping_import.EXPECTED_CANDIDATE_COUNT,
        "resolved_candidate_cards": mapping_import.EXPECTED_CANDIDATE_COUNT,
        "resolved_oversized_products": len(OVERSIZED_PRODUCT_IDS),
        "resolved_unmatched_products": (
            mapping_import.EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT
        ),
        "missing_online_code_products": len(ONLINE_CODE_CARD_PRODUCT_IDS),
    }
    mismatches = [
        f"{field}={getattr(counts, field)}, expected {expected}"
        for field, expected in expected_values.items()
        if getattr(counts, field) != expected
    ]
    if mismatches:
        raise mapping_import.ImportValidationError(
            "Identity reconciliation failed: " + "; ".join(mismatches) + "."
        )


def main() -> int:
    args = parse_args()
    if args.import_run_id < 1:
        raise mapping_import.ImportValidationError(
            "--import-run-id must be a positive integer."
        )

    database_url = mapping_import.get_database_url()

    with psycopg.connect(database_url) as connection:
        run = load_import_run(connection, args.import_run_id)
        rows = load_staging_rows(connection, args.import_run_id)
        validate_staging_rows(rows)
        counts = resolve_identities(connection, rows)
        validate_counts(counts)

    print("Primal Clash Cardmarket mapping pre-merge validation passed")
    print(f"Import run ID: {args.import_run_id}")
    print(f"Run reference: {run['run_reference']}")
    print(f"Staged records: {counts.staged}")
    print(f"Candidate rows: {counts.candidates}")
    print(f"Resolved candidate market products: {counts.resolved_candidate_products}")
    print(f"Resolved candidate canonical cards: {counts.resolved_candidate_cards}")
    print(f"Excluded rows: {counts.excluded}")
    print(f"Resolved oversized products: {counts.resolved_oversized_products}")
    print(f"Missing Online Code Card products: {counts.missing_online_code_products}")
    print(
        "Resolved unmatched duplicate products: "
        f"{counts.resolved_unmatched_products}"
    )
    print("Database writes: 0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (mapping_import.ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

