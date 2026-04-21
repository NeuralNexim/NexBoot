<!--
  plan/details/02_NexBoot-v1.1-plan.md  —  NexBoot v1.1.0 detail plan
-->

# Plan: NexBoot v1.1.0

> **Milestone tag**: NexBoot-v1.1
> **Repo**: `NeuralNexim/NexBoot`
> **Branch**: `feature/abi-enforcement` → `release/v1.1` → `main`
> **Prerequisites**: NexBoot v1.0.0 complete ✅
> **ABI version**: 1 (no ABI change; enforcement formalized)

---

## Problem Statement

NexBoot v1.0.0 implements the 4-layer ABI enforcement at runtime but does not
formally document the architecture boundary or enforce it in CI. This means:

- A contributor could accidentally commit `.asm`/`.c`/`.h`/`.s` source, coupling
  NexBoot to the bootloader and breaking the installer-tool separation.
- The 4-layer enforcement strategy exists in code but has no canonical design
  document, making future ABI version changes risky.
- `plan/implementation-rules.md` and `docs/developer-manual.md` have no section
  that names or explains the architecture boundary.

This milestone formalizes all four enforcement layers and adds CI-level
protection against source boundary violations.

---

## Deliverables

| File | Change | Purpose |
|------|--------|---------|
| `plan/details/02_NexBoot-v1.1-plan.md` | New | This plan document |
| `plan/implementation-rules.md` | Add §3 | Architecture boundary rules (permanent) |
| `docs/developer-manual.md` | Add §7 | Architecture boundary — roles, enforcement, ABI versioning |
| `.gitignore` | Extend | Block `*.asm`, `*.c`, `*.h`, `*.s` from staging |
| `tests/test_source_boundary.py` | New | CI test — fails if any bootloader source file appears in repo |
| `plan/status.md` | Extend | Add NexBoot v1.1.0 milestone and gating table |

No changes to `lib/`, `nexboot.py`, or `tests/test_nexboot.py` — the 4-layer
runtime enforcement is already fully implemented in v1.0.0.

---

## 4-Layer ABI Enforcement Design

These layers are already implemented in v1.0.0. This section is the canonical
design record; it informs §3 of `implementation-rules.md` and §7 of
`developer-manual.md`.

### Layer 1 — ABI Version Gate

**Where**: `lib/manifest.py`, at manifest parse time  
**What it checks**: The `abi_version` field in `build-manifest.json`

```python
SUPPORTED_ABI_VERSIONS = {1}

if manifest["abi_version"] not in SUPPORTED_ABI_VERSIONS:
    raise ManifestError(
        f"Unsupported ABI version {manifest['abi_version']}. "
        f"Supported: {SUPPORTED_ABI_VERSIONS}"
    )
```

**Why**: Prevents silently consuming a manifest generated for a future or past
ABI revision. NexBoot refuses to proceed rather than corrupt an image.

**CI gate**: `examples/nexos/build-manifest.json` always declares
`"abi_version": 1`. A breaking ABI change **must** bump this value and add a
new entry to `SUPPORTED_ABI_VERSIONS`.

---

### Layer 2 — Artifact Integrity Verification

**Where**: `lib/manifest.py`, after Layer 1, before patching  
**What it checks**: SHA256 hash + byte size of every artifact file

| Artifact | Expected size (ABI v1) | Verified by |
|----------|------------------------|-------------|
| `bootloader.bin` | exactly 512 bytes | SHA256 + size |
| `stage2.bin` | exactly 65024 bytes | SHA256 + size |
| `kernel-stripped.elf` | declared in manifest | SHA256 + size |
| `crc32_patch.py` | declared in manifest | SHA256 + size |

**Why**: Detects stale, corrupted, or mismatched artifacts before any disk
write. An artifact from the wrong build would silently produce a non-bootable
image.

**CI gate**: SHA256 values in `examples/nexos/build-manifest.json` must stay
in sync with the actual files in the repository. A stale SHA256 fails the
integration test — this is intentional and must not be suppressed.

---

### Layer 3 — Cross-Field Formula Validation

**Where**: `lib/manifest.py`, after Layer 2  
**What it checks**: Internal consistency of the manifest's computed fields

```
kernel_secs  == ⌈kernel-stripped.elf size / 512⌉
nexfs_sb_lba == 128 + ((kernel_secs + 63) & ~63)
kernel_secs  <= 65535   (must fit in LE16 at image byte 506)
```

**Why**: `kernel_secs` and `nexfs_sb_lba` are computed by the NexTinyOS build
system. A bug in `gen_manifest.py` or any hand-edit would place NexFS at the
wrong disk location and corrupt every subsequent boot.

