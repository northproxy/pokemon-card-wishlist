"""
Script: merge_primal_clash_listing_parts.py

Purpose:
    Merge the four partial Primal Clash Cardmarket listing exports into one
    validated CSV containing direct Cardmarket product IDs.

    Rows are deduplicated by listing URL. The script rejects conflicting
    URL-to-product-ID mappings and excludes unsuccessful HTTP responses from
    the final merged output.

Lifecycle:
    Temporary discovery utility.

Removal:
    May be deleted after the merged listing is accepted as a raw project
    source and equivalent import validation exists in the permanent pipeline.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TMP_DIR = REPO_ROOT / "tmp"
OUTPUT_FILE = TMP_DIR / "primal_clash_de_merged.csv"

INPUT_FILES = (
    TMP_DIR / "primal_clash_de_with_product_ids.csv",
    TMP_DIR / "primal_clash_page1_resume_from_52.csv",
    TMP_DIR / "primal_clash_page2.csv",
    TMP_DIR / "primal_clash_page2_resume_from_30.csv",
)

OUTPUT_COLUMNS = (
    "card_name",
    "set_name",
    "set_code",
    "card_number",
    "url",
    "id_product",
    "edition_code",
    "http_status",
)


def require_file(path: Path) -> None:
    """Stop execution when a required input file does not exist."""
    if not path.is_file():
        raise FileNotFoundError(f"Required input file not found: {path}")


def load_rows(path: Path) -> list[dict[str, str]]:
    """Load one semicolon-separated browser export."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        actual_columns = set(reader.fieldnames or [])
        missing_columns = set(OUTPUT_COLUMNS) - actual_columns

        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(
                f"Missing columns in {path.name}: {missing}"
            )

        return [
            {
                column: (row.get(column) or "").strip()
                for column in OUTPUT_COLUMNS
            }
            for row in reader
        ]


def numeric_sort_key(row: dict[str, str]) -> tuple[int, str, str]:
    """Sort numeric collector numbers first, then version and URL."""
    card_number = row["card_number"]

    number = int(card_number) if card_number.isdigit() else 999999

    return (
        number,
        row["edition_code"],
        row["url"],
    )


def main() -> None:
    for path in INPUT_FILES:
        require_file(path)

    all_rows: list[dict[str, str]] = []

    print("Input files:")

    for path in INPUT_FILES:
        rows = load_rows(path)
        all_rows.extend(rows)

        status_counts = Counter(
            row["http_status"]
            for row in rows
        )

        print(
            f"- {path.name}: {len(rows):,} rows | "
            f"statuses={dict(sorted(status_counts.items()))}"
        )

    successful_rows = [
        row
        for row in all_rows
        if row["http_status"] == "200" and row["id_product"]
    ]

    rows_by_url: dict[str, dict[str, str]] = {}
    duplicate_rows = 0

    for row in successful_rows:
        url = row["url"]

        if not url:
            raise ValueError("Successful row has an empty URL.")

        existing = rows_by_url.get(url)

        if existing is None:
            rows_by_url[url] = row
            continue

        duplicate_rows += 1

        if existing["id_product"] != row["id_product"]:
            raise ValueError(
                "Conflicting id_product values for URL:\n"
                f"URL: {url}\n"
                f"First: {existing['id_product']}\n"
                f"Second: {row['id_product']}"
            )

        comparable_columns = (
            "card_name",
            "set_name",
            "set_code",
            "card_number",
            "edition_code",
        )

        for column in comparable_columns:
            if existing[column] != row[column]:
                raise ValueError(
                    f"Conflicting {column} values for URL:\n"
                    f"URL: {url}\n"
                    f"First: {existing[column]!r}\n"
                    f"Second: {row[column]!r}"
                )

    merged_rows = sorted(
        rows_by_url.values(),
        key=numeric_sort_key,
    )

    product_to_urls: dict[str, list[str]] = {}

    for row in merged_rows:
        product_to_urls.setdefault(
            row["id_product"],
            [],
        ).append(row["url"])

    shared_product_ids = {
        product_id: urls
        for product_id, urls in product_to_urls.items()
        if len(urls) > 1
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=OUTPUT_COLUMNS,
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(merged_rows)

    card_rows = [
        row
        for row in merged_rows
        if row["card_number"].isdigit()
    ]

    non_numeric_rows = [
        row
        for row in merged_rows
        if not row["card_number"].isdigit()
    ]

    print()
    print(f"Combined input rows: {len(all_rows):,}")
    print(f"Successful input rows: {len(successful_rows):,}")
    print(f"Duplicate successful rows removed: {duplicate_rows:,}")
    print(f"Merged unique rows: {len(merged_rows):,}")
    print(f"Numeric collector-number rows: {len(card_rows):,}")
    print(f"Non-numeric rows: {len(non_numeric_rows):,}")
    print(f"Unique idProduct values: {len(product_to_urls):,}")
    print(
        "idProduct values referenced by multiple URLs: "
        f"{len(shared_product_ids):,}"
    )

    if shared_product_ids:
        print()
        print("Shared idProduct values:")

        for product_id in sorted(shared_product_ids, key=int):
            print(f"- {product_id}")

            for url in shared_product_ids[product_id]:
                print(f"    {url}")

    print()
    print(f"Output file: {OUTPUT_FILE}")
    print("Original source files were not modified.")


if __name__ == "__main__":
    main()