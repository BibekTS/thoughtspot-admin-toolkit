# Upgrade

## Method
1. **Read the upstream changelog and migration guide** for every version you cross, and list the
   breaking changes that touch this repo (grep for each API).
2. **One dependency (or one coupled group) per PR.** Never batch unrelated upgrades.
3. **Upgrade, then fix what broke**, applying the migration guide literally. No opportunistic
   rewrites.
4. **Full bar plus a real run** with `/test` plus a real run (`make dev`, or the `run` skill). Tooling and runtime upgrades break things
   no unit test covers.
5. Lockfile committed. Note the rollback (the previous version) in the PR body.

## In this project
- **Python:** `pyproject.toml` (hatch build; deps are floors, no lockfile) with dev extras via `pip install -e ".[dev]"`. CI uses Python 3.11 (`.github/workflows/ci.yml`); `ruff` `target-version = "py310"`. With no lockfile, a floating dep can break `main` silently, so bisect versions explicitly as W7 did.
- **Known breaking-change history:**
  - W2: unbounded `ruff` pin caused `ruff format --check` drift; ruff is now bounded `>=0.15.0,<0.16.0`. A ruff bump may reformat files: run `ruff format` as its own commit and update the bound deliberately.
  - W7: `sqlmodel>=0.0.45` rejects naive datetimes (78 failures on 0.0.47). Floor raised in PR #61; all datetimes aware UTC. Test sqlmodel/SQLAlchemy/pydantic/fastapi upgrades against the whole suite, not a slice.
  - `keyring` backends vary by OS; the probe at `ts_admin/config.py` must keep working.
- **Frontend:** npm, `frontend/package-lock.json` (commit it). Pinned majors: `next` 14.2.5 (static export, `output: "export"` in `frontend/next.config.js`), `ag-grid-community`/`ag-grid-react` ^32, `@xyflow/react` ^12, `react` ^18, `vitest` ^2, `@playwright/test` ^1.47. AG Grid and Next majors change APIs: read their migration guides and grep usages in `frontend/components/` and `frontend/pages/`. CI uses Node 20.
- **Beyond the gates:** `ruff check` ∧ `ruff format --check` ∧ `pytest tests/unit/` ∧ `pytest tests/integration/` ∧ `cd frontend && npx tsc --noEmit` ∧ `cd frontend && npm run build`; also run `cd frontend && npm test` (vitest) locally since CI skips it, and watch for TS REST API v2 drift in `ts_admin/ts_client/client.py`.
- **Protected:** `.github/workflows/*` (toolchain versions in CI) need a human; propose, don't edit.
