<!--
  plan/details/03_NexBoot-v1.0-release-plan.md  —  NexBoot v1.0.0 release-gate plan
-->

# Plan: NexBoot v1.0.0 Release Gates

> **Milestone tag**: NexBoot-v1.0-release
> **Repo**: `NeuralNexim/NexBoot`
> **Branch**: `feature/ci-workflow` → `release/v1.0` → `main`
> **Prerequisites**: NexBoot v1.0.0 implementation ✅ (all lib/ + tests complete)
> **Successor**: NexBoot-v1.1 (ABI enforcement formalization)
> **ABI version**: 1 (no ABI change)

---

## Prior Release Context

Facts from NexBoot v1.0.0 implementation that constrain this milestone:

1. `SUPPORTED_ABI_VERSIONS = (1,)` — tuple in `lib/manifest.py`; gate in `validate()`
2. `REQUIRED_ARTIFACTS = ("bootloader.bin", "stage2.bin", "kernel-stripped.elf", "crc32_patch.py")` — 4 required files
3. `BOOTLOADER_SIZE_EXPECTED = 512` — exact byte size enforced for `bootloader.bin`
4. `STAGE2_SIZE_EXPECTED = 65024` — exact byte size enforced for `stage2.bin` (127 × 512)
5. `KERNEL_SECS_MAX = 0xFFFF` — LE16 maximum for `kernel_secs` field at image byte 506
6. `ManifestError` — sole exception class for all manifest and artifact validation failures
7. `parse(path) -> dict` — JSON-decode; raises `ManifestError` on `FileNotFoundError`, `PermissionError`, `JSONDecodeError`, `OSError`
8. `validate(manifest, artifacts_dir, abi_check=1) -> None` — 4-layer: ABI gate → SHA256+size → formula → offset constants
9. `apply(image, manifest, verbose=False) -> None` — patches KERNEL_SECS (byte 506 LE16) → SB_LBA (byte 512 LE32) → CRC32 (bytes 512:65532, LE32 at byte 65532); order is critical
10. `create(size_kb) -> bytearray` — zero-filled image of `size_kb × 1024` bytes
11. `write_artifact(image, data, lba) -> None` — bounds-checked write at `lba × 512`
12. `load_artifact(artifacts_dir, name) -> bytes` — raises `ManifestError` on not-found, permission, or OSError
13. `save(image, path) -> None` — raises `ManifestError` on `PermissionError` or `OSError`
14. CLI flags: `--manifest`, `--artifacts`, `--output` (hdd.img), `--abi-check` (1), `--size-kb` (16384), `--dry-run`, `--verbose`
15. `pyproject.toml` ruff config: `target-version = "py38"`, `line-length = 100`, `select = ["E", "F", "W", "I"]`, `ignore = ["E501"]`
16. `tests/test_nexboot.py` — 75 passed, 2 skipped (Windows permission tests), 97% coverage
17. ABI v1 patch offset constants: `kernel_secs_offset = 506`, `nexfs_sb_lba_offset = 512`, `stage2_crc32_offset = 65532`
18. Formula invariants: `kernel_secs = ⌈kernel_elf_size / 512⌉`; `nexfs_sb_lba = 128 + ((kernel_secs + 63) & ~63)`
19. CRC32 range is `image[512:65532]` — SB_LBA bytes fall within this range so SB_LBA must be patched first
20. Branch flow: `feature/<topic>` → `release/vX.Y` → `main`; never merge feature → main directly

---

## Platform / Target

- **CI runner**: `ubuntu-latest` (GitHub Actions)
- **Python matrix**: 3.10, 3.11, 3.12
- **No-op guarantee**: all existing tests pass unchanged on Windows local dev (2 skipped via `@pytest.mark.skipif(sys.platform == "win32", ...)`)
- **Lint tool**: `ruff` — config in `pyproject.toml`; no separate `.ruff.toml`

---

## Overview

All NexBoot v1.0.0 implementation deliverables are complete and tested locally
at 97% coverage. The three remaining gating criteria before tagging `v1.0.0` are:
(1) a GitHub Actions CI workflow that runs pytest + ruff across Python 3.10/3.11/3.12,
(2) a cross-repo note in NexTinyOS `docs/developer-manual.md` linking NexBoot,
and (3) the `v1.0.0` tag itself.

This milestone delivers the CI workflow, adds two new test modules that verify
the CI configuration and v1.0.0 gating criteria as code, updates `plan/status.md`
to mark v1.0.0 complete and stub the v1.1.0 milestone, and documents the
NexTinyOS cross-repo note as a template for the maintainer to apply.

