<!--
  plan/details/01_NexBoot-v1-plan.md  —  NexBoot v1.0.0 detail plan
-->

# Plan: NexBoot v1.0.0

> **Milestone tag**: NexBoot-v1
> **Repo**: `NeuralNexim/NexBoot`
> **Branch**: `main` (initial release, no sub-release branches)
> **Prerequisites**: R0013-installer-artifacts ✅ (NexTinyOS PR #46)
> **ABI version**: 1

---

## Problem Statement

R0013-installer-artifacts produced a self-contained artifact bundle and formal
NexBoot ABI v1 spec (`docs/boot-interface-contract.md` in NexTinyOS). NexBoot
is the Python consumer: it reads the bundle, verifies it, and assembles a
bootable disk image — without ever owning `.asm` or `.c` source.

---

## Deliverables

| File | Purpose |
|------|---------|
| `nexboot.py` | CLI entry point |
| `lib/manifest.py` | ABI v1 manifest parser + deep validator |
| `lib/patcher.py` | KERNEL_SECS / SB_LBA / CRC32 patcher (strict ordering) |
| `lib/image.py` | Blank image creation, artifact writing, save |
| `tests/test_nexboot.py` | pytest suite ≥ 95% coverage |
| `.github/workflows/ci.yml` | Lint (ruff) + pytest, Python 3.10/3.11/3.12 |
| `examples/nexos/build-manifest.json` | Reference manifest from NexTinyOS |
| `docs/developer-manual.md` | §1–§6: prerequisites, install, CLI, lib, test, extend |
| `README.md`, `LICENSE`, `CLAUDE.md` | Repo metadata |
| `plan/` | status.md, implementation-rules.md, branching-strategy.md |

---

## Assembly Procedure (NexBoot implements this)

1. Parse + validate `build-manifest.json`
2. Create blank disk image (`--size-kb × 1024` zeros)
3. Write `bootloader.bin` → LBA 0
4. Write `stage2.bin` → LBA 1–127
5. Write `kernel-stripped.elf` → LBA 128
6. Patch `KERNEL_SECS` at image byte 506 (LE16)
7. Patch `SB_LBA` at image byte 512 (LE32) — **must precede CRC32**
8. Compute CRC32(image[512:65532]) → write LE32 at image byte 65532
9. Print summary

---

## Validation Rules

- `abi_version` must equal `--abi-check` (default 1)
- All four artifact files must exist, match declared size and SHA256
- `bootloader.bin` must be exactly 512 bytes
- `stage2.bin` must be exactly 65024 bytes
- `disk_layout.kernel_secs` must equal `⌈kernel_elf_size / 512⌉`
- `disk_layout.nexfs_sb_lba` must equal `128 + ((kernel_secs + 63) & ~63)`
- `kernel_secs` must fit in LE16 (≤ 65535)
- All image_relative patch offsets must match ABI v1 values exactly

---

## Gating Criteria

All items in `plan/status.md` must be ✅ before tagging `v1.0.0`.
