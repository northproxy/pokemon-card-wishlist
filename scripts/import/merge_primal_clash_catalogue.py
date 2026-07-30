"""
Script: merge_primal_clash_catalogue.py

Purpose:
    Merge one validated Primal Clash catalogue staging run into the production
    `expansions`, `expansion_source_identifiers`, and `cards` tables.

    The merge records one `import_record_outcomes` row for every staged card and
    completes the selected `import_runs` row with production merge counts.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the validated first-import
    vertical slice. It may later be replaced by a generic catalogue merge
    utility only after equivalent identity resolution, outcome recording,
    idempotency, rollback, and validation behaviour are implemented and tested.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any, Sequence

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb


EXPECTED_RUN_KIND = "catalogue"
EXPECTED_SOURCE_SYSTEM = "pokemon_tcg_data"
EXPECTED_SOURCE_ENTITY_TYPE = "card"
EXPECTED_SCOPE_TYPE = "expansion"
EXPECTED_SCOPE_REFERENCE = "pokemon_tcg_data:xy5"
EXPECTED_SOURCE_EXPANSION_ID = "xy5"
EXPECTED_RECORD_COUNT = 164
EXPECTED_SOURCE_ARTIFACT_CHECKSUM = (
    "5459b8982782a31829526e8fb7eb76cb"
    "fb18d09c092034505be77cfe9a2b5110"
)

EXPANSION_KEY = "primal_clash"
EXPANSION_NAME = "Primal Clash"
EXPANSION_SOURCE_NAME = "Primal Clash"


class CatalogueMergeError(RuntimeError):
    """Raised when the controlled catalogue merge cannot proceed safely."""


@dataclass(frozen=True)
class ValidatedRun:
    """Validated import-run metadata required by the merge."""

    import_run_id: int
    run_reference: str
    source_artifact_checksum: str
    total_source_records: int
    valid_source_records: int
    rejected_records: int


@dataclass(frozen=True)
class StagedCard:
    """One validated staging card ready for production merge."""

    staging_card_id: int
    source_record_reference: str
    source_system: str
    source_card_id: str
    source_expansion_id: str
    collector_number: str
    name: str
    rarity: str | None
    image_small_url: str | None
    image_large_url: str | None


@dataclass(frozen=True)
class CardMergeCounts:
    """Card-level merge outcome counts."""

    inserted: int
    updated: int
    unchanged: int
    reactivated: int

    @property
    def processed(self) -> int:
        """Return the total number of processed staging cards."""

        return (
            self.inserted
            + self.updated
            + self.unchanged
            + self.reactivated
        )


@dataclass(frozen=True)
class MergeResult:
    """Summary of one committed catalogue production merge."""

    import_run_id: int
    run_reference: str
    expansion_id: int
    card_counts: CardMergeCounts
    final_status: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Merge one validated Primal Clash catalogue staging run into "
            "production catalogue tables."
        )
    )
    parser.add_argument(
        "--import-run-id",
        type=int,
        required=True,
        help="Validated catalogue import_run_id to merge.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help=(
            "PostgreSQL connection URL. Defaults to the DATABASE_URL "
            "environment variable."
        ),
    )

    args = parser.parse_args(argv)

    if args.import_run_id < 1:
        parser.error("--import-run-id must be a positive integer.")

    if not args.database_url:
        parser.error(
            "--database-url is required when DATABASE_URL is not set."
        )

    return args


def load_and_lock_validated_run(
    connection: Connection[Any],
    import_run_id: int,
) -> ValidatedRun:
    """Load and lock the selected import run and validate its merge contract."""

    row = connection.execute(
        """
        SELECT
            import_run_id,
            run_reference,
            run_kind,
            source_system,
            source_entity_type,
            source_artifact_checksum,
            scope_type,
            scope_reference,
            status,
            total_source_records,
            valid_source_records,
            rejected_records,
            staging_loaded_at,
            validated_at,
            merge_started_at,
            completed_at
        FROM import_runs
        WHERE import_run_id = %s
        FOR UPDATE
        """,
        (import_run_id,),
    ).fetchone()

    if row is None:
        raise CatalogueMergeError(
            f"Import run does not exist: {import_run_id}."
        )

    (
        loaded_import_run_id,
        run_reference,
        run_kind,
        source_system,
        source_entity_type,
        source_artifact_checksum,
        scope_type,
        scope_reference,
        status,
        total_source_records,
        valid_source_records,
        rejected_records,
        staging_loaded_at,
        validated_at,
        merge_started_at,
        completed_at,
    ) = row

    expected_values = {
        "run_kind": (run_kind, EXPECTED_RUN_KIND),
        "source_system": (
            source_system,
            EXPECTED_SOURCE_SYSTEM,
        ),
        "source_entity_type": (
            source_entity_type,
            EXPECTED_SOURCE_ENTITY_TYPE,
        ),
        "scope_type": (scope_type, EXPECTED_SCOPE_TYPE),
        "scope_reference": (
            scope_reference,
            EXPECTED_SCOPE_REFERENCE,
        ),
        "status": (status, "validated"),
    }

    mismatches = [
        f"{field_name}: expected={expected!r}, actual={actual!r}"
        for field_name, (actual, expected) in expected_values.items()
        if actual != expected
    ]

    if mismatches:
        raise CatalogueMergeError(
            "Import run does not satisfy the controlled merge contract:\n- "
            + "\n- ".join(mismatches)
        )

    if source_artifact_checksum != EXPECTED_SOURCE_ARTIFACT_CHECKSUM:
        raise CatalogueMergeError(
            "Source artifact checksum does not match the validated fixture: "
            f"expected={EXPECTED_SOURCE_ARTIFACT_CHECKSUM}, "
            f"actual={source_artifact_checksum}."
        )

    if staging_loaded_at is None or validated_at is None:
        raise CatalogueMergeError(
            "Validated import run is missing staging or validation timestamps."
        )

    if merge_started_at is not None or completed_at is not None:
        raise CatalogueMergeError(
            "Validated import run already contains merge lifecycle timestamps."
        )

    if total_source_records != EXPECTED_RECORD_COUNT:
        raise CatalogueMergeError(
            "Unexpected total source record count: "
            f"expected={EXPECTED_RECORD_COUNT}, "
            f"actual={total_source_records}."
        )

    if valid_source_records != EXPECTED_RECORD_COUNT:
        raise CatalogueMergeError(
            "Unexpected valid source record count: "
            f"expected={EXPECTED_RECORD_COUNT}, "
            f"actual={valid_source_records}."
        )

    if rejected_records != 0:
        raise CatalogueMergeError(
            "Controlled production merge requires zero rejected records: "
            f"actual={rejected_records}."
        )

    return ValidatedRun(
        import_run_id=int(loaded_import_run_id),
        run_reference=str(run_reference),
        source_artifact_checksum=str(source_artifact_checksum),
        total_source_records=int(total_source_records),
        valid_source_records=int(valid_source_records),
        rejected_records=int(rejected_records),
    )


def load_validated_staging_cards(
    connection: Connection[Any],
    run: ValidatedRun,
) -> list[StagedCard]:
    """Load all valid staging cards and revalidate persisted staging state."""

    rows = connection.execute(
        """
        SELECT
            staging_card_id,
            source_record_reference,
            source_system,
            source_card_id,
            source_expansion_id,
            collector_number,
            name,
            rarity,
            image_small_url,
            image_large_url
        FROM staging_cards
        WHERE import_run_id = %s
        ORDER BY staging_card_id
        """,
        (run.import_run_id,),
    ).fetchall()

    if len(rows) != run.total_source_records:
        raise CatalogueMergeError(
            "Staging row count does not match import-run summary: "
            f"expected={run.total_source_records}, actual={len(rows)}."
        )

    invalid_state_row = connection.execute(
        """
        SELECT
            staging_card_id,
            normalization_status,
            validation_status,
            validation_completed_at
        FROM staging_cards
        WHERE import_run_id = %s
          AND (
              normalization_status <> 'normalized'
              OR validation_status <> 'valid'
              OR validation_completed_at IS NULL
          )
        ORDER BY staging_card_id
        LIMIT 1
        """,
        (run.import_run_id,),
    ).fetchone()

    if invalid_state_row is not None:
        raise CatalogueMergeError(
            "Staging contains a record that is not fully validated: "
            f"staging_card_id={invalid_state_row[0]}, "
            f"normalization_status={invalid_state_row[1]!r}, "
            f"validation_status={invalid_state_row[2]!r}."
        )

    duplicate_identity = connection.execute(
        """
        SELECT
            source_system,
            source_card_id,
            count(*)
        FROM staging_cards
        WHERE import_run_id = %s
        GROUP BY
            source_system,
            source_card_id
        HAVING count(*) > 1
        ORDER BY
            source_system,
            source_card_id
        LIMIT 1
        """,
        (run.import_run_id,),
    ).fetchone()

    if duplicate_identity is not None:
        raise CatalogueMergeError(
            "Duplicate source card identity exists in staging: "
            f"{duplicate_identity[0]}:{duplicate_identity[1]}, "
            f"count={duplicate_identity[2]}."
        )

    staged_cards: list[StagedCard] = []

    for row in rows:
        (
            staging_card_id,
            source_record_reference,
            source_system,
            source_card_id,
            source_expansion_id,
            collector_number,
            name,
            rarity,
            image_small_url,
            image_large_url,
        ) = row

        required_values = {
            "source_record_reference": source_record_reference,
            "source_system": source_system,
            "source_card_id": source_card_id,
            "source_expansion_id": source_expansion_id,
            "collector_number": collector_number,
            "name": name,
        }

        missing_fields = [
            field_name
            for field_name, value in required_values.items()
            if value is None
        ]

        if missing_fields:
            raise CatalogueMergeError(
                "Valid staging record is missing required production fields: "
                f"staging_card_id={staging_card_id}, "
                f"fields={', '.join(missing_fields)}."
            )

        if source_system != EXPECTED_SOURCE_SYSTEM:
            raise CatalogueMergeError(
                "Unexpected staging source system: "
                f"staging_card_id={staging_card_id}, "
                f"actual={source_system!r}."
            )

        if source_expansion_id != EXPECTED_SOURCE_EXPANSION_ID:
            raise CatalogueMergeError(
                "Unexpected staging source expansion ID: "
                f"staging_card_id={staging_card_id}, "
                f"actual={source_expansion_id!r}."
            )

        staged_cards.append(
            StagedCard(
                staging_card_id=int(staging_card_id),
                source_record_reference=str(source_record_reference),
                source_system=str(source_system),
                source_card_id=str(source_card_id),
                source_expansion_id=str(source_expansion_id),
                collector_number=str(collector_number),
                name=str(name),
                rarity=rarity,
                image_small_url=image_small_url,
                image_large_url=image_large_url,
            )
        )

    return staged_cards


def require_no_existing_outcomes(
    connection: Connection[Any],
    import_run_id: int,
) -> None:
    """Prevent a run from creating duplicate merge outcomes."""

    row = connection.execute(
        """
        SELECT count(*)
        FROM import_record_outcomes
        WHERE import_run_id = %s
        """,
        (import_run_id,),
    ).fetchone()

    if row is None:
        raise CatalogueMergeError(
            "Could not verify existing import-record outcomes."
        )

    existing_outcomes = int(row[0])

    if existing_outcomes != 0:
        raise CatalogueMergeError(
            "Import run already has merge outcomes: "
            f"import_run_id={import_run_id}, "
            f"outcomes={existing_outcomes}."
        )


def resolve_or_create_expansion(
    connection: Connection[Any],
) -> int:
    """Resolve the controlled expansion identity or create it idempotently."""

    source_identity_row = connection.execute(
        """
        SELECT
            esi.expansion_id,
            e.expansion_key,
            e.name
        FROM expansion_source_identifiers AS esi
        JOIN expansions AS e
            ON e.expansion_id = esi.expansion_id
        WHERE esi.source_system = %s
          AND esi.source_expansion_id = %s
        FOR UPDATE OF esi, e
        """,
        (
            EXPECTED_SOURCE_SYSTEM,
            EXPECTED_SOURCE_EXPANSION_ID,
        ),
    ).fetchone()

    if source_identity_row is not None:
        expansion_id, expansion_key, expansion_name = source_identity_row

        if expansion_key != EXPANSION_KEY:
            raise CatalogueMergeError(
                "Source expansion identity points to an unexpected "
                "internal expansion key: "
                f"expected={EXPANSION_KEY!r}, "
                f"actual={expansion_key!r}."
            )

        if expansion_name != EXPANSION_NAME:
            raise CatalogueMergeError(
                "Source expansion identity points to an expansion with an "
                "unexpected name: "
                f"expected={EXPANSION_NAME!r}, "
                f"actual={expansion_name!r}."
            )

        return int(expansion_id)

    expansion_row = connection.execute(
        """
        SELECT
            expansion_id,
            name
        FROM expansions
        WHERE expansion_key = %s
        FOR UPDATE
        """,
        (EXPANSION_KEY,),
    ).fetchone()

    if expansion_row is None:
        created_row = connection.execute(
            """
            INSERT INTO expansions (
                expansion_key,
                name
            )
            VALUES (%s, %s)
            RETURNING expansion_id
            """,
            (
                EXPANSION_KEY,
                EXPANSION_NAME,
            ),
        ).fetchone()

        if created_row is None:
            raise CatalogueMergeError(
                "PostgreSQL did not return the created expansion ID."
            )

        expansion_id = int(created_row[0])
    else:
        expansion_id, existing_name = expansion_row

        if existing_name != EXPANSION_NAME:
            raise CatalogueMergeError(
                "Existing expansion key has an unexpected name: "
                f"expansion_key={EXPANSION_KEY!r}, "
                f"expected={EXPANSION_NAME!r}, "
                f"actual={existing_name!r}."
            )

        expansion_id = int(expansion_id)

    connection.execute(
        """
        INSERT INTO expansion_source_identifiers (
            expansion_id,
            source_system,
            source_expansion_id,
            source_name
        )
        VALUES (%s, %s, %s, %s)
        """,
        (
            expansion_id,
            EXPECTED_SOURCE_SYSTEM,
            EXPECTED_SOURCE_EXPANSION_ID,
            EXPANSION_SOURCE_NAME,
        ),
    )

    return expansion_id


def mark_merge_started(
    connection: Connection[Any],
    import_run_id: int,
) -> None:
    """Advance the selected import run to merge_started."""

    result = connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'merge_started',
            merge_started_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE import_run_id = %s
          AND status = 'validated'
          AND merge_started_at IS NULL
          AND completed_at IS NULL
        """,
        (import_run_id,),
    )

    if result.rowcount != 1:
        raise CatalogueMergeError(
            "Import run could not transition from validated to merge_started."
        )


