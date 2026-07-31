"""
Script: merge_primal_clash_market_mappings.py

Purpose:
    Merge one validated Primal Clash Cardmarket mapping staging run into the
    mapping review and production mapping tables. The merge creates or validates
    mapping cases, records one observation per eligible staged source record,
    preserves candidate and status-history evidence, creates active production
    mappings only for confirmed canonical-card mappings, records one audit
    outcome per staged source record, reconciles all counts, and commits the
    complete merge in one PostgreSQL transaction.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the validated vertical slice.
    It may be replaced only by a generalized market-mapping merge utility that
    preserves equivalent identity, review-history, exclusion, audit,
    idempotency, and rollback guarantees.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import import_primal_clash_market_mappings as mapping_import


CONFIRMATION_SCOPE = "card"
CONFIRMATION_METHOD = "direct_source_identifier"
DIRECT_EVIDENCE_LEVEL = "direct"
DERIVED_EVIDENCE_LEVEL = "derived"
CANDIDATE_GENERATION_METHOD = "direct_identifier_candidate"

ONLINE_CODE_CARD_REASON_CODE = "online_code_card_out_of_scope"
OVERSIZED_CARD_REASON_CODE = "oversized_card_out_of_scope"
UNMATCHED_DUPLICATE_REASON_CODE = "unmatched_duplicate_candidate"

INITIAL_TRANSITION_REASON_CODE = "controlled_fixture_initial_state"

ONLINE_CODE_CARD_PRODUCT_IDS = frozenset(
    {
        "300914",
        "300919",
        "300971",
        "300972",
    }
)

OVERSIZED_PRODUCT_IDS = frozenset(
    {
        "363664",
        "363665",
    }
)


@dataclass
class MergeCounts:
    mapping_inserted: int = 0
    mapping_unchanged: int = 0
    skipped: int = 0
    cases_inserted: int = 0
    observations_inserted: int = 0
    candidates_inserted: int = 0
    status_transitions_inserted: int = 0

    @property
    def production_processed(self) -> int:
        return self.mapping_inserted + self.mapping_unchanged

    @property
    def total_outcomes(self) -> int:
        return self.production_processed + self.skipped


@dataclass(frozen=True)
class DesiredCaseState:
    status: str
    confirmation_scope: str | None
    card_id: int | None
    card_edition_id: int | None
    card_variant_id: int | None
    confirmation_method: str | None
    evidence_level: str
    reason_code: str | None
    reason_detail: str | None

    @property
    def is_resolved(self) -> bool:
        return self.status in {
            "confirmed",
            "excluded",
            "unmatched_duplicate_candidate",
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge one validated Primal Clash Cardmarket mapping staging run "
            "into mapping review and production mapping tables."
        )
    )
    parser.add_argument(
        "--import-run-id",
        type=int,
        required=True,
        help="Validated Cardmarket mapping import run to merge.",
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
        raise RuntimeError("Validation query returned no row.")
    return int(row[0])


def lock_and_validate_import_run(
    connection: Connection[Any],
    import_run_id: int,
) -> dict[str, Any]:
    run = fetch_one_dict(
        connection,
        """
        SELECT *
        FROM import_runs
        WHERE import_run_id = %(import_run_id)s
        FOR UPDATE
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
            "Import run is not eligible for this controlled merge: "
            + "; ".join(mismatches)
            + "."
        )

    if run.get("merge_started_at") is not None or run.get("completed_at") is not None:
        raise mapping_import.ImportValidationError(
            "Import run already contains merge lifecycle timestamps."
        )

    existing_outcomes = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_record_outcomes
        WHERE import_run_id = %(import_run_id)s
        """,
        {"import_run_id": import_run_id},
    )
    if existing_outcomes != 0:
        raise mapping_import.ImportValidationError(
            f"Import run already has {existing_outcomes} record outcomes."
        )

    return run


def load_and_validate_staging_rows(
    connection: Connection[Any],
    import_run_id: int,
) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
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
            FROM staging_market_mappings
            WHERE import_run_id = %(import_run_id)s
            ORDER BY source_product_id
            FOR UPDATE
            """,
            {"import_run_id": import_run_id},
        )
        rows = [dict(row) for row in cursor.fetchall()]

    if len(rows) != mapping_import.EXPECTED_RECORD_COUNT:
        raise mapping_import.ImportValidationError(
            f"Expected {mapping_import.EXPECTED_RECORD_COUNT} staging rows, "
            f"found {len(rows)}."
        )

    product_ids: set[str] = set()
    references: set[str] = set()
    status_counts = {
        "candidate": 0,
        "excluded": 0,
        "unmatched_duplicate_candidate": 0,
    }
    candidate_with_edition_code = 0

    for row in rows:
        product_id = row["source_product_id"]
        reference = row["source_record_reference"]
        status = row["proposed_status"]

        if (
            row["market_source_system"] != mapping_import.SOURCE_SYSTEM
            or not product_id
            or not reference
            or status not in mapping_import.ALLOWED_MAPPING_STATUSES
            or row["evidence_reference"] is None
            or row["evidence_payload"] is None
            or row["raw_payload"] is None
            or not row["record_checksum"]
            or row["normalization_status"] != "normalized"
            or row["validation_status"] != "valid"
            or row["validation_completed_at"] is None
            or row["confirmation_scope"] is not None
            or row["confirmation_method"] is not None
            or row["evidence_level"] is not None
        ):
            raise mapping_import.ImportValidationError(
                "Staging mapping row is incomplete or not valid: "
                f"{reference!r}."
            )

        if product_id in product_ids:
            raise mapping_import.ImportValidationError(
                f"Duplicate staged source_product_id: {product_id}."
            )
        if reference in references:
            raise mapping_import.ImportValidationError(
                f"Duplicate staged source_record_reference: {reference}."
            )
        product_ids.add(product_id)
        references.add(reference)

        if status == "candidate":
            if (
                row["catalogue_source_system"]
                != mapping_import.CATALOGUE_SOURCE_SYSTEM
                or not row["source_card_id"]
            ):
                raise mapping_import.ImportValidationError(
                    f"Candidate row {reference!r} has no canonical-card identity."
                )
            if row["source_edition_code"] is not None:
                candidate_with_edition_code += 1
        elif (
            row["catalogue_source_system"] is not None
            or row["source_card_id"] is not None
        ):
            raise mapping_import.ImportValidationError(
                f"Non-candidate row {reference!r} unexpectedly has a card target."
            )

        status_counts[status] += 1

    expected_status_counts = {
        "candidate": mapping_import.EXPECTED_CANDIDATE_COUNT,
        "excluded": mapping_import.EXPECTED_EXCLUDED_COUNT,
        "unmatched_duplicate_candidate": (
            mapping_import.EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT
        ),
    }
    if status_counts != expected_status_counts:
        raise mapping_import.ImportValidationError(
            f"Staging status counts are {status_counts}, "
            f"expected {expected_status_counts}."
        )

    if (
        candidate_with_edition_code
        != mapping_import.EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT
    ):
        raise mapping_import.ImportValidationError(
            "Candidate rows with edition code are "
            f"{candidate_with_edition_code}, expected "
            f"{mapping_import.EXPECTED_CANDIDATE_WITH_EDITION_CODE_COUNT}."
        )

    excluded_ids = {
        row["source_product_id"]
        for row in rows
        if row["proposed_status"] == "excluded"
    }
    expected_excluded_ids = ONLINE_CODE_CARD_PRODUCT_IDS | OVERSIZED_PRODUCT_IDS
    if excluded_ids != expected_excluded_ids:
        raise mapping_import.ImportValidationError(
            "Excluded product identities do not match the controlled fixture. "
            f"Expected {sorted(expected_excluded_ids)}, "
            f"found {sorted(excluded_ids)}."
        )

    return rows


