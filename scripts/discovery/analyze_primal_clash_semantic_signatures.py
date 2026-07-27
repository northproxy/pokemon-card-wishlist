"""
Script: analyze_primal_clash_semantic_signatures.py

Purpose:
    Compare Primal Clash canonical cards with Cardmarket product names using
    semantic signatures built from card names, abilities, and attacks.

    This script is diagnostic only. It reports possible matches and ambiguity
    groups but does not modify mapping-review.csv or confirm any mapping.

Lifecycle:
    Temporary discovery utility.

Removal:
    May be deleted after semantic matching rules are incorporated into the
    permanent mapping builder and equivalent validation is covered by a
    permanent script or automated test.
"""

from __future__ import annotations

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


def require_file(path: Path) -> None:
    """Stop execution when a required file does not exist."""
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")


def load_records(path: Path) -> list[dict[str, Any]]:
    """Load and validate the records array from one fixture JSON file."""
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


def normalize_text(value: Any) -> str:
    """
    Normalize source text for conservative semantic comparison.

    Cardmarket may omit the space after the Mega marker:
        MGardevoir EX -> M Gardevoir-EX
        MAggron EX -> M Aggron-EX

    Original source values are not changed.
    """
    text = str(value or "").strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    # Insert a space between the Mega marker "M" and the Pokémon name.
    text = re.sub(
        r"^M(?=[A-Z][a-z])",
        "M ",
        text,
    )

    text = text.casefold()
    text = text.replace("-ex", " ex")
    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())


def canonical_name_signature(card: dict[str, Any]) -> str:
    """Return the normalized canonical card name."""
    return normalize_text(card.get("name"))


def canonical_semantic_terms(card: dict[str, Any]) -> list[str]:
    """Collect normalized ability and attack names from one canonical card."""
    terms: list[str] = []

    abilities = card.get("abilities", [])

    if isinstance(abilities, list):
        for ability in abilities:
            if not isinstance(ability, dict):
                continue

            name = normalize_text(ability.get("name"))

            if name:
                terms.append(name)

    attacks = card.get("attacks", [])

    if isinstance(attacks, list):
        for attack in attacks:
            if not isinstance(attack, dict):
                continue

            name = normalize_text(attack.get("name"))

            if name:
                terms.append(name)

    return terms


def product_name_parts(product_name: Any) -> tuple[str, list[str]]:
    """
    Split a Cardmarket product name into base name and bracket terms.

    Example:
        'Sceptile [Leaf Blade | Power Poison]'
        becomes:
        ('sceptile', ['leaf blade', 'power poison'])
    """
    original = str(product_name or "").strip()

    match = re.match(
        r"^(.*?)\s*(?:\[([^\]]*)])?\s*$",
        original,
    )

    if not match:
        return normalize_text(original), []

    base_name = normalize_text(match.group(1))
    bracket_text = match.group(2) or ""

    ignored_terms = {
        "primal clash",
    }

    terms = [
        normalized_part
        for part in bracket_text.split("|")
        if (
            (normalized_part := normalize_text(part))
            and normalized_part not in ignored_terms
        )
    ]

    return base_name, terms


def semantic_match(
    card: dict[str, Any],
    product: dict[str, Any],
) -> bool:
    """
    Return True when base names match and Cardmarket bracket terms match
    canonical ability/attack names.

    Products without bracket terms match by normalized card name only.
    """
    card_name = canonical_name_signature(card)
    card_terms = canonical_semantic_terms(card)

    product_name, product_terms = product_name_parts(
        product.get("name")
    )

    if card_name != product_name:
        return False

    if not product_terms:
        return True

    return product_terms == card_terms


def main() -> None:
    required_files = (
        CANONICAL_CARDS_FILE,
        CARDMARKET_PRODUCTS_FILE,
    )

    for path in required_files:
        require_file(path)

    cards = load_records(CANONICAL_CARDS_FILE)
    products = load_records(CARDMARKET_PRODUCTS_FILE)

    matches_by_card: dict[str, list[dict[str, Any]]] = defaultdict(list)
    matches_by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for card in cards:
        card_id = str(card.get("id", "")).strip()

        for product in products:
            if not semantic_match(card, product):
                continue

            product_id = str(
                product.get("idProduct", "")
            ).strip()

            matches_by_card[card_id].append(product)
            matches_by_product[product_id].append(card)

    unmatched_cards = [
        card
        for card in cards
        if not matches_by_card.get(str(card.get("id", "")).strip())
    ]

    unmatched_products = [
        product
        for product in products
        if not matches_by_product.get(
            str(product.get("idProduct", "")).strip()
        )
    ]

    card_match_count_groups: dict[int, int] = defaultdict(int)

    for card in cards:
        card_id = str(card.get("id", "")).strip()
        match_count = len(matches_by_card.get(card_id, []))
        card_match_count_groups[match_count] += 1

    shared_products = {
        product_id: matched_cards
        for product_id, matched_cards in matches_by_product.items()
        if len(matched_cards) > 1
    }

    print("Semantic signature analysis")
    print()

    print(f"Canonical cards: {len(cards):,}")
    print(f"Cardmarket products: {len(products):,}")
    print(f"Unmatched canonical cards: {len(unmatched_cards):,}")
    print(f"Unmatched Cardmarket products: {len(unmatched_products):,}")
    print(
        "Products matching multiple canonical cards: "
        f"{len(shared_products):,}"
    )

    print()
    print("Canonical cards grouped by product-match count:")

    for match_count in sorted(card_match_count_groups):
        print(
            f"- {match_count} product match(es): "
            f"{card_match_count_groups[match_count]:,} card(s)"
        )

    if unmatched_cards:
        print()
        print("Unmatched canonical cards:")

        for card in unmatched_cards:
            print(
                f"- {card.get('id', '')} | "
                f"#{card.get('number', '')} | "
                f"{card.get('name', '')} | "
                f"terms={canonical_semantic_terms(card)}"
            )

    if unmatched_products:
        print()
        print("Unmatched Cardmarket products:")

        for product in sorted(
            unmatched_products,
            key=lambda item: int(item["idProduct"]),
        ):
            product_id = product.get("idProduct", "")
            product_name = product.get("name", "")

            print(f"- {product_id} | {product_name}")

    if shared_products:
        print()
        print("Products still matching multiple canonical cards:")

        for product_id in sorted(shared_products, key=int):
            product = next(
                item
                for item in products
                if str(item.get("idProduct", "")).strip()
                == product_id
            )

            card_ids = sorted(
                str(card.get("id", "")).strip()
                for card in shared_products[product_id]
            )

            print(
                f"- {product_id} | {product.get('name', '')} | "
                f"{', '.join(card_ids)}"
            )

    print()
    print("Semantic signature analysis completed.")


if __name__ == "__main__":
    main()