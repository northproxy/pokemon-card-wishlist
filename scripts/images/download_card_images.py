"""
Script: download_card_images.py

Usage:
    py ./scripts/images/download_card_images.py xy5
    py ./scripts/images/download_card_images.py xy5.json

Purpose:
    Download small and large Pokémon card images using image URLs stored
    in a Pokémon TCG Data JSON set file.

    The script reads a JSON file from the configured external source
    directory and stores downloaded images inside the repository using
    a separate directory for each set.

    Example output for the "xy5" set:

        images/raw/xy5/xy5-1.png
        images/raw/xy5/xy5-1_hires.png

Lifecycle:
    Permanent project utility.

Removal:
    This script should remain in the repository while local card images
    are downloaded directly from Pokémon TCG Data JSON source files.

    It may be replaced only after equivalent image download, validation,
    retry, and local-storage behaviour is implemented in the permanent
    catalogue import pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# External directory containing Pokémon TCG Data card JSON files.
SOURCE_DIRECTORY = Path(
    r"R:\_dev\Pokemon-cardmarket-bi"
    r"\TEMP\pokemon-tcg-data-master\cards\en"
)

# Repository-relative root directory for downloaded raw images.
OUTPUT_ROOT_DIRECTORY = Path("images") / "raw"

# Network request settings.
REQUEST_TIMEOUT_SECONDS = 30
MAX_DOWNLOAD_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

# Identify the project when requesting files from the remote image server.
USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "Pokemon-Card-Wishlist-Image-Downloader/1.0"
)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    The JSON extension is optional.

    Examples:
        py ./scripts/images/download_card_images.py xy5
        py ./scripts/images/download_card_images.py xy5.json
    """

    parser = argparse.ArgumentParser(
        description=(
            "Download Pokémon card images from a Pokémon TCG Data "
            "JSON set file."
        )
    )

    parser.add_argument(
        "file_name",
        help=(
            "Set JSON filename. The .json extension is optional, "
            "for example: xy5 or xy5.json."
        ),
    )

    return parser.parse_args()


def resolve_source_file(file_name: str) -> Path:
    """
    Build the complete path to the source JSON file.

    Only the supplied filename is used. Any directory component passed
    by the user is ignored because source files must come from the
    configured SOURCE_DIRECTORY.
    """

    supplied_path = Path(file_name)

    # Add the JSON extension automatically when it is missing.
    if supplied_path.suffix.lower() != ".json":
        supplied_path = supplied_path.with_suffix(".json")

    return SOURCE_DIRECTORY / supplied_path.name


def load_cards(source_file: Path) -> list[dict[str, Any]]:
    """
    Load and validate the top-level JSON structure.

    The Pokémon TCG Data card files are expected to contain a JSON array
    where every array item represents one card.
    """

    try:
        with source_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except FileNotFoundError as error:
        raise RuntimeError(
            f"Source file not found: {source_file}"
        ) from error

    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid JSON in {source_file}: "
            f"line {error.lineno}, column {error.colno}."
        ) from error

    except OSError as error:
        raise RuntimeError(
            f"Could not read source file {source_file}: {error}"
        ) from error

    if not isinstance(data, list):
        raise RuntimeError(
            f"Expected a JSON array in {source_file}, "
            f"but found {type(data).__name__}."
        )

    cards: list[dict[str, Any]] = []

    for item in data:
        if isinstance(item, dict):
            cards.append(item)
        else:
            # Preserve validation responsibility in main(), where invalid
            # source records can be counted and reported.
            cards.append({"__invalid_source_record__": item})

    return cards


def sanitize_file_name(value: str) -> str:
    """
    Replace characters that are invalid in Windows filenames.

    Pokémon TCG Data card IDs normally contain only safe characters,
    but this protects the script against unexpected future source IDs.
    """

    forbidden_characters = '<>:"/\\|?*'

    sanitized = "".join(
        "_" if character in forbidden_characters else character
        for character in value
    )

    # Windows filenames cannot end with a space or period.
    return sanitized.strip().strip(".")


def get_image_targets(
    card: dict[str, Any],
    output_directory: Path,
) -> list[tuple[str, Path]]:
    """
    Convert one card record into downloadable image targets.

    A valid card may produce:

    - one target for the small image;
    - one target for the large image.

    Invalid or incomplete image metadata produces no targets.
    """

    card_id = card.get("id")
    images = card.get("images")

    if not isinstance(card_id, str) or not card_id.strip():
        return []

    if not isinstance(images, dict):
        return []

    safe_card_id = sanitize_file_name(card_id)

    if not safe_card_id:
        return []

    targets: list[tuple[str, Path]] = []

    small_url = images.get("small")

    if isinstance(small_url, str) and small_url.strip():
        targets.append(
            (
                small_url,
                output_directory / f"{safe_card_id}.png",
            )
        )

    large_url = images.get("large")

    if isinstance(large_url, str) and large_url.strip():
        targets.append(
            (
                large_url,
                output_directory / f"{safe_card_id}_hires.png",
            )
        )

    return targets


