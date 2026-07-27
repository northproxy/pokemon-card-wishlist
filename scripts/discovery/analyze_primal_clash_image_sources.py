"""
Script: analyze_primal_clash_image_sources.py

Purpose:
    Inspect image metadata in the Primal Clash canonical-card fixture.

    The script validates that every canonical card has deterministic small and
    large image URLs and checks whether those URLs match the expected set-code
    and collector-number pattern.

    It does not download images or modify fixture data.

Lifecycle:
    Temporary discovery utility.

Removal:
    May be deleted after permanent image-source validation is added to the
    fixture validator or import pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_FILE = (
    REPO_ROOT
    / "data"
    / "fixtures"
    / "primal-clash"
    / "canonical-cards.json"
)


def load_records(path: Path) -> list[dict[str, Any]]:
    """Load canonical-card records from the fixture."""
    if not path.is_file():
        raise FileNotFoundError(f"Required fixture file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")

    records = payload.get("records")

    if not isinstance(records, list):
        raise ValueError(f"'records' must be a list in {path.name}")

    return records


def expected_paths(
    card_id: str,
    collector_number: str,
) -> tuple[str, str]:
    """Return expected URL paths for small and large card images."""
    if "-" not in card_id:
        raise ValueError(f"Unexpected canonical card ID: {card_id}")

    set_code = card_id.rsplit("-", 1)[0]

    return (
        f"/{set_code}/{collector_number}.png",
        f"/{set_code}/{collector_number}_hires.png",
    )


def main() -> None:
    records = load_records(FIXTURE_FILE)

    missing_images = []
    malformed_images = []
    unexpected_paths = []

    small_urls = set()
    large_urls = set()

    for record in records:
        card_id = str(record.get("id", "")).strip()
        collector_number = str(record.get("number", "")).strip()
        images = record.get("images")

        if not isinstance(images, dict):
            missing_images.append(
                f"{card_id or '<missing id>'}: images object missing"
            )
            continue

        small = str(images.get("small", "")).strip()
        large = str(images.get("large", "")).strip()

        if not small or not large:
            missing_images.append(
                f"{card_id}: small={bool(small)}, large={bool(large)}"
            )
            continue

        small_urls.add(small)
        large_urls.add(large)

        small_parsed = urlparse(small)
        large_parsed = urlparse(large)

        for label, parsed in (
            ("small", small_parsed),
            ("large", large_parsed),
        ):
            if (
                parsed.scheme != "https"
                or parsed.netloc != "images.pokemontcg.io"
            ):
                malformed_images.append(
                    f"{card_id}: unexpected {label} URL "
                    f"{parsed.geturl()}"
                )

        expected_small, expected_large = expected_paths(
            card_id,
            collector_number,
        )

        if small_parsed.path != expected_small:
            unexpected_paths.append(
                f"{card_id}: small path {small_parsed.path!r}, "
                f"expected {expected_small!r}"
            )

        if large_parsed.path != expected_large:
            unexpected_paths.append(
                f"{card_id}: large path {large_parsed.path!r}, "
                f"expected {expected_large!r}"
            )

    print(f"Input file: {FIXTURE_FILE}")
    print(f"Canonical cards: {len(records):,}")
    print(f"Unique small image URLs: {len(small_urls):,}")
    print(f"Unique large image URLs: {len(large_urls):,}")
    print(f"Missing image metadata: {len(missing_images):,}")
    print(f"Malformed image URLs: {len(malformed_images):,}")
    print(f"Unexpected image paths: {len(unexpected_paths):,}")

    if missing_images:
        print()
        print("Missing image metadata:")
        for item in missing_images:
            print(f"- {item}")

    if malformed_images:
        print()
        print("Malformed image URLs:")
        for item in malformed_images:
            print(f"- {item}")

    if unexpected_paths:
        print()
        print("Unexpected image paths:")
        for item in unexpected_paths:
            print(f"- {item}")

    if missing_images or malformed_images or unexpected_paths:
        raise ValueError("Image-source metadata validation failed.")

    print()
    print("Primal Clash image-source metadata validation passed.")


if __name__ == "__main__":
    main()