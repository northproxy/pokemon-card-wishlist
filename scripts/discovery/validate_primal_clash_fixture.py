"""
Script: validate_primal_clash_fixture.py

Purpose:
    Validate the generated Primal Clash fixture files and the final mapping
    review produced from direct Cardmarket product IDs.

    Validation covers:
    - JSON fixture structure and declared record counts;
    - expected mapping-status counts;
    - complete canonical-card coverage;
    - unique directly mapped Cardmarket product coverage;
    - explicit duplicate-candidate and excluded-product handling;
    - absence of unresolved mapping statuses.
    - deterministic canonical-card image URL metadata;

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while the Primal Clash fixture remains part of import
    validation. It may be replaced only by an equivalent automated test or
    generalized fixture-validation command.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "primal-clash"

FIXTURE_FILES = (
    "canonical-cards.json",
    "cardmarket-products.json",
    "cardmarket-prices.json",
)

MAPPING_REVIEW_FILE = FIXTURE_DIR / "mapping-review.csv"

EXPECTED_STATUS_COUNTS = {
    "candidate": 167,
    "unmatched_duplicate_candidate": 6,
    "excluded": 4,
}

EXPECTED_CANDIDATE_CANONICAL_CARDS = 164
EXPECTED_CANDIDATE_PRODUCTS = 167
EXPECTED_MAPPING_ROWS = 177

FORBIDDEN_STATUSES = {
    "ambiguous",
    "conflict",
    "unmatched",
}

EXPECTED_IMAGE_HOST = "images.pokemontcg.io"
EXPECTED_IMAGE_SCHEME = "https"

def require_file(path: Path) -> None:
    """Stop validation when a required fixture file does not exist."""
    if not path.is_file():
        raise FileNotFoundError(f"Required fixture file not found: {path}")


def load_json(path: Path) -> dict[str, Any]:
    """Load and validate one fixture JSON document."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")

    return payload


def validate_json_fixture(path: Path) -> int:
    """
    Validate one JSON fixture and return its actual record count.
    """
    payload = load_json(path)

    records = payload.get("records")
    declared_count = payload.get("recordCount")

    if not isinstance(records, list):
        raise ValueError(f"'records' must be a list in {path.name}")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(
                f"Record {index} must be an object in {path.name}"
            )

    if declared_count != len(records):
        raise ValueError(
            f"Record-count mismatch in {path.name}: "
            f"declared {declared_count}, actual {len(records)}"
        )

    print(f"{path.name}:")
    print(f"  recordCount field: {declared_count}")
    print(f"  actual records:    {len(records)}")

    if records:
        print(
            "  first record keys: "
            f"{sorted(records[0].keys())}"
        )

    print()

    return len(records)

