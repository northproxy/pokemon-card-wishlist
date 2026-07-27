"""
Script: analyze_primal_clash_edition_groups.py

Purpose:
    Inspect the remaining ambiguous Primal Clash mapping groups.

    The script groups canonical cards and Cardmarket products by their shared
    semantic signature, then prints collector numbers, product IDs, metacard
    IDs, dates, and scraped listing URLs.

    This is a diagnostic script only. It does not modify mapping-review.csv
    and does not confirm mappings based on product ordering.

Lifecycle:
    Temporary discovery utility.

Removal:
    May be deleted after edition and variant mapping rules are documented and
    implemented in the permanent mapping builder with equivalent validation.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "primal-clash"

CANONICAL_CARDS_FILE = FIXTURE_DIR / "canonical-cards.json"
CARDMARKET_PRODUCTS_FILE = FIXTURE_DIR / "cardmarket-products.json"
MAPPING_REVIEW_FILE = FIXTURE_DIR / "mapping-review.csv"

IGNORED_PRODUCT_TERMS = {
    "primal clash",
}


def require_file(path: Path) -> None:
    """Stop execution when a required file does not exist."""
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")


def load_json_records(path: Path) -> list[dict[str, Any]]:
    """Load and validate a fixture JSON records array."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")

    records = payload.get("records")

    if not isinstance(records, list):
        raise ValueError(f"'records' must be a list in {path}")

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

        return [
            {
                key: (value or "").strip()
                for key, value in row.items()
            }
            for row in reader
        ]


def normalize_text(value: Any) -> str:
    """Normalize card and product text for semantic grouping."""
    text = str(value or "").strip()
    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = re.sub(
        r"^M(?=[A-Z][a-z])",
        "M ",
        text,
    )

    text = text.casefold()
    text = text.replace("-ex", " ex")
    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())


def canonical_semantic_terms(card: dict[str, Any]) -> tuple[str, ...]:
    """Return normalized ability and attack terms for one canonical card."""
    terms: list[str] = []

    abilities = card.get("abilities", [])

    if isinstance(abilities, list):
        for ability in abilities:
            if isinstance(ability, dict):
                name = normalize_text(ability.get("name"))

                if name:
                    terms.append(name)

    attacks = card.get("attacks", [])

    if isinstance(attacks, list):
        for attack in attacks:
            if isinstance(attack, dict):
                name = normalize_text(attack.get("name"))

                if name:
                    terms.append(name)

    return tuple(terms)


def product_name_parts(
    product_name: Any,
) -> tuple[str, tuple[str, ...]]:
    """Split a Cardmarket product name into base name and bracket terms."""
    original = str(product_name or "").strip()

    match = re.match(
        r"^(.*?)\s*(?:\[([^\]]*)])?\s*$",
        original,
    )

    if not match:
        return normalize_text(original), ()

    base_name = normalize_text(match.group(1))
    bracket_text = match.group(2) or ""

    terms = tuple(
        normalized_part
        for part in bracket_text.split("|")
        if (
            (normalized_part := normalize_text(part))
            and normalized_part not in IGNORED_PRODUCT_TERMS
        )
    )

    return base_name, terms


def canonical_signature(
    card: dict[str, Any],
) -> tuple[str, tuple[str, ...]]:
    """Build a canonical semantic signature."""
    return (
        normalize_text(card.get("name")),
        canonical_semantic_terms(card),
    )


def product_signature(
    product: dict[str, Any],
) -> tuple[str, tuple[str, ...]]:
    """Build a Cardmarket semantic signature."""
    return product_name_parts(product.get("name"))


def collector_number_key(value: Any) -> tuple[int, str]:
    """Sort numeric collector numbers before non-numeric values."""
    text = str(value or "").strip()

    if text.isdigit():
        return int(text), ""

    return 999999, text.casefold()


def main() -> None:
    required_files = (
        CANONICAL_CARDS_FILE,
        CARDMARKET_PRODUCTS_FILE,
        MAPPING_REVIEW_FILE,
    )

    for path in required_files:
        require_file(path)

    cards = load_json_records(CANONICAL_CARDS_FILE)
    products = load_json_records(CARDMARKET_PRODUCTS_FILE)
    mapping_rows = load_mapping_rows(MAPPING_REVIEW_FILE)

    cards_by_signature: dict[
        tuple[str, tuple[str, ...]],
        list[dict[str, Any]],
    ] = defaultdict(list)

    products_by_signature: dict[
        tuple[str, tuple[str, ...]],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for card in cards:
        cards_by_signature[canonical_signature(card)].append(card)

    for product in products:
        products_by_signature[product_signature(product)].append(product)

    listing_rows_by_card_id: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for row in mapping_rows:
        if row.get("mapping_status") != "ambiguous":
            continue

        card_id = row.get("canonical_card_id", "")

        if card_id:
            listing_rows_by_card_id[card_id].append(row)

    ambiguous_signatures = []

    for signature, signature_cards in cards_by_signature.items():
        signature_products = products_by_signature.get(signature, [])

        if len(signature_cards) > 1 or len(signature_products) > 1:
            if signature_cards and signature_products:
                ambiguous_signatures.append(
                    (
                        signature,
                        signature_cards,
                        signature_products,
                    )
                )

    ambiguous_signatures.sort(
        key=lambda item: min(
            collector_number_key(card.get("number"))
            for card in item[1]
        )
    )

    print("Primal Clash edition-group analysis")
    print()
    print(f"Ambiguous semantic groups: {len(ambiguous_signatures):,}")

    for index, (
        signature,
        signature_cards,
        signature_products,
    ) in enumerate(ambiguous_signatures, start=1):
        normalized_name, terms = signature

        sorted_cards = sorted(
            signature_cards,
            key=lambda card: collector_number_key(
                card.get("number")
            ),
        )

        sorted_products = sorted(
            signature_products,
            key=lambda product: int(product["idProduct"]),
        )

        print()
        print(
            f"Group {index}: {normalized_name} | "
            f"terms={list(terms)}"
        )

        print("  Canonical cards:")

        for card in sorted_cards:
            card_id = str(card.get("id", "")).strip()
            listing_rows = listing_rows_by_card_id.get(card_id, [])

            listing_urls = sorted(
                {
                    row.get("listing_url", "")
                    for row in listing_rows
                    if row.get("listing_url", "")
                }
            )

            print(
                f"  - {card_id} | "
                f"#{card.get('number', '')} | "
                f"{card.get('name', '')}"
            )

            for listing_url in listing_urls:
                print(f"      listing: {listing_url}")

        print("  Cardmarket products:")

        for product in sorted_products:
            print(
                f"  - idProduct={product.get('idProduct', '')} | "
                f"idMetacard={product.get('idMetacard', '')} | "
                f"dateAdded={product.get('dateAdded', '')} | "
                f"{product.get('name', '')}"
            )

    print()
    print("Edition-group analysis completed.")
    print("No mappings were modified.")


if __name__ == "__main__":
    main()