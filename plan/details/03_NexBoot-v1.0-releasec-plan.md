<!--
  plan/details/03_NexBoot-v1.0-releasec-plan.md  —  NexBoot v1.0.0 release sub-phase c
-->

# Plan: NexBoot v1.0.0 Release — Sub-phase c (Polish)

> **Sub-phase**: c — Polish + Release
> **Branch**: `feature/ci-workflow` (continues from sub-phase b)
> **Prerequisite**: Sub-phases a and b complete ✅; CI green on `feature/ci-workflow`
> **Delivers**: `plan/status.md` completion + NexTinyOS cross-repo note template + `v1.0.0` tag procedure

---

## Prior Release Context

Facts relevant to this sub-phase:

1. After sub-phases a + b: `tests/test_ci_config.py` (≥ 30), `tests/test_release_gate.py` (≥ 38), `tests/test_nexboot.py` (75 + 2 skipped) all passing
2. `plan/status.md` v1.0.0 gating table has 4 ⏳ items remaining before this sub-phase
3. The "CI passes against a real NexTinyOS artifact bundle" gate requires a live NexTinyOS artifact; it is documented as ⏳ with a note until confirmed
4. "NexTinyOS `docs/developer-manual.md` updated to link NexBoot" is a cross-repo action; NexBoot provides the template text only
5. `v1.0.0` tag is created on `main` after `release/v1.0` merges; not created on a feature branch
6. Branch flow requires `feature/ci-workflow` → `release/v1.0` → `main` before tagging
7. `plan/status.md` must add a NexBoot v1.1.0 milestone section referencing `plan/details/02_NexBoot-v1.1-plan.md`
8. `docs/developer-manual.md` §1 should mention `.venv` activation for local dev (Windows: `.\.venv\Scripts\Activate.ps1`)
9. `SUPPORTED_ABI_VERSIONS = (1,)` — no change; v1.1.0 does not touch ABI
10. Total test count after this sub-phase: ≥ 135 passed, 2 skipped, 97%+ coverage

---

## Overview

This sub-phase closes the v1.0.0 milestone. It updates `plan/status.md` to mark
all completable gates ✅ and adds the v1.1.0 milestone stub. It adds a `.venv`
setup note to `docs/developer-manual.md` §1 so Windows developers can reproduce
the local test run. It documents a cross-repo note template for NexTinyOS
maintainers to link NexBoot from their developer manual. Finally, it defines the
exact tag and merge procedure as a checklist in `plan/status.md`.

No new test files are created in this sub-phase. The master integration test
suite is the combined run of all three test files from sub-phases a, b, and the
pre-existing suite — providing ≥ 135 assertions at ≥ 95% coverage.

Sub-plan c also serves as the canonical record of the `v1.0.0` release procedure
so future maintainers can reproduce the same flow for v1.1.0 and beyond.

---

## Implementation

### `plan/status.md` — Update v1.0.0 section

Mark the following gates ✅ after CI confirms green:

| Gate | Action |
|------|--------|
| GitHub Actions CI passing (Python 3.10+, pytest, lint) | ✅ after `release/v1.0` CI green |
| CI passes against a real NexTinyOS artifact bundle | ✅ when confirmed; else document as deferred to v1.1.0 |
| NexTinyOS `docs/developer-manual.md` updated to link NexBoot | ✅ after cross-repo PR merged |
| `v1.0.0` tag created | ✅ after `release/v1.0` merges to `main` |

Add test result line: `tests/test_nexboot.py` + `tests/test_ci_config.py` + `tests/test_release_gate.py`
≥ 135 passed, 2 skipped.

### `plan/status.md` — Add v1.1.0 milestone stub

Append after the v1.0.0 section:

```markdown
---

## NexBoot v1.1.0  ⏳ Planned

**Branch**: `feature/abi-enforcement` → `release/v1.1` → `main`
**Prerequisites**: NexBoot v1.0.0 complete ✅
**Plan**: [02_NexBoot-v1.1-plan.md](details/02_NexBoot-v1.1-plan.md)
**Implementation plan**: [03_NexBoot-v1.0-release-plan.md](details/03_NexBoot-v1.0-release-plan.md)

### Gating criteria

(See plan/details/02_NexBoot-v1.1-plan.md for full gate table)

---

## Next Task

Implement v1.1.0: architecture boundary enforcement.
See plan/details/02_NexBoot-v1.1-plan.md.
```