def resolve_market_product(
    connection: Connection[Any],
    row: dict[str, Any],
) -> dict[str, Any] | None:
    product = fetch_one_dict(
        connection,
        """
        SELECT
            market_product_id,
            source_system,
            source_product_id,
            is_active
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

    product_id = row["source_product_id"]
    if product_id in ONLINE_CODE_CARD_PRODUCT_IDS:
        if product is not None:
            raise mapping_import.ImportValidationError(
                f"Online Code Card product {product_id} unexpectedly exists "
                "in market_products."
            )
        return None

    if product is None:
        raise mapping_import.ImportValidationError(
            f"Required market product {product_id} could not be resolved."
        )
    if product["is_active"] is not True:
        raise mapping_import.ImportValidationError(
            f"Required market product {product_id} is not active."
        )
    return product


def resolve_card(
    connection: Connection[Any],
    row: dict[str, Any],
) -> dict[str, Any] | None:
    if row["proposed_status"] != "candidate":
        return None

    card = fetch_one_dict(
        connection,
        """
        SELECT
            card_id,
            source_system,
            source_card_id,
            is_active
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
    if card is None:
        raise mapping_import.ImportValidationError(
            "Required canonical card could not be resolved: "
            f"{row['catalogue_source_system']}/"
            f"{row['source_card_id']}."
        )
    if card["is_active"] is not True:
        raise mapping_import.ImportValidationError(
            f"Required canonical card {row['source_card_id']} is not active."
        )
    return card


def desired_case_state(
    row: dict[str, Any],
    card: dict[str, Any] | None,
) -> DesiredCaseState:
    status = row["proposed_status"]
    evidence_detail = str(
        row["evidence_payload"].get("evidence")
        or "Controlled Primal Clash mapping fixture."
    )

    if status == "candidate":
        if card is None:
            raise RuntimeError("Candidate row reached merge without a card.")
        return DesiredCaseState(
            status="confirmed",
            confirmation_scope=CONFIRMATION_SCOPE,
            card_id=int(card["card_id"]),
            card_edition_id=None,
            card_variant_id=None,
            confirmation_method=CONFIRMATION_METHOD,
            evidence_level=DIRECT_EVIDENCE_LEVEL,
            reason_code=None,
            reason_detail=None,
        )

    if status == "excluded":
        product_id = row["source_product_id"]
        if product_id in ONLINE_CODE_CARD_PRODUCT_IDS:
            reason_code = ONLINE_CODE_CARD_REASON_CODE
            evidence_level = DERIVED_EVIDENCE_LEVEL
        elif product_id in OVERSIZED_PRODUCT_IDS:
            reason_code = OVERSIZED_CARD_REASON_CODE
            evidence_level = DIRECT_EVIDENCE_LEVEL
        else:
            raise mapping_import.ImportValidationError(
                f"Unexpected excluded product identity: {product_id}."
            )
        return DesiredCaseState(
            status="excluded",
            confirmation_scope=None,
            card_id=None,
            card_edition_id=None,
            card_variant_id=None,
            confirmation_method=None,
            evidence_level=evidence_level,
            reason_code=reason_code,
            reason_detail=evidence_detail,
        )

    if status == "unmatched_duplicate_candidate":
        return DesiredCaseState(
            status="unmatched_duplicate_candidate",
            confirmation_scope=None,
            card_id=None,
            card_edition_id=None,
            card_variant_id=None,
            confirmation_method=None,
            evidence_level=DERIVED_EVIDENCE_LEVEL,
            reason_code=UNMATCHED_DUPLICATE_REASON_CODE,
            reason_detail=evidence_detail,
        )

    raise mapping_import.ImportValidationError(
        f"Unsupported staged mapping status: {status!r}."
    )


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
            "Import run could not transition from validated to merge_started."
        )


