## Downloading raw card images

Raw card images can be downloaded from Pokemon TCG Data JSON set files using:

```powershell
py ./scripts/images/download_card_images.py <set_code>
```

Example:

```powershell
py ./scripts/images/download_card_images.py xy5
```

Images are stored under:

```text
images/raw/<set_code>/
```

See [`scripts/images/README.md`](../scripts/images/README.md) for full usage, configuration, behaviour, and validation details.
