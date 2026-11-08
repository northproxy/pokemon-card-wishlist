"""Validate and stage the 30th Celebration: Classic Collection (me55c) cards.

This script follows the validated Primal Clash catalogue staging contract.
Only import_runs and staging_cards are written; production tables are untouched.
The separate production merge is NOT part of this script.

Run from repository root, after installing psycopg:
    python scripts/import/import_30th_celebration_classic_collection_catalogue.py \
        --run-reference me55c-catalogue-001

For offline fixture checks without a database connection:
    python scripts/import/import_30th_celebration_classic_collection_catalogue.py \
        --validate-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SOURCE_PATH = Path("data/fixtures/30th-celebration-classic-collection/canonical-cards.json")
SOURCE_SYSTEM = "pokemon_tcg_data"
SET_ID = "me55c"
RECORD_COUNT = 30
SCOPE_REFERENCE = f"{SOURCE_SYSTEM}:{SET_ID}"
IMPORTER_VERSION = "me55c-catalogue-v1"


class ImportValidationError(ValueError):
    pass


class ImportDatabaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class Artifact:
    path: Path
    source_file: str
    records: list[dict[str, Any]]
    sha256: str


@dataclass(frozen=True)
class Card:
    reference: str
    card_id: str
    number: str
    name: str
    rarity: str | None
    image_small: str
    image_large: str
    raw: dict[str, Any]
    checksum: str


def nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ImportValidationError(f"{label} must be non-empty, trimmed text")
    return value


def validate_artifact(path: Path) -> Artifact:
    if not path.is_file():
        raise ImportValidationError(f"Fixture not found: {path}")
    try:
        raw_bytes = path.read_bytes()
        fixture = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ImportValidationError(f"Cannot read fixture: {error}") from error
    if not isinstance(fixture, dict):
        raise ImportValidationError("Fixture must be a JSON object (not the raw card array)")
    if nonempty(fixture.get("sourceFile"), "sourceFile") != "me55c.json":
        raise ImportValidationError("Expected sourceFile=me55c.json")
    if nonempty(fixture.get("sourceSystem"), "sourceSystem") != SOURCE_SYSTEM:
        raise ImportValidationError(f"Expected sourceSystem={SOURCE_SYSTEM}")
    if nonempty(fixture.get("setId"), "setId") != SET_ID:
        raise ImportValidationError(f"Expected setId={SET_ID}")
    count = fixture.get("recordCount")
    if type(count) is not int or count != RECORD_COUNT:
        raise ImportValidationError(f"Expected recordCount={RECORD_COUNT}, got {count!r}")
    records = fixture.get("records")
    if not isinstance(records, list) or len(records) != RECORD_COUNT:
        raise ImportValidationError(f"Expected exactly {RECORD_COUNT} records")
    if any(not isinstance(record, dict) for record in records):
        raise ImportValidationError("Each record must be a JSON object")
    return Artifact(path, fixture["sourceFile"], records, hashlib.sha256(raw_bytes).hexdigest())


def normalize_cards(artifact: Artifact) -> list[Card]:
    cards: list[Card] = []
    identities: set[str] = set()
    for index, record in enumerate(artifact.records):
        label = f"records[{index}]"
        card_id = nonempty(record.get("id"), f"{label}.id")
        if not re.fullmatch(r"me55c-[0-9]+[A-Za-z]*", card_id):
            raise ImportValidationError(f"{label}: unexpected source card ID {card_id!r}")
        if card_id in identities:
            raise ImportValidationError(f"Duplicate source card ID: {card_id}")
        identities.add(card_id)
        number = nonempty(record.get("number"), f"{label}.number")
        if not number.isdecimal() or number != re.fullmatch(r"me55c-([0-9]+)[A-Za-z]*", card_id).group(1):
            raise ImportValidationError(f"{label}: collector number conflicts with {card_id}")
        name = nonempty(record.get("name"), f"{label}.name")
        rarity = record.get("rarity")
        if rarity is not None:
            rarity = nonempty(rarity, f"{label}.rarity")
        images = record.get("images")
        if not isinstance(images, dict):
            raise ImportValidationError(f"{label}.images must be an object")
        image_small = nonempty(images.get("small"), f"{label}.images.small")
        image_large = nonempty(images.get("large"), f"{label}.images.large")
        for size, actual in (("small", image_small), ("large", image_large)):
            expected = f"https://images.scrydex.com/pokemon/{card_id}/{size}"
            if actual != expected:
                raise ImportValidationError(f"{label}: expected {size} URL {expected!r}, got {actual!r}")
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        cards.append(Card(
            reference=f"{artifact.path.as_posix()}#{card_id}",
            card_id=card_id,
            number=number,
            name=name,
            rarity=rarity,
            image_small=image_small,
            image_large=image_large,
            raw=record,
            checksum=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        ))
    return cards


def stage(database_url: str, artifact: Artifact, cards: list[Card], run_reference: str) -> tuple[int, int]:
    # Import inside stage so --validate-only needs no PostgreSQL libraries.
    try:
        import psycopg
        from psycopg.errors import UniqueViolation
        from psycopg.types.json import Jsonb
    except ImportError as error:
        raise ImportDatabaseError("psycopg is required for staging") from error
    try:
        with psycopg.connect(database_url) as connection:
            row = connection.execute("""
                INSERT INTO import_runs (
                    run_reference, run_kind, source_system, source_entity_type,
                    source_artifact_reference, source_artifact_checksum, scope_type,
                    scope_reference, is_authoritative, status, importer_version
                ) VALUES (%s, 'catalogue', %s, 'card', %s, %s, 'expansion',
                          %s, true, 'created', %s) RETURNING import_run_id
            """, (run_reference, SOURCE_SYSTEM, artifact.path.as_posix(), artifact.sha256,
                  SCOPE_REFERENCE, IMPORTER_VERSION)).fetchone()
            if row is None:
                raise ImportDatabaseError("No import_run_id returned")
            run_id = int(row[0])
            data = [(
                run_id, card.reference, SOURCE_SYSTEM, card.card_id, SET_ID,
                card.number, card.name, card.rarity, card.image_small,
                card.image_large, Jsonb(card.raw), card.checksum,
            ) for card in cards]
            with connection.cursor() as cursor:
                cursor.executemany("""
                    INSERT INTO staging_cards (
                        import_run_id, source_record_reference, source_system,
                        source_card_id, source_expansion_id, collector_number,
                        name, rarity, image_small_url, image_large_url,
                        raw_payload, record_checksum, normalization_status,
                        validation_status, validation_completed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              %s, %s, 'normalized', 'valid', CURRENT_TIMESTAMP)
                """, data)
            first = connection.execute("""
                UPDATE import_runs SET status = 'staging_loaded',
                    staging_loaded_at = CURRENT_TIMESTAMP,
                    total_source_records = %s, updated_at = CURRENT_TIMESTAMP
                WHERE import_run_id = %s AND status = 'created'
            """, (len(cards), run_id))
            if first.rowcount != 1:
                raise ImportDatabaseError("Cannot transition to staging_loaded")
            counts = connection.execute("""
                SELECT count(*), count(*) FILTER (WHERE validation_status = 'valid'),
                    count(*) FILTER (WHERE validation_status = 'rejected')
                FROM staging_cards WHERE import_run_id = %s
            """, (run_id,)).fetchone()
            if counts is None or tuple(map(int, counts)) != (RECORD_COUNT, RECORD_COUNT, 0):
                raise ImportDatabaseError(f"Persisted staging counts mismatch: {counts}")
            pending = connection.execute("""
                SELECT count(*) FROM staging_cards WHERE import_run_id = %s
                  AND (normalization_status <> 'normalized'
                       OR validation_status <> 'valid'
                       OR validation_completed_at IS NULL)
            """, (run_id,)).fetchone()
            if pending is None or int(pending[0]) != 0:
                raise ImportDatabaseError("Persisted staging contains unvalidated rows")
            duplicate = connection.execute("""
                SELECT count(*) FROM (
                    SELECT source_system, source_card_id FROM staging_cards
                    WHERE import_run_id = %s
                    GROUP BY source_system, source_card_id HAVING count(*) > 1
                ) AS duplicates
            """, (run_id,)).fetchone()
            if duplicate is None or int(duplicate[0]) != 0:
                raise ImportDatabaseError("Persisted staging contains duplicate source identities")
            completed = connection.execute("""
                UPDATE import_runs SET status = 'validated',
                    validated_at = CURRENT_TIMESTAMP,
                    total_source_records = %s, valid_source_records = %s,
                    rejected_records = 0, updated_at = CURRENT_TIMESTAMP
                WHERE import_run_id = %s AND status = 'staging_loaded'
            """, (RECORD_COUNT, RECORD_COUNT, run_id))
            if completed.rowcount != 1:
                raise ImportDatabaseError("Cannot transition to validated")
        return run_id, RECORD_COUNT
    except UniqueViolation as error:
        raise ImportDatabaseError(f"Run reference already exists: {run_reference}") from error
    except psycopg.Error as error:
        raise ImportDatabaseError(f"Staging transaction failed: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_PATH)
    parser.add_argument("--validate-only", action="store_true", help="Check fixture without connecting to PostgreSQL")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--run-reference", help="Unique import-run reference (required for staging)")
    args = parser.parse_args()
    if not args.validate_only:
        if not args.database_url:
            parser.error("--database-url or DATABASE_URL required for staging")
        if not args.run_reference or args.run_reference != args.run_reference.strip():
            parser.error("--run-reference must be non-empty, trimmed text")
    try:
        artifact = validate_artifact(args.source)
        cards = normalize_cards(artifact)
        print(f"Fixture valid: set={SET_ID}, cards={len(cards)}, SHA-256={artifact.sha256}")
        print(f"Source file: {artifact.path}")
        if args.validate_only:
            print("Validation only: PostgreSQL not accessed")
            return 0
        run_id, staged = stage(args.database_url, artifact, cards, args.run_reference)
        print(f"Staging committed: run_id={run_id}, staged={staged}, status=validated")
        print("Production merge: not executed")
        return 0
    except (ImportValidationError, ImportDatabaseError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
