# tests/test_nexboot.py  —  NexBoot pytest suite (ABI v1)

import binascii
import hashlib
import json
import math
import os
import struct

import pytest

import nexboot
from lib.image import create, load_artifact, save, write_artifact
from lib.manifest import (
    BOOTLOADER_SIZE_EXPECTED,
    STAGE2_SIZE_EXPECTED,
    ManifestError,
    parse,
    validate,
)
from lib.patcher import apply as patch_image

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_artifacts(tmpdir, kernel_size=1024):
    """Write fake artifact files and return (paths_dict, hashes_dict)."""
    bootloader = b"\x00" * BOOTLOADER_SIZE_EXPECTED
    stage2 = b"\x00" * STAGE2_SIZE_EXPECTED
    kernel = b"\x00" * kernel_size
    patcher = b"# fake patcher\n"

    files = {
        "bootloader.bin": bootloader,
        "stage2.bin": stage2,
        "kernel-stripped.elf": kernel,
        "crc32_patch.py": patcher,
    }
    for name, data in files.items():
        with open(os.path.join(tmpdir, name), "wb") as fh:
            fh.write(data)
    return files


def _make_manifest(kernel_size=1024):
    """Return a valid ABI v1 manifest dict for a kernel of *kernel_size* bytes."""
    bootloader = b"\x00" * BOOTLOADER_SIZE_EXPECTED
    stage2 = b"\x00" * STAGE2_SIZE_EXPECTED
    kernel = b"\x00" * kernel_size
    patcher = b"# fake patcher\n"

    kernel_secs = math.ceil(kernel_size / 512)
    nexfs_sb_lba = 128 + ((kernel_secs + 63) & ~63)

    return {
        "abi_version": 1,
        "build": {
            "git_sha": "abc123",
            "build_date": "2026-01-01T00:00:00Z",
            "build_target": "i386",
        },
        "artifacts": {
            "bootloader.bin": {
                "size": BOOTLOADER_SIZE_EXPECTED,
                "sha256": _sha256(bootloader),
            },
            "stage2.bin": {
                "size": STAGE2_SIZE_EXPECTED,
                "sha256": _sha256(stage2),
            },
            "kernel-stripped.elf": {
                "size": kernel_size,
                "sha256": _sha256(kernel),
            },
            "crc32_patch.py": {
                "size": len(patcher),
                "sha256": _sha256(patcher),
            },
        },
        "disk_layout": {
            "kernel_secs": kernel_secs,
            "nexfs_sb_lba": nexfs_sb_lba,
        },
        "patch_offsets": {
            "image_relative": {
                "kernel_secs_offset": 506,
                "nexfs_sb_lba_offset": 512,
                "stage2_crc32_offset": 65532,
            },
            "artifact_relative": {
                "kernel_secs": {"artifact": "bootloader.bin", "offset": 506},
                "nexfs_sb_lba": {"artifact": "stage2.bin", "offset": 0},
                "stage2_crc32": {"artifact": "stage2.bin", "offset": 65020},
            },
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# manifest.parse tests
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestParse:
    def test_parse_valid(self, tmp_path):
        manifest = _make_manifest()
        path = tmp_path / "build-manifest.json"
        path.write_text(json.dumps(manifest))
        result = parse(str(path))
        assert result["abi_version"] == 1

    def test_parse_file_not_found(self):
        with pytest.raises(ManifestError, match="not found"):
            parse("/nonexistent/path/build-manifest.json")

    def test_parse_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json}")
        with pytest.raises(ManifestError, match="JSON parse error"):
            parse(str(path))


# ─────────────────────────────────────────────────────────────────────────────
# manifest.validate — abi_version tests
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestValidateAbiVersion:
    def test_valid_abi_version(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        validate(manifest, str(tmp_path))  # should not raise

    def test_missing_abi_version(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        del manifest["abi_version"]
        with pytest.raises(ManifestError, match="missing top-level field"):
            validate(manifest, str(tmp_path))

    def test_wrong_abi_version(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["abi_version"] = 99
        with pytest.raises(ManifestError, match="abi_version mismatch"):
            validate(manifest, str(tmp_path))

    def test_abi_version_not_integer(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["abi_version"] = "1"
        with pytest.raises(ManifestError, match="abi_version must be an integer"):
            validate(manifest, str(tmp_path))

    def test_abi_check_overrides(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["abi_version"] = 2
        with pytest.raises(ManifestError, match="abi_version mismatch"):
            validate(manifest, str(tmp_path), abi_check=1)


# ─────────────────────────────────────────────────────────────────────────────
# manifest.validate — required fields
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestValidateRequiredFields:
    @pytest.mark.parametrize("field", ["artifacts", "disk_layout", "patch_offsets", "build"])
    def test_missing_top_level_field(self, tmp_path, field):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        del manifest[field]
        with pytest.raises(ManifestError, match="missing top-level field"):
            validate(manifest, str(tmp_path))

    def test_missing_build_git_sha(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        del manifest["build"]["git_sha"]
        with pytest.raises(ManifestError, match="missing build field"):
            validate(manifest, str(tmp_path))


# ─────────────────────────────────────────────────────────────────────────────
# manifest.validate — artifact entry tests
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestValidateArtifacts:
    def test_missing_artifact_entry(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        del manifest["artifacts"]["bootloader.bin"]
        with pytest.raises(ManifestError, match="missing artifact entry"):
            validate(manifest, str(tmp_path))

    def test_wrong_sha256(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["artifacts"]["bootloader.bin"]["sha256"] = "a" * 64
        with pytest.raises(ManifestError, match="SHA256 mismatch"):
            validate(manifest, str(tmp_path))

    def test_wrong_artifact_size_in_manifest(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        # Mismatch: manifest says 600 bytes but file is 512 bytes
        manifest["artifacts"]["bootloader.bin"]["size"] = 600
        # Also fix sha256 to avoid hash mismatch overshadowing size check
        # The size check is on the manifest fixed-size constraint (512), not the file
        with pytest.raises(ManifestError, match="bootloader.bin size must be 512"):
            validate(manifest, str(tmp_path))

    def test_artifact_file_not_found(self, tmp_path):
        # Don't create artifact files
        manifest = _make_manifest()
        with pytest.raises(ManifestError, match="artifact file not found"):
            validate(manifest, str(tmp_path))

    def test_sha256_wrong_length(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["artifacts"]["bootloader.bin"]["sha256"] = "abc"
        with pytest.raises(ManifestError, match="64 lowercase hex chars"):
            validate(manifest, str(tmp_path))

    def test_sha256_uppercase(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["artifacts"]["bootloader.bin"]["sha256"] = "A" * 64
        with pytest.raises(ManifestError, match="64 lowercase hex chars"):
            validate(manifest, str(tmp_path))

    def test_artifact_size_mismatch_with_file(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        # Write a real file but tell manifest it's 1 byte
        manifest["artifacts"]["crc32_patch.py"]["size"] = 1
        # Update sha256 to a wrong-length string to trigger artifact size error first
        # Actually let's just give wrong size and right hash doesn't exist for 1 byte
        # The file size mismatch check comes before hash check
        with pytest.raises(ManifestError, match="size mismatch"):
            validate(manifest, str(tmp_path))


# ─────────────────────────────────────────────────────────────────────────────
# manifest.validate — disk_layout cross-field invariants
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestValidateDiskLayout:
    def test_kernel_secs_mismatch_with_kernel_size(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest(kernel_size=1024)
        # kernel_secs should be 2 for 1024 bytes; set it wrong
        manifest["disk_layout"]["kernel_secs"] = 99
        # Also fix nexfs_sb_lba to avoid cascading error
        manifest["disk_layout"]["nexfs_sb_lba"] = 128 + ((99 + 63) & ~63)
        with pytest.raises(ManifestError, match="kernel_secs.*does not match"):
            validate(manifest, str(tmp_path))

    def test_nexfs_sb_lba_wrong_formula(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest(kernel_size=1024)
        manifest["disk_layout"]["nexfs_sb_lba"] = 999  # wrong
        with pytest.raises(ManifestError, match="nexfs_sb_lba.*does not match"):
            validate(manifest, str(tmp_path))

    def test_kernel_secs_exceeds_le16(self, tmp_path):
        # kernel_secs > 65535 triggers LE16 overflow error
        manifest = _make_manifest(kernel_size=1024)
        manifest["disk_layout"]["kernel_secs"] = 0x10000  # > 65535
        with pytest.raises(ManifestError, match="exceeds LE16 maximum"):
            validate(manifest, str(tmp_path))

    def test_kernel_secs_not_integer(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["disk_layout"]["kernel_secs"] = "bad"
        with pytest.raises(ManifestError, match="kernel_secs must be a positive integer"):
            validate(manifest, str(tmp_path))


# ─────────────────────────────────────────────────────────────────────────────
# manifest.validate — patch_offsets
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestValidatePatchOffsets:
    def test_wrong_kernel_secs_offset(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["patch_offsets"]["image_relative"]["kernel_secs_offset"] = 100
        with pytest.raises(ManifestError, match="kernel_secs_offset must be 506"):
            validate(manifest, str(tmp_path))

    def test_wrong_crc32_offset(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["patch_offsets"]["image_relative"]["stage2_crc32_offset"] = 0
        with pytest.raises(ManifestError, match="stage2_crc32_offset must be 65532"):
            validate(manifest, str(tmp_path))


# ─────────────────────────────────────────────────────────────────────────────
# image.create tests
# ─────────────────────────────────────────────────────────────────────────────

class TestImageCreate:
    def test_create_correct_size(self):
        img = create(16)  # 16 KB
        assert len(img) == 16 * 1024

    def test_create_all_zeros(self):
        img = create(8)
        assert all(b == 0 for b in img)

    def test_create_returns_bytearray(self):
        img = create(4)
        assert isinstance(img, bytearray)

    def test_create_invalid_size(self):
        with pytest.raises(ManifestError, match="positive integer"):
            create(0)
        with pytest.raises(ManifestError, match="positive integer"):
            create(-1)


# ─────────────────────────────────────────────────────────────────────────────
# image.write_artifact tests
# ─────────────────────────────────────────────────────────────────────────────

class TestImageWriteArtifact:
    def test_write_at_lba0(self):
        img = create(4)
        data = b"\xAB" * 512
        write_artifact(img, data, 0)
        assert img[0:512] == bytearray(data)

    def test_write_at_lba1(self):
        img = create(64)
        data = b"\xCD" * 512
        write_artifact(img, data, 1)
        assert img[512:1024] == bytearray(data)

    def test_write_does_not_overflow(self):
        img = create(1)  # 1024 bytes
        data = b"\xFF" * 512
        write_artifact(img, data, 1)  # LBA 1 = offset 512, ends at 1024 — OK
        assert img[512:1024] == bytearray(data)

    def test_write_out_of_bounds(self):
        img = create(1)  # 1024 bytes
        data = b"\xFF" * 512
        with pytest.raises(ManifestError, match="exceeds image size"):
            write_artifact(img, data, 2)  # LBA 2 = offset 1024, would need 1536 — fail

    def test_write_does_not_resize(self):
        img = create(1)
        original_len = len(img)
        data = b"\xAB" * 512
        write_artifact(img, data, 0)
        assert len(img) == original_len


# ─────────────────────────────────────────────────────────────────────────────
# image.save and load_artifact tests
# ─────────────────────────────────────────────────────────────────────────────

class TestImageSaveLoad:
    def test_save_and_reload(self, tmp_path):
        img = create(4)
        img[0] = 0xAB
        img[1023] = 0xCD
        out_path = str(tmp_path / "test.img")
        save(img, out_path)
        with open(out_path, "rb") as fh:
            data = fh.read()
        assert len(data) == 4 * 1024
        assert data[0] == 0xAB
        assert data[1023] == 0xCD

    def test_load_artifact(self, tmp_path):
        content = b"\xDE\xAD\xBE\xEF"
        path = tmp_path / "test.bin"
        path.write_bytes(content)
        result = load_artifact(str(tmp_path), "test.bin")
        assert result == content

    def test_load_artifact_not_found(self, tmp_path):
        with pytest.raises(ManifestError, match="not found"):
            load_artifact(str(tmp_path), "missing.bin")


# ─────────────────────────────────────────────────────────────────────────────
# patcher.apply tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPatcher:
    def _make_image(self, size_kb=128):
        return create(size_kb)

    def test_kernel_secs_patched_correctly(self):
        manifest = _make_manifest(kernel_size=1024)
        img = self._make_image()
        patch_image(img, manifest)
        kernel_secs = struct.unpack_from("<H", img, 506)[0]
        assert kernel_secs == manifest["disk_layout"]["kernel_secs"]

    def test_sb_lba_patched_correctly(self):
        manifest = _make_manifest(kernel_size=1024)
        img = self._make_image()
        patch_image(img, manifest)
        sb_lba = struct.unpack_from("<I", img, 512)[0]
        assert sb_lba == manifest["disk_layout"]["nexfs_sb_lba"]

    def test_crc32_patched_correctly(self):
        manifest = _make_manifest(kernel_size=1024)
        img = self._make_image()
        patch_image(img, manifest)
        # After patching, verify CRC32 is correct
        expected_crc = binascii.crc32(bytes(img[512:65532])) & 0xFFFFFFFF
        stored_crc = struct.unpack_from("<I", img, 65532)[0]
        assert stored_crc == expected_crc

    def test_crc32_known_answer(self):
        """Known-answer: binascii.crc32 and zlib.crc32 produce identical results.

        Both use ISO 3309 (Ethernet) CRC32 — NexTinyOS's crc32_patch.py uses zlib.
        """
        import zlib
        data = b"\x01\x02\x03\xAB\xCD" * 13004  # 65020 bytes, non-trivial content
        expected = zlib.crc32(data) & 0xFFFFFFFF
        actual = binascii.crc32(data) & 0xFFFFFFFF
        assert actual == expected

    def test_patch_order_sb_lba_before_crc(self):
        """CRC32 must cover the SB_LBA-patched bytes."""
        manifest = _make_manifest(kernel_size=1024)
        img = self._make_image()
        patch_image(img, manifest)

        # SB_LBA is at img[512:516]; the CRC covers img[512:65532].
        # If SB_LBA were patched AFTER the CRC, the stored CRC would be
        # CRC32 of all-zeros[0:65020], which differs from CRC32 of the
        # patched region.
        sb_lba = manifest["disk_layout"]["nexfs_sb_lba"]
        expected_region = bytearray(65020)  # img[512:65532]
        struct.pack_into("<I", expected_region, 0, sb_lba)  # SB_LBA at offset 0
        expected_crc = binascii.crc32(bytes(expected_region)) & 0xFFFFFFFF
        stored_crc = struct.unpack_from("<I", img, 65532)[0]
        assert stored_crc == expected_crc

    def test_image_too_small_for_crc(self):
        manifest = _make_manifest(kernel_size=1024)
        img = create(32)  # 32 KB — too small for CRC field at 65532
        with pytest.raises(ManifestError, match="out of image bounds|too small"):
            patch_image(img, manifest)

    def test_verbose_output(self, capsys):
        manifest = _make_manifest(kernel_size=1024)
        img = self._make_image()
        patch_image(img, manifest, verbose=True)
        out = capsys.readouterr().out
        assert "KERNEL_SECS" in out
        assert "SB_LBA" in out
        assert "CRC32" in out


# ─────────────────────────────────────────────────────────────────────────────
# nexboot.main integration tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNexbootMain:
    def _write_manifest(self, path, manifest):
        with open(path, "w") as fh:
            json.dump(manifest, fh)

    def test_full_assembly(self, tmp_path):
        kernel_size = 1024
        _make_artifacts(str(tmp_path), kernel_size)
        manifest = _make_manifest(kernel_size)
        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)
        output_path = str(tmp_path / "hdd.img")

        rc = nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--output", output_path,
        ])
        assert rc == 0
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) == 16384 * 1024

    def test_full_assembly_verbose(self, tmp_path, capsys):
        kernel_size = 1024
        _make_artifacts(str(tmp_path), kernel_size)
        manifest = _make_manifest(kernel_size)
        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)
        output_path = str(tmp_path / "hdd.img")

        rc = nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--output", output_path,
            "--verbose",
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "KERNEL_SECS" in out

    def test_dry_run_no_file(self, tmp_path):
        kernel_size = 1024
        _make_artifacts(str(tmp_path), kernel_size)
        manifest = _make_manifest(kernel_size)
        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)
        output_path = str(tmp_path / "hdd.img")

        rc = nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--output", output_path,
            "--dry-run",
        ])
        assert rc == 0
        assert not os.path.exists(output_path)

    def test_dry_run_prints_message(self, tmp_path, capsys):
        kernel_size = 1024
        _make_artifacts(str(tmp_path), kernel_size)
        manifest = _make_manifest(kernel_size)
        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)

        nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--dry-run",
        ])
        out = capsys.readouterr().out
        assert "dry-run" in out

    def test_bad_manifest_returns_1(self, tmp_path, capsys):
        manifest_path = str(tmp_path / "bad.json")
        with open(manifest_path, "w") as fh:
            fh.write("{}")
        rc = nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
        ])
        assert rc == 1
        err = capsys.readouterr().err
        assert "error" in err

    def test_missing_manifest_returns_1(self, tmp_path, capsys):
        rc = nexboot.main([
            "--manifest", str(tmp_path / "nonexistent.json"),
            "--artifacts", str(tmp_path),
        ])
        assert rc == 1

    def test_custom_output_path(self, tmp_path):
        kernel_size = 512
        _make_artifacts(str(tmp_path), kernel_size)
        manifest = _make_manifest(kernel_size)
        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)
        custom_out = str(tmp_path / "my_custom.img")

        rc = nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--output", custom_out,
        ])
        assert rc == 0
        assert os.path.exists(custom_out)

    def test_custom_size_kb(self, tmp_path):
        kernel_size = 512
        _make_artifacts(str(tmp_path), kernel_size)
        manifest = _make_manifest(kernel_size)
        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)
        output_path = str(tmp_path / "hdd.img")

        rc = nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--output", output_path,
            "--size-kb", "32768",
        ])
        assert rc == 0
        assert os.path.getsize(output_path) == 32768 * 1024

    def test_output_image_patches_applied(self, tmp_path):
        """Verify the assembled image has correct patched fields at byte level."""
        kernel_size = 1024
        _make_artifacts(str(tmp_path), kernel_size)
        manifest = _make_manifest(kernel_size)
        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)
        output_path = str(tmp_path / "hdd.img")

        nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--output", output_path,
        ])

        with open(output_path, "rb") as fh:
            img = bytearray(fh.read())

        # KERNEL_SECS at 506 (LE16)
        kernel_secs = struct.unpack_from("<H", img, 506)[0]
        assert kernel_secs == manifest["disk_layout"]["kernel_secs"]

        # SB_LBA at 512 (LE32)
        sb_lba = struct.unpack_from("<I", img, 512)[0]
        assert sb_lba == manifest["disk_layout"]["nexfs_sb_lba"]

        # CRC32 at 65532 (LE32) — covers bytes 512..65531
        stored_crc = struct.unpack_from("<I", img, 65532)[0]
        expected_crc = binascii.crc32(bytes(img[512:65532])) & 0xFFFFFFFF
        assert stored_crc == expected_crc

    def test_abi_check_flag(self, tmp_path, capsys):
        kernel_size = 1024
        _make_artifacts(str(tmp_path), kernel_size)
        manifest = _make_manifest(kernel_size)
        manifest["abi_version"] = 2
        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)

        rc = nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--abi-check", "1",
        ])
        assert rc == 1

    def test_bootloader_written_at_lba0(self, tmp_path):
        """Bootloader bytes are present at offset 0 of the output image."""
        kernel_size = 512
        bootloader_data = bytes(range(256)) * 2  # 512 non-zero bytes
        stage2 = b"\x00" * STAGE2_SIZE_EXPECTED
        kernel = b"\x00" * kernel_size
        patcher = b"# fake patcher\n"

        for name, data in [
            ("bootloader.bin", bootloader_data),
            ("stage2.bin", stage2),
            ("kernel-stripped.elf", kernel),
            ("crc32_patch.py", patcher),
        ]:
            with open(os.path.join(str(tmp_path), name), "wb") as fh:
                fh.write(data)

        manifest = _make_manifest(kernel_size)
        # Fix sha256 for our custom bootloader
        manifest["artifacts"]["bootloader.bin"]["sha256"] = _sha256(bootloader_data)

        manifest_path = str(tmp_path / "build-manifest.json")
        self._write_manifest(manifest_path, manifest)
        output_path = str(tmp_path / "hdd.img")

        nexboot.main([
            "--manifest", manifest_path,
            "--artifacts", str(tmp_path),
            "--output", output_path,
        ])

        with open(output_path, "rb") as fh:
            img = fh.read()
        # Bytes 0..505 are unmodified bootloader data;
        # bytes 506..507 are overwritten by KERNEL_SECS patch.
        assert img[0:506] == bootloader_data[0:506]
        assert img[508:512] == bootloader_data[508:512]