def case_matches_state(
    case: dict[str, Any],
    state: DesiredCaseState,
) -> bool:
    return (
        case["current_status"] == state.status
        and case["current_confirmation_scope"] == state.confirmation_scope
        and case["current_card_id"] == state.card_id
        and case["current_card_edition_id"] == state.card_edition_id
        and case["current_card_variant_id"] == state.card_variant_id
        and case["resolved_at"] is not None
    )


def get_or_create_mapping_case(
    connection: Connection[Any],
    *,
    market_product_id: int,
    state: DesiredCaseState,
    counts: MergeCounts,
) -> tuple[dict[str, Any], bool]:
    existing = fetch_one_dict(
        connection,
        """
        SELECT
            mapping_case_id,
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
        FROM card_market_mapping_cases
        WHERE market_product_id = %(market_product_id)s
        FOR UPDATE
        """,
        {"market_product_id": market_product_id},
    )

    if existing is not None:
        if not case_matches_state(existing, state):
            raise mapping_import.ImportValidationError(
                "Existing mapping case does not match the controlled desired "
                f"state for market_product_id {market_product_id}."
            )
        return existing, False

    inserted = fetch_one_dict(
        connection,
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
            %(current_status)s,
            %(current_confirmation_scope)s,
            %(current_card_id)s,
            %(current_card_edition_id)s,
            %(current_card_variant_id)s,
            NULL,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP,
            CASE
                WHEN %(is_resolved)s THEN CURRENT_TIMESTAMP
                ELSE NULL
            END
        )
        RETURNING
            mapping_case_id,
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
        """,
        {
            "market_product_id": market_product_id,
            "current_status": state.status,
            "current_confirmation_scope": state.confirmation_scope,
            "current_card_id": state.card_id,
            "current_card_edition_id": state.card_edition_id,
            "current_card_variant_id": state.card_variant_id,
            "is_resolved": state.is_resolved,
        },
    )
    if inserted is None:
        raise RuntimeError("Database did not return mapping_case_id.")

    counts.cases_inserted += 1
    return inserted, True


def insert_observation(
    connection: Connection[Any],
    *,
    import_run_id: int,
    mapping_case_id: int,
    row: dict[str, Any],
    state: DesiredCaseState,
    is_new_case: bool,
    counts: MergeCounts,
) -> int:
    observation_result = (
        "accepted_transition" if is_new_case else "accepted_support"
    )

    inserted = connection.execute(
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
            %(observation_status)s,
            %(proposed_confirmation_scope)s,
            %(proposed_card_id)s,
            %(proposed_card_edition_id)s,
            %(proposed_card_variant_id)s,
            %(confirmation_method)s,
            %(evidence_level)s,
            %(evidence_reference)s,
            %(evidence_payload)s,
            %(observation_result)s,
            %(result_reason_code)s,
            %(result_reason_detail)s
        )
        RETURNING mapping_case_observation_id
        """,
        {
            "mapping_case_id": mapping_case_id,
            "import_run_id": import_run_id,
            "source_record_reference": row["source_record_reference"],
            "observation_status": state.status,
            "proposed_confirmation_scope": state.confirmation_scope,
            "proposed_card_id": state.card_id,
            "proposed_card_edition_id": state.card_edition_id,
            "proposed_card_variant_id": state.card_variant_id,
            "confirmation_method": state.confirmation_method,
            "evidence_level": state.evidence_level,
            "evidence_reference": row["evidence_reference"],
            "evidence_payload": Jsonb(row["evidence_payload"]),
            "observation_result": observation_result,
            "result_reason_code": state.reason_code,
            "result_reason_detail": state.reason_detail,
        },
    ).fetchone()
    if inserted is None:
        raise RuntimeError("Database did not return mapping_case_observation_id.")

    counts.observations_inserted += 1
    return int(inserted[0])