**CI gate**: `tests/test_nexboot.py` includes parametrised cases for formula
edge-cases: exact multiples of 512, single-sector kernels, `kernel_secs` at
maximum (65535).

---

### Layer 4 — ABI Offset Hardcoding Check

**Where**: `lib/patcher.py`, before any write  
**What it checks**: `patch_offsets` in the manifest exactly match ABI v1 constants

| Field | ABI v1 value | Checked against |
|-------|-------------|-----------------|
| `kernel_secs_offset` | 506 | hardcoded constant in `patcher.py` |
| `nexfs_sb_lba_offset` | 512 | hardcoded constant in `patcher.py` |
| `stage2_crc32_offset` | 65532 | hardcoded constant in `patcher.py` |

**Why**: Patch offsets are physical byte positions inside the stage2 binary. If
these change (bootloader rewrite), `abi_version` must also change. This layer
catches the case where offsets are updated in the manifest but `abi_version` is
not bumped.

**Critical patch order** (enforced here): `SB_LBA` is patched **before** CRC32.
CRC32 covers `image[512:65532]`, which includes the SB_LBA bytes. Reversing
the order produces a valid-looking but permanently corrupt image.

**CI gate**: `tests/test_nexboot.py` tampers with each offset field and asserts
`ManifestError` is raised.

---

## Enforcement Flow

```
build-manifest.json arrives
        │
        ▼
[Layer 1] abi_version ∈ {1}?          ─── NO ──→ ManifestError: unsupported ABI
        │ YES
        ▼
[Layer 2] SHA256 + size match?         ─── NO ──→ ManifestError: artifact corrupt
        │ YES
        ▼
[Layer 3] kernel_secs + sb_lba valid?  ─── NO ──→ ManifestError: formula mismatch
        │ YES
        ▼
[Layer 4] patch offsets == ABI v1?     ─── NO ──→ ManifestError: offset violation
        │ YES
        ▼
    Assemble disk image (safe to write)
```

---

## Architecture Boundary Rules (for §3 of implementation-rules.md)

NexBoot is an **installer tool**, not a bootloader source repository.

| What lives here | What stays in NexTinyOS |
|-----------------|-------------------------|
| `nexboot.py`, `lib/`, `tests/` — assembler / patcher | `.asm`, `.c`, `.h`, `.s` bootloader source |
| `build-manifest.json` schema validation | `docs/boot-interface-contract.md` (the ABI spec) |
| Binary artifact reads and image writes | `make installer-artifacts` (build system) |

Hard rules:
- **Never commit `.asm`, `.c`, `.h`, or `.s` files.** `.gitignore` enforces
  this passively; `tests/test_source_boundary.py` enforces it actively in CI.
- **Never embed bootloader-internal constants** outside the named constants in
  `lib/manifest.py` that are derived from the ABI contract.
- **`abi_version` is the single source of truth.** Bump it for any breaking
  ABI change; never silently mutate an existing version.

---

## ABI Versioning Rule (for §7 of developer-manual.md)

When `docs/boot-interface-contract.md` in NexTinyOS changes in a breaking way:

1. Increment `abi_version` in the contract document (NexTinyOS)
2. Add the new version to `SUPPORTED_ABI_VERSIONS` in `lib/manifest.py`
3. Update Layer 4 offset constants in `lib/patcher.py` if patch offsets changed
4. Extend `validate()` with new field checks gated on the new `abi_version`
5. Update `docs/developer-manual.md` §6 (Extending NexBoot) and §7 ABI table
6. Update `README.md` ABI compatibility table
7. Bump NexBoot to `v1.1.0` (additive) or `v2.0.0` (breaking) per semver
8. Keep the previous ABI version supported for at least one minor release cycle

---

## Gating Criteria

All items below must be ✅ before tagging `v1.1.0`.  
Status legend: ✅ Complete · 🔀 PR Open · 🔄 In Progress · ⏳ Planned

| Gate | Status |
|------|--------|
| `plan/details/02_NexBoot-v1.1-plan.md` present | ✅ |
| `plan/implementation-rules.md` §3 added (architecture boundary) | ⏳ |
| `docs/developer-manual.md` §7 added (architecture boundary) | ⏳ |
| `.gitignore` extended with `*.asm`, `*.c`, `*.h`, `*.s` | ⏳ |
| `tests/test_source_boundary.py` present and passing | ⏳ |
| `plan/status.md` updated with v1.1.0 milestone | ⏳ |
| `pytest tests/ --cov` ≥ 95% with new test file included | ⏳ |
| CI green on `release/v1.1` branch | ⏳ |
| `v1.1.0` tag created on `main` | ⏳ |