def record_card_outcome(
    connection: Connection[Any],
    import_run_id: int,
    card: StagedCard,
    production_card_id: int,
    outcome_type: str,
    change_summary: dict[str, Any] | None = None,
) -> None:
    """Record one card-level production merge outcome."""

    connection.execute(
        """
        INSERT INTO import_record_outcomes (
            import_run_id,
            entity_type,
            source_system,
            source_entity_id,
            source_record_reference,
            production_entity_id,
            outcome_type,
            change_summary
        )
        VALUES (
            %s,
            'card',
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            import_run_id,
            card.source_system,
            card.source_card_id,
            card.source_record_reference,
            production_card_id,
            outcome_type,
            (
                Jsonb(change_summary)
                if change_summary is not None
                else None
            ),
        ),
    )


def merge_one_card(
    connection: Connection[Any],
    import_run_id: int,
    expansion_id: int,
    card: StagedCard,
) -> str:
    """Insert, update, reactivate, or retain one production card."""

    existing_row = connection.execute(
        """
        SELECT
            card_id,
            expansion_id,
            collector_number,
            name,
            rarity,
            image_small_url,
            image_large_url,
            is_active
        FROM cards
        WHERE source_system = %s
          AND source_card_id = %s
        FOR UPDATE
        """,
        (
            card.source_system,
            card.source_card_id,
        ),
    ).fetchone()

    if existing_row is None:
        inserted_row = connection.execute(
            """
            INSERT INTO cards (
                expansion_id,
                source_system,
                source_card_id,
                collector_number,
                name,
                rarity,
                image_small_url,
                image_large_url
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING card_id
            """,
            (
                expansion_id,
                card.source_system,
                card.source_card_id,
                card.collector_number,
                card.name,
                card.rarity,
                card.image_small_url,
                card.image_large_url,
            ),
        ).fetchone()

        if inserted_row is None:
            raise CatalogueMergeError(
                "PostgreSQL did not return the inserted card ID: "
                f"{card.source_system}:{card.source_card_id}."
            )

        production_card_id = int(inserted_row[0])

        record_card_outcome(
            connection=connection,
            import_run_id=import_run_id,
            card=card,
            production_card_id=production_card_id,
            outcome_type="inserted",
            change_summary={
                "inserted_fields": [
                    "expansion_id",
                    "source_system",
                    "source_card_id",
                    "collector_number",
                    "name",
                    "rarity",
                    "image_small_url",
                    "image_large_url",
                ]
            },
        )

        return "inserted"

    (
        production_card_id,
        existing_expansion_id,
        existing_collector_number,
        existing_name,
        existing_rarity,
        existing_image_small_url,
        existing_image_large_url,
        existing_is_active,
    ) = existing_row

    if int(existing_expansion_id) != expansion_id:
        raise CatalogueMergeError(
            "Existing card identity is linked to an unexpected expansion: "
            f"{card.source_system}:{card.source_card_id}, "
            f"expected_expansion_id={expansion_id}, "
            f"actual_expansion_id={existing_expansion_id}."
        )

    current_values = {
        "collector_number": existing_collector_number,
        "name": existing_name,
        "rarity": existing_rarity,
        "image_small_url": existing_image_small_url,
        "image_large_url": existing_image_large_url,
    }
    incoming_values = {
        "collector_number": card.collector_number,
        "name": card.name,
        "rarity": card.rarity,
        "image_small_url": card.image_small_url,
        "image_large_url": card.image_large_url,
    }

    changed_fields = [
        field_name
        for field_name, incoming_value in incoming_values.items()
        if current_values[field_name] != incoming_value
    ]

    if not existing_is_active:
        connection.execute(
            """
            UPDATE cards
            SET
                collector_number = %s,
                name = %s,
                rarity = %s,
                image_small_url = %s,
                image_large_url = %s,
                is_active = true,
                retired_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE card_id = %s
            """,
            (
                card.collector_number,
                card.name,
                card.rarity,
                card.image_small_url,
                card.image_large_url,
                production_card_id,
            ),
        )

        record_card_outcome(
            connection=connection,
            import_run_id=import_run_id,
            card=card,
            production_card_id=int(production_card_id),
            outcome_type="reactivated",
            change_summary={
                "reactivated": True,
                "changed_fields": changed_fields,
            },
        )

        return "reactivated"

    if changed_fields:
        previous_values = {
            field_name: current_values[field_name]
            for field_name in changed_fields
        }
        new_values = {
            field_name: incoming_values[field_name]
            for field_name in changed_fields
        }

        connection.execute(
            """
            UPDATE cards
            SET
                collector_number = %s,
                name = %s,
                rarity = %s,
                image_small_url = %s,
                image_large_url = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE card_id = %s
            """,
            (
                card.collector_number,
                card.name,
                card.rarity,
                card.image_small_url,
                card.image_large_url,
                production_card_id,
            ),
        )

        record_card_outcome(
            connection=connection,
            import_run_id=import_run_id,
            card=card,
            production_card_id=int(production_card_id),
            outcome_type="updated",
            change_summary={
                "changed_fields": changed_fields,
                "previous_values": previous_values,
                "new_values": new_values,
            },
        )

        return "updated"

    record_card_outcome(
        connection=connection,
        import_run_id=import_run_id,
        card=card,
        production_card_id=int(production_card_id),
        outcome_type="unchanged",
    )

    return "unchanged"


def merge_cards(
    connection: Connection[Any],
    import_run_id: int,
    expansion_id: int,
    cards: list[StagedCard],
) -> CardMergeCounts:
    """Merge every validated staging card and count outcomes."""

    counters = {
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "reactivated": 0,
    }

    for card in cards:
        outcome = merge_one_card(
            connection=connection,
            import_run_id=import_run_id,
            expansion_id=expansion_id,
            card=card,
        )
        counters[outcome] += 1

    return CardMergeCounts(
        inserted=counters["inserted"],
        updated=counters["updated"],
        unchanged=counters["unchanged"],
        reactivated=counters["reactivated"],
    )


def validate_merge_results(
    connection: Connection[Any],
    run: ValidatedRun,
    expansion_id: int,
    counts: CardMergeCounts,
) -> None:
    """Validate production and outcome counts before committing."""

    if counts.processed != run.valid_source_records:
        raise CatalogueMergeError(
            "Card merge counts do not reconcile with valid staging records: "
            f"processed={counts.processed}, "
            f"valid_source_records={run.valid_source_records}."
        )

    production_card_count_row = connection.execute(
        """
        SELECT count(*)
        FROM cards
        WHERE expansion_id = %s
          AND source_system = %s
          AND is_active = true
        """,
        (
            expansion_id,
            EXPECTED_SOURCE_SYSTEM,
        ),
    ).fetchone()

    if production_card_count_row is None:
        raise CatalogueMergeError(
            "Could not validate production card count."
        )

    production_card_count = int(production_card_count_row[0])

    if production_card_count != EXPECTED_RECORD_COUNT:
        raise CatalogueMergeError(
            "Unexpected active production card count for Primal Clash: "
            f"expected={EXPECTED_RECORD_COUNT}, "
            f"actual={production_card_count}."
        )

    outcome_count_row = connection.execute(
        """
        SELECT count(*)
        FROM import_record_outcomes
        WHERE import_run_id = %s
          AND entity_type = 'card'
        """,
        (run.import_run_id,),
    ).fetchone()

    if outcome_count_row is None:
        raise CatalogueMergeError(
            "Could not validate import-record outcome count."
        )

    outcome_count = int(outcome_count_row[0])

    if outcome_count != run.valid_source_records:
        raise CatalogueMergeError(
            "Card outcome count does not match valid source records: "
            f"expected={run.valid_source_records}, "
            f"actual={outcome_count}."
        )

    duplicate_production_identity = connection.execute(
        """
        SELECT
            source_system,
            source_card_id,
            count(*)
        FROM cards
        GROUP BY
            source_system,
            source_card_id
        HAVING count(*) > 1
        LIMIT 1
        """
    ).fetchone()

    if duplicate_production_identity is not None:
        raise CatalogueMergeError(
            "Duplicate production card identity detected: "
            f"{duplicate_production_identity[0]}:"
            f"{duplicate_production_identity[1]}, "
            f"count={duplicate_production_identity[2]}."
        )


def mark_succeeded(
    connection: Connection[Any],
    run: ValidatedRun,
    counts: CardMergeCounts,
) -> None:
    """Complete the import run after successful production validation."""

    result = connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'succeeded',
            completed_at = CURRENT_TIMESTAMP,
            inserted_records = %s,
            updated_records = %s,
            unchanged_records = %s,
            missing_records = 0,
            retired_records = 0,
            failure_code = NULL,
            failure_detail = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE import_run_id = %s
          AND status = 'merge_started'
          AND merge_started_at IS NOT NULL
          AND completed_at IS NULL
        """,
        (
            counts.inserted,
            counts.updated + counts.reactivated,
            counts.unchanged,
            run.import_run_id,
        ),
    )

    if result.rowcount != 1:
        raise CatalogueMergeError(
            "Import run could not transition from merge_started to succeeded."
        )


def execute_merge(
    database_url: str,
    import_run_id: int,
) -> MergeResult:
    """Execute and commit one controlled production catalogue merge."""

    try:
        with psycopg.connect(database_url) as connection:
            run = load_and_lock_validated_run(
                connection=connection,
                import_run_id=import_run_id,
            )

            cards = load_validated_staging_cards(
                connection=connection,
                run=run,
            )

            require_no_existing_outcomes(
                connection=connection,
                import_run_id=run.import_run_id,
            )

            expansion_id = resolve_or_create_expansion(
                connection=connection,
            )

            mark_merge_started(
                connection=connection,
                import_run_id=run.import_run_id,
            )

            counts = merge_cards(
                connection=connection,
                import_run_id=run.import_run_id,
                expansion_id=expansion_id,
                cards=cards,
            )

            validate_merge_results(
                connection=connection,
                run=run,
                expansion_id=expansion_id,
                counts=counts,
            )

            mark_succeeded(
                connection=connection,
                run=run,
                counts=counts,
            )

        return MergeResult(
            import_run_id=run.import_run_id,
            run_reference=run.run_reference,
            expansion_id=expansion_id,
            card_counts=counts,
            final_status="succeeded",
        )

    except CatalogueMergeError:
        raise
    except psycopg.Error as exc:
        raise CatalogueMergeError(
            f"PostgreSQL catalogue merge transaction failed: {exc}"
        ) from exc


def print_merge_summary(result: MergeResult) -> None:
    """Print the committed production merge result."""

    print("Primal Clash catalogue production merge committed")
    print(f"Import run ID: {result.import_run_id}")
    print(f"Run reference: {result.run_reference}")
    print(f"Expansion ID: {result.expansion_id}")
    print(f"Inserted cards: {result.card_counts.inserted}")
    print(f"Updated cards: {result.card_counts.updated}")
    print(f"Reactivated cards: {result.card_counts.reactivated}")
    print(f"Unchanged cards: {result.card_counts.unchanged}")
    print(f"Processed cards: {result.card_counts.processed}")
    print(f"Final status: {result.final_status}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the controlled production catalogue merge."""

    args = parse_args(argv)

    try:
        result = execute_merge(
            database_url=args.database_url,
            import_run_id=args.import_run_id,
        )
    except CatalogueMergeError as exc:
        print(f"Catalogue merge failed: {exc}", file=sys.stderr)
        return 1

    print_merge_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())