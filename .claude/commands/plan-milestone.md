# plan-milestone

Analyse a project's roadmap and existing plan documents, then generate a
complete set of structured implementation-detail plan files for the next
milestone.

## Input

Optional milestone identifier (e.g. `v2.0`, `R0014`, `PHASE-4`).
If omitted, infer from `plan/status.md` "Next Task" entry or ask the user.

$ARGUMENTS

## Procedure

### 1 — Gather source material (run in parallel)

Read the following, all at once:
- `plan/status.md` — current milestone status and "Next Task"
- `plan/implementation-rules.md` — project constraints, test requirements
- The most recent completed milestone plan in `plan/details/` (as a template)
- The project README or developer manual for public API context

Identify the target milestone tag from the arguments or from `plan/status.md`.

### 2 — Determine the sub-phase split

Divide the milestone into exactly **three sub-phases** (a / b / c):

| Sub-phase | Typical character |
|-----------|------------------|
| **a** | Foundation — new data structures, detection/init, first diagnostic |
| **b** | Core logic — implementation, integration, second diagnostic |
| **c** | Polish — library wrappers, master test suite, all doc updates |

Each sub-phase must be independently reviewable and testable. Document the
rationale briefly in the top-level plan.

### 3 — Draft the top-level plan

Sections (in order):

1. **Header** — milestone tag, branch, prerequisite releases, successor.
2. **Prior Release Context** — bullet list (10–20 items) of constants, API
   symbols, structs, and decisions from previous milestones that constrain
   this one. Facts only; no code blocks.
3. **Platform / Target** — supported environments and any no-op fallback
   guarantee on unsupported targets.
4. **Overview** — 2–3 paragraphs: what changes, why, fallback guarantee.
5. **Goals** — sub-sections: Core mechanisms, CLI/API changes (table with
   sub-phase column), Library/SDK changes, Documentation, Tests.
6. **New Constants & Symbols** — table: symbol, value/type, meaning.
7. **Architecture Changes** — table: document/file, section, change.
8. **Test Results Target** — expected pass counts per suite; all prior suites
   must remain green.
9. **Sub-Phase Summary** — table linking to sub-plan files with one-line
   summaries.

### 4 — Draft sub-plan a

Sections (in order):

1. **Header** — sub-phase title, branch, prerequisite.
2. **Prior Release Context** — focus on facts relevant to this sub-phase.
3. **Overview** — what this sub-phase delivers and why it is self-contained.
4. **Implementation** — detailed design per new file or module:
   - Key data structures/types (code blocks in the project's language).
   - Key function/method signatures with brief behavioural description.
   - Critical sequences (init order, protocol steps) in code blocks.
5. **CLI / API Changes** — for each new command or endpoint: synopsis,
   options table, example output.
6. **Updated Existing Components** — what changes and how.
7. **Implementation Standards** — cross-reference to project rules relevant
   to this sub-phase.
8. **Security** — trust boundaries, input validation, access control notes.
9. **Files Changed / Created** — table: file, new/modified, purpose.
10. **Test Coverage** — test groups, assertion counts, what each covers
    (minimum 30 assertions).
11. **Commit Message** — verbatim commit message to copy-paste.

### 5 — Draft sub-plans b and c

Follow the same section template as sub-plan a.

Sub-plan c **must also include**:
- **Library / SDK changes** — new public functions, signature-stable upgrades.
- **Documentation update spec** — per-section instructions for each doc file
  that needs updating.
- **Master integration test suite** — full assertion list covering all three
  sub-phases (minimum 60 assertions).

### 6 — Validate before writing

For each draft, verify manually:
- Prior-context bullets reference real symbols visible in the codebase.
- Every new CLI command or public API documents its prerequisites.
- Assertion count floors: a ≥ 30, b ≥ 30, c ≥ 60, total ≥ 120.
- No plan file references project-specific tools or infrastructure that
  doesn't exist in this project.

### 7 — Write files

Determine the next sequential `NN` prefix by listing `plan/details/` — take
the highest existing number and increment by one for each new file.

Write four files to `plan/details/`:
1. `NN_<TAG>-plan.md`   — top-level plan
2. `NN_<TAG>a-plan.md`  — sub-phase a
3. `NN_<TAG>b-plan.md`  — sub-phase b
4. `NN_<TAG>c-plan.md`  — sub-phase c

### 8 — Branch and commit (only if user confirms)

Ask the user whether to also create the release branch and commit now.
If yes:
- Create branch `release/<TAG>` (or project convention) from integration branch.
- Stage the four new plan files only.
- Commit: `docs(<TAG>): add implementation plan — <one-line summary>`
- Push with `-u origin <branch>`.

## Output format

After all files are written:

| File | Lines | Sub-phase |
|------|-------|-----------|
| NN_TAG-plan.md  | N | top-level |
| NN_TAGa-plan.md | N | a |
| NN_TAGb-plan.md | N | b |
| NN_TAGc-plan.md | N | c |

Then briefly describe what each sub-phase delivers and the test assertion floor.
