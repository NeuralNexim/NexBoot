# NexBoot — Implementation Rules

Adapted from NexTinyOS `plan/implementation-rules.md` for Python/pytest.

---

## §1 — Python Style

- **Python 3.8+** minimum; no third-party runtime dependencies (stdlib only).
- **PEP 8**: 4-space indentation; no tabs; 79-char line limit preferred.
- **File header**: every `.py` starts with:
  ```python
  # nexboot/lib/manifest.py  —  Brief description
  ```
- **Type hints** on all public functions.
- **Docstrings** for module-level and public functions (one-liner minimum).
- **Error handling**: raise `ManifestError` / `NexBootError` in library code;
  `nexboot.py` catches it and calls `sys.exit(1)`.
- **Internal helpers** prefixed with `_`; not exported from the module.
- **Constants**: `UPPER_CASE`; no magic numbers in patch/image logic.
- **No dynamic imports**: all imports at module top level.

---

## §2 — Testing Rules

- **Framework**: `pytest`.
- **Coverage**: ≥ 95% on all files touched in each change (`pytest --cov`).
- **New test files** must be in `tests/`.
- **Every public function** needs at least one test assertion.
- **No mocking library** required — use `tmp_path` fixture and fixture helpers.
- Name test classes `Test<Topic>` and test functions `test_<scenario>`.

---

## §6 — Branching & Commit Rules

Flow: `feature/<topic>` → `release/vX.Y` → `main`

- Feature branches cut from `main`.
- Sub-features merge into a versioned release branch before `main`.
- **Never** merge a feature branch directly into `main`.
- Commit messages: `<scope>: <imperative description>`.
- Every PR that changes public API must include updated docs and tests.
- See `plan/branching-strategy.md` for full details.

---

## §8 — Pre-Commit Gate (mandatory)

Before every `git commit`:

1. **Coverage**: `pytest tests/ --cov=lib --cov=nexboot` — ≥ 95% on changed files.
2. **Peer review** (`/peer-review` skill) — BLOCKING: 0.
3. **Fix blocking issues** (`/implement-review`) if BLOCKING > 0.
4. **Docs gate** (§9) — all changed public APIs reflected in `docs/developer-manual.md`.
5. Commit with `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

---

## §9 — Documentation Gate (mandatory)

Update `docs/developer-manual.md` when:
- Public function signatures in `lib/` change.
- CLI flags (`nexboot.py`) change.
- ABI version table changes.
- New module added to `lib/`.

Update `README.md` when CLI usage or ABI version table changes.