# ─────────────────────────────────────────────────────────────────────────────
# Additional coverage tests for uncovered branches
# ─────────────────────────────────────────────────────────────────────────────

class TestManifestValidateBranches:
    """Cover remaining manifest.validate branches."""

    def test_build_not_dict(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["build"] = "not-a-dict"
        with pytest.raises(ManifestError, match="'build' must be an object"):
            validate(manifest, str(tmp_path))

    def test_artifacts_not_dict(self, tmp_path):
        manifest = _make_manifest()
        manifest["artifacts"] = "not-a-dict"
        with pytest.raises(ManifestError, match="'artifacts' must be an object"):
            validate(manifest, str(tmp_path))

    def test_artifact_entry_not_dict(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["artifacts"]["bootloader.bin"] = "not-a-dict"
        with pytest.raises(ManifestError, match="must be an object"):
            validate(manifest, str(tmp_path))

    def test_artifact_missing_size_field(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        del manifest["artifacts"]["crc32_patch.py"]["size"]
        with pytest.raises(ManifestError, match="missing field 'size'"):
            validate(manifest, str(tmp_path))

    def test_artifact_size_not_positive_integer(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["artifacts"]["crc32_patch.py"]["size"] = 0
        with pytest.raises(ManifestError, match="size must be a positive integer"):
            validate(manifest, str(tmp_path))

    def test_stage2_wrong_size(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["artifacts"]["stage2.bin"]["size"] = 100
        with pytest.raises(ManifestError, match="stage2.bin size must be"):
            validate(manifest, str(tmp_path))

    def test_disk_layout_not_dict(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["disk_layout"] = "not-a-dict"
        with pytest.raises(ManifestError, match="'disk_layout' must be an object"):
            validate(manifest, str(tmp_path))

    def test_nexfs_sb_lba_not_integer(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["disk_layout"]["nexfs_sb_lba"] = "bad"
        with pytest.raises(ManifestError, match="nexfs_sb_lba must be a positive integer"):
            validate(manifest, str(tmp_path))

    def test_patch_offsets_not_dict(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["patch_offsets"] = "not-a-dict"
        with pytest.raises(ManifestError, match="'patch_offsets' must be an object"):
            validate(manifest, str(tmp_path))

    def test_patch_offsets_image_relative_not_dict(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["patch_offsets"]["image_relative"] = "not-a-dict"
        with pytest.raises(ManifestError, match="image_relative.*must be an object"):
            validate(manifest, str(tmp_path))

    def test_patch_offset_field_not_integer(self, tmp_path):
        _make_artifacts(str(tmp_path))
        manifest = _make_manifest()
        manifest["patch_offsets"]["image_relative"]["nexfs_sb_lba_offset"] = "bad"
        with pytest.raises(ManifestError, match="must be an integer"):
            validate(manifest, str(tmp_path))


class TestImageSaveBranchCoverage:
    """Cover PermissionError and OSError branches in image.save."""

    def test_save_permission_error(self, tmp_path):
        import stat
        img = create(4)
        out_path = str(tmp_path / "readonly.img")
        # Create file and make it read-only
        with open(out_path, "wb") as fh:
            fh.write(b"\x00")
        os.chmod(out_path, stat.S_IRUSR | stat.S_IRGRP)
        # Only run this test if we're not root
        if os.geteuid() != 0:
            with pytest.raises(ManifestError, match="cannot write output image"):
                save(img, out_path)
        os.chmod(out_path, stat.S_IRUSR | stat.S_IWUSR)

    def test_save_os_error(self, tmp_path):
        img = create(4)
        # Write to a path that doesn't exist (parent dir doesn't exist)
        with pytest.raises(ManifestError, match="cannot write output image"):
            save(img, str(tmp_path / "nonexistent_dir" / "out.img"))

    def test_load_artifact_permission_error(self, tmp_path):
        path = tmp_path / "test.bin"
        path.write_bytes(b"\x00" * 10)
        os.chmod(str(path), 0o000)
        if os.geteuid() != 0:
            with pytest.raises(ManifestError, match="not readable"):
                load_artifact(str(tmp_path), "test.bin")
        os.chmod(str(path), 0o644)


# ─────────────────────────────────────────────────────────────────────────────
# New error-path tests (REVIEW-001, REVIEW-002, REVIEW-004)
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadArtifactOSError:
    """REVIEW-001: catch-all OSError in load_artifact()."""

    def test_load_artifact_oserror(self, tmp_path, monkeypatch):
        import errno
        path = tmp_path / "boot.bin"
        path.write_bytes(b"\x00" * 512)

        def _raise(*_a, **_kw):
            raise OSError(errno.EIO, "Input/output error")

        monkeypatch.setattr("builtins.open", _raise)
        with pytest.raises(ManifestError, match="not readable"):
            load_artifact(str(tmp_path), "boot.bin")


class TestParseOSError:
    """REVIEW-002: catch-all OSError in manifest.parse()."""

    def test_parse_oserror(self, tmp_path, monkeypatch):
        import errno
        path = tmp_path / "manifest.json"
        path.write_text("{}")

        def _raise(*_a, **_kw):
            raise OSError(errno.EIO, "Input/output error")

        monkeypatch.setattr("builtins.open", _raise)
        with pytest.raises(ManifestError, match="not readable"):
            parse(str(path))


class TestValidateVerificationOSError:
    """REVIEW-002: catch-all OSError during size/SHA256 verification."""

    def test_verification_oserror(self, tmp_path, monkeypatch):
        """Simulate OSError from os.path.getsize() during artifact verification."""
        arts_dir = str(tmp_path)
        _make_artifacts(arts_dir)
        manifest = _make_manifest()

        original_getsize = os.path.getsize

        def _bad_getsize(p):
            if "bootloader.bin" in str(p):
                raise OSError(5, "Input/output error")
            return original_getsize(p)

        monkeypatch.setattr(os.path, "getsize", _bad_getsize)
        with pytest.raises(ManifestError, match="I/O error during verification"):
            validate(manifest, str(arts_dir))


class TestPatcherMalformedManifest:
    """REVIEW-004: patcher raises ManifestError for malformed manifest."""

    def test_apply_missing_patch_offsets(self):
        manifest = _make_manifest()
        del manifest["patch_offsets"]
        img = create(128)
        with pytest.raises(ManifestError, match="malformed manifest"):
            patch_image(img, manifest)

    def test_apply_kernel_secs_out_of_range(self):
        """struct.error for kernel_secs > 65535 converts to ManifestError."""
        manifest = _make_manifest(kernel_size=1024)
        manifest["disk_layout"]["kernel_secs"] = 70000  # exceeds LE16
        img = create(128)
        with pytest.raises(ManifestError, match="KERNEL_SECS value .* out of range"):
            patch_image(img, manifest)

    def test_apply_nexfs_sb_lba_out_of_range(self):
        """struct.error for nexfs_sb_lba > 0xFFFFFFFF converts to ManifestError."""
        manifest = _make_manifest(kernel_size=1024)
        manifest["disk_layout"]["nexfs_sb_lba"] = 2**32  # exceeds LE32
        img = create(128)
        with pytest.raises(ManifestError, match="SB_LBA value .* out of range"):
            patch_image(img, manifest)

