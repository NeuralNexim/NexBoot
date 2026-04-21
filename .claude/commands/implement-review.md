# implement-review

Read the current branch's review file (produced by `/peer-review`), implement
all BLOCKING fixes, update tests to maintain ≥ 95% coverage, then mark each
item resolved.

## When to invoke

After `/peer-review` reports one or more BLOCKING issues and before `git commit`.

## Procedure

### 1 — Locate the review file

```bash
git branch --show-current
```

Review file: `plan/reviews/<branch-name-with-/-as-->-review.md`

Read the file. Build a list of all `REVIEW-NNN` blocks where
`Severity: BLOCKING` and `Resolved? ❌`.

If the file does not exist or has zero BLOCKING items, report "nothing to
implement" and exit.

### 2 — Load project rules

Read `plan/implementation-rules.md` in full. Every fix must comply with all
rules — especially style, testing framework, coverage requirements, and any
language-specific constraints.

### 3 — Track work in SQL

Insert one todo per BLOCKING review item before starting:

```sql
INSERT INTO todos (id, title, description, status) VALUES
  ('review-NNN', 'Fix REVIEW-NNN: <short title>',
   '<file>:<line> — <issue summary> — Fix: <fix summary>', 'pending');
```

### 4 — Implement each fix in order (lowest REVIEW-NNN first)

For each BLOCKING item:

1. **Read the affected file(s)** — understand context before changing anything.
2. **Apply the fix** using the `edit` tool — surgical changes only.
   - Follow the project's style rules exactly.
   - If the fix adds a new public function, update the relevant header/interface file.
   - If the fix changes user-visible behaviour, update help text / docs.
3. **Add or update tests**:
   - Add a test case that directly exercises the fixed code path.
   - If the issue was a missing error path, add a test that triggers it.
   - If the issue was a wrong assertion, fix the assertion and verify it passes.
4. **Run the project test suite** — all tests must pass; note new coverage numbers.
5. **Mark the SQL todo `in_progress` → `done`**.

### 5 — Coverage check

After all fixes, run the full test suite and check coverage on every file
that was modified. Coverage must be **≥ 95%**.

If below 95% on any changed file:
- Identify uncovered lines from the coverage report.
- Add targeted tests for those lines.
- Re-run the test suite.

### 6 — Update the review file

For each fixed BLOCKING item, update the Resolution Log:

```markdown
| REVIEW-NNN | BLOCKING | ✅ | <short fix description> |
```

Update the header when all blocking items are resolved:

```markdown
**Status**: RESOLVED
**Blocking issues**: 0
```

### 7 — Re-run peer review (mandatory)

Run `/peer-review` again to confirm the updated diff has zero BLOCKING issues.

If new BLOCKING issues appear (regressions), repeat from step 4.
Allow at most **3 fix iterations**. If BLOCKING issues remain after 3 attempts,
halt and report the conflicting REVIEW IDs to the user for manual resolution.

### 8 — Report to user

```
Fixes applied:   N
Tests added:     M  (test suite: XXXX/XXXX passed)
Coverage:        ≥ 95% on all changed files  ✅
Review status:   RESOLVED — 0 blocking issues remaining

Pre-commit gate (§8) cleared.  Ready to commit.
```
