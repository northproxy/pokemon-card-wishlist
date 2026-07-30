"""
Script: import_primal_clash_catalogue.py

Purpose:
    Load, normalize, validate, and stage the prepared Primal Clash
    canonical-card fixture in PostgreSQL.

    The script creates one persistent validated import run and writes only to
    `import_runs` and `staging_cards`. It does not merge records into production
    catalogue tables.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the validated first-import
    vertical slice. It may later be replaced by a generic catalogue importer
    only after equivalent validation, audit, transactional, and repeat-import
    behaviour are implemented and tested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import psycopg
from psycopg import Connection
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb


DEFAULT_SOURCE = Path(
    "data/fixtures/primal-clash/canonical-cards.json"
)
DEFAULT_IMPORTER_VERSION = "m4-first-import-v1"

EXPECTED_SOURCE_SYSTEM = "pokemon_tcg_data"
EXPECTED_SET_ID = "xy5"
EXPECTED_RECORD_COUNT = 164

RUN_KIND = "catalogue"
SOURCE_ENTITY_TYPE = "card"
SCOPE_TYPE = "expansion"
SCOPE_REFERENCE = "pokemon_tcg_data:xy5"


class ImportValidationError(ValueError):
    """Raised when the controlled source fixture fails validation."""


class ImportDatabaseError(RuntimeError):
    """Raised when the controlled staging transaction fails."""


@dataclass(frozen=True)
class SourceArtifact:
    """Validated source artifact and its import-level metadata."""

    path: Path
    source_file: str
    source_system: str
    set_id: str
    declared_record_count: int
    records: list[dict[str, Any]]
    sha256: str


@dataclass(frozen=True)
class NormalizedCard:
    """Normalized representation of one staging card record."""

    source_record_reference: str
    source_system: str
    source_card_id: str | None
    source_expansion_id: str | None
    collector_number: str | None
    name: str | None
    rarity: str | None
    image_small_url: str | None
    image_large_url: str | None
    raw_payload: dict[str, Any]
    record_checksum: str
    normalization_status: str
    validation_status: str
    validation_errors: tuple[str, ...]


@dataclass(frozen=True)
class StagingResult:
    """Summary of the committed persistent staging run."""

    import_run_id: int
    run_reference: str
    staged_records: int
    valid_records: int
    rejected_records: int
    final_status: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Validate and stage the prepared Primal Clash canonical-card "
            "fixture without modifying production catalogue tables."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=(
            "Path to the canonical-card fixture "
            f"(default: {DEFAULT_SOURCE.as_posix()})"
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
            "Unique import-run reference, for example "
            "'primal-clash-catalogue-dry-run-001'."
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

    args = parser.parse_args(argv)

    if not args.database_url:
        parser.error(
            "--database-url is required when DATABASE_URL is not set."
        )

    args.run_reference = require_cli_text(
        args.run_reference,
        "--run-reference",
    )
    args.importer_version = require_cli_text(
        args.importer_version,
        "--importer-version",
    )

    return args


def require_cli_text(value: str, argument_name: str) -> str:
    """Require a trimmed, non-empty CLI text value."""

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


def calculate_sha256(path: Path) -> str:
    """Return the SHA-256 checksum of a file."""

    digest = hashlib.sha256()

    try:
        with path.open("rb") as source_file:
            for chunk in iter(
                lambda: source_file.read(1024 * 1024),
                b"",
            ):
                digest.update(chunk)
    except OSError as exc:
        raise ImportValidationError(
            f"Could not read source artifact for checksum: {path}"
        ) from exc

    return digest.hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON file and require a top-level object."""

    if not path.is_file():
        raise ImportValidationError(
            f"Source artifact does not exist or is not a file: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as source_file:
            payload = json.load(source_file)
    except UnicodeDecodeError as exc:
        raise ImportValidationError(
            f"Source artifact is not valid UTF-8: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ImportValidationError(
            "Source artifact is not valid JSON: "
            f"{path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ImportValidationError(
            f"Could not read source artifact: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise ImportValidationError(
            "Top-level fixture payload must be a JSON object."
        )

    return payload


def require_non_empty_string(
    payload: dict[str, Any],
    field_name: str,
) -> str:
    """Read and validate a required non-empty string field."""

    value = payload.get(field_name)

    if not isinstance(value, str) or not value.strip():
        raise ImportValidationError(
            f"Top-level field {field_name!r} must be a non-empty string."
        )

    if value != value.strip():
        raise ImportValidationError(
            f"Top-level field {field_name!r} must not contain "
            "surrounding whitespace."
        )

    return value


def require_record_list(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Read the fixture records and require JSON objects."""

    records = payload.get("records")

    if not isinstance(records, list):
        raise ImportValidationError(
            "Top-level field 'records' must be a JSON array."
        )

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ImportValidationError(
                f"records[{index}] must be a JSON object."
            )

    return records


def validate_source_artifact(path: Path) -> SourceArtifact:
    """Load and validate the controlled Primal Clash fixture envelope."""

    payload = load_json_object(path)

    source_file = require_non_empty_string(payload, "sourceFile")
    source_system = require_non_empty_string(
        payload,
        "sourceSystem",
    )
    set_id = require_non_empty_string(payload, "setId")

    declared_record_count = payload.get("recordCount")

    if (
        not isinstance(declared_record_count, int)
        or isinstance(declared_record_count, bool)
        or declared_record_count < 0
    ):
        raise ImportValidationError(
            "Top-level field 'recordCount' must be a non-negative integer."
        )

    records = require_record_list(payload)

    if declared_record_count != len(records):
        raise ImportValidationError(
            "Declared record count does not match the records array: "
            f"declared={declared_record_count}, actual={len(records)}."
        )

    if source_system != EXPECTED_SOURCE_SYSTEM:
        raise ImportValidationError(
            "Unexpected source system: "
            f"expected={EXPECTED_SOURCE_SYSTEM!r}, "
            f"actual={source_system!r}."
        )

    if set_id != EXPECTED_SET_ID:
        raise ImportValidationError(
            "Unexpected source expansion ID: "
            f"expected={EXPECTED_SET_ID!r}, actual={set_id!r}."
        )

    if declared_record_count != EXPECTED_RECORD_COUNT:
        raise ImportValidationError(
            "Unexpected source record count: "
            f"expected={EXPECTED_RECORD_COUNT}, "
            f"actual={declared_record_count}."
        )

    return SourceArtifact(
        path=path,
        source_file=source_file,
        source_system=source_system,
        set_id=set_id,
        declared_record_count=declared_record_count,
        records=records,
        sha256=calculate_sha256(path),
    )


def normalize_optional_text(value: Any) -> str | None:
    """Normalize an optional source value to trimmed text."""

    if value is None:
        return None

    if not isinstance(value, str):
        return None

    normalized = value.strip()
    return normalized or None


def calculate_record_checksum(record: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 checksum for one source record."""

    canonical_json = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()


def validate_image_url(
    value: str | None,
    expected_path: str,
    field_name: str,
) -> list[str]:
    """Validate one deterministic Pokemon TCG image URL."""

    if value is None:
        return [f"{field_name} is required."]

    expected_url = (
        f"https://images.pokemontcg.io/{expected_path}"
    )

    if value != expected_url:
        return [
            f"{field_name} must equal {expected_url!r}; "
            f"actual={value!r}."
        ]

    return []


def build_source_record_reference(
    artifact: SourceArtifact,
    source_card_id: str | None,
    record_index: int,
) -> str:
    """Build a stable source-record reference."""

    if source_card_id is not None:
        record_fragment = source_card_id
    else:
        record_fragment = f"record-index-{record_index}"

    return f"{artifact.path.as_posix()}#{record_fragment}"


def normalize_card(
    artifact: SourceArtifact,
    record: dict[str, Any],
    record_index: int,
) -> NormalizedCard:
    """Normalize and validate one canonical-card source record."""

    source_card_id = normalize_optional_text(
        record.get("id")
    )
    collector_number = normalize_optional_text(
        record.get("number")
    )
    name = normalize_optional_text(
        record.get("name")
    )
    rarity = normalize_optional_text(
        record.get("rarity")
    )

    images = record.get("images")

    if isinstance(images, dict):
        image_small_url = normalize_optional_text(
            images.get("small")
        )
        image_large_url = normalize_optional_text(
            images.get("large")
        )
    else:
        image_small_url = None
        image_large_url = None

    source_record_reference = build_source_record_reference(
        artifact,
        source_card_id,
        record_index,
    )

    errors: list[str] = []

    if source_card_id is None:
        errors.append("source_card_id is required.")

    if collector_number is None:
        errors.append("collector_number is required.")

    if name is None:
        errors.append("name is required.")

    if collector_number is not None:
        errors.extend(
            validate_image_url(
                image_small_url,
                f"{artifact.set_id}/{collector_number}.png",
                "image_small_url",
            )
        )
        errors.extend(
            validate_image_url(
                image_large_url,
                (
                    f"{artifact.set_id}/"
                    f"{collector_number}_hires.png"
                ),
                "image_large_url",
            )
        )
    else:
        if image_small_url is None:
            errors.append("image_small_url is required.")

        if image_large_url is None:
            errors.append("image_large_url is required.")

    validation_status = (
        "valid"
        if not errors
        else "rejected"
    )

    return NormalizedCard(
        source_record_reference=source_record_reference,
        source_system=artifact.source_system,
        source_card_id=source_card_id,
        source_expansion_id=artifact.set_id,
        collector_number=collector_number,
        name=name,
        rarity=rarity,
        image_small_url=image_small_url,
        image_large_url=image_large_url,
        raw_payload=record,
        record_checksum=calculate_record_checksum(record),
        normalization_status="normalized",
        validation_status=validation_status,
        validation_errors=tuple(errors),
    )


def normalize_cards(
    artifact: SourceArtifact,
) -> list[NormalizedCard]:
    """Normalize all records and validate import-level uniqueness."""

    normalized_cards = [
        normalize_card(
            artifact=artifact,
            record=record,
            record_index=index,
        )
        for index, record in enumerate(artifact.records)
    ]

    references: set[str] = set()
    identities: set[tuple[str, str]] = set()

    for card in normalized_cards:
        if card.source_record_reference in references:
            raise ImportValidationError(
                "Duplicate source record reference: "
                f"{card.source_record_reference}"
            )

        references.add(card.source_record_reference)

        if card.source_card_id is None:
            continue

        identity = (
            card.source_system,
            card.source_card_id,
        )

        if identity in identities:
            raise ImportValidationError(
                "Duplicate source card identity: "
                f"{identity[0]}:{identity[1]}"
            )

        identities.add(identity)

    return normalized_cards


def require_all_cards_valid(
    cards: list[NormalizedCard],
) -> None:
    """Prevent database writes when any fixture record is rejected."""

    rejected_cards = [
        card
        for card in cards
        if card.validation_status == "rejected"
    ]

    if not rejected_cards:
        return

    details = []

    for card in rejected_cards:
        details.append(
            f"{card.source_record_reference}: "
            f"{'; '.join(card.validation_errors)}"
        )

    raise ImportValidationError(
        "Controlled fixture contains rejected records:\n- "
        + "\n- ".join(details)
    )


def create_import_run(
    connection: Connection[Any],
    artifact: SourceArtifact,
    run_reference: str,
    importer_version: str,
) -> int:
    """Create an import run and return its generated identifier."""

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
            status,
            importer_version
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
            'created',
            %s
        )
        RETURNING import_run_id
        """,
        (
            run_reference,
            RUN_KIND,
            artifact.source_system,
            SOURCE_ENTITY_TYPE,
            artifact.path.as_posix(),
            artifact.sha256,
            SCOPE_TYPE,
            SCOPE_REFERENCE,
            True,
            importer_version,
        ),
    ).fetchone()

    if row is None:
        raise ImportDatabaseError(
            "PostgreSQL did not return an import_run_id."
        )

    return int(row[0])


def insert_staging_cards(
    connection: Connection[Any],
    import_run_id: int,
    cards: list[NormalizedCard],
) -> None:
    """Insert normalized cards into the staging table."""

    values = [
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
        )
        for card in cards
    ]

    with connection.cursor() as cursor:
        cursor.executemany(
            """
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
            """,
            values,
        )


def mark_staging_loaded(
    connection: Connection[Any],
    import_run_id: int,
    total_source_records: int,
) -> None:
    """Advance an import run to staging_loaded."""

    connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'staging_loaded',
            staging_loaded_at = CURRENT_TIMESTAMP,
            total_source_records = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE import_run_id = %s
          AND status = 'created'
        """,
        (
            total_source_records,
            import_run_id,
        ),
    )


