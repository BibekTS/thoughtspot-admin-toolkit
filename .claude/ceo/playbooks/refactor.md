# Refactor

## Method
1. **No behaviour change, provably.** Before touching code, make sure tests pin the current
   behaviour of everything you'll move. If they don't, write those tests first, as their own
   commit.
2. **Small, mechanical steps**, each one green. Rename, move, extract, inline. Never rewrite.
3. **No new features, no bug fixes** in the same diff. Found a bug? Write it down as a `FACT:`
   line and leave it.
4. **The diff should shrink or hold steady.** A refactor that adds net lines needs a reason.
5. Gates green after every step, and the same public behaviour (outputs, API, UI) at the end.

## In this project
- **Structure to keep:** `ts_client` (thin HTTP) <- `services` (logic) <- `api` (routers); services never import from `api`, and `ts_client` never imports services or models. Frontend: pages in `frontend/pages/`, components in `frontend/components/<Feature>/`, shared helpers in `frontend/lib/`.
- **Duplicated contracts that must change together:**
  - Pydantic/response shapes in `ts_admin/api/*.py` and `frontend/lib/types.ts` + `frontend/lib/api.ts`.
  - SQLModel columns in `ts_admin/models/` and `_REBUILDABLE_SENTINELS` in `ts_admin/database.py`.
  - Endpoint paths and the registries `DRYRUN_ENDPOINTS` / `READ_ENDPOINTS` / `BACKGROUND_DISPATCH_SITES` (protected files: renaming a route means a human-approved PR).
  - `parse_iso_date` is single-sourced in `ts_admin/services/metadata_service.py`; archiver imports it.
- **Pin behaviour first:** lineage and delete-confirmation code has mutation-tested suites (`docs/dev/TESTING.md`); do not weaken them. Before moving code, check the tests would go red if you broke it.
- **Do not touch** the security layer or guard tests in a refactor (see CLAUDE.md protected paths). If the refactor needs it, stop and hand to the human.
- **Gates after every step:** `ruff check ts_admin/ tests/` ∧ `ruff format --check ts_admin/ tests/` ∧ `pytest tests/unit/ -v` ∧ `pytest tests/integration/ -v`; add `cd frontend && npx tsc --noEmit` ∧ `npm run build` for frontend moves.
