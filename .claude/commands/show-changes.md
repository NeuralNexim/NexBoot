# show-changes

Scan the current branch diff for new and updated public-facing symbols
(CLI commands, public functions, modules, API endpoints) and display a
formatted summary.

## When to invoke

Automatically at the end of `/implement-next`, and on demand whenever you
want a human-readable changelog of user-visible changes.

## Procedure

### 1 — Compute BASE and collect changed files

```bash
git branch --show-current

BASE=$(git merge-base HEAD \
       "$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)" \
       2>/dev/null \
       || git rev-parse HEAD~1 2>/dev/null)

git --no-pager diff "$BASE"..HEAD --name-only
git ls-files --others --exclude-standard
```

### 2 — Detect project language and patterns

Auto-detect from changed files or `plan/implementation-rules.md`:

| Language | Public symbol patterns |
|----------|----------------------|
| Python   | `def <name>(`, `class <name>:` in non-test files |
| C/C++    | Non-`static` function definitions in `.h` headers |
| Go       | Exported identifiers (capitalised) in non-test files |
| JS/TS    | `export function`, `export class`, `export const` |
| Other    | Any pattern specified in `plan/implementation-rules.md` |

Also detect CLI commands from patterns like:
- Python: `argparse.add_parser(`, `@click.command`, `@app.command`
- C: `cmd_*` function definitions in shell/command files
- Go: `cobra.Command{Use:`, `cli.Command{Name:`

### 3 — Classify each changed symbol

For each public symbol in the diff:
- **NEW** — not present in `$BASE`
- **UPDATED** — present in `$BASE` but the definition or signature changed
- **REMOVED** — present in `$BASE` but absent now (flag these — may be breaking)

Skip: test files, internal helpers, private symbols.

### 4 — Format and print the summary

```
╔══════════════════════════════════════════════════════════════╗
║  Changelog for <branch-name>                                 ║
╠══════════════════════════════════════════════════════════════╣
║  CLI commands  — NEW: N  UPDATED: M  REMOVED: R              ║
║  Public funcs  — NEW: N  UPDATED: M  REMOVED: R              ║
║  Modules       — NEW: N  UPDATED: M                          ║
╚══════════════════════════════════════════════════════════════╝

━━ CLI COMMANDS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── NEW: <command-name> ────────────────────────────────────────
  Usage    : <usage synopsis>
  Summary  : <one-line description>
  Options  : <key flags>
  File     : <path>

── UPDATED: <command-name> ────────────────────────────────────
  Change   : <brief description of what changed>
  File     : <path>

━━ PUBLIC FUNCTIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── NEW: <function-name> ───────────────────────────────────────
  Signature: <signature>
  Module   : <module/file>

━━ MODULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── NEW MODULE: <name> ─────────────────────────────────────────
  Purpose  : <one-line from module docstring/header>
  File     : <path>
  Exports  : <list of public functions/classes>
```

Omit any section that has zero entries.

### 5 — Flag breaking changes

If any **REMOVED** public symbols are detected:

```
⚠  WARNING: <N> public symbol(s) removed — potential breaking change:
   - <symbol> (<file>)
```

### 6 — Output destination

Print to the terminal only. This skill is read-only and has no side effects.
