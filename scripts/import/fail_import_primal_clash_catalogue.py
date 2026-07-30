"""
Script: fail_import_primal_clash_catalogue.py

Purpose:
    Intentionally interrupt a Primal Clash catalogue staging transaction after
    a controlled number of inserted records and verify that PostgreSQL rolls
    back both the import run and all partial staging rows.

Lifecycle:
    Permanent validation utility.

Removal:
    Keep this script while transactional rollback is part of the documented
    import validation process. It may be replaced only after equivalent
    rollback coverage exists in an automated integration test suite.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb


DEFAULT_SOURCE = Path(
    "data/fixtures/primal-clash/canonical-cards.json"
)
DEFAULT_IMPORTER_PATH = Path(
    "scripts/import/import_primal_clash_catalogue.py"
)
DEFAULT_IMPORTER_VERSION = "m4-first-import-v1"
DEFAULT_FAIL_AFTER_RECORDS = 10


class RollbackValidationError(RuntimeError):
    """Raised when rollback injection or verification fails."""


class IntentionalRollbackFailure(RuntimeError):
    """Raised deliberately to force the staging transaction to roll back."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Intentionally fail a Primal Clash staging import and verify "
            "that PostgreSQL rolls back all partial database changes."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=(
            "Path to the canonical-card fixture "
            f"(default: {DEFAULT_SOURCE.as_posix()})."
        ),
    )
    parser.add_argument(
        "--importer-path",
        type=Path,
        default=DEFAULT_IMPORTER_PATH,
        help=(
            "Path to the permanent catalogue importer "
            f"(default: {DEFAULT_IMPORTER_PATH.as_posix()})."
        ),
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help=(
            "PostgreSQL connection URL. Defaults to the DATABASE_URL "
            "environment variable."
        ),
    )
    parser.add_argument(
        "--run-reference",
        required=True,
        help=(
            "Unique reference used only for this rollback validation run."
        ),
    )
    parser.add_argument(
        "--importer-version",
        default=DEFAULT_IMPORTER_VERSION,
        help=(
            "Importer implementation version "
            f"(default: {DEFAULT_IMPORTER_VERSION})."
        ),
    )
    parser.add_argument(
        "--fail-after-records",
        type=int,
        default=DEFAULT_FAIL_AFTER_RECORDS,
        help=(
            "Number of staging rows to insert before forcing rollback "
            f"(default: {DEFAULT_FAIL_AFTER_RECORDS})."
        ),
    )

    args = parser.parse_args(argv)

    if not args.database_url:
        parser.error(
            "--database-url is required when DATABASE_URL is not set."
        )

    args.run_reference = require_trimmed_text(
        args.run_reference,
        "--run-reference",
    )
    args.importer_version = require_trimmed_text(
        args.importer_version,
        "--importer-version",
    )

    if args.fail_after_records < 1:
        parser.error("--fail-after-records must be at least 1.")

    return args


def require_trimmed_text(value: str, argument_name: str) -> str:
    """Require a non-empty CLI value without surrounding whitespace."""

    normalized = value.strip()

    if not normalized:
        raise argparse.ArgumentTypeError(
            f"{argument_name} must be a non-empty value."
        )

    if normalized != value:
        raise argparse.ArgumentTypeError(
            f"{argument_name} must not contain surrounding whitespace."
        )

    return normalized


def load_importer_module(path: Path) -> ModuleType:
    """Load the permanent importer module from its repository path."""

    if not path.is_file():
        raise RollbackValidationError(
            f"Importer script does not exist: {path}"
        )

    module_name = "primal_clash_catalogue_importer"

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RollbackValidationError(
            f"Could not create an import specification for: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise RollbackValidationError(
            f"Could not load importer module: {path}: {exc}"
        ) from exc

    required_functions = (
        "validate_source_artifact",
        "normalize_cards",
        "require_all_cards_valid",
        "create_import_run",
    )

    missing_functions = [
        function_name
        for function_name in required_functions
        if not callable(getattr(module, function_name, None))
    ]

    if missing_functions:
        raise RollbackValidationError(
            "Importer module is missing required functions: "
            + ", ".join(missing_functions)
        )

    return module


