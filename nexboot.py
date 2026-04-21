#!/usr/bin/env python3
# nexboot.py  —  NexBoot: assemble a bootable disk image from a build-manifest.json bundle

"""
Usage:
    nexboot.py --manifest PATH --artifacts DIR [options]

Options:
    --manifest  PATH   Path to build-manifest.json           (required)
    --artifacts DIR    Directory containing artifact files    (required)
    --output    PATH   Output disk image path (default: hdd.img)
    --abi-check INT    Fail if manifest abi_version != this  (default: 1)
    --size-kb   INT    Disk image size in KB                  (default: 16384 = 16 MB)
    --dry-run          Validate manifest and artifacts, skip image write
    --verbose          Print patch offsets and SHA256 results
    --help             Show this help message

Example:
    nexboot.py \\
      --manifest build/installer-artifacts/build-manifest.json \\
      --artifacts build/installer-artifacts/ \\
      --output hdd.img
"""

import argparse
import hashlib
import sys

from lib.image import create, load_artifact, save, write_artifact
from lib.manifest import ManifestError, parse, validate
from lib.patcher import apply as patch_image

# LBA positions per NexBoot ABI v1
_LBA_BOOTLOADER = 0
_LBA_STAGE2 = 1
_LBA_KERNEL = 128


def _print_summary(manifest, output, dry_run, verbose):
    arts = manifest["artifacts"]
    dl = manifest["disk_layout"]
    print("NexBoot v1.0.0 — assembly summary")
    print(f"  ABI version    : {manifest['abi_version']}")
    print(f"  Build SHA      : {manifest['build'].get('git_sha', 'n/a')}")
    print(f"  KERNEL_SECS    : {dl['kernel_secs']}")
    print(f"  NEXFS_SB_LBA   : {dl['nexfs_sb_lba']}")
    if verbose:
        for name in ("bootloader.bin", "stage2.bin", "kernel-stripped.elf"):
            entry = arts.get(name, {})
            print(f"  {name:<28} {entry.get('size', '?'):>8} bytes  "
                  f"sha256:{entry.get('sha256', 'n/a')[:16]}…")
    if dry_run:
        print("  [dry-run] image NOT written.")
    else:
        print(f"  Output image   : {output}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="nexboot.py",
        description="Assemble a bootable disk image from a NexBoot ABI v1 artifact bundle.",
        add_help=True,
    )
    parser.add_argument("--manifest", required=True,
                        help="Path to build-manifest.json")
    parser.add_argument("--artifacts", required=True,
                        help="Directory containing artifact files listed in manifest")
    parser.add_argument("--output", default="hdd.img",
                        help="Output disk image path (default: hdd.img)")
    parser.add_argument("--abi-check", type=int, default=1, metavar="INT",
                        help="Fail if manifest abi_version != this value (default: 1)")
    parser.add_argument("--size-kb", type=int, default=16384, metavar="INT",
                        help="Disk image size in KB (default: 16384 = 16 MB)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate manifest and artifacts without writing image")
    parser.add_argument("--verbose", action="store_true",
                        help="Print patch offsets and SHA256 verification results")

    args = parser.parse_args(argv)

    try:
        # ── step 1: parse and validate manifest ──────────────────────────────
        if args.verbose:
            print(f"nexboot: reading manifest {args.manifest!r}")
        manifest = parse(args.manifest)
        validate(manifest, args.artifacts, abi_check=args.abi_check)
        if args.verbose:
            print("nexboot: manifest validated OK")

        if args.dry_run:
            _print_summary(manifest, args.output, dry_run=True,
                           verbose=args.verbose)
            return 0

        # ── step 2: create blank image ────────────────────────────────────────
        image = create(args.size_kb)

        # ── steps 3–5: write artifacts ────────────────────────────────────────
        bootloader_data = load_artifact(args.artifacts, "bootloader.bin")
        stage2_data = load_artifact(args.artifacts, "stage2.bin")
        kernel_data = load_artifact(args.artifacts, "kernel-stripped.elf")

        write_artifact(image, bootloader_data, _LBA_BOOTLOADER)
        write_artifact(image, stage2_data, _LBA_STAGE2)
        write_artifact(image, kernel_data, _LBA_KERNEL)

        if args.verbose:
            print(f"  wrote bootloader.bin → LBA {_LBA_BOOTLOADER} "
                  f"({len(bootloader_data)} bytes)")
            print(f"  wrote stage2.bin → LBA {_LBA_STAGE2} "
                  f"({len(stage2_data)} bytes)")
            print(f"  wrote kernel-stripped.elf → LBA {_LBA_KERNEL} "
                  f"({len(kernel_data)} bytes)")

        # ── steps 6–8: patch fields ───────────────────────────────────────────
        patch_image(image, manifest, verbose=args.verbose)

        # ── step 9: save + summary ────────────────────────────────────────────
        save(image, args.output)
        _print_summary(manifest, args.output, dry_run=False,
                       verbose=args.verbose)

        if args.verbose:
            final_sha = hashlib.sha256(bytes(image)).hexdigest()
            print(f"  Image SHA256   : {final_sha}")

    except ManifestError as exc:
        print(f"nexboot: error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
