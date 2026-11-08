"""Merge validated me55c catalogue staging into production, transactionally.

Run from repository root after staging and independently reviewing its import run:
    python scripts/import/merge_30th_celebration_classic_collection_catalogue.py \
        --import-run-id 123

Check local fixture/checksum and script settings without a database connection:
    python scripts/import/merge_30th_celebration_classic_collection_catalogue.py \
        --validate-only

Only the explicitly selected, validated me55c import run can be merged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FIXTURE = Path("data/fixtures/30th-celebration-classic-collection/canonical-cards.json")
SOURCE_SYSTEM = "pokemon_tcg_data"
SET_ID = "me55c"
SCOPE_REFERENCE = f"{SOURCE_SYSTEM}:{SET_ID}"
RECORD_COUNT = 30
EXPECTED_SHA256 = "b8b20bb7ee8bfb72ea00953be7cdad0b2d17a555866d9f39b2f19c31929cc121"
EXPANSION_KEY = "30th_celebration_classic_collection"
EXPANSION_NAME = "30th Celebration: Classic Collection"


class MergeError(RuntimeError):
    """Safety contract or database operation failed."""


@dataclass(frozen=True)
class StagedCard:
    staging_card_id: int
    reference: str
    system: str
    card_id: str
    expansion_id: str
    number: str
    name: str
    rarity: str | None
    small: str | None
    large: str | None


def validate_fixture(path: Path) -> str:
    """Verify the controlled fixture against the fixed merge contract."""
    try:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        fixture = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MergeError(f"Cannot read fixture: {error}") from error
    if digest != EXPECTED_SHA256:
        raise MergeError(f"Fixture checksum changed: expected={EXPECTED_SHA256}, actual={digest}")
    if not isinstance(fixture, dict):
        raise MergeError("Fixture must be a JSON object")
    expected = {"sourceFile": "me55c.json", "sourceSystem": SOURCE_SYSTEM,
                "setId": SET_ID, "recordCount": RECORD_COUNT}
    for field, value in expected.items():
        if fixture.get(field) != value or (field == "recordCount" and type(fixture[field]) is not int):
            raise MergeError(f"Unexpected fixture {field}: {fixture.get(field)!r}")
    records = fixture.get("records")
    if not isinstance(records, list) or len(records) != RECORD_COUNT:
        raise MergeError(f"Expected {RECORD_COUNT} fixture records")
    if any(not isinstance(x, dict) for x in records):
        raise MergeError("Fixture records must all be JSON objects")
    return digest


def lock_run(conn: Any, import_run_id: int) -> None:
    row = conn.execute("""
        SELECT run_kind, source_system, source_entity_type,
               source_artifact_checksum, scope_type, scope_reference, status,
               total_source_records, valid_source_records, rejected_records,
               staging_loaded_at, validated_at, merge_started_at, completed_at
        FROM import_runs WHERE import_run_id = %s FOR UPDATE
    """, (import_run_id,)).fetchone()
    if row is None:
        raise MergeError(f"Import run not found: {import_run_id}")
    expected = ("catalogue", SOURCE_SYSTEM, "card", EXPECTED_SHA256,
                "expansion", SCOPE_REFERENCE, "validated",
                RECORD_COUNT, RECORD_COUNT, 0)
    if tuple(row[:10]) != expected:
        names = ("run_kind", "source_system", "source_entity_type", "checksum", "scope_type",
                 "scope_reference", "status", "total", "valid", "rejected")
        mismatches = [f"{n}: expected={e!r}, actual={a!r}"
                      for n, a, e in zip(names, row[:10], expected) if a != e]
        raise MergeError("Import run fails merge contract: " + "; ".join(mismatches))
    loaded, validated, started, completed = row[10:]
    if loaded is None or validated is None or started is not None or completed is not None:
        raise MergeError("Import run has invalid lifecycle timestamps")
    count = conn.execute("SELECT count(*) FROM import_record_outcomes WHERE import_run_id=%s",
                         (import_run_id,)).fetchone()
    if count is None or int(count[0]) != 0:
        raise MergeError("Import run already has merge outcomes")


def load_cards(conn: Any, import_run_id: int) -> list[StagedCard]:
    rows = conn.execute("""
        SELECT staging_card_id, source_record_reference, source_system,
               source_card_id, source_expansion_id, collector_number,
               name, rarity, image_small_url, image_large_url,
               normalization_status, validation_status, validation_completed_at
        FROM staging_cards WHERE import_run_id=%s ORDER BY staging_card_id
    """, (import_run_id,)).fetchall()
    if len(rows) != RECORD_COUNT:
        raise MergeError(f"Expected {RECORD_COUNT} staged cards, found {len(rows)}")
    cards = []
    identities = set()
    for row in rows:
        *data, norm, validation, completed_at = row
        card = StagedCard(*data)
        if norm != "normalized" or validation != "valid" or completed_at is None:
            raise MergeError(f"Unvalidated staged card: {card.staging_card_id}")
        required = (card.reference, card.system, card.card_id, card.expansion_id, card.number, card.name)
        if any(not isinstance(x, str) or not x.strip() for x in required):
            raise MergeError(f"Incomplete staging card: {card.staging_card_id}")
        if card.system != SOURCE_SYSTEM or card.expansion_id != SET_ID:
            raise MergeError(f"Unexpected source identity: {card.card_id}")
        if (card.system, card.card_id) in identities:
            raise MergeError(f"Duplicate staging card identity: {card.card_id}")
        identities.add((card.system, card.card_id))
        cards.append(card)
    return cards


def resolve_expansion(conn: Any) -> int:
    existing = conn.execute("""
        SELECT e.expansion_id, e.expansion_key, e.name
        FROM expansion_source_identifiers esi
        JOIN expansions e ON e.expansion_id=esi.expansion_id
        WHERE esi.source_system=%s AND esi.source_expansion_id=%s
        FOR UPDATE OF esi, e
    """, (SOURCE_SYSTEM, SET_ID)).fetchone()
    if existing is not None:
        eid, key, name = existing
        if key != EXPANSION_KEY or name != EXPANSION_NAME:
            raise MergeError("Existing expansion source identifier points to another expansion")
        return int(eid)

    row = conn.execute("SELECT expansion_id, name FROM expansions WHERE expansion_key=%s FOR UPDATE",
                       (EXPANSION_KEY,)).fetchone()
    if row is None:
        created = conn.execute("INSERT INTO expansions (expansion_key, name) VALUES (%s,%s) RETURNING expansion_id",
                               (EXPANSION_KEY, EXPANSION_NAME)).fetchone()
        if created is None:
            raise MergeError("Expansion creation did not return an ID")
        eid = int(created[0])
    else:
        eid, name = row
        if name != EXPANSION_NAME:
            raise MergeError("Existing expansion key has another name")
        eid = int(eid)
    conn.execute("""
        INSERT INTO expansion_source_identifiers
          (expansion_id, source_system, source_expansion_id, source_name)
        VALUES (%s,%s,%s,%s)
    """, (eid, SOURCE_SYSTEM, SET_ID, EXPANSION_NAME))
    return eid


def record_outcome(conn: Any, run_id: int, card: StagedCard, prod_id: int,
                   outcome: str, detail: dict[str, Any] | None = None) -> None:
    from psycopg.types.json import Jsonb
    conn.execute("""
        INSERT INTO import_record_outcomes
          (import_run_id, entity_type, source_system, source_entity_id,
           source_record_reference, production_entity_id, outcome_type, change_summary)
        VALUES (%s,'card',%s,%s,%s,%s,%s,%s)
    """, (run_id, card.system, card.card_id, card.reference, prod_id, outcome,
          Jsonb(detail) if detail is not None else None))


def merge_card(conn: Any, run_id: int, expansion_id: int, card: StagedCard) -> str:
    existing = conn.execute("""
        SELECT card_id, expansion_id, collector_number, name, rarity,
               image_small_url, image_large_url, is_active
        FROM cards WHERE source_system=%s AND source_card_id=%s FOR UPDATE
    """, (card.system, card.card_id)).fetchone()
    values = (card.number, card.name, card.rarity, card.small, card.large)
    fields = ("collector_number", "name", "rarity", "image_small_url", "image_large_url")
    if existing is None:
        row = conn.execute("""
            INSERT INTO cards
              (expansion_id, source_system, source_card_id, collector_number,
               name, rarity, image_small_url, image_large_url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING card_id
        """, (expansion_id, card.system, card.card_id, *values)).fetchone()
        if row is None:
            raise MergeError(f"No inserted production card ID for {card.card_id}")
        record_outcome(conn, run_id, card, int(row[0]), "inserted",
                       {"inserted_fields": ["expansion_id", "source_system", "source_card_id", *fields]})
        return "inserted"

    prod_id, existing_expansion, *other = existing
    if int(existing_expansion) != expansion_id:
        raise MergeError(f"Existing card belongs to another expansion: {card.card_id}")
    old_values, active = other[:5], other[5]
    changed = [name for name, old, new in zip(fields, old_values, values) if old != new]
    if not active or changed:
        conn.execute("""
            UPDATE cards SET collector_number=%s, name=%s, rarity=%s,
                image_small_url=%s, image_large_url=%s,
                is_active=true, retired_at=NULL, updated_at=CURRENT_TIMESTAMP
            WHERE card_id=%s
        """, (*values, prod_id))
        if not active:
            outcome = "reactivated"
            detail = {"reactivated": True, "changed_fields": changed}
        else:
            outcome = "updated"
            detail = {"changed_fields": changed,
                      "previous_values": dict(zip(changed, (old_values[fields.index(x)] for x in changed))),
                      "new_values": dict(zip(changed, (values[fields.index(x)] for x in changed)))}
        record_outcome(conn, run_id, card, int(prod_id), outcome, detail)
        return outcome
    record_outcome(conn, run_id, card, int(prod_id), "unchanged")
    return "unchanged"


def execute_merge(database_url: str, run_id: int) -> tuple[int, dict[str, int]]:
    try:
        import psycopg
    except ImportError as error:
        raise MergeError("Install psycopg before database merge") from error
    try:
        with psycopg.connect(database_url) as conn:
            lock_run(conn, run_id)
            cards = load_cards(conn, run_id)
            expansion_id = resolve_expansion(conn)
            started = conn.execute("""
                UPDATE import_runs SET status='merge_started',
                  merge_started_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                WHERE import_run_id=%s AND status='validated'
                  AND merge_started_at IS NULL AND completed_at IS NULL
            """, (run_id,))
            if started.rowcount != 1:
                raise MergeError("Cannot start merge lifecycle")
            counts = {key: 0 for key in ("inserted", "updated", "unchanged", "reactivated")}
            for card in cards:
                counts[merge_card(conn, run_id, expansion_id, card)] += 1
            if sum(counts.values()) != RECORD_COUNT:
                raise MergeError("Merge outcome counts do not reconcile")
            actual_cards = conn.execute("""
                SELECT count(*) FROM cards
                WHERE expansion_id=%s AND source_system=%s AND is_active=true
            """, (expansion_id, SOURCE_SYSTEM)).fetchone()
            if actual_cards is None or int(actual_cards[0]) != RECORD_COUNT:
                raise MergeError("Unexpected active production card count")
            outcomes = conn.execute("""
                SELECT count(*) FROM import_record_outcomes
                WHERE import_run_id=%s AND entity_type='card'
            """, (run_id,)).fetchone()
            if outcomes is None or int(outcomes[0]) != RECORD_COUNT:
                raise MergeError("Merge outcomes count mismatch")
            duplicates = conn.execute("""
                SELECT source_system, source_card_id FROM cards
                GROUP BY source_system, source_card_id HAVING count(*) > 1 LIMIT 1
            """).fetchone()
            if duplicates is not None:
                raise MergeError("Duplicate production card identity found")
            completed = conn.execute("""
                UPDATE import_runs SET status='succeeded', completed_at=CURRENT_TIMESTAMP,
                  inserted_records=%s, updated_records=%s, unchanged_records=%s,
                  missing_records=0, retired_records=0,
                  failure_code=NULL, failure_detail=NULL, updated_at=CURRENT_TIMESTAMP
                WHERE import_run_id=%s AND status='merge_started'
                  AND merge_started_at IS NOT NULL AND completed_at IS NULL
            """, (counts["inserted"], counts["updated"] + counts["reactivated"],
                  counts["unchanged"], run_id))
            if completed.rowcount != 1:
                raise MergeError("Cannot complete merge lifecycle")
        return expansion_id, counts
    except psycopg.Error as error:
        raise MergeError(f"Production merge database transaction failed: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--validate-only", action="store_true", help="Check controlled fixture only; no DB connection")
    parser.add_argument("--import-run-id", type=int)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    if not args.validate_only:
        if args.import_run_id is None or args.import_run_id <= 0:
            parser.error("--import-run-id must be a positive integer")
        if not args.database_url:
            parser.error("--database-url or DATABASE_URL is required")
    try:
        digest = validate_fixture(args.fixture)
        print(f"Controlled fixture verified: {SET_ID}, records={RECORD_COUNT}, SHA-256={digest}")
        if args.validate_only:
            print("Validation only: PostgreSQL not accessed")
            return 0
        expansion_id, counts = execute_merge(args.database_url, args.import_run_id)
        print(f"Catalogue production merge committed: run={args.import_run_id}, expansion={expansion_id}")
        print("Outcomes: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
        return 0
    except MergeError as error:
        print(f"Catalogue merge failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
