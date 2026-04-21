# NexBoot — Copilot CLI Instructions

## Test command

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=lib --cov=nexboot --cov-report=term-missing
```

Coverage on all changed files must be **≥ 95 %** before committing.

## Lint

```bash
ruff check .
```

## Build notes

- Pure Python 3.8+; no third-party **runtime** dependencies (stdlib only).
- Test dependencies: `pytest`, `pytest-cov`, `ruff`.

## Branching rules

Flow: `feature/<topic>` → `release/vX.Y` → `main`

- Feature branches are cut from `main`.
- Sub-features merge into a versioned release branch before `main`.
- **Never** merge a feature branch directly into `main`.
- Commit messages: `<scope>: <imperative description>`.
- See `plan/branching-strategy.md` for the full branch-flow diagram.

## Style notes (Python)

- Python 3.8+ minimum; stdlib only (no third-party imports in `lib/` or `nexboot.py`).
- PEP 8; 4-space indentation; no tabs.
- Every `.py` file starts with a `# path  —  brief description` comment.
- Type hints on all public functions; docstrings for module-level functions.
- Fatal errors: raise `ManifestError` (or `NexBootError`) in library code;
  `nexboot.py` catches it and calls `sys.exit(1)`.
- Internal (non-public) helpers are prefixed with `_`.
- Constants: `UPPER_CASE`; no magic numbers in patch/image logic.

## Pre-commit gate (mandatory)

Before every `git commit`:
1. `pytest tests/ --cov=lib --cov=nexboot` — coverage ≥ 95 %
2. `/peer-review` skill — BLOCKING: 0
3. Docs updated if public API or CLI changed
4. `git status` — no untracked project files

## Source rule (permanent)

Bootloader `.asm` / `.c` source **never** moves to NexBoot.
NexBoot only patches and assembles binary artifacts.
