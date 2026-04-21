# NexBoot — Branching Strategy

## Branch Flow

```
feature/<topic>  →  release/vX.Y  →  main
```

- Feature branches are cut from `main`.
- Sub-features (or phased work) merge into a versioned release branch
  (e.g. `release/v1.0`) before that release branch merges into `main`.
- **Never** merge a feature branch directly into `main`.
- `main` always holds tagged releases only.

## PR Target Table

| Branch type | PR target |
|-------------|-----------|
| `feature/<topic>` | `release/vX.Y` (the target version release branch) |
| `release/vX.Y` | `main` — only when all features for that version are merged |

## Commit Message Convention

```
<scope>: <imperative short description>
```

Examples:
- `manifest: add cross-field kernel_secs formula validation`
- `image: guard write_artifact against out-of-bounds writes`
- `ci: add Python 3.12 to test matrix`
- `docs: update developer manual §3 with --abi-check flag`

## Rules

1. Branch names: `feature/<topic>` (kebab-case topic, no spaces).
2. Release branches: `release/vX.Y` (semver minor version).
3. One PR per logical feature or fix.
4. PRs require all CI checks green before merge.
5. Squash merge into release branch; merge commit into `main`.
6. Tag `main` after each release branch merge: `git tag vX.Y.Z`.
