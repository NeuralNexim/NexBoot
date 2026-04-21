<!--
  README.md  —  NexBoot: OS-agnostic bootable disk image assembler
-->

# NexBoot

**NexBoot** is an OS-agnostic Python tool that consumes a `build-manifest.json`
artifact bundle and assembles a bootable disk image — without touching `.asm` or
`.c` source.

Any OS project that exports a `build-manifest.json` conforming to the
**NexBoot ABI v1** can use NexBoot to build a bootable image with no changes
to NexBoot source.

---

## Quick Start

```bash
python3 nexboot.py \
  --manifest build/installer-artifacts/build-manifest.json \
  --artifacts build/installer-artifacts/ \
  --output hdd.img
```

## CLI Reference

```
usage: nexboot.py [options]

Options:
  --manifest  PATH   Path to build-manifest.json          (required)
  --artifacts DIR    Directory containing artifact files   (required)
  --output    PATH   Output disk image path (default: hdd.img)
  --abi-check INT    Fail if manifest abi_version != this value (default: 1)
  --size-kb   INT    Disk image size in KB (default: 16384 = 16 MB)
  --dry-run          Validate manifest and artifacts without writing image
  --verbose          Print patch offsets and SHA256 verification results
  --help             Show this help message
```

## ABI Version Compatibility

| NexBoot version | ABI version | NexTinyOS milestone |
|-----------------|-------------|---------------------|
| 1.x             | 1           | R0013-installer-artifacts |
| 2.x (planned)   | 2           | R0014 (Ed25519 signing) |

The NexBoot ABI v1 spec is defined in
[`docs/boot-interface-contract.md`](https://github.com/NeuralNexim/NexTinyOS/blob/main/docs/boot-interface-contract.md)
in the NexTinyOS repository.

## Assembly Procedure (ABI v1)

1. Parse and validate `build-manifest.json` (ABI version, SHA256, sizes)
2. Create blank disk image
3. Write `bootloader.bin` → LBA 0
4. Write `stage2.bin` → LBA 1–127
5. Write `kernel-stripped.elf` → LBA 128
6. Patch `KERNEL_SECS` at image byte 506 (LE16)
7. Patch `SB_LBA` at image byte 512 (LE32) — **must precede CRC32**
8. Compute and write Stage 2 CRC32 at image byte 65532 (LE32)
9. Print summary

## Using NexBoot with Another OS

To use NexBoot with a different OS, that OS must:

1. Build a Stage 1 MBR and Stage 2 loader conforming to the NexBoot ABI
2. Export an ELF32 kernel binary
3. Generate a `build-manifest.json` matching the NexBoot ABI v1 schema
4. Run `nexboot.py --manifest ...`

No NexBoot source changes are needed — it is purely manifest-driven.

## Running Tests

```bash
pytest tests/
```

Requires Python 3.8+ (stdlib only — no third-party runtime dependencies).
Test dependencies: `pytest`, `pytest-cov`.

## What NexBoot Does NOT Do

- Own bootloader source (`.asm`, `.c`) — those stay in the OS repo
- Run `make seedfs` or populate any filesystem
- Sign artifacts (planned for ABI v2)
- Require changes when the kernel changes (as long as ABI version is unchanged)

## License

MIT — see [LICENSE](LICENSE).