def validate_persisted_staging(
    connection: Connection[Any],
    import_run_id: int,
    expected_records: int,
) -> tuple[int, int, int]:
    """Validate persisted staging counts and uniqueness."""

    counts = connection.execute(
        """
        SELECT
            count(*) AS total_records,
            count(*) FILTER (
                WHERE validation_status = 'valid'
            ) AS valid_records,
            count(*) FILTER (
                WHERE validation_status = 'rejected'
            ) AS rejected_records
        FROM staging_cards
        WHERE import_run_id = %s
        """,
        (import_run_id,),
    ).fetchone()

    if counts is None:
        raise ImportDatabaseError(
            "Could not read persisted staging counts."
        )

    total_records = int(counts[0])
    valid_records = int(counts[1])
    rejected_records = int(counts[2])

    if total_records != expected_records:
        raise ImportDatabaseError(
            "Persisted staging row count mismatch: "
            f"expected={expected_records}, actual={total_records}."
        )

    if valid_records + rejected_records != total_records:
        raise ImportDatabaseError(
            "Persisted staging validation states do not reconcile: "
            f"total={total_records}, valid={valid_records}, "
            f"rejected={rejected_records}."
        )

    pending_records = connection.execute(
        """
        SELECT count(*)
        FROM staging_cards
        WHERE import_run_id = %s
          AND (
              normalization_status = 'pending'
              OR validation_status = 'pending'
              OR validation_completed_at IS NULL
          )
        """,
        (import_run_id,),
    ).fetchone()

    if pending_records is None or int(pending_records[0]) != 0:
        raise ImportDatabaseError(
            "One or more staging rows remain in a pending state."
        )

    duplicate_identities = connection.execute(
        """
        SELECT count(*)
        FROM (
            SELECT
                source_system,
                source_card_id
            FROM staging_cards
            WHERE import_run_id = %s
              AND source_card_id IS NOT NULL
            GROUP BY
                source_system,
                source_card_id
            HAVING count(*) > 1
        ) AS duplicate_groups
        """,
        (import_run_id,),
    ).fetchone()

    if (
        duplicate_identities is None
        or int(duplicate_identities[0]) != 0
    ):
        raise ImportDatabaseError(
            "Duplicate source card identities exist in staging."
        )

    return (
        total_records,
        valid_records,
        rejected_records,
    )