### `docs/developer-manual.md` — §1 Prerequisites update

Add `.venv` activation instructions after the `pip install` line:

```markdown
For local development on Windows, activate the project virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ --cov=lib --cov=nexboot --cov-report=term-missing
```

On Linux/macOS:

```bash
source .venv/bin/activate
python -m pytest tests/ --cov=lib --cov=nexboot --cov-report=term-missing
```
```

### NexTinyOS Cross-Repo Note Template

The following text is to be added to NexTinyOS `docs/developer-manual.md` by
the NexTinyOS maintainer. NexBoot does not open PRs to other repositories
directly — this is the canonical template.

> **Suggested location**: after the `installer-artifacts` section in NexTinyOS
> developer manual.

```markdown
## NexBoot — Disk Image Installer

NexBoot is the installer tool for NexTinyOS. It reads the artifact bundle
produced by `make installer-artifacts`, verifies all four artifacts against
the SHA256 hashes in `build-manifest.json`, and assembles a bootable disk
image ready for use with QEMU or bare metal.

**Repository**: https://github.com/NeuralNexim/NexBoot  
**ABI contract**: `docs/boot-interface-contract.md` (this repo, ABI v1)  
**Install**:

```bash
git clone https://github.com/NeuralNexim/NexBoot.git
cd NexBoot
python3 nexboot.py \
  --manifest build/installer-artifacts/build-manifest.json \
  --artifacts build/installer-artifacts/ \
  --output hdd.img
```

Any OS that produces a `build-manifest.json` conforming to ABI v1 can use
NexBoot without modification.
```

### `v1.0.0` Tag and Merge Procedure

```
1. Confirm CI green on `feature/ci-workflow` (all 3 Python versions)
2. Open PR: feature/ci-workflow → release/v1.0
3. Squash-merge into release/v1.0
4. Confirm CI green on release/v1.0
5. Open PR: release/v1.0 → main
6. Merge commit (not squash) into main
7. Confirm CI green on main
8. git tag v1.0.0
9. git push origin v1.0.0
10. Update plan/status.md: v1.0.0 → ✅ Complete, v1.1.0 → 🔄 In Progress
```

---

## Library / SDK Changes

None. All public API signatures in `lib/` remain unchanged.

| Symbol | Change |
|--------|--------|
| `ManifestError` | No change |
| `parse()` | No change |
| `validate()` | No change |
| `apply()` | No change |
| `create()`, `write_artifact()`, `load_artifact()`, `save()` | No change |

---

## Documentation Update Spec

| File | Section | Instruction |
|------|---------|-------------|
| `plan/status.md` | v1.0.0 table | Mark 4 ⏳ gates ✅ after confirmation |
| `plan/status.md` | New section | Append v1.1.0 stub + updated "Next Task" |
| `docs/developer-manual.md` | §1 Prerequisites | Add `.venv` activation block (Windows + Linux) |

---

## Master Integration Test Suite

Run order and expected results after all three sub-phases:

```bash
python -m pytest tests/ --cov=lib --cov=nexboot --cov-report=term-missing -v
```

| Suite | Expected | Assertions |
|-------|----------|------------|
| `tests/test_nexboot.py` | 75 passed, 2 skipped | ABI v1 runtime: parse, validate, patch, image, CLI |
| `tests/test_ci_config.py` | ≥ 30 passed | CI YAML structure: triggers, matrix, steps, security |
| `tests/test_release_gate.py` | ≥ 38 passed | v1.0.0 gates: file existence, ruff config, .gitignore, §1–§6 |
| **Total** | **≥ 143 passed, 2 skipped** | |

Coverage targets:

| Module | Target |
|--------|--------|
| `lib/__init__.py` | 100% |
| `lib/manifest.py` | ≥ 95% |
| `lib/patcher.py` | 100% |
| `lib/image.py` | ≥ 95% |
| `nexboot.py` | 100% |
| `tests/test_ci_config.py` | 100% |
| `tests/test_release_gate.py` | 100% |
| **Overall** | **≥ 97%** |

---

## Files Changed / Created

| File | Status | Purpose |
|------|--------|---------|
| `plan/status.md` | Modified | Mark v1.0.0 ✅, add v1.1.0 stub, update Next Task |
| `docs/developer-manual.md` | Modified | §1: add `.venv` activation note |

---

## Commit Message

```
docs: mark v1.0.0 complete in status.md, add v1.1.0 stub, update developer manual §1

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```