def update_case_observation_source(
    connection: Connection[Any],
    *,
    mapping_case_id: int,
    observation_id: int,
) -> None:
    result = connection.execute(
        """
        UPDATE card_market_mapping_cases
        SET
            status_source_observation_id = %(observation_id)s,
            last_observed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE mapping_case_id = %(mapping_case_id)s
        """,
        {
            "mapping_case_id": mapping_case_id,
            "observation_id": observation_id,
        },
    )
    if result.rowcount != 1:
        raise mapping_import.ImportValidationError(
            f"Mapping case {mapping_case_id} could not be updated."
        )


def insert_selected_candidate(
    connection: Connection[Any],
    *,
    mapping_case_id: int,
    observation_id: int,
    row: dict[str, Any],
    state: DesiredCaseState,
    counts: MergeCounts,
) -> None:
    if state.status != "confirmed" or state.card_id is None:
        return

    connection.execute(
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
            %(candidate_card_id)s,
            NULL,
            NULL,
            1,
            NULL,
            %(generation_method)s,
            %(evidence_level)s,
            %(evidence_reference)s,
            %(evidence_payload)s,
            'selected',
            NULL,
            CURRENT_TIMESTAMP
        )
        """,
        {
            "mapping_case_id": mapping_case_id,
            "observation_id": observation_id,
            "candidate_card_id": state.card_id,
            "generation_method": CANDIDATE_GENERATION_METHOD,
            "evidence_level": state.evidence_level,
            "evidence_reference": row["evidence_reference"],
            "evidence_payload": Jsonb(row["evidence_payload"]),
        },
    )
    counts.candidates_inserted += 1


def insert_initial_status_history(
    connection: Connection[Any],
    *,
    mapping_case_id: int,
    observation_id: int,
    state: DesiredCaseState,
    counts: MergeCounts,
) -> None:
    connection.execute(
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
            %(new_status)s,
            NULL,
            %(new_confirmation_scope)s,
            NULL,
            %(new_card_id)s,
            NULL,
            %(new_card_edition_id)s,
            NULL,
            %(new_card_variant_id)s,
            %(transition_reason_code)s,
            %(transition_reason_detail)s
        )
        """,
        {
            "mapping_case_id": mapping_case_id,
            "observation_id": observation_id,
            "new_status": state.status,
            "new_confirmation_scope": state.confirmation_scope,
            "new_card_id": state.card_id,
            "new_card_edition_id": state.card_edition_id,
            "new_card_variant_id": state.card_variant_id,
            "transition_reason_code": INITIAL_TRANSITION_REASON_CODE,
            "transition_reason_detail": (
                "Initial state accepted from the validated controlled "
                "Primal Clash mapping fixture."
            ),
        },
    )
    counts.status_transitions_inserted += 1


