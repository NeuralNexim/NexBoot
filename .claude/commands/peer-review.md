# peer-review

Launch a `claude-opus-4.7` code-review agent against the current branch diff
and write a structured review file.  The output file is the contract between
this skill and the `/implement-review` skill.

## When to invoke

After implementing a phase and before committing — mandatory per
`plan/implementation-rules.md`.

## Procedure

### 1 — Determine scope

```bash
git branch --show-current

BASE=$(git merge-base HEAD \
       "$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)" \
       2>/dev/null \
       || git rev-parse HEAD~1 2>/dev/null \
       || git rev-parse --root)

git --no-pager diff "$BASE"..HEAD          # committed changes since fork point
git --no-pager diff                        # any unstaged working-tree changes
git --no-pager diff "$BASE"..HEAD --stat   # file list with line deltas
```

Collect:
- **Branch name** (used in the review file path)
- **Full diff** (`git diff $BASE..HEAD` + `git diff` for unstaged)
- **List of changed files** with line-count deltas

Also read `plan/implementation-rules.md` to extract project-specific
constraints (language, testing framework, coverage requirements, style rules)
to include in the review agent prompt.

### 2 — Review file path

```
plan/reviews/<branch-name>-review.md
```

Replace `/` with `-` in the branch name.
Example: `plan/reviews/feature-auth-jwt-review.md`

Create `plan/reviews/` if it does not exist.

### 3 — Launch the review agent

Use the `task` tool with:
- `agent_type`: `"code-review"`
- `model`: `"claude-opus-4.7"`
- `mode`: `"background"`

**Prompt template** (fill in `<BRANCH>`, `<PROJECT_RULES>`, `<FILE_LIST>`, `<DIFF>`):

```
You are reviewing code changes on branch <BRANCH>.

Project-specific constraints (from plan/implementation-rules.md):
<PROJECT_RULES>

Standard review criteria:
- Correctness: logic errors, off-by-one, integer overflow, wrong return values
- Error handling: unhandled exceptions/errors, silent failures, missing null checks
- Security: input validation, path traversal, injection, credential exposure
- Resource management: leaks, double-free, unclosed handles
- Test quality: wrong assertions, missing edge cases, missing error-path coverage
- API contracts: breaking changes, undocumented preconditions, incorrect docs

Changed files:
<FILE_LIST>

Full diff:
<DIFF>

For each issue found, output EXACTLY this format (one block per issue):

### REVIEW-NNN
**Severity**: BLOCKING | NON-BLOCKING
**File**: <path>
**Line**: <line-number or range>
**Category**: bug | logic-error | security | missing-error-path | wrong-assertion | undefined-behaviour | test-gap | style
**Issue**: <one-paragraph description of the problem>
**Fix**: <concrete fix — code snippet if helpful>

At the end output a summary line:
BLOCKING: N  NON-BLOCKING: M  TOTAL: T
```

Wait for the agent to complete before continuing.

### 4 — Write the review file

Create `plan/reviews/<branch>-review.md`:

```markdown
# Code Review: <branch-name>
**Date**: <ISO timestamp>
**Reviewer**: claude-opus-4.7
**Status**: OPEN
**Blocking issues**: N
**Non-blocking issues**: M

---

<paste agent output verbatim>

---

## Resolution Log

| ID | Severity | Resolved? | Commit |
|----|----------|-----------|--------|
| REVIEW-001 | BLOCKING | ❌ | — |
...
```

### 5 — Report to user

```
Branch:       <branch>
Review:       plan/reviews/<branch>-review.md
Blocking:     N  ← must be 0 before any commit
Non-blocking: M  ← may be deferred
```

If `N == 0`: pre-commit gate is clear — proceed to commit.
If `N > 0`: run `/implement-review` next.
