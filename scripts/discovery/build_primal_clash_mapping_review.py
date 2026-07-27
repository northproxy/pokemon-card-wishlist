"""
Script: build_primal_clash_mapping_review.py

Purpose:
    Build a review-oriented CSV that connects Primal Clash canonical cards,
    scraped Cardmarket listing rows, Cardmarket products, and price records.

    The primary mapping evidence is the direct Cardmarket product ID extracted
    from each individual Cardmarket product page:

        listing.id_product -> product.idProduct

    Canonical collector numbers connect listing rows to canonical cards.
    Normalized names, abilities, and attacks are used as validation evidence,
    not as a fallback that silently chooses a different product.

    Online Code Cards remain explicitly excluded from the MVP card scope.
    Unreferenced Cardmarket products remain visible as unmatched evidence.

Lifecycle:
    Permanent project utility.

Removal:
    Keep this script while Primal Clash remains the reference vertical slice.
    It may be replaced only by a generalized mapping pipeline that preserves
    equivalent direct-ID evidence, statuses, and validation output.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "primal-clash"
CARDMARKET_RAW_DIR = REPO_ROOT / "data" / "raw" / "cardmarket"

CANONICAL_CARDS_FILE = FIXTURE_DIR / "canonical-cards.json"
CARDMARKET_PRODUCTS_FILE = FIXTURE_DIR / "cardmarket-products.json"
CARDMARKET_PRICES_FILE = FIXTURE_DIR / "cardmarket-prices.json"
LISTING_FILE = CARDMARKET_RAW_DIR / "primal_clash_de.csv"

OUTPUT_FILE = FIXTURE_DIR / "mapping-review.csv"

SUPPORTED_SET_CODE = "PRC"

IGNORED_PRODUCT_TERMS = {
    "primal clash",
}

OUTPUT_COLUMNS = (
    "canonical_card_id",
    "collector_number",
    "canonical_name",
    "listing_name",
    "listing_url",
    "edition_code",
    "cardmarket_product_id",
    "cardmarket_product_name",
    "cardmarket_metacard_id",
    "mapping_status",
    "mapping_method",
    "evidence",
    "avg30",
    "avg30_holo",
    "price_snapshot_at",
)


def require_file(path: Path) -> None:
    """Stop execution when a required source file does not exist."""
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")


def load_json_object(path: Path) -> dict[str, Any]:
    """Load one fixture JSON document and validate its top-level structure."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")

    return payload


def get_records(
    payload: dict[str, Any],
    source_name: str,
) -> list[dict[str, Any]]:
    """Extract and validate the records list from a fixture document."""
    records = payload.get("records")

    if not isinstance(records, list):
        raise ValueError(f"'records' must be a list in {source_name}")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(
                f"Record {index} must be an object in {source_name}"
            )

    return records


