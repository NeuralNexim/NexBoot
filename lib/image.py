# lib/image.py  —  NexBoot disk image creation and artifact writing

import os

from lib.manifest import ManifestError

BYTES_PER_SECTOR = 512


def create(size_kb):
    """Return a zero-filled bytearray of *size_kb* × 1024 bytes.

    Raises ManifestError if *size_kb* is not a positive integer.
    """
    if not isinstance(size_kb, int) or size_kb <= 0:
        raise ManifestError(f"--size-kb must be a positive integer, got {size_kb!r}")
    return bytearray(size_kb * 1024)


def write_artifact(image, data, lba):
    """Write *data* (bytes or bytearray) into *image* starting at LBA *lba*.

    Raises ManifestError if the write would exceed image bounds.
    """
    offset = lba * BYTES_PER_SECTOR
    end = offset + len(data)
    if offset < 0 or end > len(image):
        raise ManifestError(
            f"write_artifact: data ({len(data)} bytes) at LBA {lba} "
            f"(offset {offset}..{end-1}) exceeds image size {len(image)}"
        )
    image[offset:end] = data


def load_artifact(artifacts_dir, name):
    """Read and return the raw bytes of artifact *name* from *artifacts_dir*.

    Raises ManifestError if the file cannot be read.
    """
    path = os.path.join(artifacts_dir, name)
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        raise ManifestError(f"artifact file not found: {path}")
    except PermissionError:
        raise ManifestError(f"artifact file not readable: {path}")
    except OSError as exc:
        raise ManifestError(f"artifact file not readable: {path}: {exc}") from exc


def save(image, path):
    """Write *image* (bytearray) to *path*.

    Raises ManifestError if the file cannot be written.
    """
    try:
        with open(path, "wb") as fh:
            fh.write(image)
    except PermissionError:
        raise ManifestError(f"cannot write output image: permission denied: {path}")
    except OSError as exc:
        raise ManifestError(f"cannot write output image: {exc}")
