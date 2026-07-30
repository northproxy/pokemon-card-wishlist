"""
Script: import_primal_clash_market_products.py

Purpose:
    Validate and normalize the controlled Primal Clash Cardmarket product
    fixture, create one import_runs record, persist all source records in
    staging_market_products, reconcile the staged state, and commit the run
    with status 'validated'. The script does not merge production rows.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the validated vertical slice.
    It may be replaced only by a generalized market-product importer that
    preserves the same validation, audit, rollback, and staging guarantees.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_PATH = (
    REPO_ROOT / "data" / "fixtures" / "primal-clash" / "cardmarket-products.json"
)

SOURCE_SYSTEM = "cardmarket"
SOURCE_ENTITY_TYPE = "market_product"
RUN_KIND = "market_products"
SCOPE_TYPE = "expansion"
EXPECTED_EXPANSION_ID = "1585"
EXPECTED_RECORD_COUNT = 177
EXPECTED_ELIGIBLE_COUNT = 173
EXPECTED_CODE_CARD_COUNT = 4
EXPECTED_MISSING_SOURCE_CREATED_AT_COUNT = 164
EXPECTED_PRESENT_SOURCE_CREATED_AT_COUNT = 13
MISSING_SOURCE_TIMESTAMP_SENTINEL = "0000-00-00 00:00:00"
EXPECTED_CODE_CARD_IDS = frozenset({"300914", "300919", "300971", "300972"})
REQUIRED_RECORD_FIELDS = frozenset(
    {
        "idProduct",
        "idExpansion",
        "idMetacard",
        "idCategory",
        "categoryName",
        "name",
        "dateAdded",
    }
)


class ImportValidationError(RuntimeError):
    """Raised when the controlled fixture or persisted staging state is invalid."""


@dataclass(frozen=True)
class NormalizedMarketProduct:
    """Normalized representation of one Cardmarket product source record."""

    source_record_reference: str
    source_product_id: str
    source_expansion_id: str
    source_metaproduct_id: str
    raw_name: str
    source_category_id: str
    source_category_name: str
    source_created_at: datetime | None
    raw_payload: dict[str, Any]
    record_checksum: str

    @property
    def is_online_code_card(self) -> bool:
        return (
            self.source_category_id == "51"
            and self.raw_name.startswith("Online Code Card")
        )


@dataclass(frozen=True)
class FixtureData:
    """Validated fixture metadata and normalized records."""

    source_file: str
    source_created_at: str | None
    artifact_reference: str
    artifact_checksum: str
    records: tuple[NormalizedMarketProduct, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and stage the controlled Primal Clash Cardmarket "
            "product fixture without executing a production merge."
        )
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help="Path to cardmarket-products.json.",
    )
    parser.add_argument(
        "--run-reference",
        required=True,
        help="Unique human-readable import run reference.",
    )
    parser.add_argument(
        "--importer-version",
        required=True,
        help="Importer implementation version or repository revision.",
    )
    return parser.parse_args()


def normalize_required_text(value: Any, field_name: str, record_number: int) -> str:
    if isinstance(value, bool):
        raise ImportValidationError(
            f"Record {record_number}: {field_name} must not be boolean."
        )

    if not isinstance(value, (str, int)):
        raise ImportValidationError(
            f"Record {record_number}: {field_name} must be string or integer."
        )

    normalized = str(value).strip()
    if not normalized:
        raise ImportValidationError(
            f"Record {record_number}: {field_name} is empty."
        )
    return normalized


def parse_source_created_at(
    value: Any,
    field_name: str,
    record_number: int,
) -> datetime | None:
    text = normalize_required_text(value, field_name, record_number)

    if text == MISSING_SOURCE_TIMESTAMP_SENTINEL:
        return None

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ImportValidationError(
            f"Record {record_number}: {field_name} is neither the controlled "
            f"missing-value sentinel nor a valid timestamp: {text!r}."
        ) from exc

    # Cardmarket fixture timestamps have no explicit offset. Treat real values
    # as UTC for deterministic timestamptz persistence in this controlled import.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def calculate_record_checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def calculate_file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_source_record_reference(source_product_id: str) -> str:
    return f"cardmarket-products.json#idProduct={source_product_id}"


def normalize_record(
    raw_record: Any,
    record_number: int,
) -> NormalizedMarketProduct:
    if not isinstance(raw_record, dict):
        raise ImportValidationError(
            f"Record {record_number}: expected a JSON object."
        )

    missing_fields = sorted(REQUIRED_RECORD_FIELDS - raw_record.keys())
    if missing_fields:
        raise ImportValidationError(
            f"Record {record_number}: missing fields: {', '.join(missing_fields)}."
        )

    source_product_id = normalize_required_text(
        raw_record["idProduct"], "idProduct", record_number
    )
    source_expansion_id = normalize_required_text(
        raw_record["idExpansion"], "idExpansion", record_number
    )
    source_metaproduct_id = normalize_required_text(
        raw_record["idMetacard"], "idMetacard", record_number
    )
    source_category_id = normalize_required_text(
        raw_record["idCategory"], "idCategory", record_number
    )
    source_category_name = normalize_required_text(
        raw_record["categoryName"], "categoryName", record_number
    )
    raw_name = normalize_required_text(raw_record["name"], "name", record_number)
    source_created_at = parse_source_created_at(
        raw_record["dateAdded"], "dateAdded", record_number
    )

    if source_expansion_id != EXPECTED_EXPANSION_ID:
        raise ImportValidationError(
            f"Record {record_number}: expected idExpansion "
            f"{EXPECTED_EXPANSION_ID}, received {source_expansion_id}."
        )

    return NormalizedMarketProduct(
        source_record_reference=build_source_record_reference(source_product_id),
        source_product_id=source_product_id,
        source_expansion_id=source_expansion_id,
        source_metaproduct_id=source_metaproduct_id,
        raw_name=raw_name,
        source_category_id=source_category_id,
        source_category_name=source_category_name,
        source_created_at=source_created_at,
        raw_payload=raw_record,
        record_checksum=calculate_record_checksum(raw_record),
    )


def validate_unique_values(
    values: Iterable[str],
    label: str,
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    if duplicates:
        duplicate_text = ", ".join(sorted(duplicates))
        raise ImportValidationError(f"Duplicate {label}: {duplicate_text}.")


def load_and_validate_fixture(path: Path) -> FixtureData:
    resolved_path = path.expanduser().resolve()

    if not resolved_path.is_file():
        raise ImportValidationError(f"Fixture does not exist: {resolved_path}")

    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ImportValidationError("Fixture is not valid UTF-8.") from exc
    except json.JSONDecodeError as exc:
        raise ImportValidationError(
            f"Fixture is not valid JSON: line {exc.lineno}, column {exc.colno}."
        ) from exc

    if not isinstance(payload, dict):
        raise ImportValidationError("Top-level fixture payload must be an object.")

    source_system = payload.get("sourceSystem")
    expansion_id = payload.get("expansionId")
    declared_count = payload.get("recordCount")
    records = payload.get("records")

    if source_system != SOURCE_SYSTEM:
        raise ImportValidationError(
            f"Expected sourceSystem {SOURCE_SYSTEM!r}, received {source_system!r}."
        )
    if str(expansion_id).strip() != EXPECTED_EXPANSION_ID:
        raise ImportValidationError(
            f"Expected expansionId {EXPECTED_EXPANSION_ID!r}, "
            f"received {expansion_id!r}."
        )
    if not isinstance(declared_count, int) or isinstance(declared_count, bool):
        raise ImportValidationError("recordCount must be an integer.")
    if not isinstance(records, list):
        raise ImportValidationError("records must be a JSON array.")
    if declared_count != len(records):
        raise ImportValidationError(
            f"recordCount declares {declared_count}, but records contains "
            f"{len(records)} elements."
        )
    if declared_count != EXPECTED_RECORD_COUNT:
        raise ImportValidationError(
            f"Expected {EXPECTED_RECORD_COUNT} records, received {declared_count}."
        )

    normalized_records = tuple(
        normalize_record(raw_record, index)
        for index, raw_record in enumerate(records, start=1)
    )

    validate_unique_values(
        (record.source_record_reference for record in normalized_records),
        "source_record_reference values",
    )
    validate_unique_values(
        (record.source_product_id for record in normalized_records),
        "source_product_id values",
    )

    code_card_records = tuple(
        record for record in normalized_records if record.is_online_code_card
    )
    code_card_ids = frozenset(
        record.source_product_id for record in code_card_records
    )
    eligible_count = len(normalized_records) - len(code_card_records)
    missing_source_created_at_count = sum(
        record.source_created_at is None for record in normalized_records
    )
    present_source_created_at_count = (
        len(normalized_records) - missing_source_created_at_count
    )

    if (
        missing_source_created_at_count
        != EXPECTED_MISSING_SOURCE_CREATED_AT_COUNT
    ):
        raise ImportValidationError(
            "Expected "
            f"{EXPECTED_MISSING_SOURCE_CREATED_AT_COUNT} missing source "
            f"timestamps, found {missing_source_created_at_count}."
        )
    if (
        present_source_created_at_count
        != EXPECTED_PRESENT_SOURCE_CREATED_AT_COUNT
    ):
        raise ImportValidationError(
            "Expected "
            f"{EXPECTED_PRESENT_SOURCE_CREATED_AT_COUNT} real source "
            f"timestamps, found {present_source_created_at_count}."
        )

    if len(code_card_records) != EXPECTED_CODE_CARD_COUNT:
        raise ImportValidationError(
            f"Expected {EXPECTED_CODE_CARD_COUNT} Online Code Card records, "
            f"found {len(code_card_records)}."
        )
    if code_card_ids != EXPECTED_CODE_CARD_IDS:
        raise ImportValidationError(
            "Online Code Card identities do not match the controlled fixture. "
            f"Expected {sorted(EXPECTED_CODE_CARD_IDS)}, "
            f"found {sorted(code_card_ids)}."
        )
    if eligible_count != EXPECTED_ELIGIBLE_COUNT:
        raise ImportValidationError(
            f"Expected {EXPECTED_ELIGIBLE_COUNT} eligible products, "
            f"found {eligible_count}."
        )

    try:
        artifact_reference = str(resolved_path.relative_to(REPO_ROOT))
    except ValueError:
        artifact_reference = str(resolved_path)

    return FixtureData(
        source_file=normalize_required_text(
            payload.get("sourceFile"), "sourceFile", 0
        ),
        source_created_at=(
            str(payload["sourceCreatedAt"]).strip()
            if payload.get("sourceCreatedAt") is not None
            else None
        ),
        artifact_reference=artifact_reference.replace("\\", "/"),
        artifact_checksum=calculate_file_checksum(resolved_path),
        records=normalized_records,
    )


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise ImportValidationError(
            "DATABASE_URL is not set. Set it in the current shell without "
            "committing credentials to the repository."
        )
    return database_url


def create_import_run(
    connection: Connection[Any],
    *,
    run_reference: str,
    importer_version: str,
    fixture: FixtureData,
) -> int:
    row = connection.execute(
        """
        INSERT INTO import_runs (
            run_reference,
            run_kind,
            source_system,
            source_entity_type,
            source_artifact_reference,
            source_artifact_checksum,
            scope_type,
            scope_reference,
            is_authoritative,
            importer_version,
            status
        )
        VALUES (
            %(run_reference)s,
            %(run_kind)s,
            %(source_system)s,
            %(source_entity_type)s,
            %(source_artifact_reference)s,
            %(source_artifact_checksum)s,
            %(scope_type)s,
            %(scope_reference)s,
            TRUE,
            %(importer_version)s,
            'created'
        )
        RETURNING import_run_id
        """,
        {
            "run_reference": run_reference,
            "run_kind": RUN_KIND,
            "source_system": SOURCE_SYSTEM,
            "source_entity_type": SOURCE_ENTITY_TYPE,
            "source_artifact_reference": fixture.artifact_reference,
            "source_artifact_checksum": fixture.artifact_checksum,
            "scope_type": SCOPE_TYPE,
            "scope_reference": f"{SOURCE_SYSTEM}:{EXPECTED_EXPANSION_ID}",
            "importer_version": importer_version,
        },
    ).fetchone()

    if row is None:
        raise RuntimeError("Database did not return import_run_id.")
    return int(row[0])


def insert_staging_records(
    connection: Connection[Any],
    import_run_id: int,
    records: tuple[NormalizedMarketProduct, ...],
) -> None:
    insert_sql = """
        INSERT INTO staging_market_products (
            import_run_id,
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
        )
        VALUES (
            %(import_run_id)s,
            %(source_record_reference)s,
            %(source_system)s,
            %(source_product_id)s,
            %(source_expansion_id)s,
            %(source_metaproduct_id)s,
            %(raw_name)s,
            %(source_category_id)s,
            %(source_category_name)s,
            %(source_created_at)s,
            %(raw_payload)s,
            %(record_checksum)s,
            'normalized',
            'valid',
            CURRENT_TIMESTAMP
        )
    """

    parameters = [
        {
            "import_run_id": import_run_id,
            "source_record_reference": record.source_record_reference,
            "source_system": SOURCE_SYSTEM,
            "source_product_id": record.source_product_id,
            "source_expansion_id": record.source_expansion_id,
            "source_metaproduct_id": record.source_metaproduct_id,
            "raw_name": record.raw_name,
            "source_category_id": record.source_category_id,
            "source_category_name": record.source_category_name,
            "source_created_at": record.source_created_at,
            "raw_payload": Jsonb(record.raw_payload),
            "record_checksum": record.record_checksum,
        }
        for record in records
    ]

    with connection.cursor() as cursor:
        cursor.executemany(insert_sql, parameters)


def mark_staging_loaded(
    connection: Connection[Any],
    import_run_id: int,
    record_count: int,
) -> None:
    connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'staging_loaded',
            staging_loaded_at = CURRENT_TIMESTAMP,
            total_source_records = %(record_count)s
        WHERE import_run_id = %(import_run_id)s
          AND status = 'created'
        """,
        {
            "import_run_id": import_run_id,
            "record_count": record_count,
        },
    )