No changes to `lib/`, `nexboot.py`, or `tests/test_nexboot.py` — all library
code is stable. The `v1.0.0` tag is created on `main` after the release branch
merges and CI is confirmed green.

---

## Goals

### Core Mechanisms

- GitHub Actions workflow runs on every push and PR to `main`
- Python 3.10, 3.11, 3.12 all pass in the matrix independently (`fail-fast: false`)
- `ruff check .` passes with zero violations before pytest runs
- `pytest tests/ --cov=lib --cov=nexboot` achieves ≥ 95% coverage on every matrix entry
- All gating criteria from `plan/status.md` are codified as assertions in `tests/test_release_gate.py`

### CLI / API Changes

No CLI or public API changes in this milestone.

| Change | File | Sub-phase |
|--------|------|-----------|
| None | — | — |

### New Files

| File | Sub-phase | Purpose |
|------|-----------|---------|
| `.github/workflows/ci.yml` | a | CI pipeline: checkout → setup-python → install deps → ruff → pytest+cov |
| `tests/test_ci_config.py` | a | Assert CI YAML structure is correct (≥ 30 assertions) |
| `tests/test_release_gate.py` | b | Assert all v1.0.0 gating criteria are met as code (≥ 30 assertions) |

### Documentation

| Document | Section | Change | Sub-phase |
|----------|---------|--------|-----------|
| `plan/status.md` | v1.0.0 gates | Mark CI gates ✅ after merge | c |
| `plan/status.md` | New section | Add NexBoot v1.1.0 milestone stub | c |
| `docs/developer-manual.md` | §1 Prerequisites | Add `.venv` setup note | c |

### Tests

| Suite | Assertions | Sub-phase |
|-------|------------|-----------|
| `tests/test_ci_config.py` | ≥ 30 | a |
| `tests/test_release_gate.py` | ≥ 30 | b |
| Master integration (all suites) | ≥ 135 total | c |

---

## New Constants & Symbols

| Symbol | Type | Module | Meaning |
|--------|------|--------|---------|
| `REPO_ROOT` | `pathlib.Path` | `test_ci_config.py` | Absolute path to repo root; used to locate `.github/workflows/ci.yml` |
| `CI_WORKFLOW_PATH` | `pathlib.Path` | `test_ci_config.py` | `REPO_ROOT / ".github/workflows/ci.yml"` |
| `REPO_ROOT` | `pathlib.Path` | `test_release_gate.py` | Absolute path to repo root; used to assert required files exist |

---

## Architecture Changes

| Document / File | Section | Change |
|-----------------|---------|--------|
| `.github/workflows/ci.yml` | New file | Python matrix CI: ruff + pytest + coverage |
| `tests/test_ci_config.py` | New file | Structural assertions on the CI YAML |
| `tests/test_release_gate.py` | New file | File-existence and config assertions for v1.0.0 gates |
| `plan/status.md` | v1.0.0 table | CI gates updated to ✅ after merge |
| `plan/status.md` | New section | NexBoot v1.1.0 milestone stub added |

---

## Test Results Target

| Suite | Prior count | This milestone | Expected total |
|-------|-------------|----------------|----------------|
| `tests/test_nexboot.py` | 75 passed, 2 skipped | unchanged | 75 passed, 2 skipped |
| `tests/test_ci_config.py` | — | ≥ 30 new | ≥ 30 passed |
| `tests/test_release_gate.py` | — | ≥ 30 new | ≥ 30 passed |
| **Total** | **75 + 2 skipped** | **+≥ 60** | **≥ 135 + 2 skipped** |

Coverage target: ≥ 95% on all files touched (new test files are 100% covered by
definition; `lib/` and `nexboot.py` must stay ≥ 95%).

---

## Sub-Phase Summary

| File | Sub-phase | One-line summary |
|------|-----------|-----------------|
| [03_NexBoot-v1.0-releasea-plan.md](03_NexBoot-v1.0-releasea-plan.md) | a — Foundation | CI workflow YAML + `test_ci_config.py` (≥ 30 assertions) |
| [03_NexBoot-v1.0-releaseb-plan.md](03_NexBoot-v1.0-releaseb-plan.md) | b — Core | `test_release_gate.py` asserting all v1.0.0 gates as code (≥ 30 assertions) |
| [03_NexBoot-v1.0-releasec-plan.md](03_NexBoot-v1.0-releasec-plan.md) | c — Polish | `plan/status.md` completion + NexTinyOS cross-repo note template + master suite (≥ 60) |