def get_or_create_production_mapping(
    connection: Connection[Any],
    *,
    mapping_case_id: int,
    market_product_id: int,
    row: dict[str, Any],
    state: DesiredCaseState,
    counts: MergeCounts,
) -> int:
    if state.status != "confirmed" or state.card_id is None:
        raise RuntimeError("Production mapping requested for non-confirmed state.")

    existing = fetch_one_dict(
        connection,
        """
        SELECT
            card_market_product_mapping_id,
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
        FROM card_market_product_mappings
        WHERE market_product_id = %(market_product_id)s
          AND is_active = TRUE
        FOR UPDATE
        """,
        {"market_product_id": market_product_id},
    )

    desired_values = {
        "mapping_case_id": mapping_case_id,
        "market_product_id": market_product_id,
        "card_id": state.card_id,
        "card_edition_id": None,
        "card_variant_id": None,
        "confirmation_scope": CONFIRMATION_SCOPE,
        "confirmation_method": CONFIRMATION_METHOD,
        "evidence_level": DIRECT_EVIDENCE_LEVEL,
        "evidence_reference": row["evidence_reference"],
    }

    if existing is not None:
        mismatches = [
            f"{field}={existing[field]!r}, expected {expected!r}"
            for field, expected in desired_values.items()
            if existing[field] != expected
        ]
        if existing["superseded_at"] is not None:
            mismatches.append("superseded_at is not NULL")
        if mismatches:
            raise mapping_import.ImportValidationError(
                "Existing active production mapping does not match the "
                f"controlled desired mapping for market_product_id "
                f"{market_product_id}: "
                + "; ".join(mismatches)
                + "."
            )

        counts.mapping_unchanged += 1
        return int(existing["card_market_product_mapping_id"])

    inserted = connection.execute(
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
            %(confirmation_method)s,
            %(evidence_level)s,
            %(evidence_reference)s,
            TRUE,
            NULL
        )
        RETURNING card_market_product_mapping_id
        """,
        {
            "mapping_case_id": mapping_case_id,
            "market_product_id": market_product_id,
            "card_id": state.card_id,
            "confirmation_method": CONFIRMATION_METHOD,
            "evidence_level": DIRECT_EVIDENCE_LEVEL,
            "evidence_reference": row["evidence_reference"],
        },
    ).fetchone()
    if inserted is None:
        raise RuntimeError(
            "Database did not return card_market_product_mapping_id."
        )

    counts.mapping_inserted += 1
    return int(inserted[0])


def record_outcome(
    connection: Connection[Any],
    *,
    import_run_id: int,
    row: dict[str, Any],
    outcome_type: str,
    production_entity_id: int | None,
    reason_code: str | None = None,
    reason_detail: str | None = None,
    change_summary: dict[str, Any] | None = None,
) -> None:
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
            %(outcome_type)s,
            %(reason_code)s,
            %(reason_detail)s,
            %(change_summary)s
        )
        """,
        {
            "import_run_id": import_run_id,
            "source_system": row["market_source_system"],
            "source_entity_id": row["source_product_id"],
            "source_record_reference": row["source_record_reference"],
            "production_entity_id": production_entity_id,
            "outcome_type": outcome_type,
            "reason_code": reason_code,
            "reason_detail": reason_detail,
            "change_summary": (
                Jsonb(change_summary) if change_summary is not None else None
            ),
        },
    )


