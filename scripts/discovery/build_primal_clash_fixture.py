from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

CARDMARKET_DIR = REPO_ROOT / "data" / "raw" / "cardmarket"
CATALOGUE_DIR = REPO_ROOT / "data" / "raw" / "catalogue"
FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "primal-clash"

PRODUCTS_FILE = CARDMARKET_DIR / "products_singles_6.json"
PRICES_FILE = CARDMARKET_DIR / "price_guide_6.json"
LISTING_FILE = CARDMARKET_DIR / "primal_clash_de.csv"
CARDS_FILE = CATALOGUE_DIR / "xy5.json"

PRIMAL_CLASH_CARDMARKET_EXPANSION_ID = "1585"


def require_file(path: Path) -> None:
    """Stop the script when a required source file is missing."""
    if not path.is_file():
        raise FileNotFoundError(f"Required source file not found: {path}")


def load_json(path: Path) -> Any:
    """Read one JSON source file."""
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def count_csv_rows(path: Path) -> int:
    """Count data rows in the semicolon-separated Cardmarket listing."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return sum(1 for _ in csv.DictReader(file, delimiter=";"))


def extract_records(payload: Any, source_name: str) -> list[dict[str, Any]]:
    """
    Find the list of records inside a source JSON document.

    Different source files may use different top-level keys.
    """
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("products", "priceGuides", "data", "cards"):
            value = payload.get(key)

            if isinstance(value, list):
                return value

    raise ValueError(
        f"Could not find a record list in {source_name}. "
        f"Top-level type: {type(payload).__name__}"
    )


def get_created_at(payload: Any) -> str | None:
    """Return the source snapshot timestamp when it exists."""
    if isinstance(payload, dict):
        value = payload.get("createdAt")

        if isinstance(value, str):
            return value

    return None


def normalize_id(value: Any) -> str:
    """Convert numeric or textual source identifiers to comparable text."""
    return str(value).strip()

def write_json(path: Path, payload: Any) -> None:
    """Write deterministic, human-readable JSON output."""
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

def main() -> None:
    source_files = (
        PRODUCTS_FILE,
        PRICES_FILE,
        LISTING_FILE,
        CARDS_FILE,
    )

    # Step 1: verify that every required source exists.
    for path in source_files:
        require_file(path)

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    # Step 2: load the source files.
    products_payload = load_json(PRODUCTS_FILE)
    prices_payload = load_json(PRICES_FILE)
    cards_payload = load_json(CARDS_FILE)

    # Step 3: extract the record lists from the JSON documents.
    products = extract_records(products_payload, PRODUCTS_FILE.name)
    prices = extract_records(prices_payload, PRICES_FILE.name)
    cards = extract_records(cards_payload, CARDS_FILE.name)

    listing_rows = count_csv_rows(LISTING_FILE)

    # Step 4: select only Cardmarket products from Primal Clash.
    primal_clash_products = [
        product
        for product in products
        if normalize_id(product.get("idExpansion"))
        == PRIMAL_CLASH_CARDMARKET_EXPANSION_ID
    ]

    # Step 5: create a price lookup by Cardmarket product ID.
    price_by_product_id = {
        normalize_id(price.get("idProduct")): price
        for price in prices
        if price.get("idProduct") is not None
    }

    # Step 6: check which Primal Clash products have price records.
    products_with_prices = [
        product
        for product in primal_clash_products
        if normalize_id(product.get("idProduct")) in price_by_product_id
    ]

    products_without_prices = [
        product
        for product in primal_clash_products
        if normalize_id(product.get("idProduct")) not in price_by_product_id
    ]

    primal_clash_products.sort(
        key=lambda product: int(normalize_id(product["idProduct"]))
    )

    primal_clash_product_ids = {
        normalize_id(product["idProduct"])
        for product in primal_clash_products
    }

    primal_clash_prices = [
        price
        for price in prices
        if normalize_id(price.get("idProduct"))
        in primal_clash_product_ids
    ]

    primal_clash_prices.sort(
        key=lambda price: int(normalize_id(price["idProduct"]))
    )

    canonical_cards = sorted(
        cards,
        key=lambda card: normalize_id(card.get("id", ""))
    )

    canonical_cards_output = {
        "sourceFile": CARDS_FILE.name,
        "sourceSystem": "pokemon_tcg_data",
        "setId": "xy5",
        "recordCount": len(canonical_cards),
        "records": canonical_cards,
    }

    products_output = {
        "sourceFile": PRODUCTS_FILE.name,
        "sourceSystem": "cardmarket",
        "sourceCreatedAt": get_created_at(products_payload),
        "expansionId": PRIMAL_CLASH_CARDMARKET_EXPANSION_ID,
        "recordCount": len(primal_clash_products),
        "records": primal_clash_products,
    }

    prices_output = {
        "sourceFile": PRICES_FILE.name,
        "sourceSystem": "cardmarket",
        "sourceCreatedAt": get_created_at(prices_payload),
        "recordCount": len(primal_clash_prices),
        "records": primal_clash_prices,
    }

    write_json(
        FIXTURE_DIR / "canonical-cards.json",
        canonical_cards_output,
    )

    write_json(
        FIXTURE_DIR / "cardmarket-products.json",
        products_output,
    )

    write_json(
        FIXTURE_DIR / "cardmarket-prices.json",
        prices_output,
    )

    # Step 7: print a validation summary.
    print(f"Repository root: {REPO_ROOT}")
    print(f"Fixture directory: {FIXTURE_DIR}")

    print()
    print("Source validation passed:")
    print(f"- {PRODUCTS_FILE.name}: {len(products):,} records")
    print(f"- {PRICES_FILE.name}: {len(prices):,} records")
    print(f"- {CARDS_FILE.name}: {len(cards):,} records")
    print(f"- {LISTING_FILE.name}: {listing_rows:,} rows")

    print()
    print("Snapshot metadata:")
    print(
        f"- products createdAt: "
        f"{get_created_at(products_payload) or 'unknown'}"
    )
    print(
        f"- prices createdAt: "
        f"{get_created_at(prices_payload) or 'unknown'}"
    )

    print()
    print("Primal Clash selection:")
    print(f"- canonical cards: {len(cards):,}")
    print(
        "- Cardmarket products with idExpansion 1585: "
        f"{len(primal_clash_products):,}"
    )
    print(f"- products with price records: {len(products_with_prices):,}")
    print(f"- products without price records: {len(products_without_prices):,}")
    print()
    print("Fixture files written:")
    print("- canonical-cards.json")
    print("- cardmarket-products.json")
    print("- cardmarket-prices.json")

if __name__ == "__main__":
    main()