def validate_canonical_image_metadata(
    path: Path,
) -> None:
    """
    Validate deterministic small and large image metadata for canonical cards.

    This validation checks fixture metadata only. It does not download images
    or verify remote availability.
    """
    payload = load_json(path)
    records = payload.get("records")

    if not isinstance(records, list):
        raise ValueError(f"'records' must be a list in {path.name}")

    missing_metadata: list[str] = []
    malformed_urls: list[str] = []
    unexpected_paths: list[str] = []

    small_urls: set[str] = set()
    large_urls: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(
                f"Record {index} must be an object in {path.name}"
            )

        card_id = str(record.get("id", "")).strip()
        collector_number = str(record.get("number", "")).strip()
        images = record.get("images")

        if not card_id or "-" not in card_id:
            raise ValueError(
                f"Unexpected canonical card ID at record {index}: "
                f"{card_id!r}"
            )

        if not collector_number:
            raise ValueError(
                f"Missing collector number for canonical card {card_id}"
            )

        if not isinstance(images, dict):
            missing_metadata.append(
                f"{card_id}: images object missing"
            )
            continue

        small_url = str(images.get("small", "")).strip()
        large_url = str(images.get("large", "")).strip()

        if not small_url or not large_url:
            missing_metadata.append(
                f"{card_id}: "
                f"small={bool(small_url)}, "
                f"large={bool(large_url)}"
            )
            continue

        small_urls.add(small_url)
        large_urls.add(large_url)

        set_code = card_id.rsplit("-", 1)[0]

        expected_small_path = (
            f"/{set_code}/{collector_number}.png"
        )
        expected_large_path = (
            f"/{set_code}/{collector_number}_hires.png"
        )

        for label, url, expected_path in (
            ("small", small_url, expected_small_path),
            ("large", large_url, expected_large_path),
        ):
            parsed = urlparse(url)

            if (
                parsed.scheme != EXPECTED_IMAGE_SCHEME
                or parsed.netloc != EXPECTED_IMAGE_HOST
            ):
                malformed_urls.append(
                    f"{card_id}: unexpected {label} URL {url}"
                )

            if parsed.path != expected_path:
                unexpected_paths.append(
                    f"{card_id}: {label} path {parsed.path!r}, "
                    f"expected {expected_path!r}"
                )

    if missing_metadata:
        raise ValueError(
            "Missing canonical-card image metadata: "
            + "; ".join(missing_metadata)
        )

    if malformed_urls:
        raise ValueError(
            "Malformed canonical-card image URLs: "
            + "; ".join(malformed_urls)
        )

    if unexpected_paths:
        raise ValueError(
            "Unexpected canonical-card image paths: "
            + "; ".join(unexpected_paths)
        )

    if len(small_urls) != len(records):
        raise ValueError(
            "Small image URLs are not unique: "
            f"records={len(records)}, "
            f"unique URLs={len(small_urls)}"
        )

    if len(large_urls) != len(records):
        raise ValueError(
            "Large image URLs are not unique: "
            f"records={len(records)}, "
            f"unique URLs={len(large_urls)}"
        )

    print("Canonical image metadata:")
    print(f"  canonical cards:          {len(records)}")
    print(f"  unique small image URLs:  {len(small_urls)}")
    print(f"  unique large image URLs:  {len(large_urls)}")
    print("  missing image metadata:   0")
    print("  malformed image URLs:     0")
    print("  unexpected image paths:   0")
    print()


