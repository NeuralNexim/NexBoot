# Code Review: main (initial commit)
**Date**: 2025-07-16
**Reviewer**: claude-opus-4.7
**Status**: RESOLVED
**Blocking issues**: 0
**Non-blocking issues**: 0

---

### REVIEW-001
**Severity**: BLOCKING
**File**: `lib/image.py`
**Line**: `load_artifact()` — the `except` chain ending at ~line 40
**Category**: missing-error-path
**Issue**: `load_artifact()` catches only `FileNotFoundError` and `PermissionError`. Any other `OSError` — `EIO` from a flaky disk, `ESTALE` from an NFS mount, `ENOSPC` mid-read on a compressed fs — falls through unhandled. Because `nexboot.py:main()` catches only `ManifestError`, the uncaught `OSError` produces a Python traceback and an exit code of 1 via the interpreter default, bypassing the `"nexboot: error: …"` message entirely. Confirmed live: simulated `OSError(errno.EIO)` escapes the function unchanged.
**Fix**: Add a catch-all after the specific handlers:
```python
except OSError as exc:
    raise ManifestError(f"artifact file not readable: {path}: {exc}")
```

---

### REVIEW-002
**Severity**: BLOCKING
**File**: `lib/manifest.py`
**Line**: `parse()` (~line 30–40) and `_sha256_file()` (~line 160–170), plus `os.path.getsize()` call inside `validate()`
**Category**: missing-error-path
**Issue**: Three separate spots in `manifest.py` can leak raw `OSError` past `nexboot.py`'s `except ManifestError` guard. `parse()` catches `FileNotFoundError`, `PermissionError`, and `JSONDecodeError` but nothing else — a disk read error mid-`json.load()` escapes. `_sha256_file()` has **zero** exception handling: if the file disappears between the `os.path.isfile()` TOCTOU check and the `open()`, or if any read chunk raises `EIO`, the OSError propagates directly to `main()`. The unguarded `os.path.getsize(path)` call in `validate()` has the same exposure. All three paths are in the file-verification loop called from `nexboot.py:main()`.
**Fix**: Wrap `_sha256_file()` body in a `try/except OSError` and convert to `ManifestError`. Add a catch-all `except OSError` to `parse()`. Guard `os.path.getsize()` similarly, or fold it into a try block alongside the `_sha256_file()` call.

---

### REVIEW-003
**Severity**: NON-BLOCKING
**File**: `lib/manifest.py`
**Line**: `validate()` — nexfs_sb_lba cross-field check, approximately lines 108–115
**Category**: logic-error
**Issue**: The `nexfs_sb_lba` formula cross-check executes unconditionally even when `kernel_secs > KERNEL_SECS_MAX` is already in the error list. For `kernel_secs = 65536`, the formula computes `expected_sb = 128 + ((65536 + 63) & ~63) = 65664` — a value derived from an **invalid** kernel_secs that itself exceeds the LE16 ceiling. If the manifest has a plausible `nexfs_sb_lba` (e.g. `192`, correct for a small kernel), a second spurious error is emitted. This confuses a developer because it suggests two unrelated problems when there is one.
**Fix**: Gate the `nexfs_sb_lba` formula check on the absence of a prior `kernel_secs` range error:
```python
elif kernel_secs > KERNEL_SECS_MAX:
    errors.append(...)
else:
    # kernel_secs is valid — now cross-check nexfs_sb_lba
    if isinstance(nexfs_sb_lba, int):
        expected_sb = 128 + ((kernel_secs + 63) & ~63)
        if nexfs_sb_lba != expected_sb:
            errors.append(...)
```

---

### REVIEW-004
**Severity**: NON-BLOCKING
**File**: `lib/patcher.py`
**Line**: `apply()` — lines 1–10 of the function body (dict access and `struct.pack_into` calls)
**Category**: missing-error-path
**Issue**: `apply()` uses bare `[]` key access on the manifest dict and calls `struct.pack_into` without guards. A malformed manifest passed directly raises `KeyError` or `struct.error` instead of `ManifestError`. A test asserting `pytest.raises(ManifestError)` against `apply()` with a truncated manifest will fail with an unexpected `KeyError`. Both failure modes confirmed live.
**Fix**: Wrap the manifest access block and `struct.pack_into` calls in try/except that converts `KeyError`, `TypeError`, and `struct.error` to `ManifestError`.

---

BLOCKING: 2  NON-BLOCKING: 2  TOTAL: 4

---

## Resolution Log

| ID | Severity | Resolved? | Commit |
|----|----------|-----------|--------|
| REVIEW-001 | BLOCKING | ✅ | initial |
| REVIEW-002 | BLOCKING | ✅ | initial |
| REVIEW-003 | NON-BLOCKING | ✅ | initial |
| REVIEW-004 | NON-BLOCKING | ✅ | initial |
