"""
Script: fail_import_primal_clash_market_products.py

Purpose:
    Validate transactional rollback for the controlled Primal Clash Cardmarket
    product staging workflow. The script creates an import run, inserts a
    controlled partial set of staging_market_products rows, raises an
    intentional exception, and verifies that no import or staging rows survive.

Lifecycle:
    Permanent project validation utility.

Removal:
    Keep this script while the Cardmarket product import remains part of the
    validated Primal Clash vertical slice. It may be replaced only by automated
    integration tests that preserve equivalent failure-injection and rollback
    evidence.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import psycopg
from psycopg import Connection

import import_primal_clash_market_products as market_import


class IntentionalRollbackError(RuntimeError):
    """Raised deliberately after a controlled number of staging inserts."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Intentionally fail a Primal Clash Cardmarket product staging "
            "transaction and verify complete rollback."
        )
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=market_import.DEFAULT_FIXTURE_PATH,
        help="Path to cardmarket-products.json.",
    )
    parser.add_argument(
        "--run-reference",
        required=True,
        help="Unique reference used only for this rollback validation.",
    )
    parser.add_argument(
        "--importer-version",
        required=True,
        help="Importer implementation version or repository revision.",
    )
    parser.add_argument(
        "--fail-after-records",
        type=int,
        default=10,
        help="Number of staging rows inserted before the intentional failure.",
    )
    return parser.parse_args()


def fetch_scalar(
    connection: Connection[Any],
    query: str,
    parameters: dict[str, Any],
) -> int:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise RuntimeError("Verification query returned no row.")
    return int(row[0])


def assert_run_reference_is_unused(
    connection: Connection[Any],
    run_reference: str,
) -> None:
    existing_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_runs
        WHERE run_reference = %(run_reference)s
        """,
        {"run_reference": run_reference},
    )
    if existing_count != 0:
        raise market_import.ImportValidationError(
            f"Run reference already exists: {run_reference!r}. "
            "Choose a new rollback-test reference."
        )


def verify_complete_rollback(
    database_url: str,
    run_reference: str,
) -> tuple[int, int]:
    with psycopg.connect(database_url) as connection:
        surviving_import_runs = fetch_scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM import_runs
            WHERE run_reference = %(run_reference)s
            """,
            {"run_reference": run_reference},
        )

        surviving_staging_rows = fetch_scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM staging_market_products AS staging
            JOIN import_runs AS runs
              ON runs.import_run_id = staging.import_run_id
            WHERE runs.run_reference = %(run_reference)s
            """,
            {"run_reference": run_reference},
        )

    return surviving_import_runs, surviving_staging_rows


def main() -> int:
    args = parse_args()

    run_reference = args.run_reference.strip()
    importer_version = args.importer_version.strip()

    if not run_reference:
        raise market_import.ImportValidationError(
            "--run-reference must not be empty."
        )
    if not importer_version:
        raise market_import.ImportValidationError(
            "--importer-version must not be empty."
        )
    if args.fail_after_records < 1:
        raise market_import.ImportValidationError(
            "--fail-after-records must be at least 1."
        )

    fixture = market_import.load_and_validate_fixture(args.fixture)
    if args.fail_after_records >= len(fixture.records):
        raise market_import.ImportValidationError(
            "--fail-after-records must be smaller than the fixture record count "
            f"({len(fixture.records)})."
        )

    database_url = market_import.get_database_url()
    attempted_import_run_id: int | None = None

    try:
        with psycopg.connect(database_url) as connection:
            assert_run_reference_is_unused(connection, run_reference)

            with connection.transaction():
                attempted_import_run_id = market_import.create_import_run(
                    connection,
                    run_reference=run_reference,
                    importer_version=importer_version,
                    fixture=fixture,
                )

                partial_records = fixture.records[: args.fail_after_records]
                market_import.insert_staging_records(
                    connection,
                    attempted_import_run_id,
                    partial_records,
                )

                persisted_partial_count = fetch_scalar(
                    connection,
                    """
                    SELECT COUNT(*)
                    FROM staging_market_products
                    WHERE import_run_id = %(import_run_id)s
                    """,
                    {"import_run_id": attempted_import_run_id},
                )
                if persisted_partial_count != args.fail_after_records:
                    raise market_import.ImportValidationError(
                        "Failure injection setup did not persist the expected "
                        f"partial row count. Expected {args.fail_after_records}, "
                        f"found {persisted_partial_count}."
                    )

                raise IntentionalRollbackError(
                    "Intentional rollback validation failure after "
                    f"{args.fail_after_records} staging records."
                )

    except IntentionalRollbackError as exc:
        print(f"Expected failure triggered: {exc}")

    if attempted_import_run_id is None:
        raise RuntimeError(
            "The intentional failure was triggered before an import run was created."
        )

    surviving_import_runs, surviving_staging_rows = verify_complete_rollback(
        database_url,
        run_reference,
    )

    if surviving_import_runs != 0 or surviving_staging_rows != 0:
        raise market_import.ImportValidationError(
            "Transactional rollback validation failed. "
            f"Surviving import runs: {surviving_import_runs}; "
            f"surviving staging rows: {surviving_staging_rows}."
        )

    print("Transactional rollback validation passed")
    print(f"Attempted import run ID: {attempted_import_run_id}")
    print(f"Run reference: {run_reference}")
    print(f"Attempted staging rows: {args.fail_after_records}")
    print(f"Surviving import runs: {surviving_import_runs}")
    print(f"Surviving staging rows: {surviving_staging_rows}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (market_import.ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
