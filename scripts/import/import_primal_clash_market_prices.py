"""
Script: import_primal_clash_market_prices.py

Purpose:
    Validate and normalize the controlled Primal Clash Cardmarket price
    fixture, create one import_runs record, persist all source records in
    staging_market_prices, reconcile the staged state, and commit the run with
    status 'validated'. The script does not merge production price snapshots.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the validated vertical slice.
    It may be replaced only by a generalized market-price importer that
    preserves the same source-snapshot, validation, audit, rollback, and
    staging guarantees.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_PATH = (
    REPO_ROOT / "data" / "fixtures" / "primal-clash" / "cardmarket-prices.json"
)

SOURCE_SYSTEM = "cardmarket"
SOURCE_ENTITY_TYPE = "market_price"
RUN_KIND = "market_prices"
SCOPE_TYPE = "expansion"
EXPECTED_EXPANSION_ID = "1585"
EXPECTED_RECORD_COUNT = 177
EXPECTED_CATEGORY_ID = "51"
EXPECTED_AVG30_COUNT = 177
EXPECTED_AVG30_HOLO_COUNT = 169
EXPECTED_MISSING_AVG30_HOLO_COUNT = 8
CURRENCY_CODE = "EUR"
REQUIRED_RECORD_FIELDS = frozenset(
    {
        "idProduct",
        "idCategory",
        "avg30",
        "avg30-holo",
    }
)


class ImportValidationError(RuntimeError):
    """Raised when the controlled fixture or persisted staging state is invalid."""


@dataclass(frozen=True)
class NormalizedMarketPrice:
    """Normalized representation of one Cardmarket price source record."""

    source_record_reference: str
    source_product_id: str
    source_snapshot_at: datetime
    currency_code: str
    avg30_raw: str | None
    avg30: Decimal | None
    avg30_holo_raw: str | None
    avg30_holo: Decimal | None
    raw_payload: dict[str, Any]
    record_checksum: str


@dataclass(frozen=True)
class FixtureData:
    """Validated fixture metadata and normalized price records."""

    source_file: str
    source_created_at: datetime
    artifact_reference: str
    artifact_checksum: str
    records: tuple[NormalizedMarketPrice, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and stage the controlled Primal Clash Cardmarket price "
            "fixture without executing a production merge."
        )
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help="Path to cardmarket-prices.json.",
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


def parse_snapshot_timestamp(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ImportValidationError(f"{field_name} must be a non-empty string.")

    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ImportValidationError(
            f"{field_name} is not a valid timestamp: {text!r}."
        ) from exc

    if parsed.tzinfo is None:
        raise ImportValidationError(
            f"{field_name} must include an explicit timezone offset."
        )

    return parsed.astimezone(timezone.utc)


def normalize_optional_price(
    value: Any,
    field_name: str,
    record_number: int,
) -> tuple[str | None, Decimal | None]:
    if value is None:
        return None, None

    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ImportValidationError(
            f"Record {record_number}: {field_name} must be numeric or null."
        )

    raw_text = str(value).strip()
    if not raw_text:
        raise ImportValidationError(
            f"Record {record_number}: {field_name} must not be empty."
        )

    try:
        normalized = Decimal(raw_text)
    except InvalidOperation as exc:
        raise ImportValidationError(
            f"Record {record_number}: {field_name} is not a valid decimal."
        ) from exc

    if not normalized.is_finite():
        raise ImportValidationError(
            f"Record {record_number}: {field_name} must be finite."
        )
    if normalized < 0:
        raise ImportValidationError(
            f"Record {record_number}: {field_name} must be non-negative."
        )
    if normalized.as_tuple().exponent < -4:
        raise ImportValidationError(
            f"Record {record_number}: {field_name} has more than four "
            "fractional digits."
        )
    if normalized >= Decimal("100000000"):
        raise ImportValidationError(
            f"Record {record_number}: {field_name} exceeds numeric(12,4)."
        )

    return raw_text, normalized


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
    return f"cardmarket-prices.json#idProduct={source_product_id}"


def normalize_record(
    raw_record: Any,
    record_number: int,
    source_snapshot_at: datetime,
) -> NormalizedMarketPrice:
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
    source_category_id = normalize_required_text(
        raw_record["idCategory"], "idCategory", record_number
    )
    if source_category_id != EXPECTED_CATEGORY_ID:
        raise ImportValidationError(
            f"Record {record_number}: expected idCategory "
            f"{EXPECTED_CATEGORY_ID}, received {source_category_id}."
        )

    avg30_raw, avg30 = normalize_optional_price(
        raw_record["avg30"], "avg30", record_number
    )
    avg30_holo_raw, avg30_holo = normalize_optional_price(
        raw_record["avg30-holo"], "avg30-holo", record_number
    )

    if avg30 is None and avg30_holo is None:
        raise ImportValidationError(
            f"Record {record_number}: avg30 and avg30-holo are both null."
        )

    return NormalizedMarketPrice(
        source_record_reference=build_source_record_reference(source_product_id),
        source_product_id=source_product_id,
        source_snapshot_at=source_snapshot_at,
        currency_code=CURRENCY_CODE,
        avg30_raw=avg30_raw,
        avg30=avg30,
        avg30_holo_raw=avg30_holo_raw,
        avg30_holo=avg30_holo,
        raw_payload=raw_record,
        record_checksum=calculate_record_checksum(raw_record),
    )


def validate_unique_values(values: Iterable[str], label: str) -> None:
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
    declared_count = payload.get("recordCount")
    records = payload.get("records")

    if source_system != SOURCE_SYSTEM:
        raise ImportValidationError(
            f"Expected sourceSystem {SOURCE_SYSTEM!r}, received {source_system!r}."
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

    source_created_at = parse_snapshot_timestamp(
        payload.get("sourceCreatedAt"), "sourceCreatedAt"
    )
    normalized_records = tuple(
        normalize_record(raw_record, index, source_created_at)
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

    avg30_count = sum(record.avg30 is not None for record in normalized_records)
    avg30_holo_count = sum(
        record.avg30_holo is not None for record in normalized_records
    )
    missing_avg30_holo_count = len(normalized_records) - avg30_holo_count

    if avg30_count != EXPECTED_AVG30_COUNT:
        raise ImportValidationError(
            f"Expected {EXPECTED_AVG30_COUNT} non-null avg30 values, "
            f"found {avg30_count}."
        )
    if avg30_holo_count != EXPECTED_AVG30_HOLO_COUNT:
        raise ImportValidationError(
            f"Expected {EXPECTED_AVG30_HOLO_COUNT} non-null avg30-holo "
            f"values, found {avg30_holo_count}."
        )
    if missing_avg30_holo_count != EXPECTED_MISSING_AVG30_HOLO_COUNT:
        raise ImportValidationError(
            f"Expected {EXPECTED_MISSING_AVG30_HOLO_COUNT} null avg30-holo "
            f"values, found {missing_avg30_holo_count}."
        )

    try:
        artifact_reference = str(resolved_path.relative_to(REPO_ROOT))
    except ValueError:
        artifact_reference = str(resolved_path)

    return FixtureData(
        source_file=normalize_required_text(
            payload.get("sourceFile"), "sourceFile", 0
        ),
        source_created_at=source_created_at,
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
    records: tuple[NormalizedMarketPrice, ...],
) -> None:
    insert_sql = """
        INSERT INTO staging_market_prices (
            import_run_id,
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
        )
        VALUES (
            %(import_run_id)s,
            %(source_record_reference)s,
            %(source_system)s,
            %(source_product_id)s,
            %(source_snapshot_at)s,
            %(currency_code)s,
            %(avg30_raw)s,
            %(avg30)s,
            %(avg30_holo_raw)s,
            %(avg30_holo)s,
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
            "source_snapshot_at": record.source_snapshot_at,
            "currency_code": record.currency_code,
            "avg30_raw": record.avg30_raw,
            "avg30": record.avg30,
            "avg30_holo_raw": record.avg30_holo_raw,
            "avg30_holo": record.avg30_holo,
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
    result = connection.execute(
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
    if result.rowcount != 1:
        raise ImportValidationError(
            "Import run could not transition from created to staging_loaded."
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
    expected_snapshot_at: datetime,
) -> tuple[int, int]:
    parameters = {
        "import_run_id": import_run_id,
        "expected_snapshot_at": expected_snapshot_at,
    }

    staged_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_prices
        WHERE import_run_id = %(import_run_id)s
        """,
        parameters,
    )
    valid_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_prices
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
        FROM staging_market_prices
        WHERE import_run_id = %(import_run_id)s
          AND (
              source_system <> 'cardmarket'
              OR source_product_id IS NULL
              OR source_snapshot_at IS NULL
              OR source_snapshot_at <> %(expected_snapshot_at)s
              OR currency_code <> 'EUR'
              OR (avg30 IS NULL AND avg30_holo IS NULL)
              OR (avg30 IS NOT NULL AND avg30 < 0)
              OR (avg30_holo IS NOT NULL AND avg30_holo < 0)
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
            FROM staging_market_prices
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
            FROM staging_market_prices
            WHERE import_run_id = %(import_run_id)s
            GROUP BY source_product_id
            HAVING COUNT(*) > 1
        ) AS duplicates
        """,
        parameters,
    )
    distinct_snapshot_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(DISTINCT source_snapshot_at)
        FROM staging_market_prices
        WHERE import_run_id = %(import_run_id)s
        """,
        parameters,
    )
    avg30_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_prices
        WHERE import_run_id = %(import_run_id)s
          AND avg30 IS NOT NULL
        """,
        parameters,
    )
    avg30_holo_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_prices
        WHERE import_run_id = %(import_run_id)s
          AND avg30_holo IS NOT NULL
        """,
        parameters,
    )
    missing_avg30_holo_count = staged_count - avg30_holo_count

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
    if distinct_snapshot_count != 1:
        failures.append(
            f"distinct source_snapshot_at values: {distinct_snapshot_count}, expected 1"
        )
    if avg30_count != EXPECTED_AVG30_COUNT:
        failures.append(
            f"non-null avg30 count is {avg30_count}, "
            f"expected {EXPECTED_AVG30_COUNT}"
        )
    if avg30_holo_count != EXPECTED_AVG30_HOLO_COUNT:
        failures.append(
            f"non-null avg30_holo count is {avg30_holo_count}, "
            f"expected {EXPECTED_AVG30_HOLO_COUNT}"
        )
    if missing_avg30_holo_count != EXPECTED_MISSING_AVG30_HOLO_COUNT:
        failures.append(
            f"null avg30_holo count is {missing_avg30_holo_count}, "
            f"expected {EXPECTED_MISSING_AVG30_HOLO_COUNT}"
        )

    if failures:
        raise ImportValidationError(
            "Persisted staging validation failed: " + "; ".join(failures) + "."
        )

    return avg30_count, avg30_holo_count


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
    avg30_count = sum(record.avg30 is not None for record in fixture.records)
    avg30_holo_count = sum(
        record.avg30_holo is not None for record in fixture.records
    )

    print("Primal Clash Cardmarket price fixture validation passed")
    print(f"Source file: {fixture.source_file}")
    print(f"Source system: {SOURCE_SYSTEM}")
    print(f"Source expansion ID: {EXPECTED_EXPANSION_ID}")
    print(f"Source snapshot at: {fixture.source_created_at.isoformat()}")
    print(f"Currency: {CURRENCY_CODE}")
    print(f"Source records: {len(fixture.records)}")
    print(f"Normalized records: {len(fixture.records)}")
    print(f"Valid records: {len(fixture.records)}")
    print("Rejected records: 0")
    print(f"Records with avg30: {avg30_count}")
    print(f"Records with avg30-holo: {avg30_holo_count}")
    print(
        "Records without avg30-holo: "
        f"{len(fixture.records) - avg30_holo_count}"
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
            persisted_avg30_count, persisted_avg30_holo_count = (
                validate_persisted_staging(
                    connection,
                    import_run_id,
                    fixture.source_created_at,
                )
            )
            mark_validated(connection, import_run_id, len(fixture.records))

    print()
    print("Primal Clash Cardmarket price staging import committed")
    print(f"Import run ID: {import_run_id}")
    print(f"Run reference: {run_reference}")
    print(f"Source snapshot at: {fixture.source_created_at.isoformat()}")
    print(f"Currency: {CURRENCY_CODE}")
    print(f"Staged records: {len(fixture.records)}")
    print(f"Valid records: {len(fixture.records)}")
    print("Rejected records: 0")
    print(f"Records with avg30: {persisted_avg30_count}")
    print(f"Records with avg30-holo: {persisted_avg30_holo_count}")
    print(
        "Records without avg30-holo: "
        f"{len(fixture.records) - persisted_avg30_holo_count}"
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