def mark_validated(
    connection: Connection[Any],
    import_run_id: int,
    total_records: int,
    valid_records: int,
    rejected_records: int,
) -> None:
    """Advance an import run to validated."""

    result = connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'validated',
            validated_at = CURRENT_TIMESTAMP,
            total_source_records = %s,
            valid_source_records = %s,
            rejected_records = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE import_run_id = %s
          AND status = 'staging_loaded'
        """,
        (
            total_records,
            valid_records,
            rejected_records,
            import_run_id,
        ),
    )

    if result.rowcount != 1:
        raise ImportDatabaseError(
            "Import run could not transition from "
            "'staging_loaded' to 'validated'."
        )


def persist_validated_staging_run(
    database_url: str,
    artifact: SourceArtifact,
    cards: list[NormalizedCard],
    run_reference: str,
    importer_version: str,
) -> StagingResult:
    """Create and commit one persistent validated staging run."""

    try:
        with psycopg.connect(database_url) as connection:
            import_run_id = create_import_run(
                connection=connection,
                artifact=artifact,
                run_reference=run_reference,
                importer_version=importer_version,
            )

            insert_staging_cards(
                connection=connection,
                import_run_id=import_run_id,
                cards=cards,
            )

            mark_staging_loaded(
                connection=connection,
                import_run_id=import_run_id,
                total_source_records=len(cards),
            )

            (
                total_records,
                valid_records,
                rejected_records,
            ) = validate_persisted_staging(
                connection=connection,
                import_run_id=import_run_id,
                expected_records=len(cards),
            )

            if rejected_records != 0:
                raise ImportDatabaseError(
                    "The controlled fixture unexpectedly produced "
                    f"{rejected_records} rejected staging records."
                )

            mark_validated(
                connection=connection,
                import_run_id=import_run_id,
                total_records=total_records,
                valid_records=valid_records,
                rejected_records=rejected_records,
            )

        return StagingResult(
            import_run_id=import_run_id,
            run_reference=run_reference,
            staged_records=total_records,
            valid_records=valid_records,
            rejected_records=rejected_records,
            final_status="validated",
        )

    except UniqueViolation as exc:
        raise ImportDatabaseError(
            f"Import run reference already exists: {run_reference!r}. "
            "Use a new unique --run-reference."
        ) from exc
    except psycopg.Error as exc:
        raise ImportDatabaseError(
            f"PostgreSQL staging transaction failed: {exc}"
        ) from exc


def print_validation_summary(
    artifact: SourceArtifact,
) -> None:
    """Print a concise fixture-envelope validation summary."""

    print("Primal Clash catalogue fixture validation passed")
    print(f"Source path: {artifact.path}")
    print(f"Source file: {artifact.source_file}")
    print(f"Source system: {artifact.source_system}")
    print(f"Set ID: {artifact.set_id}")
    print(
        f"Record count: {artifact.declared_record_count}"
    )
    print(f"SHA-256: {artifact.sha256}")


def print_record_summary(
    cards: list[NormalizedCard],
) -> None:
    """Print normalized record counts."""

    valid_cards = [
        card
        for card in cards
        if card.validation_status == "valid"
    ]
    rejected_cards = [
        card
        for card in cards
        if card.validation_status == "rejected"
    ]

    print(f"Normalized records: {len(cards)}")
    print(f"Valid records: {len(valid_cards)}")
    print(f"Rejected records: {len(rejected_cards)}")


def print_staging_summary(result: StagingResult) -> None:
    """Print the committed staging-run result."""

    print("Persistent staging transaction committed")
    print(f"Import run ID: {result.import_run_id}")
    print(f"Run reference: {result.run_reference}")
    print(f"Staged records: {result.staged_records}")
    print(f"Valid records: {result.valid_records}")
    print(f"Rejected records: {result.rejected_records}")
    print(f"Final status: {result.final_status}")
    print("Production merge: not executed")


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Run the controlled persistent staging import."""

    args = parse_args(argv)

    try:
        artifact = validate_source_artifact(args.source)
        cards = normalize_cards(artifact)
        require_all_cards_valid(cards)

        result = persist_validated_staging_run(
            database_url=args.database_url,
            artifact=artifact,
            cards=cards,
            run_reference=args.run_reference,
            importer_version=args.importer_version,
        )
    except (
        ImportValidationError,
        ImportDatabaseError,
    ) as exc:
        print(
            f"Import failed: {exc}",
            file=sys.stderr,
        )
        return 1

    print_validation_summary(artifact)
    print_record_summary(cards)
    print_staging_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())