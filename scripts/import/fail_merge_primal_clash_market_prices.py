"""
Script: fail_merge_primal_clash_market_prices.py

Purpose:
    Intentionally fail one controlled Primal Clash Cardmarket price production
    merge transaction after inserting one price snapshot and its audit outcome,
    then verify that the snapshot, outcome, and import-run lifecycle changes are
    rolled back completely.

Lifecycle:
    Permanent project validation utility.

Removal:
    Keep this script while the Cardmarket price merge remains part of the
    validated Primal Clash vertical slice. It may be replaced only by automated
    integration tests that preserve equivalent failure-injection and rollback
    evidence.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import psycopg
from psycopg import Connection

import import_primal_clash_market_prices as price_import
import merge_primal_clash_market_prices as price_merge


class IntentionalMergeRollbackError(RuntimeError):
    """Raised deliberately after one complete price snapshot write."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Intentionally fail a Primal Clash Cardmarket price merge "
            "transaction and verify complete rollback."
        )
    )
    parser.add_argument(
        "--import-run-id",
        type=int,
        required=True,
        help="Validated Cardmarket price import run used for rollback testing.",
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
    import_run_id: int,
) -> dict[str, int]:
    return {
        "snapshots": fetch_scalar(
            connection,
            "SELECT COUNT(*) FROM market_price_snapshots",
            {},
        ),
        "run_outcomes": fetch_scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM import_record_outcomes
            WHERE import_run_id = %(import_run_id)s
            """,
            {"import_run_id": import_run_id},
        ),
    }


def select_rollback_row(
    connection: Connection[Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    for row in rows:
        source_product_id = row["source_product_id"]
        if source_product_id in price_merge.EXPECTED_ONLINE_CODE_CARD_IDS:
            continue

        market_product = price_merge.resolve_market_product(
            connection,
            source_product_id,
        )
        if market_product is None or market_product["is_active"] is not True:
            continue

        existing_count = fetch_scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM market_price_snapshots
            WHERE market_product_id = %(market_product_id)s
              AND source_snapshot_at = %(source_snapshot_at)s
            """,
            {
                "market_product_id": int(market_product["market_product_id"]),
                "source_snapshot_at": row["source_snapshot_at"],
            },
        )
        if existing_count == 0:
            return row

    raise price_import.ImportValidationError(
        "No eligible staging row without an existing production snapshot "
        "was found for rollback validation."
    )


def verify_partial_state(
    connection: Connection[Any],
    *,
    import_run_id: int,
    baseline: dict[str, int],
) -> None:
    current = load_baseline_counts(connection, import_run_id)
    expected = {
        "snapshots": baseline["snapshots"] + 1,
        "run_outcomes": baseline["run_outcomes"] + 1,
    }
    if current != expected:
        raise price_import.ImportValidationError(
            f"Partial merge state is {current}, expected {expected}."
        )


def verify_complete_rollback(
    database_url: str,
    *,
    import_run_id: int,
    baseline: dict[str, int],
) -> tuple[dict[str, Any], dict[str, int]]:
    with psycopg.connect(database_url) as connection:
        run = price_merge.fetch_one_dict(
            connection,
            """
            SELECT *
            FROM import_runs
            WHERE import_run_id = %(import_run_id)s
            """,
            {"import_run_id": import_run_id},
        )
        if run is None:
            raise price_import.ImportValidationError(
                f"Import run {import_run_id} disappeared after rollback."
            )
        final_counts = load_baseline_counts(connection, import_run_id)

    if final_counts != baseline:
        raise price_import.ImportValidationError(
            f"Rollback counts are {final_counts}, expected {baseline}."
        )
    if run["status"] != "validated":
        raise price_import.ImportValidationError(
            f"Import run status survived as {run['status']!r}."
        )
    if run["merge_started_at"] is not None or run["completed_at"] is not None:
        raise price_import.ImportValidationError(
            "Import run merge timestamps survived rollback."
        )

    return run, final_counts


def main() -> int:
    args = parse_args()
    if args.import_run_id < 1:
        raise price_import.ImportValidationError(
            "--import-run-id must be a positive integer."
        )

    database_url = price_import.get_database_url()
    attempted_snapshot_id: int | None = None
    attempted_source_product_id: str | None = None

    with psycopg.connect(database_url) as connection:
        price_merge.lock_and_validate_import_run(
            connection,
            args.import_run_id,
        )
        baseline = load_baseline_counts(connection, args.import_run_id)

    try:
        with psycopg.connect(database_url) as connection:
            with connection.transaction():
                run = price_merge.lock_and_validate_import_run(
                    connection,
                    args.import_run_id,
                )
                rows = price_merge.load_and_validate_staging_rows(
                    connection,
                    args.import_run_id,
                )
                rollback_row = select_rollback_row(connection, rows)
                price_merge.mark_merge_started(connection, args.import_run_id)

                counts = price_merge.MergeCounts()
                price_merge.merge_one_price(
                    connection,
                    import_run_id=args.import_run_id,
                    row=rollback_row,
                    counts=counts,
                )
                if counts.inserted != 1 or counts.total_outcomes != 1:
                    raise price_import.ImportValidationError(
                        "Rollback probe did not create exactly one inserted "
                        "snapshot outcome."
                    )

                snapshot = price_merge.fetch_one_dict(
                    connection,
                    """
                    SELECT market_price_snapshot_id
                    FROM market_price_snapshots
                    WHERE import_run_id = %(import_run_id)s
                      AND source_record_reference = %(source_record_reference)s
                    """,
                    {
                        "import_run_id": args.import_run_id,
                        "source_record_reference": rollback_row[
                            "source_record_reference"
                        ],
                    },
                )
                if snapshot is None:
                    raise RuntimeError(
                        "Inserted rollback snapshot could not be resolved."
                    )

                attempted_snapshot_id = int(
                    snapshot["market_price_snapshot_id"]
                )
                attempted_source_product_id = rollback_row["source_product_id"]
                verify_partial_state(
                    connection,
                    import_run_id=args.import_run_id,
                    baseline=baseline,
                )

                raise IntentionalMergeRollbackError(
                    "Intentional rollback after one complete price snapshot."
                )

    except IntentionalMergeRollbackError as exc:
        print(f"Expected failure triggered: {exc}")

    if attempted_snapshot_id is None or attempted_source_product_id is None:
        raise RuntimeError(
            "Intentional failure occurred before the partial price state "
            "was created."
        )

    run, final_counts = verify_complete_rollback(
        database_url,
        import_run_id=args.import_run_id,
        baseline=baseline,
    )

    print("Price production merge transactional rollback validation passed")
    print(f"Import run ID: {args.import_run_id}")
    print(f"Run reference: {run['run_reference']}")
    print(f"Attempted source product ID: {attempted_source_product_id}")
    print(f"Attempted price snapshot ID: {attempted_snapshot_id}")
    print(f"Surviving price snapshots: {final_counts['snapshots']}")
    print(f"Surviving run outcomes: {final_counts['run_outcomes']}")
    print("Final import run status: validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (price_import.ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
