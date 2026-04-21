# lib/manifest.py  —  NexBoot ABI v1 build-manifest.json parser and validator

import hashlib
import json
import math
import os

# ── ABI v1 invariants ─────────────────────────────────────────────────────────

SUPPORTED_ABI_VERSIONS = (1,)

REQUIRED_ARTIFACTS = (
    "bootloader.bin",
    "stage2.bin",
    "kernel-stripped.elf",
    "crc32_patch.py",
)

BOOTLOADER_SIZE_EXPECTED = 512
STAGE2_SIZE_EXPECTED = 65024  # 127 × 512

KERNEL_SECS_MAX = 0xFFFF  # LE16 field limit


class ManifestError(Exception):
    """Raised when a build-manifest.json is invalid or inconsistent."""
    pass


def parse(path):
    """Parse build-manifest.json at *path* and return the decoded dict.

    Raises ManifestError if the file cannot be read or parsed.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise ManifestError(f"manifest not found: {path}")
    except PermissionError:
        raise ManifestError(f"manifest not readable: {path}")
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest JSON parse error: {exc}")
    except OSError as exc:
        raise ManifestError(f"manifest not readable: {path}: {exc}") from exc


def validate(manifest, artifacts_dir, abi_check=1):
    """Validate *manifest* dict and all artifact files under *artifacts_dir*.

    Checks:
    - abi_version present and equals *abi_check*
    - required top-level fields present and correct types
    - all four required artifacts present, matching size and SHA256
    - disk_layout cross-field invariants (kernel_secs formula, nexfs_sb_lba formula)
    - patch_offsets nested structure and ABI-expected values
    - kernel_secs fits in LE16

    Raises ManifestError on any violation.
    """
    errors = []

    # ── top-level required fields ─────────────────────────────────────────────
    for field in ("abi_version", "artifacts", "disk_layout", "patch_offsets", "build"):
        if field not in manifest:
            errors.append(f"missing top-level field: {field!r}")

    if errors:
        raise ManifestError("; ".join(errors))

    # ── abi_version ───────────────────────────────────────────────────────────
    abi = manifest.get("abi_version")
    if not isinstance(abi, int):
        errors.append(f"abi_version must be an integer, got {type(abi).__name__}")
    elif abi != abi_check:
        errors.append(
            f"abi_version mismatch: manifest has {abi}, expected {abi_check}"
        )

    # ── build block ───────────────────────────────────────────────────────────
    build = manifest.get("build", {})
    if not isinstance(build, dict):
        errors.append("'build' must be an object")
    else:
        for bfield in ("git_sha", "build_date", "build_target"):
            if bfield not in build:
                errors.append(f"missing build field: {bfield!r}")

    # ── artifacts block ───────────────────────────────────────────────────────
    arts = manifest.get("artifacts", {})
    if not isinstance(arts, dict):
        errors.append("'artifacts' must be an object")
    else:
        for name in REQUIRED_ARTIFACTS:
            if name not in arts:
                errors.append(f"missing artifact entry: {name!r}")
            else:
                entry = arts[name]
                if not isinstance(entry, dict):
                    errors.append(f"artifact entry {name!r} must be an object")
                    continue
                for afield in ("size", "sha256"):
                    if afield not in entry:
                        errors.append(f"artifact {name!r} missing field {afield!r}")
                # sha256 must be 64 lowercase hex chars
                sha = entry.get("sha256", "")
                if not (isinstance(sha, str) and len(sha) == 64 and
                        all(c in "0123456789abcdef" for c in sha)):
                    errors.append(
                        f"artifact {name!r} sha256 must be 64 lowercase hex chars"
                    )
                # size must be a positive integer
                sz = entry.get("size")
                if not isinstance(sz, int) or sz <= 0:
                    errors.append(f"artifact {name!r} size must be a positive integer")

    # ── fixed-size artifact constraints ───────────────────────────────────────
    if isinstance(arts, dict):
        bl_entry = arts.get("bootloader.bin", {})
        if isinstance(bl_entry, dict) and bl_entry.get("size") != BOOTLOADER_SIZE_EXPECTED:
            errors.append(
                f"bootloader.bin size must be {BOOTLOADER_SIZE_EXPECTED}, "
                f"got {bl_entry.get('size')}"
            )
        s2_entry = arts.get("stage2.bin", {})
        if isinstance(s2_entry, dict) and s2_entry.get("size") != STAGE2_SIZE_EXPECTED:
            errors.append(
                f"stage2.bin size must be {STAGE2_SIZE_EXPECTED}, "
                f"got {s2_entry.get('size')}"
            )

    # ── disk_layout block ─────────────────────────────────────────────────────
    dl = manifest.get("disk_layout", {})
    if not isinstance(dl, dict):
        errors.append("'disk_layout' must be an object")
    else:
        kernel_secs = dl.get("kernel_secs")
        nexfs_sb_lba = dl.get("nexfs_sb_lba")
        if not isinstance(nexfs_sb_lba, int) or nexfs_sb_lba <= 0:
            errors.append("disk_layout.nexfs_sb_lba must be a positive integer")
        if not isinstance(kernel_secs, int) or kernel_secs <= 0:
            errors.append("disk_layout.kernel_secs must be a positive integer")
        elif kernel_secs > KERNEL_SECS_MAX:
            errors.append(
                f"disk_layout.kernel_secs {kernel_secs} exceeds LE16 maximum "
                f"{KERNEL_SECS_MAX}"
            )
        else:
            # kernel_secs is valid — cross-check nexfs_sb_lba formula
            if isinstance(nexfs_sb_lba, int) and nexfs_sb_lba > 0:
                expected_sb = 128 + ((kernel_secs + 63) & ~63)
                if nexfs_sb_lba != expected_sb:
                    errors.append(
                        f"disk_layout.nexfs_sb_lba {nexfs_sb_lba} does not match "
                        f"formula 128 + ((kernel_secs + 63) & ~63) = {expected_sb}"
                    )

            # cross-field: kernel_secs matches actual kernel artifact size
            kern_entry = arts.get("kernel-stripped.elf", {}) if isinstance(arts, dict) else {}
            kern_size = kern_entry.get("size") if isinstance(kern_entry, dict) else None
            if isinstance(kern_size, int):
                expected_secs = math.ceil(kern_size / 512)
                if kernel_secs != expected_secs:
                    errors.append(
                        f"disk_layout.kernel_secs {kernel_secs} does not match "
                        f"ceil(kernel size {kern_size} / 512) = {expected_secs}"
                    )

    # ── patch_offsets block ───────────────────────────────────────────────────
    po = manifest.get("patch_offsets", {})
    if not isinstance(po, dict):
        errors.append("'patch_offsets' must be an object")
    else:
        ir = po.get("image_relative", {})
        if not isinstance(ir, dict):
            errors.append("'patch_offsets.image_relative' must be an object")
        else:
            for ifield, expected in (
                ("kernel_secs_offset", 506),
                ("nexfs_sb_lba_offset", 512),
                ("stage2_crc32_offset", 65532),
            ):
                val = ir.get(ifield)
                if not isinstance(val, int):
                    errors.append(
                        f"patch_offsets.image_relative.{ifield} must be an integer"
                    )
                elif val != expected:
                    errors.append(
                        f"patch_offsets.image_relative.{ifield} must be {expected} "
                        f"for ABI v1, got {val}"
                    )

    if errors:
        raise ManifestError("; ".join(errors))

    # ── artifact file existence and hash verification ─────────────────────────
    if not isinstance(arts, dict):
        return  # already reported above

    file_errors = []
    for name in REQUIRED_ARTIFACTS:
        entry = arts.get(name)
        if not isinstance(entry, dict):
            continue
        path = os.path.join(artifacts_dir, name)
        if not os.path.isfile(path):
            file_errors.append(f"artifact file not found: {path}")
            continue
        if not os.access(path, os.R_OK):
            file_errors.append(f"artifact file not readable: {path}")
            continue

        try:
            actual_size = os.path.getsize(path)
            expected_size = entry.get("size")
            if isinstance(expected_size, int) and actual_size != expected_size:
                file_errors.append(
                    f"{name}: size mismatch (manifest {expected_size}, "
                    f"file {actual_size})"
                )

            expected_sha = entry.get("sha256", "")
            actual_sha = _sha256_file(path)
            if actual_sha != expected_sha:
                file_errors.append(
                    f"{name}: SHA256 mismatch\n"
                    f"  manifest: {expected_sha}\n"
                    f"  file:     {actual_sha}"
                )
        except OSError as exc:
            file_errors.append(f"{name}: I/O error during verification: {exc}")

    if file_errors:
        raise ManifestError("\n".join(file_errors))


def _sha256_file(path):
    """Return lowercase hex SHA256 digest of the file at *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