def fetch_scalar(
    connection: Connection[Any],
    query: str,
    parameters: dict[str, Any],
) -> int:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise RuntimeError("Validation query returned no row.")
    return int(row[0])


def validate_persisted_staging(
    connection: Connection[Any],
    import_run_id: int,
) -> tuple[int, int]:
    parameters = {"import_run_id": import_run_id}

    staged_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_products
        WHERE import_run_id = %(import_run_id)s
        """,
        parameters,
    )
    valid_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_products
        WHERE import_run_id = %(import_run_id)s
          AND normalization_status = 'normalized'
          AND validation_status = 'valid'
          AND validation_completed_at IS NOT NULL
        """,
        parameters,
    )
    invalid_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_products
        WHERE import_run_id = %(import_run_id)s
          AND (
              source_system <> 'cardmarket'
              OR source_product_id IS NULL
              OR source_expansion_id <> '1585'
              OR source_metaproduct_id IS NULL
              OR raw_name IS NULL
              OR source_category_id IS NULL
              OR source_category_name IS NULL
              OR raw_payload IS NULL
              OR record_checksum IS NULL
              OR normalization_status <> 'normalized'
              OR validation_status <> 'valid'
              OR validation_completed_at IS NULL
          )
        """,
        parameters,
    )
    duplicate_reference_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT source_record_reference
            FROM staging_market_products
            WHERE import_run_id = %(import_run_id)s
            GROUP BY source_record_reference
            HAVING COUNT(*) > 1
        ) AS duplicates
        """,
        parameters,
    )
    duplicate_product_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT source_product_id
            FROM staging_market_products
            WHERE import_run_id = %(import_run_id)s
            GROUP BY source_product_id
            HAVING COUNT(*) > 1
        ) AS duplicates
        """,
        parameters,
    )
    missing_source_created_at_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_products
        WHERE import_run_id = %(import_run_id)s
          AND source_created_at IS NULL
        """,
        parameters,
    )
    present_source_created_at_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_products
        WHERE import_run_id = %(import_run_id)s
          AND source_created_at IS NOT NULL
        """,
        parameters,
    )
    code_card_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_products
        WHERE import_run_id = %(import_run_id)s
          AND source_category_id = '51'
          AND raw_name LIKE 'Online Code Card%%'
        """,
        parameters,
    )
    eligible_count = staged_count - code_card_count

    failures: list[str] = []
    if staged_count != EXPECTED_RECORD_COUNT:
        failures.append(
            f"staged count is {staged_count}, expected {EXPECTED_RECORD_COUNT}"
        )
    if valid_count != EXPECTED_RECORD_COUNT:
        failures.append(
            f"valid count is {valid_count}, expected {EXPECTED_RECORD_COUNT}"
        )
    if invalid_count != 0:
        failures.append(f"incomplete or invalid staged rows: {invalid_count}")
    if duplicate_reference_count != 0:
        failures.append(
            f"duplicate source_record_reference groups: {duplicate_reference_count}"
        )
    if duplicate_product_count != 0:
        failures.append(
            f"duplicate source_product_id groups: {duplicate_product_count}"
        )
    if (
        missing_source_created_at_count
        != EXPECTED_MISSING_SOURCE_CREATED_AT_COUNT
    ):
        failures.append(
            "missing source_created_at count is "
            f"{missing_source_created_at_count}, expected "
            f"{EXPECTED_MISSING_SOURCE_CREATED_AT_COUNT}"
        )
    if (
        present_source_created_at_count
        != EXPECTED_PRESENT_SOURCE_CREATED_AT_COUNT
    ):
        failures.append(
            "present source_created_at count is "
            f"{present_source_created_at_count}, expected "
            f"{EXPECTED_PRESENT_SOURCE_CREATED_AT_COUNT}"
        )
    if code_card_count != EXPECTED_CODE_CARD_COUNT:
        failures.append(
            f"Online Code Card count is {code_card_count}, "
            f"expected {EXPECTED_CODE_CARD_COUNT}"
        )
    if eligible_count != EXPECTED_ELIGIBLE_COUNT:
        failures.append(
            f"eligible product count is {eligible_count}, "
            f"expected {EXPECTED_ELIGIBLE_COUNT}"
        )

    if failures:
        raise ImportValidationError(
            "Persisted staging validation failed: " + "; ".join(failures) + "."
        )

    return eligible_count, code_card_count


