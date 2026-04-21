<!--
  plan/details/03_NexBoot-v1.0-releasea-plan.md  —  NexBoot v1.0.0 release sub-phase a
-->

# Plan: NexBoot v1.0.0 Release — Sub-phase a (Foundation)

> **Sub-phase**: a — CI Foundation
> **Branch**: `feature/ci-workflow`
> **Prerequisite**: NexBoot v1.0.0 implementation complete ✅
> **Delivers**: `.github/workflows/ci.yml` + `tests/test_ci_config.py`

---

## Prior Release Context

Facts relevant to this sub-phase:

1. `pyproject.toml` ruff config: `target-version = "py38"`, `line-length = 100`, `select = ["E", "F", "W", "I"]`, `ignore = ["E501"]`
2. Test command: `pytest tests/ --cov=lib --cov=nexboot --cov-report=term-missing`
3. Lint command: `ruff check .`
4. Test deps: `pytest`, `pytest-cov`, `ruff` — no third-party runtime deps
5. `tests/test_nexboot.py` — 75 passed, 2 skipped (Windows `chmod` tests), 97% coverage
6. Branch flow: `feature/ci-workflow` → `release/v1.0` → `main`
7. Python minimum: 3.8; CI matrix: 3.10, 3.11, 3.12
8. `ManifestError` is the sole public exception; no new exceptions in this sub-phase
9. No changes to `lib/` or `nexboot.py` in this sub-phase
10. `.venv` is in `.gitignore`; CI must install deps fresh from `pyproject.toml` or direct `pip install`

---

## Overview

This sub-phase creates the GitHub Actions CI workflow and a companion test
module that validates the workflow's structure as assertions. The CI workflow
runs on every push and pull request to `main`, executes `ruff check .` before
`pytest`, and uses a 3-version Python matrix so regressions on any supported
interpreter are caught immediately. The companion `tests/test_ci_config.py`
reads the YAML as plain text and asserts the structural requirements — this
means the CI configuration is itself subject to the same pre-commit gate as
all other code.

This sub-phase is self-contained: it adds only new files, changes nothing in
`lib/` or `tests/test_nexboot.py`, and its new test file is independently
runnable locally before CI is ever triggered.

---

## Implementation

### `.github/workflows/ci.yml`

Key structural requirements:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-cov ruff

      - name: Lint with ruff
        run: ruff check .

      - name: Test with pytest
        run: |
          pytest tests/ --cov=lib --cov=nexboot --cov-report=term-missing
```

Design decisions:
- `fail-fast: false` — all 3 matrix variants run even if one fails, so per-version failures are visible
- `actions/checkout@v4` and `actions/setup-python@v5` — current pinned major versions
- Lint step (`ruff`) runs before tests so formatting errors surface first
- No coverage threshold `--cov-fail-under` in CI command — threshold is enforced by pre-commit gate; CI shows the number
- No `GITHUB_TOKEN` or secrets required — pure test/lint run

### `tests/test_ci_config.py`

```python
# tests/test_ci_config.py  —  Structural assertions on .github/workflows/ci.yml

import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
```

Key function signatures:

```python
def _read_ci() -> str:
    """Read the CI workflow file as a string. Fails fast if missing."""

class TestCIWorkflowExists:
    def test_workflow_file_exists(self) -> None: ...

class TestCIWorkflowTriggers:
    def test_has_on_trigger(self) -> None: ...
    def test_triggers_on_push(self) -> None: ...
    def test_triggers_on_pull_request(self) -> None: ...
    def test_triggers_on_main_branch(self) -> None: ...

class TestCIWorkflowMatrix:
    def test_has_strategy(self) -> None: ...
    def test_has_matrix(self) -> None: ...
    def test_matrix_has_python_version(self) -> None: ...
    def test_matrix_includes_310(self) -> None: ...
    def test_matrix_includes_311(self) -> None: ...
    def test_matrix_includes_312(self) -> None: ...
    def test_fail_fast_false(self) -> None: ...

class TestCIWorkflowRunner:
    def test_runs_on_ubuntu(self) -> None: ...
    def test_uses_checkout_action(self) -> None: ...
    def test_uses_setup_python_action(self) -> None: ...
    def test_uses_matrix_python_version(self) -> None: ...

class TestCIWorkflowSteps:
    def test_has_pip_install(self) -> None: ...
    def test_installs_pytest(self) -> None: ...
    def test_installs_pytest_cov(self) -> None: ...
    def test_installs_ruff(self) -> None: ...
    def test_has_ruff_check(self) -> None: ...
    def test_has_pytest_step(self) -> None: ...
    def test_pytest_covers_lib(self) -> None: ...
    def test_pytest_covers_nexboot(self) -> None: ...
    def test_pytest_cov_report(self) -> None: ...
    def test_lint_step_before_test_step(self) -> None: ...

class TestCIWorkflowSecurity:
    def test_no_hardcoded_token(self) -> None: ...
    def test_no_sudo(self) -> None: ...
    def test_no_force_push(self) -> None: ...
    def test_pip_upgrade_present(self) -> None: ...
```

Critical sequence for `test_lint_step_before_test_step`:

```python
ci_text = _read_ci()
ruff_pos = ci_text.index("ruff check")
pytest_pos = ci_text.index("pytest tests/")
assert ruff_pos < pytest_pos, "ruff must run before pytest"
```

---

## CLI / API Changes

None in this sub-phase.

---

## Updated Existing Components

None. This sub-phase adds only new files.

---

## Implementation Standards

- `tests/test_ci_config.py` follows §1 (file header comment) and §2 (test naming: `Test<Topic>` / `test_<scenario>`) from `plan/implementation-rules.md`
- `pathlib.Path` used throughout — no `os.path` string manipulation
- No third-party imports in `test_ci_config.py` (stdlib only: `pathlib`)
- All test functions have no parameters (no `tmp_path` needed — reads repo files directly)

---

## Security

- CI workflow must not expose `GITHUB_TOKEN` in logs — assert its absence from the YAML text
- No `sudo` in CI steps — the `ubuntu-latest` runner provides a non-root environment by default
- Pinned action versions (`@v4`, `@v5`) — not `@latest`; prevents supply-chain drift

---

## Files Changed / Created

| File | Status | Purpose |
|------|--------|---------|
| `.github/workflows/ci.yml` | New | GitHub Actions CI pipeline |
| `tests/test_ci_config.py` | New | Structural assertions on CI YAML (≥ 30 assertions) |

---

## Test Coverage

| Class | Test functions | What it covers |
|-------|---------------|----------------|
| `TestCIWorkflowExists` | 1 | File presence |
| `TestCIWorkflowTriggers` | 4 | `on: push/pull_request: branches: [main]` |
| `TestCIWorkflowMatrix` | 6 | Python 3.10/3.11/3.12 matrix, `fail-fast: false` |
| `TestCIWorkflowRunner` | 4 | `ubuntu-latest`, `checkout`, `setup-python`, matrix ref |
| `TestCIWorkflowSteps` | 10 | pip, pytest, pytest-cov, ruff, `--cov` flags, lint-before-test order |
| `TestCIWorkflowSecurity` | 4 | No hardcoded token, no sudo, no force-push, pip upgrade |
| **Total** | **≥ 30** | Full structural coverage of `ci.yml` |

---

## Commit Message

```
ci: add GitHub Actions workflow and CI config test suite

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```