def merge_one_mapping(
    connection: Connection[Any],
    *,
    import_run_id: int,
    row: dict[str, Any],
    counts: MergeCounts,
) -> None:
    market_product = resolve_market_product(connection, row)
    card = resolve_card(connection, row)
    state = desired_case_state(row, card)

    if market_product is None:
        if row["source_product_id"] not in ONLINE_CODE_CARD_PRODUCT_IDS:
            raise RuntimeError("Unexpected missing market product.")
        record_outcome(
            connection,
            import_run_id=import_run_id,
            row=row,
            outcome_type="skipped",
            production_entity_id=None,
            reason_code=state.reason_code,
            reason_detail=state.reason_detail,
        )
        counts.skipped += 1
        return

    market_product_id = int(market_product["market_product_id"])
    mapping_case, is_new_case = get_or_create_mapping_case(
        connection,
        market_product_id=market_product_id,
        state=state,
        counts=counts,
    )
    mapping_case_id = int(mapping_case["mapping_case_id"])

    observation_id = insert_observation(
        connection,
        import_run_id=import_run_id,
        mapping_case_id=mapping_case_id,
        row=row,
        state=state,
        is_new_case=is_new_case,
        counts=counts,
    )

    insert_selected_candidate(
        connection,
        mapping_case_id=mapping_case_id,
        observation_id=observation_id,
        row=row,
        state=state,
        counts=counts,
    )

    if is_new_case:
        insert_initial_status_history(
            connection,
            mapping_case_id=mapping_case_id,
            observation_id=observation_id,
            state=state,
            counts=counts,
        )

    update_case_observation_source(
        connection,
        mapping_case_id=mapping_case_id,
        observation_id=observation_id,
    )

    if state.status == "confirmed":
        production_mapping_id = get_or_create_production_mapping(
            connection,
            mapping_case_id=mapping_case_id,
            market_product_id=market_product_id,
            row=row,
            state=state,
            counts=counts,
        )
        outcome_type = "inserted" if is_new_case else "unchanged"
        record_outcome(
            connection,
            import_run_id=import_run_id,
            row=row,
            outcome_type=outcome_type,
            production_entity_id=production_mapping_id,
        )
        return

    record_outcome(
        connection,
        import_run_id=import_run_id,
        row=row,
        outcome_type="skipped",
        production_entity_id=None,
        reason_code=state.reason_code,
        reason_detail=state.reason_detail,
    )
    counts.skipped += 1


