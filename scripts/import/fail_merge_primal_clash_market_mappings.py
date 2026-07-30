"""
Script: fail_merge_primal_clash_market_mappings.py

Purpose:
    Intentionally fail one controlled Primal Clash Cardmarket mapping
    production merge transaction after creating a partial mapping state, then
    verify that all lifecycle, review, production mapping, and audit writes are
    rolled back completely.

Lifecycle:
    Permanent project validation utility.

Removal:
    Keep this script while the Cardmarket mapping merge remains part of the
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
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import import_primal_clash_market_mappings as mapping_import


class IntentionalMergeRollbackError(RuntimeError):
    """Raised deliberately after controlled production writes."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Intentionally fail a Primal Clash Cardmarket mapping merge "
            "transaction and verify complete rollback."
        )
    )
    parser.add_argument(
        "--import-run-id",
        type=int,
        required=True,
        help="Validated Cardmarket mapping import run used for rollback testing.",
    )
    return parser.parse_args()


def fetch_one_dict(
    connection: Connection[Any],
    query: str,
    parameters: dict[str, Any],
) -> dict[str, Any] | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, parameters)
        row = cursor.fetchone()
    return dict(row) if row is not None else None


def fetch_scalar(
    connection: Connection[Any],
    query: str,
    parameters: dict[str, Any],
) -> int:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise RuntimeError("Verification query returned no row.")
    return int(row[0])


def load_and_validate_import_run(
    connection: Connection[Any],
    import_run_id: int,
    *,
    for_update: bool,
) -> dict[str, Any]:
    lock_clause = "FOR UPDATE" if for_update else ""
    run = fetch_one_dict(
        connection,
        f"""
        SELECT *
        FROM import_runs
        WHERE import_run_id = %(import_run_id)s
        {lock_clause}
        """,
        {"import_run_id": import_run_id},
    )
    if run is None:
        raise mapping_import.ImportValidationError(
            f"Import run {import_run_id} does not exist."
        )

    expected_values = {
        "run_kind": mapping_import.RUN_KIND,
        "source_system": mapping_import.SOURCE_SYSTEM,
        "source_entity_type": mapping_import.SOURCE_ENTITY_TYPE,
        "scope_type": mapping_import.SCOPE_TYPE,
        "scope_reference": (
            f"{mapping_import.SOURCE_SYSTEM}:"
            f"{mapping_import.EXPECTED_EXPANSION_ID}"
        ),
        "status": "validated",
        "total_source_records": mapping_import.EXPECTED_RECORD_COUNT,
        "valid_source_records": mapping_import.EXPECTED_RECORD_COUNT,
        "rejected_records": 0,
    }

    mismatches = [
        f"{column}={run.get(column)!r}, expected {expected!r}"
        for column, expected in expected_values.items()
        if run.get(column) != expected
    ]
    if mismatches:
        raise mapping_import.ImportValidationError(
            "Import run is not eligible for rollback validation: "
            + "; ".join(mismatches)
            + "."
        )

    if run.get("merge_started_at") is not None or run.get("completed_at") is not None:
        raise mapping_import.ImportValidationError(
            "Import run already contains merge lifecycle timestamps."
        )

    return run