def load_listing_rows(path: Path) -> list[dict[str, str]]:
    """Load the semicolon-separated Cardmarket listing with direct IDs."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        required_columns = {
            "card_name",
            "set_name",
            "set_code",
            "card_number",
            "url",
            "id_product",
            "edition_code",
            "http_status",
        }

        actual_columns = set(reader.fieldnames or [])
        missing_columns = required_columns - actual_columns

        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(
                f"Missing listing columns in {path.name}: {missing}"
            )

        rows = [
            {
                key: (value or "").strip()
                for key, value in row.items()
            }
            for row in reader
        ]

    duplicate_urls = [
        url
        for url, count in Counter(
            row["url"]
            for row in rows
            if row["url"]
        ).items()
        if count > 1
    ]

    if duplicate_urls:
        duplicate_text = "\n".join(
            f"- {url}"
            for url in sorted(duplicate_urls)
        )

        raise ValueError(
            "Listing file contains duplicate URLs:\n"
            f"{duplicate_text}"
        )

    return rows


def normalize_text(value: Any) -> str:
    """
    Normalize source text for conservative semantic comparison.

    Cardmarket may omit the space after the Mega marker:

        MGardevoir EX -> M Gardevoir-EX
        MAggron EX -> M Aggron-EX

    Original source values are preserved.
    """
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


def normalize_collector_number(value: Any) -> str:
    """Normalize collector numbers while preserving non-numeric suffixes."""
    text = str(value or "").strip()

    if text.isdigit():
        return str(int(text))

    return text.casefold()


def collector_number_sort_key(value: Any) -> tuple[int, str]:
    """Sort numeric collector numbers before non-numeric values."""
    normalized = normalize_collector_number(value)

    if normalized.isdigit():
        return int(normalized), ""

    return 999999, normalized


def canonical_semantic_terms(card: dict[str, Any]) -> list[str]:
    """Collect normalized ability and attack names from a canonical card."""
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
    Split a Cardmarket product name into base name and semantic terms.

    Example:

        Sceptile [Leaf Blade | Power Poison]

    becomes:

        ("sceptile", ["leaf blade", "power poison"])
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

    terms = [
        normalized_part
        for part in bracket_text.split("|")
        if (
            (normalized_part := normalize_text(part))
            and normalized_part not in IGNORED_PRODUCT_TERMS
        )
    ]

    return base_name, terms


def semantic_validation(
    card: dict[str, Any],
    product: dict[str, Any],
) -> tuple[bool, str]:
    """
    Validate a direct listing-to-product mapping semantically.

    The direct product ID remains the source relationship. A failed semantic
    check produces a conflict row and does not select another product.
    """
    canonical_name = normalize_text(card.get("name"))
    canonical_terms = canonical_semantic_terms(card)

    product_name, product_terms = product_name_parts(
        product.get("name")
    )

    if canonical_name != product_name:
        return (
            False,
            (
                "Normalized card and product names differ: "
                f"canonical={canonical_name!r}; "
                f"product={product_name!r}."
            ),
        )

    if product_terms and product_terms != canonical_terms:
        return (
            False,
            (
                "Cardmarket semantic terms differ from canonical "
                "ability/attack terms: "
                f"canonical_terms={canonical_terms}; "
                f"product_terms={product_terms}."
            ),
        )

    return (
        True,
        (
            "Direct idProduct relationship validated; "
            f"canonical_name={canonical_name!r}; "
            f"canonical_terms={canonical_terms}; "
            f"product_terms={product_terms}."
        ),
    )


def extract_edition_code(url: str) -> str:
    """Extract a Cardmarket version marker such as V1 or V2 from a URL."""
    match = re.search(
        r"-(V\d+)(?:-|$)",
        url,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return match.group(1).upper()


def is_online_code_card(name: Any) -> bool:
    """Identify code-card products that are excluded from the MVP."""
    return "online code card" in normalize_text(name)


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    """Write a deterministic UTF-8 CSV suitable for review in VS Code."""
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=OUTPUT_COLUMNS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def empty_output_row() -> dict[str, Any]:
    """Return one output row with every expected column present."""
    return {
        column: ""
        for column in OUTPUT_COLUMNS
    }


def build_unique_lookup(
    records: list[dict[str, Any]],
    key_name: str,
    source_name: str,
) -> dict[str, dict[str, Any]]:
    """Build a lookup and reject duplicate non-empty source identifiers."""
    lookup: dict[str, dict[str, Any]] = {}

    for record in records:
        key = str(record.get(key_name, "")).strip()

        if not key:
            continue

        if key in lookup:
            raise ValueError(
                f"Duplicate {key_name}={key!r} in {source_name}"
            )

        lookup[key] = record

    return lookup

def is_unmatched_duplicate_candidate(
    product: dict[str, Any],
    all_products: list[dict[str, Any]],
    directly_referenced_product_ids: set[str],
) -> bool:
    """
    Return True when an unlisted product differs from a directly mapped
    sibling only by idProduct and dateAdded.
    """
    product_id = str(product.get("idProduct", "")).strip()
    metacard_id = str(product.get("idMetacard", "")).strip()

    if not product_id or not metacard_id:
        return False

    ignored_fields = {
        "idProduct",
        "dateAdded",
    }

    sibling_products = [
        sibling
        for sibling in all_products
        if (
            str(sibling.get("idProduct", "")).strip()
            in directly_referenced_product_ids
            and str(sibling.get("idMetacard", "")).strip()
            == metacard_id
        )
    ]

    for sibling in sibling_products:
        comparison_fields = (
            set(product)
            | set(sibling)
        ) - ignored_fields

        if all(
            product.get(field) == sibling.get(field)
            for field in comparison_fields
        ):
            return True

    return False


def main() -> None:
    required_files = (
        CANONICAL_CARDS_FILE,
        CARDMARKET_PRODUCTS_FILE,
        CARDMARKET_PRICES_FILE,
        LISTING_FILE,
    )

    for path in required_files:
        require_file(path)

    canonical_payload = load_json_object(CANONICAL_CARDS_FILE)
    products_payload = load_json_object(CARDMARKET_PRODUCTS_FILE)
    prices_payload = load_json_object(CARDMARKET_PRICES_FILE)

    canonical_cards = get_records(
        canonical_payload,
        CANONICAL_CARDS_FILE.name,
    )
    products = get_records(
        products_payload,
        CARDMARKET_PRODUCTS_FILE.name,
    )
    prices = get_records(
        prices_payload,
        CARDMARKET_PRICES_FILE.name,
    )
    listing_rows = load_listing_rows(LISTING_FILE)

    price_snapshot_at = str(
        prices_payload.get("sourceCreatedAt") or ""
    )

    products_by_id = build_unique_lookup(
        products,
        "idProduct",
        CARDMARKET_PRODUCTS_FILE.name,
    )

    prices_by_product_id = build_unique_lookup(
        prices,
        "idProduct",
        CARDMARKET_PRICES_FILE.name,
    )

    canonical_cards_by_number: dict[
        str,
        dict[str, Any],
    ] = {}

    for card in canonical_cards:
        collector_number = normalize_collector_number(
            card.get("number")
        )

        if not collector_number:
            raise ValueError(
                "Canonical card has an empty collector number: "
                f"{card.get('id', '')}"
            )

        if collector_number in canonical_cards_by_number:
            existing = canonical_cards_by_number[collector_number]

            raise ValueError(
                "Duplicate canonical collector number:\n"
                f"Number: {collector_number}\n"
                f"First: {existing.get('id', '')}\n"
                f"Second: {card.get('id', '')}"
            )

        canonical_cards_by_number[collector_number] = card

    output_rows: list[dict[str, Any]] = []

    referenced_product_ids: set[str] = set()
    referenced_canonical_card_ids: set[str] = set()

    for listing_row in sorted(
        listing_rows,
        key=lambda row: (
            collector_number_sort_key(row["card_number"]),
            row["edition_code"],
            row["url"],
        ),
    ):
        set_code = listing_row["set_code"]
        collector_number = normalize_collector_number(
            listing_row["card_number"]
        )
        listing_url = listing_row["url"]
        listing_product_id = listing_row["id_product"]
        http_status = listing_row["http_status"]

        row = empty_output_row()

        row.update(
            {
                "collector_number": collector_number,
                "listing_name": listing_row["card_name"],
                "listing_url": listing_url,
                "edition_code": (
                    listing_row["edition_code"]
                    or extract_edition_code(listing_url)
                ),
                "cardmarket_product_id": listing_product_id,
                "price_snapshot_at": price_snapshot_at,
            }
        )

        if set_code != SUPPORTED_SET_CODE:
            row.update(
                {
                    "mapping_status": "excluded",
                    "mapping_method": "listing_scope_rule",
                    "evidence": (
                        f"Listing set code {set_code!r} is outside "
                        f"supported set code {SUPPORTED_SET_CODE!r}."
                    ),
                }
            )
            output_rows.append(row)
            continue

        if not collector_number.isdigit():
            row.update(
                {
                    "mapping_status": "excluded",
                    "mapping_method": "listing_scope_rule",
                    "evidence": (
                        "Listing row is outside the supported numeric "
                        "collector-number card scope."
                    ),
                }
            )
            output_rows.append(row)
            continue

        if http_status != "200":
            row.update(
                {
                    "mapping_status": "conflict",
                    "mapping_method": "listing_http_validation",
                    "evidence": (
                        "Listing row was not collected from a successful "
                        f"HTTP response: http_status={http_status!r}."
                    ),
                }
            )
            output_rows.append(row)
            continue

        if not listing_product_id:
            row.update(
                {
                    "mapping_status": "conflict",
                    "mapping_method": "direct_listing_product_id",
                    "evidence": (
                        "Successful listing row does not contain id_product."
                    ),
                }
            )
            output_rows.append(row)
            continue

        canonical_card = canonical_cards_by_number.get(
            collector_number
        )

        if canonical_card is None:
            product = products_by_id.get(listing_product_id)
            price = prices_by_product_id.get(listing_product_id, {})

            if product is not None:
                row.update(
                    {
                        "cardmarket_product_name": str(
                            product.get("name", "")
                        ),
                        "cardmarket_metacard_id": str(
                            product.get("idMetacard", "")
                        ),
                        "avg30": price.get("avg30", ""),
                        "avg30_holo": price.get("avg30-holo", ""),
                    }
                )

            row.update(
                {
                    "mapping_status": "conflict",
                    "mapping_method": (
                        "collector_number_and_direct_product_id"
                    ),
                    "evidence": (
                        "Listing collector number does not exist in the "
                        "canonical Primal Clash fixture."
                    ),
                }
            )
            output_rows.append(row)
            continue

        canonical_card_id = str(
            canonical_card.get("id", "")
        ).strip()

        canonical_name = str(
            canonical_card.get("name", "")
        ).strip()

        row.update(
            {
                "canonical_card_id": canonical_card_id,
                "canonical_name": canonical_name,
            }
        )

        referenced_canonical_card_ids.add(canonical_card_id)

        product = products_by_id.get(listing_product_id)

        if product is None:
            row.update(
                {
                    "mapping_status": "conflict",
                    "mapping_method": "direct_listing_product_id",
                    "evidence": (
                        "Listing id_product does not exist in the "
                        "Cardmarket product fixture."
                    ),
                }
            )
            output_rows.append(row)
            continue

        product_name = str(product.get("name", "")).strip()
        metacard_id = str(product.get("idMetacard", "")).strip()

        price = prices_by_product_id.get(
            listing_product_id,
            {},
        )

        row.update(
            {
                "cardmarket_product_name": product_name,
                "cardmarket_metacard_id": metacard_id,
                "avg30": price.get("avg30", ""),
                "avg30_holo": price.get("avg30-holo", ""),
            }
        )

        if is_online_code_card(product_name):
            row.update(
                {
                    "mapping_status": "excluded",
                    "mapping_method": "product_scope_rule",
                    "evidence": (
                        "Online Code Card is outside MVP catalogue scope."
                    ),
                }
            )
            output_rows.append(row)
            referenced_product_ids.add(listing_product_id)
            continue

        semantic_valid, semantic_evidence = semantic_validation(
            canonical_card,
            product,
        )

        if not semantic_valid:
            row.update(
                {
                    "mapping_status": "conflict",
                    "mapping_method": (
                        "direct_listing_product_id_with_"
                        "semantic_validation"
                    ),
                    "evidence": semantic_evidence,
                }
            )
            output_rows.append(row)
            referenced_product_ids.add(listing_product_id)
            continue

        row.update(
            {
                "mapping_status": "candidate",
                "mapping_method": (
                    "collector_number_and_direct_listing_product_id"
                ),
                "evidence": (
                    "Canonical card matched by collector number. "
                    "Cardmarket product matched by direct id_product "
                    "extracted from the individual listing page. "
                    f"{semantic_evidence}"
                ),
            }
        )

        output_rows.append(row)
        referenced_product_ids.add(listing_product_id)

    for card in sorted(
        canonical_cards,
        key=lambda item: (
            collector_number_sort_key(item.get("number")),
            str(item.get("id", "")),
        ),
    ):
        card_id = str(card.get("id", "")).strip()

        if card_id in referenced_canonical_card_ids:
            continue

        row = empty_output_row()

        row.update(
            {
                "canonical_card_id": card_id,
                "collector_number": normalize_collector_number(
                    card.get("number")
                ),
                "canonical_name": str(card.get("name", "")).strip(),
                "mapping_status": "unmatched",
                "mapping_method": "collector_number_listing",
                "evidence": (
                    "Canonical card was not referenced by any supported "
                    "Cardmarket listing row."
                ),
                "price_snapshot_at": price_snapshot_at,
            }
        )

        output_rows.append(row)

    for product in sorted(
        products,
        key=lambda item: int(str(item.get("idProduct", "0"))),
    ):
        product_id = str(product.get("idProduct", "")).strip()

        if product_id in referenced_product_ids:
            continue

        product_name = str(product.get("name", "")).strip()
        price = prices_by_product_id.get(product_id, {})

        excluded = is_online_code_card(product_name)

        duplicate_candidate = (
            not excluded
            and is_unmatched_duplicate_candidate(
                product,
                products,
                referenced_product_ids,
            )
        )

        row = empty_output_row()

        row.update(
            {
                "cardmarket_product_id": product_id,
                "cardmarket_product_name": product_name,
                "cardmarket_metacard_id": str(
                    product.get("idMetacard", "")
                ),
                "mapping_status": (
                    "excluded"
                    if excluded
                    else (
                        "unmatched_duplicate_candidate"
                        if duplicate_candidate
                        else "unmatched"
                    )
                ),
                "mapping_method": (
                    "product_scope_rule"
                    if excluded
                    else (
                        "unlisted_duplicate_candidate_rule"
                        if duplicate_candidate
                        else "direct_listing_product_coverage"
                    )
                ),
                "evidence": (
                    "Online Code Card is outside MVP catalogue scope."
                    if excluded
                    else (
                        "Product is not referenced by a successful listing "
                        "URL and matches a directly mapped sibling in every "
                        "inspected field except idProduct and dateAdded."
                        if duplicate_candidate
                        else (
                            "Cardmarket product exists in the Primal Clash "
                            "product fixture but was not referenced by any "
                            "successful direct-ID listing row."
                        )
                    )
                ),
                "avg30": price.get("avg30", ""),
                "avg30_holo": price.get("avg30-holo", ""),
                "price_snapshot_at": price_snapshot_at,
            }
        )

        output_rows.append(row)

    output_rows.sort(
        key=lambda row: (
            collector_number_sort_key(row["collector_number"]),
            row["canonical_card_id"],
            row["edition_code"],
            row["listing_url"],
            (
                int(row["cardmarket_product_id"])
                if row["cardmarket_product_id"].isdigit()
                else 999999999
            ),
        )
    )

    write_csv(OUTPUT_FILE, output_rows)

    status_counts = Counter(
        str(row["mapping_status"])
        for row in output_rows
    )

    direct_candidate_rows = [
        row
        for row in output_rows
        if row["mapping_status"] == "candidate"
    ]

    direct_product_ids = {
        row["cardmarket_product_id"]
        for row in direct_candidate_rows
        if row["cardmarket_product_id"]
    }

    direct_canonical_ids = {
        row["canonical_card_id"]
        for row in direct_candidate_rows
        if row["canonical_card_id"]
    }

    print(f"Output file: {OUTPUT_FILE}")
    print(f"Output rows: {len(output_rows):,}")

    print()
    print("Mapping status counts:")

    for status in sorted(status_counts):
        print(f"- {status}: {status_counts[status]:,}")

    print()
    print("Direct-ID coverage:")
    print(
        "- candidate listing rows with direct idProduct: "
        f"{len(direct_candidate_rows):,}"
    )
    print(
        "- unique canonical cards referenced by candidates: "
        f"{len(direct_canonical_ids):,}"
    )
    print(
        "- unique Cardmarket products referenced by candidates: "
        f"{len(direct_product_ids):,}"
    )

    print()
    print("Important:")
    print("- candidate rows are not yet owner-confirmed mappings")
    print("- direct idProduct evidence replaces product-order guessing")
    print("- semantic mismatches are reported as conflicts")
    print("- unreferenced duplicate-like products remain visible as unmatched_duplicate_candidate evidence")
    print("- excluded products remain visible as scope evidence")


if __name__ == "__main__":
    main()