def download_file(url: str, destination: Path) -> str:
    """
    Download one image to its final destination.

    Existing non-empty files are skipped.

    New downloads are first written to a temporary ".part" file. The
    temporary file is renamed only after the complete response has been
    received, preventing incomplete downloads from appearing as valid
    image files.

    Returns:
        "downloaded" when a new file was saved.
        "skipped" when an existing non-empty file was found.
    """

    if destination.exists() and destination.stat().st_size > 0:
        return "skipped"

    temporary_file = destination.with_suffix(
        destination.suffix + ".part"
    )

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/png,image/*;q=0.8,*/*;q=0.5",
        },
    )

    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        try:
            with urlopen(
                request,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                content = response.read()

            if not content:
                raise RuntimeError(
                    "The remote server returned an empty response."
                )

            # Ensure an old temporary file cannot affect the new download.
            temporary_file.unlink(missing_ok=True)

            temporary_file.write_bytes(content)
            temporary_file.replace(destination)

            return "downloaded"

        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            RuntimeError,
        ) as error:
            temporary_file.unlink(missing_ok=True)

            if attempt == MAX_DOWNLOAD_ATTEMPTS:
                raise RuntimeError(
                    f"Failed after {MAX_DOWNLOAD_ATTEMPTS} attempts: "
                    f"{error}"
                ) from error

            print(
                f"  Retry {attempt}/{MAX_DOWNLOAD_ATTEMPTS - 1} "
                f"after error: {error}",
                file=sys.stderr,
            )

            time.sleep(RETRY_DELAY_SECONDS)

    # This line should never be reached, but keeps the return contract
    # explicit for static analysis tools.
    raise RuntimeError("Unexpected download failure.")


def main() -> int:
    """
    Run the complete image download process.

    Returns:
        0 when all required downloads succeeded or already existed.
        1 when the source file is invalid or at least one download failed.
    """

    arguments = parse_arguments()
    source_file = resolve_source_file(arguments.file_name)

    # Use the JSON filename without ".json" as the set directory name.
    #
    # Example:
    #     xy5.json -> images/raw/xy5
    set_code = sanitize_file_name(source_file.stem)

    if not set_code:
        print(
            "Error: Could not determine a valid set code "
            "from the filename.",
            file=sys.stderr,
        )
        return 1

    output_directory = OUTPUT_ROOT_DIRECTORY / set_code

    print(f"Source file: {source_file}")
    print(
        "Output directory: "
        f"{(Path.cwd() / output_directory).resolve()}"
    )
    print()

    try:
        cards = load_cards(source_file)

    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    # Create images/raw/<set-code> when it does not already exist.
    output_directory.mkdir(parents=True, exist_ok=True)

    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    invalid_record_count = 0
    missing_image_metadata_count = 0

    # Calculate the expected number of image operations for progress output.
    total_targets = sum(
        len(get_image_targets(card, output_directory))
        for card in cards
        if "__invalid_source_record__" not in card
    )

    processed_targets = 0

    for card_number, card in enumerate(cards, start=1):
        if "__invalid_source_record__" in card:
            invalid_record_count += 1

            print(
                f"[card {card_number}/{len(cards)}] "
                "Skipped invalid card record.",
                file=sys.stderr,
            )

            continue

        card_id = card.get("id", f"record-{card_number}")

        targets = get_image_targets(
            card=card,
            output_directory=output_directory,
        )

        if not targets:
            missing_image_metadata_count += 1

            print(
                f"[card {card_number}/{len(cards)}] "
                f"{card_id}: no usable image URLs.",
                file=sys.stderr,
            )

            continue

        for url, destination in targets:
            processed_targets += 1

            try:
                result = download_file(
                    url=url,
                    destination=destination,
                )

                if result == "downloaded":
                    downloaded_count += 1
                    status = "downloaded"
                else:
                    skipped_count += 1
                    status = "already exists"

                print(
                    f"[{processed_targets}/{total_targets}] "
                    f"{destination.name}: {status}"
                )

            except RuntimeError as error:
                failed_count += 1

                print(
                    f"[{processed_targets}/{total_targets}] "
                    f"{destination.name}: FAILED — {error}",
                    file=sys.stderr,
                )

    print()
    print("Download summary")
    print("----------------")
    print(f"Set code:              {set_code}")
    print(f"Cards in JSON:         {len(cards)}")
    print(f"Downloaded images:     {downloaded_count}")
    print(f"Existing images:       {skipped_count}")
    print(f"Failed downloads:      {failed_count}")
    print(f"Invalid card records:  {invalid_record_count}")
    print(
        "Missing image data:   "
        f"{missing_image_metadata_count}"
    )

    # A failed image request or structurally invalid source record should
    # produce a non-zero process exit code for scripts and CI workflows.
    if failed_count > 0 or invalid_record_count > 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