def load_baseline_counts(
    connection: Connection[Any],
    import_run_id: int,
) -> dict[str, int]:
    return {
        "mapping_cases": fetch_scalar(
            connection,
            "SELECT COUNT(*) FROM card_market_mapping_cases",
            {},
        ),
        "observations": fetch_scalar(
            connection,
            "SELECT COUNT(*) FROM mapping_case_observations",
            {},
        ),
        "candidates": fetch_scalar(
            connection,
            "SELECT COUNT(*) FROM mapping_candidates",
            {},
        ),
        "status_history": fetch_scalar(
            connection,
            "SELECT COUNT(*) FROM mapping_status_history",
            {},
        ),
        "production_mappings": fetch_scalar(
            connection,
            "SELECT COUNT(*) FROM card_market_product_mappings",
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


def load_first_candidate(
    connection: Connection[Any],
    import_run_id: int,
) -> dict[str, Any]:
    row = fetch_one_dict(
        connection,
        """
        SELECT
            source_record_reference,
            market_source_system,
            source_product_id,
            catalogue_source_system,
            source_card_id,
            evidence_reference,
            evidence_payload
        FROM staging_market_mappings
        WHERE import_run_id = %(import_run_id)s
          AND proposed_status = 'candidate'
        ORDER BY source_product_id
        LIMIT 1
        FOR UPDATE
        """,
        {"import_run_id": import_run_id},
    )
    if row is None:
        raise mapping_import.ImportValidationError(
            "No candidate staging row was found."
        )
    return row


def resolve_candidate_identities(
    connection: Connection[Any],
    row: dict[str, Any],
) -> tuple[int, int]:
    market_product = fetch_one_dict(
        connection,
        """
        SELECT market_product_id, is_active
        FROM market_products
        WHERE source_system = %(source_system)s
          AND source_product_id = %(source_product_id)s
        FOR UPDATE
        """,
        {
            "source_system": row["market_source_system"],
            "source_product_id": row["source_product_id"],
        },
    )
    if market_product is None or market_product["is_active"] is not True:
        raise mapping_import.ImportValidationError(
            "Rollback candidate market product is missing or inactive."
        )

    card = fetch_one_dict(
        connection,
        """
        SELECT card_id, is_active
        FROM cards
        WHERE source_system = %(source_system)s
          AND source_card_id = %(source_card_id)s
        FOR UPDATE
        """,
        {
            "source_system": row["catalogue_source_system"],
            "source_card_id": row["source_card_id"],
        },
    )
    if card is None or card["is_active"] is not True:
        raise mapping_import.ImportValidationError(
            "Rollback candidate canonical card is missing or inactive."
        )

    return int(market_product["market_product_id"]), int(card["card_id"])


def mark_merge_started(
    connection: Connection[Any],
    import_run_id: int,
) -> None:
    result = connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'merge_started',
            merge_started_at = CURRENT_TIMESTAMP
        WHERE import_run_id = %(import_run_id)s
          AND status = 'validated'
        """,
        {"import_run_id": import_run_id},
    )
    if result.rowcount != 1:
        raise mapping_import.ImportValidationError(
            "Import run could not transition to merge_started."
        )


def create_partial_mapping_state(
    connection: Connection[Any],
    *,
    import_run_id: int,
    row: dict[str, Any],
    market_product_id: int,
    card_id: int,
) -> dict[str, int]:
    case_row = connection.execute(
        """
        INSERT INTO card_market_mapping_cases (
            market_product_id,
            current_status,
            current_confirmation_scope,
            current_card_id,
            current_card_edition_id,
            current_card_variant_id,
            status_source_observation_id,
            first_observed_at,
            last_observed_at,
            resolved_at
        )
        VALUES (
            %(market_product_id)s,
            'confirmed',
            'card',
            %(card_id)s,
            NULL,
            NULL,
            NULL,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        RETURNING mapping_case_id
        """,
        {
            "market_product_id": market_product_id,
            "card_id": card_id,
        },
    ).fetchone()
    if case_row is None:
        raise RuntimeError("Database did not return mapping_case_id.")
    mapping_case_id = int(case_row[0])

    observation_row = connection.execute(
        """
        INSERT INTO mapping_case_observations (
            mapping_case_id,
            import_run_id,
            source_record_reference,
            observation_status,
            proposed_confirmation_scope,
            proposed_card_id,
            proposed_card_edition_id,
            proposed_card_variant_id,
            confirmation_method,
            evidence_level,
            evidence_reference,
            evidence_payload,
            observation_result,
            result_reason_code,
            result_reason_detail
        )
        VALUES (
            %(mapping_case_id)s,
            %(import_run_id)s,
            %(source_record_reference)s,
            'confirmed',
            'card',
            %(card_id)s,
            NULL,
            NULL,
            'direct_source_identifier',
            'direct',
            %(evidence_reference)s,
            %(evidence_payload)s,
            'accepted_transition',
            NULL,
            NULL
        )
        RETURNING mapping_case_observation_id
        """,
        {
            "mapping_case_id": mapping_case_id,
            "import_run_id": import_run_id,
            "source_record_reference": row["source_record_reference"],
            "card_id": card_id,
            "evidence_reference": row["evidence_reference"],
            "evidence_payload": Jsonb(row["evidence_payload"]),
        },
    ).fetchone()
    if observation_row is None:
        raise RuntimeError(
            "Database did not return mapping_case_observation_id."
        )
    observation_id = int(observation_row[0])

    connection.execute(
        """
        UPDATE card_market_mapping_cases
        SET
            status_source_observation_id = %(observation_id)s,
            updated_at = CURRENT_TIMESTAMP
        WHERE mapping_case_id = %(mapping_case_id)s
        """,
        {
            "observation_id": observation_id,
            "mapping_case_id": mapping_case_id,
        },
    )

    candidate_row = connection.execute(
        """
        INSERT INTO mapping_candidates (
            mapping_case_id,
            mapping_case_observation_id,
            candidate_scope,
            candidate_card_id,
            candidate_card_edition_id,
            candidate_card_variant_id,
            candidate_rank,
            candidate_score,
            generation_method,
            evidence_level,
            evidence_reference,
            evidence_payload,
            candidate_state,
            state_reason_code,
            state_changed_at
        )
        VALUES (
            %(mapping_case_id)s,
            %(observation_id)s,
            'card',
            %(card_id)s,
            NULL,
            NULL,
            1,
            NULL,
            'direct_identifier_candidate',
            'direct',
            %(evidence_reference)s,
            %(evidence_payload)s,
            'selected',
            NULL,
            CURRENT_TIMESTAMP
        )
        RETURNING mapping_candidate_id
        """,
        {
            "mapping_case_id": mapping_case_id,
            "observation_id": observation_id,
            "card_id": card_id,
            "evidence_reference": row["evidence_reference"],
            "evidence_payload": Jsonb(row["evidence_payload"]),
        },
    ).fetchone()
    if candidate_row is None:
        raise RuntimeError("Database did not return mapping_candidate_id.")

    history_row = connection.execute(
        """
        INSERT INTO mapping_status_history (
            mapping_case_id,
            mapping_case_observation_id,
            previous_status,
            new_status,
            previous_confirmation_scope,
            new_confirmation_scope,
            previous_card_id,
            new_card_id,
            previous_card_edition_id,
            new_card_edition_id,
            previous_card_variant_id,
            new_card_variant_id,
            transition_reason_code,
            transition_reason_detail
        )
        VALUES (
            %(mapping_case_id)s,
            %(observation_id)s,
            NULL,
            'confirmed',
            NULL,
            'card',
            NULL,
            %(card_id)s,
            NULL,
            NULL,
            NULL,
            NULL,
            'controlled_rollback_probe',
            'Intentional partial production merge used to validate rollback.'
        )
        RETURNING mapping_status_history_id
        """,
        {
            "mapping_case_id": mapping_case_id,
            "observation_id": observation_id,
            "card_id": card_id,
        },
    ).fetchone()
    if history_row is None:
        raise RuntimeError(
            "Database did not return mapping_status_history_id."
        )

    production_mapping_row = connection.execute(
        """
        INSERT INTO card_market_product_mappings (
            mapping_case_id,
            market_product_id,
            card_id,
            card_edition_id,
            card_variant_id,
            confirmation_scope,
            confirmation_method,
            evidence_level,
            evidence_reference,
            is_active,
            superseded_at
        )
        VALUES (
            %(mapping_case_id)s,
            %(market_product_id)s,
            %(card_id)s,
            NULL,
            NULL,
            'card',
            'direct_source_identifier',
            'direct',
            %(evidence_reference)s,
            TRUE,
            NULL
        )
        RETURNING card_market_product_mapping_id
        """,
        {
            "mapping_case_id": mapping_case_id,
            "market_product_id": market_product_id,
            "card_id": card_id,
            "evidence_reference": row["evidence_reference"],
        },
    ).fetchone()
    if production_mapping_row is None:
        raise RuntimeError(
            "Database did not return card_market_product_mapping_id."
        )
    production_mapping_id = int(production_mapping_row[0])

    outcome_row = connection.execute(
        """
        INSERT INTO import_record_outcomes (
            import_run_id,
            entity_type,
            source_system,
            source_entity_id,
            source_record_reference,
            production_entity_id,
            outcome_type,
            reason_code,
            reason_detail,
            change_summary
        )
        VALUES (
            %(import_run_id)s,
            'card_market_product_mapping',
            %(source_system)s,
            %(source_entity_id)s,
            %(source_record_reference)s,
            %(production_entity_id)s,
            'inserted',
            NULL,
            NULL,
            NULL
        )
        RETURNING import_record_outcome_id
        """,
        {
            "import_run_id": import_run_id,
            "source_system": row["market_source_system"],
            "source_entity_id": row["source_product_id"],
            "source_record_reference": row["source_record_reference"],
            "production_entity_id": production_mapping_id,
        },
    ).fetchone()
    if outcome_row is None:
        raise RuntimeError("Database did not return import_record_outcome_id.")

    return {
        "mapping_case_id": mapping_case_id,
        "mapping_case_observation_id": observation_id,
        "mapping_candidate_id": int(candidate_row[0]),
        "mapping_status_history_id": int(history_row[0]),
        "card_market_product_mapping_id": production_mapping_id,
        "import_record_outcome_id": int(outcome_row[0]),
    }


def verify_partial_state(
    connection: Connection[Any],
    *,
    import_run_id: int,
    baseline: dict[str, int],
) -> None:
    current = load_baseline_counts(connection, import_run_id)
    expected = {
        "mapping_cases": baseline["mapping_cases"] + 1,
        "observations": baseline["observations"] + 1,
        "candidates": baseline["candidates"] + 1,
        "status_history": baseline["status_history"] + 1,
        "production_mappings": baseline["production_mappings"] + 1,
        "run_outcomes": baseline["run_outcomes"] + 1,
    }
    if current != expected:
        raise mapping_import.ImportValidationError(
            f"Partial merge state is {current}, expected {expected}."
        )


def verify_complete_rollback(
    database_url: str,
    *,
    import_run_id: int,
    baseline: dict[str, int],
) -> dict[str, int]:
    with psycopg.connect(database_url) as connection:
        run = load_and_validate_import_run(
            connection,
            import_run_id,
            for_update=False,
        )
        final_counts = load_baseline_counts(connection, import_run_id)

    if final_counts != baseline:
        raise mapping_import.ImportValidationError(
            f"Rollback counts are {final_counts}, expected {baseline}."
        )
    if run["status"] != "validated":
        raise mapping_import.ImportValidationError(
            f"Import run status survived as {run['status']!r}."
        )
    if run["merge_started_at"] is not None or run["completed_at"] is not None:
        raise mapping_import.ImportValidationError(
            "Import run merge timestamps survived rollback."
        )

    return final_counts


def main() -> int:
    args = parse_args()

    if args.import_run_id < 1:
        raise mapping_import.ImportValidationError(
            "--import-run-id must be a positive integer."
        )

    database_url = mapping_import.get_database_url()
    created_ids: dict[str, int] | None = None

    with psycopg.connect(database_url) as connection:
        load_and_validate_import_run(
            connection,
            args.import_run_id,
            for_update=False,
        )
        baseline = load_baseline_counts(connection, args.import_run_id)

    try:
        with psycopg.connect(database_url) as connection:
            with connection.transaction():
                run = load_and_validate_import_run(
                    connection,
                    args.import_run_id,
                    for_update=True,
                )
                row = load_first_candidate(connection, args.import_run_id)
                market_product_id, card_id = resolve_candidate_identities(
                    connection,
                    row,
                )
                mark_merge_started(connection, args.import_run_id)
                created_ids = create_partial_mapping_state(
                    connection,
                    import_run_id=args.import_run_id,
                    row=row,
                    market_product_id=market_product_id,
                    card_id=card_id,
                )
                verify_partial_state(
                    connection,
                    import_run_id=args.import_run_id,
                    baseline=baseline,
                )

                raise IntentionalMergeRollbackError(
                    "Intentional rollback after one complete mapping chain."
                )

    except IntentionalMergeRollbackError as exc:
        print(f"Expected failure triggered: {exc}")

    if created_ids is None:
        raise RuntimeError(
            "Intentional failure occurred before partial mapping state "
            "was created."
        )

    final_counts = verify_complete_rollback(
        database_url,
        import_run_id=args.import_run_id,
        baseline=baseline,
    )

    print("Production merge transactional rollback validation passed")
    print(f"Import run ID: {args.import_run_id}")
    print(f"Run reference: {run['run_reference']}")
    print("Attempted mapping chains: 1")
    print(f"Attempted mapping case ID: {created_ids['mapping_case_id']}")
    print(
        "Attempted observation ID: "
        f"{created_ids['mapping_case_observation_id']}"
    )
    print(
        "Attempted production mapping ID: "
        f"{created_ids['card_market_product_mapping_id']}"
    )
    print(f"Surviving mapping cases: {final_counts['mapping_cases']}")
    print(f"Surviving observations: {final_counts['observations']}")
    print(f"Surviving candidates: {final_counts['candidates']}")
    print(f"Surviving status history rows: {final_counts['status_history']}")
    print(
        "Surviving production mappings: "
        f"{final_counts['production_mappings']}"
    )
    print(f"Surviving run outcomes: {final_counts['run_outcomes']}")
    print("Final import run status: validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (mapping_import.ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