def load_mapping_rows(path: Path) -> list[dict[str, str]]:
    """Load and validate the mapping-review CSV structure."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "canonical_card_id",
            "collector_number",
            "canonical_name",
            "listing_url",
            "cardmarket_product_id",
            "cardmarket_product_name",
            "cardmarket_metacard_id",
            "mapping_status",
            "mapping_method",
            "evidence",
        }

        actual_columns = set(reader.fieldnames or [])
        missing_columns = required_columns - actual_columns

        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(
                f"Missing columns in {path.name}: {missing}"
            )

        return [
            {
                key: (value or "").strip()
                for key, value in row.items()
            }
            for row in reader
        ]


def validate_mapping_review(
    rows: list[dict[str, str]],
    canonical_card_count: int,
) -> None:
    """Validate final direct-ID mapping coverage and controlled statuses."""
    if len(rows) != EXPECTED_MAPPING_ROWS:
        raise ValueError(
            "Unexpected mapping row count: "
            f"expected {EXPECTED_MAPPING_ROWS}, actual {len(rows)}"
        )

    status_counts = Counter(
        row["mapping_status"]
        for row in rows
    )

    unexpected_statuses = (
        set(status_counts)
        - set(EXPECTED_STATUS_COUNTS)
    )

    if unexpected_statuses:
        raise ValueError(
            "Unexpected mapping statuses: "
            f"{sorted(unexpected_statuses)}"
        )

    for status, expected_count in EXPECTED_STATUS_COUNTS.items():
        actual_count = status_counts.get(status, 0)

        if actual_count != expected_count:
            raise ValueError(
                f"Unexpected count for status {status!r}: "
                f"expected {expected_count}, actual {actual_count}"
            )

    present_forbidden_statuses = {
        status
        for status in FORBIDDEN_STATUSES
        if status_counts.get(status, 0)
    }

    if present_forbidden_statuses:
        raise ValueError(
            "Forbidden unresolved statuses are present: "
            f"{sorted(present_forbidden_statuses)}"
        )

    candidate_rows = [
        row
        for row in rows
        if row["mapping_status"] == "candidate"
    ]

    canonical_ids = {
        row["canonical_card_id"]
        for row in candidate_rows
        if row["canonical_card_id"]
    }

    product_ids = {
        row["cardmarket_product_id"]
        for row in candidate_rows
        if row["cardmarket_product_id"]
    }

    listing_urls = {
        row["listing_url"]
        for row in candidate_rows
        if row["listing_url"]
    }

    if len(canonical_ids) != EXPECTED_CANDIDATE_CANONICAL_CARDS:
        raise ValueError(
            "Unexpected candidate canonical-card coverage: "
            f"expected {EXPECTED_CANDIDATE_CANONICAL_CARDS}, "
            f"actual {len(canonical_ids)}"
        )

    if len(canonical_ids) != canonical_card_count:
        raise ValueError(
            "Candidate mappings do not cover every canonical card: "
            f"canonical fixture={canonical_card_count}, "
            f"candidate coverage={len(canonical_ids)}"
        )

    if len(product_ids) != EXPECTED_CANDIDATE_PRODUCTS:
        raise ValueError(
            "Unexpected candidate product coverage: "
            f"expected {EXPECTED_CANDIDATE_PRODUCTS}, "
            f"actual {len(product_ids)}"
        )

    if len(listing_urls) != len(candidate_rows):
        raise ValueError(
            "Candidate listing URLs are not unique: "
            f"candidate rows={len(candidate_rows)}, "
            f"unique URLs={len(listing_urls)}"
        )

    duplicate_candidate_rows = [
        row
        for row in rows
        if row["mapping_status"]
        == "unmatched_duplicate_candidate"
    ]

    for row in duplicate_candidate_rows:
        if row["canonical_card_id"]:
            raise ValueError(
                "unmatched_duplicate_candidate must not reference a "
                f"canonical card: {row['cardmarket_product_id']}"
            )

        if not row["cardmarket_product_id"]:
            raise ValueError(
                "unmatched_duplicate_candidate is missing idProduct."
            )

    excluded_rows = [
        row
        for row in rows
        if row["mapping_status"] == "excluded"
    ]

    for row in excluded_rows:
        if "online code card" not in (
            row["cardmarket_product_name"].casefold()
        ):
            raise ValueError(
                "Excluded row is not an Online Code Card: "
                f"{row['cardmarket_product_id']} | "
                f"{row['cardmarket_product_name']}"
            )

    print(f"{MAPPING_REVIEW_FILE.name}:")
    print(f"  total rows:                         {len(rows)}")
    print(
        "  candidate rows:                     "
        f"{status_counts['candidate']}"
    )
    print(
        "  unique candidate canonical cards:   "
        f"{len(canonical_ids)}"
    )
    print(
        "  unique candidate products:          "
        f"{len(product_ids)}"
    )
    print(
        "  unmatched duplicate candidates:     "
        f"{status_counts['unmatched_duplicate_candidate']}"
    )
    print(
        "  excluded products:                  "
        f"{status_counts['excluded']}"
    )
    print("  unresolved statuses:                0")
    print()


def main() -> None:
    for filename in FIXTURE_FILES:
        require_file(FIXTURE_DIR / filename)

    require_file(MAPPING_REVIEW_FILE)

    fixture_counts = {
        filename: validate_json_fixture(FIXTURE_DIR / filename)
        for filename in FIXTURE_FILES
    }

    validate_canonical_image_metadata(
        FIXTURE_DIR / "canonical-cards.json"
    )

    mapping_rows = load_mapping_rows(MAPPING_REVIEW_FILE)

    validate_mapping_review(
        mapping_rows,
        canonical_card_count=fixture_counts[
            "canonical-cards.json"
        ],
    )

    print("Primal Clash fixture validation passed.")


if __name__ == "__main__":
    main()