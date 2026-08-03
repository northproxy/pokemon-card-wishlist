"""
Script: fail_import_primal_clash_market_prices.py

Purpose:
    Intentionally fail one controlled Primal Clash Cardmarket price staging
    transaction after creating a partial import state, then verify that the
    import_runs and staging_market_prices writes are rolled back completely.

Lifecycle:
    Permanent project validation utility.

Removal:
    Keep this script while the Primal Clash price staging import remains part
    of the validated vertical slice. It may be replaced only by automated
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

import import_primal_clash_market_prices as price_import


class IntentionalImportRollbackError(RuntimeError):
    """Raised deliberately after controlled staging writes."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Intentionally fail a Primal Clash Cardmarket price staging "
            "transaction and verify complete rollback."
        )
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=price_import.DEFAULT_FIXTURE_PATH,
        help="Path to cardmarket-prices.json.",
    )
    parser.add_argument(
        "--run-reference",
        required=True,
        help="Unique run reference used only inside the rolled-back transaction.",
    )
    parser.add_argument(
        "--importer-version",
        required=True,
        help="Importer implementation version or repository revision.",
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


def load_baseline_counts(
    connection: Connection[Any],
    run_reference: str,
) -> dict[str, int]:
    return {
        "matching_runs": fetch_scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM import_runs
            WHERE run_reference = %(run_reference)s
            """,
            {"run_reference": run_reference},
        ),
        "staging_rows": fetch_scalar(
            connection,
            "SELECT COUNT(*) FROM staging_market_prices",
            {},
        ),
    }


def verify_partial_state(
    connection: Connection[Any],
    *,
    import_run_id: int,
    expected_staging_rows: int,
) -> None:
    run_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_runs
        WHERE import_run_id = %(import_run_id)s
          AND status = 'created'
        """,
        {"import_run_id": import_run_id},
    )
    staging_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_prices
        WHERE import_run_id = %(import_run_id)s
        """,
        {"import_run_id": import_run_id},
    )

    if run_count != 1:
        raise price_import.ImportValidationError(
            f"Partial import run count is {run_count}, expected 1."
        )
    if staging_count != expected_staging_rows:
        raise price_import.ImportValidationError(
            f"Partial staging count is {staging_count}, expected "
            f"{expected_staging_rows}."
        )


def verify_complete_rollback(
    database_url: str,
    *,
    run_reference: str,
    baseline: dict[str, int],
) -> dict[str, int]:
    with psycopg.connect(database_url) as connection:
        final_counts = load_baseline_counts(connection, run_reference)

    if final_counts != baseline:
        raise price_import.ImportValidationError(
            f"Rollback counts are {final_counts}, expected {baseline}."
        )

    return final_counts


def main() -> int:
    args = parse_args()

    run_reference = args.run_reference.strip()
    importer_version = args.importer_version.strip()
    if not run_reference:
        raise price_import.ImportValidationError(
            "--run-reference must not be empty."
        )
    if not importer_version:
        raise price_import.ImportValidationError(
            "--importer-version must not be empty."
        )

    fixture = price_import.load_and_validate_fixture(args.fixture)
    database_url = price_import.get_database_url()

    with psycopg.connect(database_url) as connection:
        baseline = load_baseline_counts(connection, run_reference)

    if baseline["matching_runs"] != 0:
        raise price_import.ImportValidationError(
            f"Run reference {run_reference!r} already exists."
        )

    partial_record_count = 1
    attempted_import_run_id: int | None = None

    try:
        with psycopg.connect(database_url) as connection:
            with connection.transaction():
                attempted_import_run_id = price_import.create_import_run(
                    connection,
                    run_reference=run_reference,
                    importer_version=importer_version,
                    fixture=fixture,
                )
                price_import.insert_staging_records(
                    connection,
                    attempted_import_run_id,
                    fixture.records[:partial_record_count],
                )
                verify_partial_state(
                    connection,
                    import_run_id=attempted_import_run_id,
                    expected_staging_rows=partial_record_count,
                )

                raise IntentionalImportRollbackError(
                    "Intentional rollback after one staged market-price record."
                )

    except IntentionalImportRollbackError as exc:
        print(f"Expected failure triggered: {exc}")

    if attempted_import_run_id is None:
        raise RuntimeError(
            "Intentional failure occurred before partial staging state "
            "was created."
        )

    final_counts = verify_complete_rollback(
        database_url,
        run_reference=run_reference,
        baseline=baseline,
    )

    print("Price staging transactional rollback validation passed")
    print(f"Attempted import run ID: {attempted_import_run_id}")
    print(f"Run reference: {run_reference}")
    print(f"Attempted staged records: {partial_record_count}")
    print(f"Surviving matching import runs: {final_counts['matching_runs']}")
    print(f"Final staging row count: {final_counts['staging_rows']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (price_import.ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