def mark_validated(
    connection: Connection[Any],
    import_run_id: int,
    valid_count: int,
) -> None:
    result = connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'validated',
            validated_at = CURRENT_TIMESTAMP,
            valid_source_records = %(valid_count)s,
            rejected_records = 0
        WHERE import_run_id = %(import_run_id)s
          AND status = 'staging_loaded'
        """,
        {
            "import_run_id": import_run_id,
            "valid_count": valid_count,
        },
    )

    if result.rowcount != 1:
        raise ImportValidationError(
            "Import run could not transition from staging_loaded to validated."
        )


def main() -> int:
    args = parse_args()

    run_reference = args.run_reference.strip()
    importer_version = args.importer_version.strip()
    if not run_reference:
        raise ImportValidationError("--run-reference must not be empty.")
    if not importer_version:
        raise ImportValidationError("--importer-version must not be empty.")

    fixture = load_and_validate_fixture(args.fixture)
    code_card_count = sum(
        record.is_online_code_card for record in fixture.records
    )
    eligible_count = len(fixture.records) - code_card_count

    print("Primal Clash Cardmarket product fixture validation passed")
    print(f"Source file: {fixture.source_file}")
    print(f"Source system: {SOURCE_SYSTEM}")
    print(f"Source expansion ID: {EXPECTED_EXPANSION_ID}")
    print(f"Source records: {len(fixture.records)}")
    print(f"Normalized records: {len(fixture.records)}")
    print(f"Valid records: {len(fixture.records)}")
    print("Rejected records: 0")
    print(f"Eligible market products: {eligible_count}")
    print(f"Out-of-scope Online Code Card records: {code_card_count}")
    print(
        "Missing source timestamps normalized to NULL: "
        f"{EXPECTED_MISSING_SOURCE_CREATED_AT_COUNT}"
    )
    print(
        "Parsed source timestamps: "
        f"{EXPECTED_PRESENT_SOURCE_CREATED_AT_COUNT}"
    )

    database_url = get_database_url()

    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            import_run_id = create_import_run(
                connection,
                run_reference=run_reference,
                importer_version=importer_version,
                fixture=fixture,
            )
            insert_staging_records(connection, import_run_id, fixture.records)
            mark_staging_loaded(connection, import_run_id, len(fixture.records))
            persisted_eligible_count, persisted_code_card_count = (
                validate_persisted_staging(connection, import_run_id)
            )
            mark_validated(connection, import_run_id, len(fixture.records))

    print()
    print("Primal Clash Cardmarket product staging import committed")
    print(f"Import run ID: {import_run_id}")
    print(f"Run reference: {run_reference}")
    print(f"Staged records: {len(fixture.records)}")
    print(f"Valid records: {len(fixture.records)}")
    print("Rejected records: 0")
    print(f"Eligible market products: {persisted_eligible_count}")
    print(
        "Out-of-scope Online Code Card records: "
        f"{persisted_code_card_count}"
    )
    print(
        "Missing source timestamps normalized to NULL: "
        f"{EXPECTED_MISSING_SOURCE_CREATED_AT_COUNT}"
    )
    print(
        "Parsed source timestamps: "
        f"{EXPECTED_PRESENT_SOURCE_CREATED_AT_COUNT}"
    )
    print("Final status: validated")
    print("Production merge: not executed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
