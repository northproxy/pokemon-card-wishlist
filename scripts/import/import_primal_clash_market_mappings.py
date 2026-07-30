"""
Script: import_primal_clash_market_mappings.py

Purpose:
    Validate and normalize the controlled Primal Clash Cardmarket mapping
    fixture, create one import_runs record, persist all source records in
    staging_market_mappings, reconcile the staged state, and commit the run
    with status 'validated'. The script does not create production mappings.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the validated vertical slice.
    It may be replaced only by a generalized market-mapping importer that
    preserves the same validation, audit, rollback, and staging guarantees.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_PATH = (
    REPO_ROOT / "data" / "fixtures" / "primal-clash" / "mapping-review.csv"
)

SOURCE_SYSTEM = "cardmarket"
CATALOGUE_SOURCE_SYSTEM = "pokemon_tcg_data"
SOURCE_ENTITY_TYPE = "market_mapping"
RUN_KIND = "market_mappings"
SCOPE_TYPE = "expansion"
EXPECTED_EXPANSION_ID = "1585"

EXPECTED_RECORD_COUNT = 177
EXPECTED_CANDIDATE_COUNT = 167
EXPECTED_EXCLUDED_COUNT = 4
EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT = 6
EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT = 12

ALLOWED_MAPPING_STATUSES = frozenset(
    {
        "candidate",
        "excluded",
        "unmatched_duplicate_candidate",
    }
)

REQUIRED_CSV_FIELDS = frozenset(
    {
        "canonical_card_id",
        "collector_number",
        "canonical_name",
        "listing_name",
        "listing_url",
        "edition_code",
        "cardmarket_product_id",
        "cardmarket_product_name",
        "cardmarket_metacard_id",
        "mapping_status",
        "mapping_method",
        "evidence",
        "avg30",
        "avg30_holo",
        "price_snapshot_at",
    }
)


class ImportValidationError(RuntimeError):
    """Raised when the controlled fixture or persisted staging state is invalid."""


@dataclass(frozen=True)
class NormalizedMarketMapping:
    """Normalized representation of one Cardmarket mapping source record."""

    source_record_reference: str
    source_product_id: str
    catalogue_source_system: str | None
    source_card_id: str | None
    source_edition_code: str | None
    proposed_status: str
    evidence_reference: str
    evidence_payload: dict[str, Any]
    raw_payload: dict[str, Any]
    record_checksum: str


@dataclass(frozen=True)
class FixtureData:
    """Validated mapping fixture metadata and normalized records."""

    artifact_reference: str
    artifact_checksum: str
    records: tuple[NormalizedMarketMapping, ...]


@dataclass(frozen=True)
class PersistedCounts:
    """Validated staging counts grouped by controlled mapping status."""

    staged: int
    candidates: int
    excluded: int
    unmatched_duplicate_candidates: int
    candidate_with_edition_code: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and stage the controlled Primal Clash Cardmarket "
            "mapping fixture without executing a production merge."
        )
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help="Path to mapping-review.csv.",
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


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


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


def build_source_record_reference(
    source_product_id: str,
    record_number: int,
) -> str:
    return (
        "mapping-review.csv"
        f"#row={record_number}"
        f"&cardmarket_product_id={source_product_id}"
    )


def build_evidence_reference(
    raw_record: dict[str, str],
    source_record_reference: str,
) -> str:
    listing_url = normalize_optional_text(raw_record.get("listing_url"))
    return listing_url or source_record_reference


def normalize_record(
    raw_record: dict[str, str],
    record_number: int,
) -> NormalizedMarketMapping:
    source_product_id = normalize_required_text(
        raw_record.get("cardmarket_product_id"),
        "cardmarket_product_id",
        record_number,
    )
    source_card_id = normalize_optional_text(raw_record.get("canonical_card_id"))
    source_edition_code = normalize_optional_text(raw_record.get("edition_code"))
    proposed_status = normalize_required_text(
        raw_record.get("mapping_status"),
        "mapping_status",
        record_number,
    )
    mapping_method = normalize_required_text(
        raw_record.get("mapping_method"),
        "mapping_method",
        record_number,
    )
    evidence = normalize_required_text(
        raw_record.get("evidence"),
        "evidence",
        record_number,
    )
    source_metacard_id = normalize_required_text(
        raw_record.get("cardmarket_metacard_id"),
        "cardmarket_metacard_id",
        record_number,
    )

    if proposed_status not in ALLOWED_MAPPING_STATUSES:
        raise ImportValidationError(
            f"Record {record_number}: unsupported mapping_status "
            f"{proposed_status!r}."
        )

    if proposed_status == "candidate":
        if source_card_id is None:
            raise ImportValidationError(
                f"Record {record_number}: candidate requires canonical_card_id."
            )
        if normalize_optional_text(raw_record.get("listing_url")) is None:
            raise ImportValidationError(
                f"Record {record_number}: candidate requires listing_url."
            )
    elif source_card_id is not None:
        raise ImportValidationError(
            f"Record {record_number}: {proposed_status} must not reference "
            "canonical_card_id."
        )

    source_record_reference = build_source_record_reference(
        source_product_id,
        record_number,
    )
    evidence_reference = build_evidence_reference(
        raw_record,
        source_record_reference,
    )

    evidence_payload = {
        "mapping_method": mapping_method,
        "evidence": evidence,
        "listing_url": normalize_optional_text(raw_record.get("listing_url")),
        "collector_number": normalize_optional_text(
            raw_record.get("collector_number")
        ),
        "canonical_name": normalize_optional_text(raw_record.get("canonical_name")),
        "listing_name": normalize_optional_text(raw_record.get("listing_name")),
        "cardmarket_product_name": normalize_optional_text(
            raw_record.get("cardmarket_product_name")
        ),
        "cardmarket_metacard_id": source_metacard_id,
    }

    raw_payload = dict(raw_record)

    return NormalizedMarketMapping(
        source_record_reference=source_record_reference,
        source_product_id=source_product_id,
        catalogue_source_system=(
            CATALOGUE_SOURCE_SYSTEM if source_card_id is not None else None
        ),
        source_card_id=source_card_id,
        source_edition_code=source_edition_code,
        proposed_status=proposed_status,
        evidence_reference=evidence_reference,
        evidence_payload=evidence_payload,
        raw_payload=raw_payload,
        record_checksum=calculate_record_checksum(raw_payload),
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


def validate_fixture_counts(
    records: tuple[NormalizedMarketMapping, ...],
) -> None:
    candidate_count = sum(
        record.proposed_status == "candidate" for record in records
    )
    excluded_count = sum(
        record.proposed_status == "excluded" for record in records
    )
    unmatched_duplicate_candidate_count = sum(
        record.proposed_status == "unmatched_duplicate_candidate"
        for record in records
    )
    candidate_with_edition_code_count = sum(
        record.proposed_status == "candidate"
        and record.source_edition_code is not None
        for record in records
    )

    failures: list[str] = []
    if len(records) != EXPECTED_RECORD_COUNT:
        failures.append(
            f"record count is {len(records)}, expected {EXPECTED_RECORD_COUNT}"
        )
    if candidate_count != EXPECTED_CANDIDATE_COUNT:
        failures.append(
            f"candidate count is {candidate_count}, "
            f"expected {EXPECTED_CANDIDATE_COUNT}"
        )
    if excluded_count != EXPECTED_EXCLUDED_COUNT:
        failures.append(
            f"excluded count is {excluded_count}, "
            f"expected {EXPECTED_EXCLUDED_COUNT}"
        )
    if (
        unmatched_duplicate_candidate_count
        != EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT
    ):
        failures.append(
            "unmatched_duplicate_candidate count is "
            f"{unmatched_duplicate_candidate_count}, expected "
            f"{EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT}"
        )
    if (
        candidate_with_edition_code_count
        != EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT
    ):
        failures.append(
            "candidate rows with edition_code count is "
            f"{candidate_with_edition_code_count}, expected "
            f"{EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT}"
        )

    if failures:
        raise ImportValidationError(
            "Fixture count validation failed: " + "; ".join(failures) + "."
        )


def load_and_validate_fixture(path: Path) -> FixtureData:
    resolved_path = path.expanduser().resolve()

    if not resolved_path.is_file():
        raise ImportValidationError(f"Fixture does not exist: {resolved_path}")

    try:
        with resolved_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ImportValidationError("CSV fixture has no header row.")

            actual_fields = {field.strip() for field in reader.fieldnames if field}
            missing_fields = sorted(REQUIRED_CSV_FIELDS - actual_fields)
            if missing_fields:
                raise ImportValidationError(
                    "CSV fixture is missing columns: "
                    + ", ".join(missing_fields)
                    + "."
                )

            raw_records = [dict(row) for row in reader]
    except UnicodeDecodeError as exc:
        raise ImportValidationError("Fixture is not valid UTF-8.") from exc
    except csv.Error as exc:
        raise ImportValidationError(f"Fixture is not valid CSV: {exc}.") from exc

    normalized_records = tuple(
        normalize_record(raw_record, index)
        for index, raw_record in enumerate(raw_records, start=2)
    )

    validate_unique_values(
        (record.source_record_reference for record in normalized_records),
        "source_record_reference values",
    )
    validate_unique_values(
        (record.source_product_id for record in normalized_records),
        "source_product_id values",
    )
    validate_fixture_counts(normalized_records)

    try:
        artifact_reference = str(resolved_path.relative_to(REPO_ROOT))
    except ValueError:
        artifact_reference = str(resolved_path)

    return FixtureData(
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
    records: tuple[NormalizedMarketMapping, ...],
) -> None:
    insert_sql = """
        INSERT INTO staging_market_mappings (
            import_run_id,
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
        )
        VALUES (
            %(import_run_id)s,
            %(source_record_reference)s,
            %(market_source_system)s,
            %(source_product_id)s,
            %(catalogue_source_system)s,
            %(source_card_id)s,
            %(source_edition_code)s,
            %(proposed_status)s,
            NULL,
            NULL,
            NULL,
            %(evidence_reference)s,
            %(evidence_payload)s,
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
            "market_source_system": SOURCE_SYSTEM,
            "source_product_id": record.source_product_id,
            "catalogue_source_system": record.catalogue_source_system,
            "source_card_id": record.source_card_id,
            "source_edition_code": record.source_edition_code,
            "proposed_status": record.proposed_status,
            "evidence_reference": record.evidence_reference,
            "evidence_payload": Jsonb(record.evidence_payload),
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
) -> PersistedCounts:
    parameters = {"import_run_id": import_run_id}

    staged_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_mappings
        WHERE import_run_id = %(import_run_id)s
        """,
        parameters,
    )
    valid_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_mappings
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
        FROM staging_market_mappings
        WHERE import_run_id = %(import_run_id)s
          AND (
              market_source_system <> 'cardmarket'
              OR source_product_id IS NULL
              OR proposed_status IS NULL
              OR evidence_reference IS NULL
              OR evidence_payload IS NULL
              OR raw_payload IS NULL
              OR record_checksum IS NULL
              OR normalization_status <> 'normalized'
              OR validation_status <> 'valid'
              OR validation_completed_at IS NULL
              OR confirmation_scope IS NOT NULL
              OR confirmation_method IS NOT NULL
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
            FROM staging_market_mappings
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
            FROM staging_market_mappings
            WHERE import_run_id = %(import_run_id)s
            GROUP BY source_product_id
            HAVING COUNT(*) > 1
        ) AS duplicates
        """,
        parameters,
    )
    candidate_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_mappings
        WHERE import_run_id = %(import_run_id)s
          AND proposed_status = 'candidate'
          AND catalogue_source_system = 'pokemon_tcg_data'
          AND source_card_id IS NOT NULL
        """,
        parameters,
    )
    excluded_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_mappings
        WHERE import_run_id = %(import_run_id)s
          AND proposed_status = 'excluded'
          AND catalogue_source_system IS NULL
          AND source_card_id IS NULL
        """,
        parameters,
    )
    unmatched_duplicate_candidate_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_mappings
        WHERE import_run_id = %(import_run_id)s
          AND proposed_status = 'unmatched_duplicate_candidate'
          AND catalogue_source_system IS NULL
          AND source_card_id IS NULL
        """,
        parameters,
    )
    candidate_with_edition_code_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM staging_market_mappings
        WHERE import_run_id = %(import_run_id)s
          AND proposed_status = 'candidate'
          AND source_edition_code IS NOT NULL
        """,
        parameters,
    )

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
    if candidate_count != EXPECTED_CANDIDATE_COUNT:
        failures.append(
            f"candidate count is {candidate_count}, "
            f"expected {EXPECTED_CANDIDATE_COUNT}"
        )
    if excluded_count != EXPECTED_EXCLUDED_COUNT:
        failures.append(
            f"excluded count is {excluded_count}, "
            f"expected {EXPECTED_EXCLUDED_COUNT}"
        )
    if (
        unmatched_duplicate_candidate_count
        != EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT
    ):
        failures.append(
            "unmatched_duplicate_candidate count is "
            f"{unmatched_duplicate_candidate_count}, expected "
            f"{EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT}"
        )
    if (
        candidate_with_edition_code_count
        != EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT
    ):
        failures.append(
            "candidate rows with edition_code count is "
            f"{candidate_with_edition_code_count}, expected "
            f"{EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT}"
        )

    if failures:
        raise ImportValidationError(
            "Persisted staging validation failed: " + "; ".join(failures) + "."
        )

    return PersistedCounts(
        staged=staged_count,
        candidates=candidate_count,
        excluded=excluded_count,
        unmatched_duplicate_candidates=unmatched_duplicate_candidate_count,
        candidate_with_edition_code=candidate_with_edition_code_count,
    )


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

    candidate_count = sum(
        record.proposed_status == "candidate" for record in fixture.records
    )
    excluded_count = sum(
        record.proposed_status == "excluded" for record in fixture.records
    )
    unmatched_duplicate_candidate_count = sum(
        record.proposed_status == "unmatched_duplicate_candidate"
        for record in fixture.records
    )

    print("Primal Clash Cardmarket mapping fixture validation passed")
    print(f"Source artifact: {fixture.artifact_reference}")
    print(f"Source system: {SOURCE_SYSTEM}")
    print(f"Source expansion ID: {EXPECTED_EXPANSION_ID}")
    print(f"Source records: {len(fixture.records)}")
    print(f"Normalized records: {len(fixture.records)}")
    print(f"Valid records: {len(fixture.records)}")
    print("Rejected records: 0")
    print(f"Candidate mappings: {candidate_count}")
    print(f"Excluded mappings: {excluded_count}")
    print(
        "Unmatched duplicate candidates: "
        f"{unmatched_duplicate_candidate_count}"
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
            persisted_counts = validate_persisted_staging(
                connection,
                import_run_id,
            )
            mark_validated(connection, import_run_id, persisted_counts.staged)

    print()
    print("Primal Clash Cardmarket mapping staging import committed")
    print(f"Import run ID: {import_run_id}")
    print(f"Run reference: {run_reference}")
    print(f"Staged records: {persisted_counts.staged}")
    print(f"Valid records: {persisted_counts.staged}")
    print("Rejected records: 0")
    print(f"Candidate mappings: {persisted_counts.candidates}")
    print(f"Excluded mappings: {persisted_counts.excluded}")
    print(
        "Unmatched duplicate candidates: "
        f"{persisted_counts.unmatched_duplicate_candidates}"
    )
    print(
        "Candidate mappings with edition code: "
        f"{persisted_counts.candidate_with_edition_code}"
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