def validate_merged_state(
    connection: Connection[Any],
    *,
    import_run_id: int,
    counts: MergeCounts,
) -> None:
    if counts.production_processed != mapping_import.EXPECTED_CANDIDATE_COUNT:
        raise mapping_import.ImportValidationError(
            "Production mapping outcome count does not reconcile: "
            f"{counts.production_processed} processed, expected "
            f"{mapping_import.EXPECTED_CANDIDATE_COUNT}."
        )

    expected_skipped = (
        mapping_import.EXPECTED_EXCLUDED_COUNT
        + mapping_import.EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT
    )
    if counts.skipped != expected_skipped:
        raise mapping_import.ImportValidationError(
            f"Skipped count is {counts.skipped}, expected {expected_skipped}."
        )

    if counts.total_outcomes != mapping_import.EXPECTED_RECORD_COUNT:
        raise mapping_import.ImportValidationError(
            f"Total outcomes are {counts.total_outcomes}, expected "
            f"{mapping_import.EXPECTED_RECORD_COUNT}."
        )

    expected_case_count = (
        mapping_import.EXPECTED_RECORD_COUNT
        - len(ONLINE_CODE_CARD_PRODUCT_IDS)
    )
    case_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM card_market_mapping_cases AS cases
        JOIN market_products AS products
          ON products.market_product_id = cases.market_product_id
        WHERE products.source_system = 'cardmarket'
          AND products.source_expansion_id = '1585'
        """,
        {},
    )
    if case_count != expected_case_count:
        raise mapping_import.ImportValidationError(
            f"Production contains {case_count} Primal Clash mapping cases, "
            f"expected {expected_case_count}."
        )

    confirmed_case_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM card_market_mapping_cases AS cases
        JOIN market_products AS products
          ON products.market_product_id = cases.market_product_id
        WHERE products.source_system = 'cardmarket'
          AND products.source_expansion_id = '1585'
          AND cases.current_status = 'confirmed'
          AND cases.current_confirmation_scope = 'card'
          AND cases.current_card_id IS NOT NULL
          AND cases.current_card_edition_id IS NULL
          AND cases.current_card_variant_id IS NULL
          AND cases.resolved_at IS NOT NULL
        """,
        {},
    )
    if confirmed_case_count != mapping_import.EXPECTED_CANDIDATE_COUNT:
        raise mapping_import.ImportValidationError(
            f"Found {confirmed_case_count} confirmed card-scope cases, expected "
            f"{mapping_import.EXPECTED_CANDIDATE_COUNT}."
        )

    excluded_case_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM card_market_mapping_cases AS cases
        JOIN market_products AS products
          ON products.market_product_id = cases.market_product_id
        WHERE products.source_system = 'cardmarket'
          AND products.source_product_id = ANY(%(product_ids)s)
          AND cases.current_status = 'excluded'
          AND cases.current_confirmation_scope IS NULL
          AND cases.current_card_id IS NULL
          AND cases.resolved_at IS NOT NULL
        """,
        {"product_ids": list(OVERSIZED_PRODUCT_IDS)},
    )
    if excluded_case_count != len(OVERSIZED_PRODUCT_IDS):
        raise mapping_import.ImportValidationError(
            f"Found {excluded_case_count} oversized excluded cases, expected "
            f"{len(OVERSIZED_PRODUCT_IDS)}."
        )

    unmatched_case_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM card_market_mapping_cases AS cases
        JOIN market_products AS products
          ON products.market_product_id = cases.market_product_id
        WHERE products.source_system = 'cardmarket'
          AND products.source_expansion_id = '1585'
          AND cases.current_status = 'unmatched_duplicate_candidate'
          AND cases.current_confirmation_scope IS NULL
          AND cases.current_card_id IS NULL
          AND cases.resolved_at IS NOT NULL
        """,
        {},
    )
    if (
        unmatched_case_count
        != mapping_import.EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT
    ):
        raise mapping_import.ImportValidationError(
            f"Found {unmatched_case_count} unmatched duplicate cases, expected "
            f"{mapping_import.EXPECTED_UNMATCHED_DUPLICATE_CANDIDATE_COUNT}."
        )

    observation_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM mapping_case_observations
        WHERE import_run_id = %(import_run_id)s
        """,
        {"import_run_id": import_run_id},
    )
    if observation_count != expected_case_count:
        raise mapping_import.ImportValidationError(
            f"Recorded {observation_count} mapping observations, expected "
            f"{expected_case_count}."
        )

    candidate_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM mapping_candidates AS candidates
        JOIN mapping_case_observations AS observations
          ON observations.mapping_case_observation_id =
             candidates.mapping_case_observation_id
        WHERE observations.import_run_id = %(import_run_id)s
          AND candidates.candidate_scope = 'card'
          AND candidates.candidate_state = 'selected'
        """,
        {"import_run_id": import_run_id},
    )
    if candidate_count != mapping_import.EXPECTED_CANDIDATE_COUNT:
        raise mapping_import.ImportValidationError(
            f"Recorded {candidate_count} selected candidates, expected "
            f"{mapping_import.EXPECTED_CANDIDATE_COUNT}."
        )

    active_mapping_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM card_market_product_mappings AS mappings
        JOIN market_products AS products
          ON products.market_product_id = mappings.market_product_id
        WHERE products.source_system = 'cardmarket'
          AND products.source_expansion_id = '1585'
          AND mappings.is_active = TRUE
          AND mappings.confirmation_scope = 'card'
          AND mappings.card_edition_id IS NULL
          AND mappings.card_variant_id IS NULL
        """,
        {},
    )
    if active_mapping_count != mapping_import.EXPECTED_CANDIDATE_COUNT:
        raise mapping_import.ImportValidationError(
            f"Production contains {active_mapping_count} active card mappings, "
            f"expected {mapping_import.EXPECTED_CANDIDATE_COUNT}."
        )

    excluded_or_unmatched_mappings = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM card_market_product_mappings AS mappings
        JOIN card_market_mapping_cases AS cases
          ON cases.mapping_case_id = mappings.mapping_case_id
        WHERE mappings.is_active = TRUE
          AND cases.current_status IN (
              'excluded',
              'unmatched_duplicate_candidate'
          )
        """,
        {},
    )
    if excluded_or_unmatched_mappings != 0:
        raise mapping_import.ImportValidationError(
            "Excluded or unmatched duplicate cases have active production "
            f"mappings: {excluded_or_unmatched_mappings}."
        )

    outcome_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_record_outcomes
        WHERE import_run_id = %(import_run_id)s
          AND entity_type = 'card_market_product_mapping'
        """,
        {"import_run_id": import_run_id},
    )
    if outcome_count != mapping_import.EXPECTED_RECORD_COUNT:
        raise mapping_import.ImportValidationError(
            f"Recorded {outcome_count} mapping outcomes, expected "
            f"{mapping_import.EXPECTED_RECORD_COUNT}."
        )

    skipped_count = fetch_scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM import_record_outcomes
        WHERE import_run_id = %(import_run_id)s
          AND entity_type = 'card_market_product_mapping'
          AND outcome_type = 'skipped'
          AND reason_code IN (
              %(online_reason)s,
              %(oversized_reason)s,
              %(unmatched_reason)s
          )
          AND production_entity_id IS NULL
        """,
        {
            "import_run_id": import_run_id,
            "online_reason": ONLINE_CODE_CARD_REASON_CODE,
            "oversized_reason": OVERSIZED_CARD_REASON_CODE,
            "unmatched_reason": UNMATCHED_DUPLICATE_REASON_CODE,
        },
    )
    if skipped_count != expected_skipped:
        raise mapping_import.ImportValidationError(
            f"Recorded {skipped_count} controlled skipped outcomes, expected "
            f"{expected_skipped}."
        )


