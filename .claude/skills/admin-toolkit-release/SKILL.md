---
name: admin-toolkit-release
description: Merge the open PRs, cut the next version (patch for small changes, minor for big ones), and publish a GitHub release with the wheel attached, exactly like v0.4.7/v0.4.8. Use when the user says "release", "ship it", "merge and release", "deploy", "cut 0.x.y", or invokes /admin-toolkit-release. Args - none (auto-pick bump), `patch`, `minor`, or an explicit version like `0.5.0`.
---

# /admin-toolkit-release — merge, version, publish

Invoking this skill is the human's explicit approval to merge and release (the
CLAUDE.md autonomy line still applies to everything else). Never `--admin`,
never merge a red check, never add `human-approved`, never `git push --force`
to `main`. Stop and report on any red gate — don't relax it.

Releases live on GitHub: `gh release create` with the wheel attached and
auto-generated notes (see v0.4.7). PyPI is **not** part of this flow (it has
only 0.4.0); only run `uvx twine upload` if the user asks.

## 1. Merge open PRs

1. `git fetch origin --tags`; `gh pr list --state open --json number,title,headRefName,baseRefName,isDraft,mergeable,author`.
2. Skip drafts and anything the user didn't mean to ship (ask if unclear).
3. **Duplicates:** if a PR's diff is already on `main` (compare `git diff <merge-base> origin/<head>` with what landed), close it with a comment naming the PR that carried it — don't merge it twice.
4. Merge in dependency order (bases before stacked PRs). For each:
   - `gh pr checks <n> --watch` → all of Backend, Frontend, Protected-path guard must pass. A red **guard** means a protected path → needs the human `human-approved` label; stop and say so.
   - `gh pr merge <n> --squash --delete-branch` (repo convention: squash, `(#NN)` subject). Keep the branch if another open PR is stacked on it.
   - Stacked PR whose base was just squash-merged: in a worktree, `git rebase --onto origin/main <old-base-tip> <branch>`, rerun gates, `git push --force-with-lease`, `gh pr edit <n> --base main`, wait for CI, merge.
   - Conflict that is purely additive (both sides append tests) → keep both, `ruff format` the file, rerun gates. Anything semantic → stop and ask.
5. **Uncommitted work in the primary checkout is NOT an open PR.** Only ship it if the user confirms; then copy the diff onto a fresh branch from `origin/main` in a worktree, gate, commit, PR, CI, merge.

## 2. Pick the version

Latest tag: `git tag --sort=-v:refname | head -1`. Changes: `git log --oneline <last-tag>..origin/main` + the merged PR titles.

Pre-1.0 scheme (`0.MINOR.PATCH`):
- **minor** (`0.4.8 → 0.5.0`) — any merged PR that adds a user-visible feature (new page, endpoint, sync/job capability), changes a destructive operation's default behaviour, changes the DB schema, or breaks an API/CLI contract. Several medium features together also count.
- **patch** (`0.4.7 → 0.4.8`) — bug fixes, perf/internal refactors, docs, backlog/org-memory-only PRs, dependency bumps.
- An explicit arg (`patch` / `minor` / `0.5.0`) wins. Never bump the major (`1.0`) unless the user says so.

State the chosen version and a one-line reason per deciding PR, then continue (the user can interrupt). If no PRs merged since the last tag, stop — nothing to release.

## 3. Build in a clean worktree

Never release from the primary checkout (it may be on another branch / dirty).

```bash
R="$(git rev-parse --show-toplevel)"; V=X.Y.Z; W="$R/.claude/worktrees/release-$V"
git -C "$R" worktree add -b release-v$V "$W" origin/main && cd "$W"
```

Gates (use `$R/.venv/bin/{ruff,pytest}` if present, else `uv venv` in the scratchpad + `uv pip install -e ".[dev]"`):
```bash
ruff check ts_admin/ tests/ && ruff format --check ts_admin/ tests/
pytest tests/ -q
cd frontend && npm ci && npx tsc --noEmit && npm run build && cd ..
cp -r frontend/out/. ts_admin/static/   # fresh worktree: static/ holds only .gitkeep, no rm needed
sed -i '' "s/^version = .*/version = \"$V\"/" pyproject.toml
uv build --wheel
```

Verify before publishing:
- the wheel contains `ts_admin/static/index.html` (and ~185 static files);
- smoke test: `uv venv <scratch>/wheel-$V && uv pip install --python <scratch>/wheel-$V/bin/python dist/*.whl`, then `python -I -c "import importlib.metadata as m, ts_admin.main; print(m.version('ts-admin-toolkit'))"` prints `$V`, and `ts-admin-toolkit --help` runs.

## 4. Publish

```bash
git fetch origin && test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"   # main didn't move
git commit -m "chore: release v$V" pyproject.toml     # static/ is gitignored; only pyproject changes
git tag v$V && git push origin HEAD:main v$V
gh release create v$V dist/ts_admin_toolkit-$V-py3-none-any.whl \
  --title v$V --generate-notes --notes-start-tag <last-tag> --verify-tag
gh release view v$V --json isDraft,assets,body
```

If `main` moved, rebase the bump commit onto it and rerun the gates before tagging.

## 5. Report

Release URL, version + why that bump, merged/closed PRs, gate results, and what
was NOT verified (e.g. not run against a live cluster, UI not eyeballed).
Offer `git worktree remove` for the release worktree.
