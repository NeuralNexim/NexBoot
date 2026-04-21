# Implement Next Task

A project-agnostic skill that picks the next task from `plan/status.md`,
implements it, gates it through tests + peer review, and commits.

---

## Pre-Processing: Branch Sync Check (mandatory — run first)

Before reading any plan file or writing any code, check the local branch is
not missing commits from the integration branch (`main`, `development`, or
`master` — whichever the project uses).

```bash
CURRENT=$(git branch --show-current)
INTEGRATION=$(git branch --list main development master \
              | sed 's/^[* ]*//' | head -1)
echo "=== Branch sync check: $CURRENT vs $INTEGRATION ==="

MISSING=$(git log --oneline "$INTEGRATION" ^HEAD 2>/dev/null)

if [ -n "$MISSING" ]; then
  COUNT=$(echo "$MISSING" | wc -l | tr -d ' ')
  echo "⚠️  WARNING: $COUNT commit(s) in '$INTEGRATION' missing from '$CURRENT':"
  echo "$MISSING" | nl -ba
  echo ""
  echo "ACTION REQUIRED — merge or rebase before proceeding:"
  echo "  git fetch origin && git merge $INTEGRATION"
else
  echo "✅ '$CURRENT' is in sync with $INTEGRATION"
fi
```

**Stop and report if any missing commits are found.** Only continue once the
check passes or the user explicitly accepts the divergence.

---

## Identify Next Task

Read `plan/status.md` and identify the current "Next Task" entry.

Then:
1. Read the referenced plan file in full (e.g. `plan/details/NN_topic-plan.md`).
2. Read `plan/implementation-rules.md` — apply all rules strictly.
3. Implement the next phase in order — do not skip phases.
4. Each phase must pass its gate (tests, review) before proceeding.

---

## Pre-Commit Gate (mandatory for every commit)

### 1. Run tests and check coverage

Read `plan/implementation-rules.md` for the project's test command.
If not specified, auto-detect: `make test`, `pytest`, `npm test`, `go test ./...`.

Coverage on all files touched in this change must be **≥ 95%**.
If below 95%, add or extend tests before continuing.

### 2. Peer review

After tests pass, run the `/peer-review` skill. This creates a review file at
`plan/reviews/<branch>-review.md` using a `claude-opus-4.7` code-review agent.

```
/peer-review
```

### 3. Address blocking issues

If `/peer-review` reports **BLOCKING > 0**, run:

```
/implement-review
```

This fixes every BLOCKING item, updates tests to keep coverage ≥ 95%, marks
each item resolved, and re-runs `/peer-review` to confirm zero BLOCKING issues
remain (up to 3 iterations).

Only proceed to step 4 when the review file shows **BLOCKING: 0**.

### 4. Documentation check (mandatory)

Update documentation if any of the following changed:
- Public API signatures or new modules
- Build steps, Makefile targets, or CI workflows
- User-visible CLI commands or flags
- New test files (update the test suite list in docs)
- File tree changes

Check `docs/developer-manual.md` (or the project's equivalent) and update
any sections that are now stale.

### 5. Untracked-file audit

```bash
git status --porcelain | grep '^??'
```

Classify every untracked file:
- **Project file** (source, plan, doc, script): stage and include in this commit.
- **Generated/artefact** (`*.o`, `build/`, coverage reports): confirm in `.gitignore`.
- **Scratch/temp**: delete or add to `.gitignore`.

### 6. Commit

Only when steps 1–5 are all clean:

```bash
git add <files>
git commit -m "<scope>: <imperative description>

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### 7. Pre-PR gate

Before opening any PR, run:

```bash
PORCELAIN=$(git status --porcelain)
MODIFIED=$(echo "$PORCELAIN" | grep -v '^??' | grep -v '^!!')
if [ -n "$MODIFIED" ]; then
  echo "🚫 BLOCKED — uncommitted changes in tracked files:"
  echo "$MODIFIED"
else
  echo "✅ Working tree is clean — safe to open PR."
fi
```

**If MODIFIED is non-empty: do not open the PR.** Stage and commit all
tracked changes, then repeat steps 1–7.

---

## After completing all phases

### Branching and PR

Follow the project's branching strategy from `plan/implementation-rules.md`
(or `plan/branching-strategy.md` if present). Typical patterns:

| Branch type | PR target |
|-------------|-----------|
| `feature/<topic>` | parent release branch or `development` |
| `release/vX.Y` | `main` after all sub-tasks complete |

### Status update

- Update `plan/status.md`: mark the task ✅, record test pass counts.
- If this completes a milestone, open the release → integration PR.
- Identify the next task and update the "Next Task" section.

### Change summary (always last)

Run `/show-changes` to display a formatted summary of every new and updated
public API, command, or module introduced in this implementation.

```
/show-changes
```

---

**Key files**:
- Rules: `plan/implementation-rules.md`
- Status: `plan/status.md`
- Reviews: `plan/reviews/`
