# Image Download Utilities

This directory contains permanent project utilities for downloading and preparing local Pokemon card images.

## `download_card_images.py`

Downloads the small and large card images referenced by a Pokemon TCG Data JSON set file.

The script supports the local image-storage workflow used by the Pokemon Card Wishlist project.

## Source data

The script reads card JSON files from:

```text
R:\_dev\Pokemon-cardmarket-bi\TEMP\pokemon-tcg-data-master\cards\en
```

Each source file must contain a JSON array of card records.

The script expects image metadata in this form:

```json
"images": {
  "small": "https://images.pokemontcg.io/xy5/1.png",
  "large": "https://images.pokemontcg.io/xy5/1_hires.png"
}
```

The `.json` extension is optional when running the script.

## Usage

Run the script from the repository root.

Without the file extension:

```powershell
py ./scripts/images/download_card_images.py xy5
```

With the file extension:

```powershell
py ./scripts/images/download_card_images.py xy5.json
```

Both commands read:

```text
R:\_dev\Pokemon-cardmarket-bi\TEMP\pokemon-tcg-data-master\cards\en\xy5.json
```

## Output

Images are stored in a separate directory for each set:

```text
images/raw/<set_code>/
```

Example:

```text
images/raw/xy5/xy5-1.png
images/raw/xy5/xy5-1_hires.png
images/raw/xy5/xy5-2.png
images/raw/xy5/xy5-2_hires.png
```

Small images use:

```text
<card_id>.png
```

Large images use:

```text
<card_id>_hires.png
```

## Behaviour

The script:

- adds the `.json` extension when it is omitted;
- reads the source file from the configured external source directory;
- creates `images/raw/<set_code>/` when it does not exist;
- downloads both `small` and `large` images when available;
- skips existing non-empty files;
- retries failed downloads;
- writes downloads to temporary `.part` files before moving them to their final filenames;
- reports downloaded, existing, failed, invalid, and missing-image counts;
- returns a non-zero exit code when downloads fail or invalid source records are found.

## Re-running the script

The script is safe to run repeatedly for the same set.

Existing non-empty files are skipped, so a repeated run downloads only missing or previously failed images.

Example:

```powershell
py ./scripts/images/download_card_images.py xy5
```

## Configuration

The main configuration values are defined near the top of the script:

```python
SOURCE_DIRECTORY
OUTPUT_ROOT_DIRECTORY
REQUEST_TIMEOUT_SECONDS
MAX_DOWNLOAD_ATTEMPTS
RETRY_DELAY_SECONDS
```

Change `SOURCE_DIRECTORY` only when the external Pokemon TCG Data repository is stored in a different location.

`OUTPUT_ROOT_DIRECTORY` should remain repository-relative unless the project adopts a different local image-storage layout.

## Validation

After running the script, verify that the expected set directory exists:

```powershell
Get-ChildItem ./images/raw/xy5
```

Count the downloaded PNG files:

```powershell
(Get-ChildItem ./images/raw/xy5 -Filter *.png).Count
```

Check for incomplete temporary files:

```powershell
Get-ChildItem ./images/raw/xy5 -Filter *.part
```

A successful completed run should leave no `.part` files.

### Validated `xy5` run

The complete Primal Clash image workflow was validated with:

```powershell
py ./scripts/images/download_card_images.py xy5
```

Observed result:

- `164` card records were processed;
- `328` PNG files were present under `images/raw/xy5/`;
- no `.part` files remained;
- a repeated run downloaded `0` files;
- the repeated run skipped `328` existing files;
- failed downloads: `0`;
- invalid card records: `0`;
- missing image data: `0`.

This validates the complete `xy5` download and observed repeat-run behaviour. It does not validate image dimensions, PNG signatures, content hashes, licensing requirements, backup, restore, or Raspberry Pi storage behaviour.

## Known limitations

- The script trusts the image URLs stored in the source JSON file.
- It does not currently validate image dimensions.
- It does not currently verify PNG file signatures or content hashes.
- It does not remove local files that disappear from a later source file.
- It processes one set JSON file per invocation.
- The external source directory is currently configured as a local Windows path.
- Remote image availability depends on the external image host.

## Project role

This script is a permanent project utility that supports local image preparation for catalogue imports.

It does not import database records and does not modify catalogue, market, mapping, or wishlist data.

The script may later be called by the permanent import pipeline, but it should remain independently executable for validation, recovery, and selective set downloads.
