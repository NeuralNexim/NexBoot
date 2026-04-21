#!/usr/bin/env python3
# scripts/crc32_patch.py — Patch Stage 2 CRC32 field in disk image (R0013-boot-rewrite)
#
# Usage: python3 scripts/crc32_patch.py <image_path> <stage2_offset_bytes>
#
# Reads (127 * 512) = 65024 bytes from <image_path> at <stage2_offset_bytes>,
# computes CRC32 (IEEE 802.3 reflected, same polynomial as Stage 1 assembly) of
# the first 65020 bytes, writes the 4-byte little-endian result to bytes 65020-65023.
# Called by Makefile AFTER the NexFS SB_LBA is patched into Stage 2 header.

import struct
import sys
import zlib

STAGE2_SECS = 127
STAGE2_TOTAL = STAGE2_SECS * 512       # 65024 bytes
CRC32_COVERED = STAGE2_TOTAL - 4       # 65020 bytes
CRC32_FIELD_OFFSET = CRC32_COVERED     # offset within Stage 2 where CRC is stored

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <image_path> <stage2_offset_bytes>",
              file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    try:
        stage2_offset = int(sys.argv[2], 0)
    except ValueError:
        print(f"Error: invalid offset '{sys.argv[2]}'", file=sys.stderr)
        sys.exit(1)

    with open(image_path, 'r+b') as f:
        f.seek(stage2_offset)
        data = bytearray(f.read(STAGE2_TOTAL))
        if len(data) < STAGE2_TOTAL:
            print(f"Error: image too small at offset {stage2_offset} "
                  f"(need {STAGE2_TOTAL} bytes, got {len(data)})", file=sys.stderr)
            sys.exit(1)

        # Compute CRC32 of covered bytes (0..CRC32_COVERED-1)
        crc = zlib.crc32(bytes(data[:CRC32_COVERED])) & 0xFFFFFFFF

        # Patch CRC32 field in image
        f.seek(stage2_offset + CRC32_FIELD_OFFSET)
        f.write(struct.pack('<I', crc))

    print(f"CRC32 patched: 0x{crc:08X} at image offset "
          f"0x{stage2_offset + CRC32_FIELD_OFFSET:X}")

if __name__ == '__main__':
    main()