def complete_import_run(
    connection: Connection[Any],
    *,
    import_run_id: int,
    counts: MergeCounts,
) -> None:
    result = connection.execute(
        """
        UPDATE import_runs
        SET
            status = 'succeeded',
            completed_at = CURRENT_TIMESTAMP,
            inserted_records = %(inserted_records)s,
            updated_records = 0,
            unchanged_records = %(unchanged_records)s,
            missing_records = 0,
            retired_records = 0
        WHERE import_run_id = %(import_run_id)s
          AND status = 'merge_started'
        """,
        {
            "import_run_id": import_run_id,
            "inserted_records": counts.mapping_inserted,
            "unchanged_records": counts.mapping_unchanged,
        },
    )
    if result.rowcount != 1:
        raise mapping_import.ImportValidationError(
            "Import run could not transition from merge_started to succeeded."
        )


def main() -> int:
    args = parse_args()
    if args.import_run_id < 1:
        raise mapping_import.ImportValidationError(
            "--import-run-id must be a positive integer."
        )

    database_url = mapping_import.get_database_url()
    counts = MergeCounts()

    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            run = lock_and_validate_import_run(connection, args.import_run_id)
            staging_rows = load_and_validate_staging_rows(
                connection,
                args.import_run_id,
            )
            mark_merge_started(connection, args.import_run_id)

            for row in staging_rows:
                merge_one_mapping(
                    connection,
                    import_run_id=args.import_run_id,
                    row=row,
                    counts=counts,
                )

            validate_merged_state(
                connection,
                import_run_id=args.import_run_id,
                counts=counts,
            )
            complete_import_run(
                connection,
                import_run_id=args.import_run_id,
                counts=counts,
            )

    print("Primal Clash Cardmarket mapping production merge committed")
    print(f"Import run ID: {args.import_run_id}")
    print(f"Run reference: {run['run_reference']}")
    print(f"Inserted production mappings: {counts.mapping_inserted}")
    print(f"Unchanged production mappings: {counts.mapping_unchanged}")
    print(f"Skipped controlled records: {counts.skipped}")
    print(f"Inserted mapping cases: {counts.cases_inserted}")
    print(f"Inserted observations: {counts.observations_inserted}")
    print(f"Inserted candidates: {counts.candidates_inserted}")
    print(
        "Inserted status transitions: "
        f"{counts.status_transitions_inserted}"
    )
    print(f"Processed source records: {counts.total_outcomes}")
    print("Final status: succeeded")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (mapping_import.ImportValidationError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
