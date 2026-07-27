"""
Script: analyze_primal_clash_unmatched_products.py

Purpose:
    Inspect unmatched Primal Clash Cardmarket product records and compare them
    with directly mapped products sharing the same Cardmarket metacard ID.

    The report prints complete product records and field-level differences.
    It does not classify unmatched products or modify mapping-review.csv.

Lifecycle:
    Temporary discovery utility.

Removal:
    May be deleted after unmatched Cardmarket product handling is documented
    and implemented with equivalent permanent validation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "primal-clash"

PRODUCTS_FILE = FIXTURE_DIR / "cardmarket-products.json"
MAPPING_REVIEW_FILE = FIXTURE_DIR / "mapping-review.csv"


def require_file(path: Path) -> None:
    """Stop execution when a required input file does not exist."""
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")


def load_products(path: Path) -> list[dict[str, Any]]:
    """Load Cardmarket product records from the fixture."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")

    records = payload.get("records")

    if not isinstance(records, list):
        raise ValueError(f"'records' must be a list in {path.name}")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(
                f"Record {index} must be an object in {path.name}"
            )

    return records


def load_mapping_rows(path: Path) -> list[dict[str, str]]:
    """Load the generated mapping review CSV."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "cardmarket_product_id",
            "cardmarket_metacard_id",
            "mapping_status",
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


def normalized_value(value: Any) -> str:
    """Convert source values to deterministic printable text."""
    if value is None:
        return "<null>"

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    return str(value)


def print_record(
    label: str,
    product: dict[str, Any],
) -> None:
    """Print every field from one product record."""
    print(label)

    for key in sorted(product):
        print(f"    {key}: {normalized_value(product[key])}")


def print_differences(
    unmatched: dict[str, Any],
    sibling: dict[str, Any],
) -> None:
    """Print field differences between two product records."""
    all_keys = sorted(set(unmatched) | set(sibling))

    differences = []

    for key in all_keys:
        unmatched_value = normalized_value(unmatched.get(key))
        sibling_value = normalized_value(sibling.get(key))

        if unmatched_value == sibling_value:
            continue

        differences.append(
            (
                key,
                unmatched_value,
                sibling_value,
            )
        )

    print("  Differences:")

    if not differences:
        print("    No field differences.")
        return

    for key, unmatched_value, sibling_value in differences:
        print(f"    {key}:")
        print(f"      unmatched: {unmatched_value}")
        print(f"      sibling:   {sibling_value}")


def main() -> None:
    require_file(PRODUCTS_FILE)
    require_file(MAPPING_REVIEW_FILE)

    products = load_products(PRODUCTS_FILE)
    mapping_rows = load_mapping_rows(MAPPING_REVIEW_FILE)

    products_by_id = {
        str(product.get("idProduct", "")).strip(): product
        for product in products
        if str(product.get("idProduct", "")).strip()
    }

    matched_product_ids = {
        row["cardmarket_product_id"]
        for row in mapping_rows
        if (
            row["mapping_status"] == "candidate"
            and row["cardmarket_product_id"]
        )
    }

    unmatched_product_ids = {
        row["cardmarket_product_id"]
        for row in mapping_rows
        if (
            row["mapping_status"] == "unmatched"
            and row["cardmarket_product_id"]
        )
    }

    products_by_metacard: dict[str, list[dict[str, Any]]] = {}

    for product in products:
        metacard_id = str(
            product.get("idMetacard", "")
        ).strip()

        products_by_metacard.setdefault(
            metacard_id,
            [],
        ).append(product)

    print("Primal Clash unmatched-product analysis")
    print()
    print(f"Unmatched products: {len(unmatched_product_ids):,}")

    for product_id in sorted(unmatched_product_ids, key=int):
        unmatched = products_by_id.get(product_id)

        if unmatched is None:
            raise ValueError(
                f"Unmatched product not found in fixture: {product_id}"
            )

        metacard_id = str(
            unmatched.get("idMetacard", "")
        ).strip()

        siblings = [
            product
            for product in products_by_metacard.get(metacard_id, [])
            if (
                str(product.get("idProduct", "")).strip()
                in matched_product_ids
            )
        ]

        siblings.sort(
            key=lambda product: int(
                str(product.get("idProduct", "0"))
            )
        )

        print()
        print(
            f"Unmatched idProduct={product_id} | "
            f"idMetacard={metacard_id} | "
            f"{unmatched.get('name', '')}"
        )

        print_record("  Unmatched record:", unmatched)

        print(
            f"  Directly mapped sibling products: "
            f"{len(siblings):,}"
        )

        for sibling in siblings:
            sibling_id = str(
                sibling.get("idProduct", "")
            ).strip()

            print()
            print_record(
                f"  Sibling idProduct={sibling_id}:",
                sibling,
            )
            print_differences(unmatched, sibling)

    print()
    print("Unmatched-product analysis completed.")
    print("No mappings were modified.")


if __name__ == "__main__":
    main()