def insert_partial_staging_rows(
    connection: Connection[Any],
    import_run_id: int,
    cards: list[Any],
    fail_after_records: int,
) -> None:
    """Insert a controlled number of rows and then force an exception."""

    if fail_after_records > len(cards):
        raise RollbackValidationError(
            "Failure point exceeds normalized record count: "
            f"failure_point={fail_after_records}, records={len(cards)}."
        )

    insert_sql = """
        INSERT INTO staging_cards (
            import_run_id,
            source_record_reference,
            source_system,
            source_card_id,
            source_expansion_id,
            collector_number,
            name,
            rarity,
            image_small_url,
            image_large_url,
            raw_payload,
            record_checksum,
            normalization_status,
            validation_status,
            validation_completed_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            CURRENT_TIMESTAMP
        )
    """

    with connection.cursor() as cursor:
        for inserted_count, card in enumerate(cards, start=1):
            cursor.execute(
                insert_sql,
                (
                    import_run_id,
                    card.source_record_reference,
                    card.source_system,
                    card.source_card_id,
                    card.source_expansion_id,
                    card.collector_number,
                    card.name,
                    card.rarity,
                    card.image_small_url,
                    card.image_large_url,
                    Jsonb(card.raw_payload),
                    card.record_checksum,
                    card.normalization_status,
                    card.validation_status,
                ),
            )

            if inserted_count == fail_after_records:
                raise IntentionalRollbackFailure(
                    "Intentional rollback validation failure after "
                    f"{inserted_count} staging records."
                )


def execute_rollback_test(
    database_url: str,
    importer: ModuleType,
    source: Path,
    run_reference: str,
    importer_version: str,
    fail_after_records: int,
) -> int:
    """Execute the intentionally failing transaction."""

    artifact = importer.validate_source_artifact(source)
    cards = importer.normalize_cards(artifact)
    importer.require_all_cards_valid(cards)

    import_run_id: int | None = None

    try:
        with psycopg.connect(database_url) as connection:
            import_run_id = importer.create_import_run(
                connection=connection,
                artifact=artifact,
                run_reference=run_reference,
                importer_version=importer_version,
            )

            insert_partial_staging_rows(
                connection=connection,
                import_run_id=import_run_id,
                cards=cards,
                fail_after_records=fail_after_records,
            )

    except IntentionalRollbackFailure as exc:
        print(f"Expected failure triggered: {exc}")
    except psycopg.Error as exc:
        raise RollbackValidationError(
            f"Unexpected PostgreSQL error during rollback test: {exc}"
        ) from exc

    if import_run_id is None:
        raise RollbackValidationError(
            "The rollback test did not create an import run."
        )

    return import_run_id


def verify_rollback(
    database_url: str,
    run_reference: str,
    attempted_import_run_id: int,
) -> None:
    """Verify that no import-run or staging rows survived."""

    try:
        with psycopg.connect(database_url) as connection:
            run_count_row = connection.execute(
                """
                SELECT count(*)
                FROM import_runs
                WHERE run_reference = %s
                """,
                (run_reference,),
            ).fetchone()

            staging_count_row = connection.execute(
                """
                SELECT count(*)
                FROM staging_cards
                WHERE import_run_id = %s
                """,
                (attempted_import_run_id,),
            ).fetchone()
    except psycopg.Error as exc:
        raise RollbackValidationError(
            f"Could not verify rollback state: {exc}"
        ) from exc

    if run_count_row is None or staging_count_row is None:
        raise RollbackValidationError(
            "Rollback verification queries returned no result."
        )

    surviving_runs = int(run_count_row[0])
    surviving_staging_rows = int(staging_count_row[0])

    if surviving_runs != 0:
        raise RollbackValidationError(
            "Rollback failed: "
            f"{surviving_runs} import_runs row(s) survived."
        )

    if surviving_staging_rows != 0:
        raise RollbackValidationError(
            "Rollback failed: "
            f"{surviving_staging_rows} staging_cards row(s) survived."
        )

    print("Transactional rollback validation passed")
    print(f"Attempted import run ID: {attempted_import_run_id}")
    print(f"Run reference: {run_reference}")
    print("Surviving import runs: 0")
    print("Surviving staging rows: 0")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the intentional rollback validation."""

    args = parse_args(argv)

    try:
        importer = load_importer_module(args.importer_path)

        attempted_import_run_id = execute_rollback_test(
            database_url=args.database_url,
            importer=importer,
            source=args.source,
            run_reference=args.run_reference,
            importer_version=args.importer_version,
            fail_after_records=args.fail_after_records,
        )

        verify_rollback(
            database_url=args.database_url,
            run_reference=args.run_reference,
            attempted_import_run_id=attempted_import_run_id,
        )
    except (
        RollbackValidationError,
        importer.ImportValidationError
        if "importer" in locals()
        else RollbackValidationError,
        importer.ImportDatabaseError
        if "importer" in locals()
        else RollbackValidationError,
    ) as exc:
        print(f"Rollback validation failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())