# NexBoot — Developer Manual

## §1 Prerequisites

- Python 3.8 or later (stdlib only; no third-party runtime dependencies)
- `pytest` and `pytest-cov` for testing
- `ruff` for linting

```bash
pip install pytest pytest-cov ruff
```

---

## §2 Install and Run

Clone the repository:

```bash
git clone https://github.com/NeuralNexim/NexBoot.git
cd NexBoot
```

Assemble a disk image from a NexTinyOS artifact bundle:

```bash
python3 nexboot.py \
  --manifest build/installer-artifacts/build-manifest.json \
  --artifacts build/installer-artifacts/ \
  --output hdd.img
```

Validate an artifact bundle without writing an image:

```bash
python3 nexboot.py \
  --manifest build/installer-artifacts/build-manifest.json \
  --artifacts build/installer-artifacts/ \
  --dry-run --verbose
```

---

## §3 CLI Reference

```
nexboot.py --manifest PATH --artifacts DIR [options]

Required:
  --manifest  PATH   Path to build-manifest.json
  --artifacts DIR    Directory containing the artifact files

Optional:
  --output    PATH   Output disk image path    (default: hdd.img)
  --abi-check INT    Reject manifests with a different ABI version  (default: 1)
  --size-kb   INT    Output image size in KB   (default: 16384 = 16 MB)
  --dry-run          Validate manifest and artifacts; do not write image
  --verbose          Print patch offsets and SHA256 verification
  --help             Show this message
```

---

## §4 lib/ Module Reference

### lib/manifest.py

| Symbol | Type | Description |
|--------|------|-------------|
| `ManifestError` | `Exception` | Raised on any manifest or artifact validation failure |
| `parse(path)` | `dict` | Load and JSON-decode a manifest file |
| `validate(manifest, artifacts_dir, abi_check=1)` | `None` | Deep-validate manifest dict and artifact files |
| `BOOTLOADER_SIZE_EXPECTED` | `int` | 512 — enforced exact size for `bootloader.bin` |
| `STAGE2_SIZE_EXPECTED` | `int` | 65024 — enforced exact size for `stage2.bin` |
| `KERNEL_SECS_MAX` | `int` | 65535 — maximum value for LE16 `KERNEL_SECS` field |

### lib/patcher.py

| Symbol | Type | Description |
|--------|------|-------------|
| `apply(image, manifest, verbose=False)` | `None` | Patch KERNEL_SECS → SB_LBA → CRC32 in-place in `image` |

### lib/image.py

| Symbol | Type | Description |
|--------|------|-------------|
| `create(size_kb)` | `bytearray` | Zero-filled image of `size_kb × 1024` bytes |
| `write_artifact(image, data, lba)` | `None` | Write `data` into `image` at `lba × 512`; bounds-checked |
| `load_artifact(artifacts_dir, name)` | `bytes` | Read artifact file bytes |
| `save(image, path)` | `None` | Write image bytearray to disk |

---

## §5 Testing

Run all tests:

```bash
pytest tests/
```

Run with coverage report:

```bash
pytest tests/ --cov=lib --cov=nexboot --cov-report=term-missing
```

Coverage on all changed files must be **≥ 95 %** before committing.

---

## §6 Extending NexBoot (New ABI Version)

When NexBoot ABI v2 is defined (e.g. adding Ed25519 signing):

1. Update `SUPPORTED_ABI_VERSIONS` in `lib/manifest.py`.
2. Extend `validate()` with new ABI v2 field checks (gate on `abi_version == 2`).
3. Update `apply()` in `lib/patcher.py` if patch offsets change.
4. Increment `--abi-check` default to `2` in `nexboot.py` (or keep at `1`
   for backward compatibility — document the choice).
5. Update `docs/developer-manual.md` ABI version table.
6. Update `README.md` ABI compatibility table.
7. Tag a new minor version `vX.1`.
