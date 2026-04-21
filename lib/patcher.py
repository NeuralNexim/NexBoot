# lib/patcher.py  —  NexBoot ABI v1 disk-image field patcher

import binascii
import struct

from lib.manifest import ManifestError


def apply(image, manifest, verbose=False):
    """Patch *image* (bytearray) in-place with KERNEL_SECS, SB_LBA, and CRC32.

    Patch order is strictly enforced per ABI v1:
      1. KERNEL_SECS at image offset 506 (LE16)
      2. SB_LBA      at image offset 512 (LE32)  — must precede CRC32
      3. Stage2 CRC32 at image offset 65532 (LE32) — covers bytes 512..65531

    Offsets are read from manifest["patch_offsets"]["image_relative"] so that
    future ABI versions can declare different locations.

    Raises ManifestError if any offset is out of range or image is too small.
    """
    try:
        ir = manifest["patch_offsets"]["image_relative"]
        ks_off = ir["kernel_secs_offset"]      # 506
        sb_off = ir["nexfs_sb_lba_offset"]     # 512
        crc_off = ir["stage2_crc32_offset"]    # 65532

        dl = manifest["disk_layout"]
        kernel_secs = dl["kernel_secs"]
        nexfs_sb_lba = dl["nexfs_sb_lba"]
    except (KeyError, TypeError) as exc:
        raise ManifestError(f"malformed manifest passed to patcher: {exc}") from exc

    # ── bounds checks ─────────────────────────────────────────────────────────
    _check_bounds(image, ks_off, 2, "KERNEL_SECS (LE16)")
    _check_bounds(image, sb_off, 4, "SB_LBA (LE32)")
    _check_bounds(image, crc_off, 4, "Stage2 CRC32 (LE32)")

    # ── step 1: KERNEL_SECS (LE16) ────────────────────────────────────────────
    try:
        struct.pack_into("<H", image, ks_off, kernel_secs)
    except struct.error as exc:
        raise ManifestError(f"KERNEL_SECS value {kernel_secs} out of range: {exc}") from exc
    if verbose:
        print(f"  KERNEL_SECS = {kernel_secs} → image[{ks_off}:{ks_off+2}]")

    # ── step 2: SB_LBA (LE32) — MUST precede CRC32 ───────────────────────────
    try:
        struct.pack_into("<I", image, sb_off, nexfs_sb_lba)
    except struct.error as exc:
        raise ManifestError(f"SB_LBA value {nexfs_sb_lba} out of range: {exc}") from exc
    if verbose:
        print(f"  SB_LBA = {nexfs_sb_lba} → image[{sb_off}:{sb_off+4}]")

    # ── step 3: Stage2 CRC32 (LE32) — covers bytes sb_off..crc_off-1 ─────────
    crc_value = binascii.crc32(image[sb_off:crc_off]) & 0xFFFFFFFF
    struct.pack_into("<I", image, crc_off, crc_value)
    if verbose:
        print(
            f"  CRC32(image[{sb_off}:{crc_off}]) = 0x{crc_value:08x} "
            f"→ image[{crc_off}:{crc_off+4}]"
        )


def _check_bounds(image, offset, size, label):
    """Raise ManifestError if *offset* + *size* exceeds len(image)."""
    end = offset + size
    if offset < 0 or end > len(image):
        raise ManifestError(
            f"{label}: patch offset {offset}+{size} out of image bounds "
            f"(image size {len(image)})"
        )
