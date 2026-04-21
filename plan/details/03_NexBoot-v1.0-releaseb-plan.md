<!--
  plan/details/03_NexBoot-v1.0-releaseb-plan.md  —  NexBoot v1.0.0 release sub-phase b
-->

# Plan: NexBoot v1.0.0 Release — Sub-phase b (Core)

> **Sub-phase**: b — Core Logic
> **Branch**: `feature/ci-workflow` (continues from sub-phase a)
> **Prerequisite**: Sub-phase a complete ✅ (`.github/workflows/ci.yml` + `tests/test_ci_config.py`)
> **Delivers**: `tests/test_release_gate.py` — all v1.0.0 gating criteria as executable assertions

---

## Prior Release Context

Facts relevant to this sub-phase:

1. `plan/status.md` v1.0.0 gating table has 17 rows; 13 are ✅, 4 are ⏳
2. Required files: `nexboot.py`, `lib/__init__.py`, `lib/manifest.py`, `lib/patcher.py`, `lib/image.py`
3. Required test files: `tests/__init__.py`, `tests/test_nexboot.py`
4. Required plan files: `plan/status.md`, `plan/implementation-rules.md`, `plan/branching-strategy.md`, `plan/details/01_NexBoot-v1-plan.md`, `plan/details/02_NexBoot-v1.1-plan.md`
5. Required docs: `docs/developer-manual.md` (§1–§6)
6. Required repo files: `CLAUDE.md`, `README.md`, `LICENSE`, `pyproject.toml`, `.gitignore`
7. Required examples: `examples/nexos/build-manifest.json`
8. `pyproject.toml` must contain `[tool.ruff]` with `target-version = "py38"`, `line-length = 100`, `select = ["E", "F", "W", "I"]`
9. `.gitignore` must contain entries for `__pycache__/`, `*.py[cod]`, `.coverage`, `htmlcov/`, `*.img`
10. `docs/developer-manual.md` must contain sections `## §1` through `## §6`
11. After sub-phase a: `.github/workflows/ci.yml` and `tests/test_ci_config.py` also required
12. `REPO_ROOT = pathlib.Path(__file__).parent.parent` — same pattern as `test_ci_config.py`
13. All assertions use `pathlib.Path.exists()` or string-in-file checks; no third-party deps
14. `ManifestError` — not used in this test file; no manifest operations needed
15. Coverage must stay ≥ 95% after this sub-phase; new test file is 100% covered by definition

---

## Overview

This sub-phase translates the `plan/status.md` v1.0.0 gating table into
executable Python assertions in `tests/test_release_gate.py`. When this test
file passes, it provides machine-verified evidence that all structural
preconditions for the `v1.0.0` tag are met. This is stronger than a manual
checklist: future refactoring that accidentally deletes a required file will
fail CI before reaching `main`.

The test file covers three categories: (1) required files exist on disk,
(2) `pyproject.toml` contains the correct ruff configuration, and (3)
`docs/developer-manual.md` contains all mandatory sections. No library code
changes are made in this sub-phase.

---

## Implementation

### `tests/test_release_gate.py`

```python
# tests/test_release_gate.py  —  Assert all NexBoot v1.0.0 gating criteria as code
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
```

Key function signatures:

```python
def _read(rel_path: str) -> str:
    """Read a repo-relative file as UTF-8 text."""

class TestRequiredSourceFiles:
    """Gate: nexboot.py + lib/ implemented (stdlib only)."""
    def test_nexboot_py_exists(self) -> None: ...
    def test_lib_init_exists(self) -> None: ...
    def test_lib_manifest_exists(self) -> None: ...
    def test_lib_patcher_exists(self) -> None: ...
    def test_lib_image_exists(self) -> None: ...
    def test_tests_init_exists(self) -> None: ...
    def test_tests_nexboot_exists(self) -> None: ...

class TestRequiredRepoFiles:
    """Gate: repo metadata and config files present."""
    def test_claude_md_exists(self) -> None: ...
    def test_readme_exists(self) -> None: ...
    def test_license_exists(self) -> None: ...
    def test_pyproject_toml_exists(self) -> None: ...
    def test_gitignore_exists(self) -> None: ...

class TestRequiredPlanFiles:
    """Gate: all plan documents present."""
    def test_status_md_exists(self) -> None: ...
    def test_implementation_rules_exists(self) -> None: ...
    def test_branching_strategy_exists(self) -> None: ...
    def test_v1_plan_exists(self) -> None: ...
    def test_v1_1_plan_exists(self) -> None: ...

class TestRequiredArtifacts:
    """Gate: examples and CI config present."""
    def test_example_manifest_exists(self) -> None: ...
    def test_ci_workflow_exists(self) -> None: ...
    def test_developer_manual_exists(self) -> None: ...

class TestPyprojectConfig:
    """Gate: ruff configuration matches project standards."""
    def test_has_ruff_section(self) -> None: ...
    def test_target_version_py38(self) -> None: ...
    def test_line_length_100(self) -> None: ...
    def test_select_includes_e(self) -> None: ...
    def test_select_includes_f(self) -> None: ...
    def test_select_includes_w(self) -> None: ...
    def test_select_includes_i(self) -> None: ...

class TestGitignoreEntries:
    """Gate: .gitignore covers generated and temporary files."""
    def test_ignores_pycache(self) -> None: ...
    def test_ignores_pyc(self) -> None: ...
    def test_ignores_coverage(self) -> None: ...
    def test_ignores_htmlcov(self) -> None: ...
    def test_ignores_img(self) -> None: ...

class TestDeveloperManualSections:
    """Gate: developer-manual.md contains all required sections."""
    def test_has_section_1(self) -> None: ...
    def test_has_section_2(self) -> None: ...
    def test_has_section_3(self) -> None: ...
    def test_has_section_4(self) -> None: ...
    def test_has_section_5(self) -> None: ...
    def test_has_section_6(self) -> None: ...
```

Critical assertion examples:

```python
# TestRequiredSourceFiles
def test_nexboot_py_exists(self) -> None:
    assert (REPO_ROOT / "nexboot.py").exists()

# TestPyprojectConfig
def test_target_version_py38(self) -> None:
    content = _read("pyproject.toml")
    assert 'target-version = "py38"' in content

# TestDeveloperManualSections
def test_has_section_6(self) -> None:
    content = _read("docs/developer-manual.md")
    assert "## §6" in content
```

---

## CLI / API Changes

None in this sub-phase.

---

## Updated Existing Components

None. This sub-phase adds only `tests/test_release_gate.py`.

---

## Implementation Standards

- `tests/test_release_gate.py` follows §1 (file header), §2 (naming) from `plan/implementation-rules.md`
- Stdlib only: `pathlib` — no third-party imports
- `_read()` helper uses `encoding="utf-8"` explicitly
- All test classes have a one-line docstring stating which gate they cover
- No `tmp_path` fixture — reads real repo files via `REPO_ROOT`

---

## Security

- Test file is read-only; it never writes to disk
- No subprocess calls; no network access
- `REPO_ROOT` is computed from `__file__`, not from environment variables — cannot be redirected by an attacker controlling the environment

---

## Files Changed / Created

| File | Status | Purpose |
|------|--------|---------|
| `tests/test_release_gate.py` | New | ≥ 30 assertions covering all v1.0.0 gating criteria |

---

## Test Coverage

| Class | Test functions | Gate covered |
|-------|---------------|-------------|
| `TestRequiredSourceFiles` | 7 | `nexboot.py` + `lib/` implemented |
| `TestRequiredRepoFiles` | 5 | `CLAUDE.md`, `README.md`, `LICENSE`, `pyproject.toml`, `.gitignore` |
| `TestRequiredPlanFiles` | 5 | All 5 plan documents present |
| `TestRequiredArtifacts` | 3 | `examples/nexos/`, `ci.yml`, `developer-manual.md` |
| `TestPyprojectConfig` | 7 | Ruff config correctness |
| `TestGitignoreEntries` | 5 | Key `.gitignore` entries |
| `TestDeveloperManualSections` | 6 | §1–§6 all present |
| **Total** | **≥ 38** | All structural v1.0.0 gates |

---

## Commit Message

```
tests: add release gate assertions for v1.0.0 gating criteria

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```
