# Feature

## Method
1. **Restate the acceptance criteria** from the item. Each one maps to a test or a verifiable
   check before you write code. A criterion you can't test goes back to the CEO.
2. **Find the existing pattern**: the closest existing feature is the template. Reuse its helpers,
   structure, and naming. New infrastructure needs a reason in the report.
3. **Smallest version that meets the criteria.** No speculative options, flags, or abstractions.
4. **Build and test together**, one criterion at a time.
5. **Verify it for real** with `/test` plus a real run (`make dev`, or the `run` skill): run the feature the way a user would, at
   every required viewport or environment. Attach the evidence.
6. Docs, if the feature is user-visible and the project documents features.

## In this project
- **Where features live (by layer, one file per feature):** `ts_admin/ts_client/` (thin HTTP only, no business logic) -> `ts_admin/services/<feature>_service.py` (logic, orchestrates client + DB) -> `ts_admin/api/<feature>.py` (FastAPI router, registered in `ts_admin/main.py`) -> `ts_admin/models/` (SQLModel; cache tables under `ts_admin/models/cache/`) -> `frontend/pages/<feature>.tsx` with `frontend/components/<Feature>/`.
- **Reference features:** read-only listing = `ts_admin/api/groups.py` + `ts_admin/services/group_service.py`; destructive with dry-run = `ts_admin/api/deleter.py` + `ts_admin/services/deletion_service.py`, or the archiver (`ts_admin/api/archiver.py`); bulk write = `ts_admin/api/sharing.py`.
- **Non-negotiables for any write:** dry-run first, verify live against TS before executing, audit-log row after, background job via `job_service`. Every new table has `cluster_id: str = Field(foreign_key="clusters.id")`. Read endpoints take `cluster_id` and never return another cluster's rows.
- **Tests follow code (same change):**
  - service -> `tests/unit/test_<name>.py`; router -> `tests/integration/test_<name>_api.py`.
  - destructive endpoint -> append to `DRYRUN_ENDPOINTS` in `tests/integration/test_dryrun_safety.py`; list/read endpoint -> `READ_ENDPOINTS` in `tests/integration/test_cluster_isolation.py`; a 202 endpoint using `background_tasks.add_task` -> `BACKGROUND_DISPATCH_SITES` in `tests/unit/test_background_dispatch_sites.py`. These registries are protected paths: the PR needs the `human-approved` label; flag it, never relax an existing assertion.
  - page with a destructive action -> Playwright spec in `frontend/tests/e2e/` modeled on `archiver-dry-run.spec.ts` (not in CI, run it locally; one agent at a time since it binds ports).
- **UI:** follow `docs/dev/DESIGN.md` (no gradients/glows, tokens only, check both themes). AG Grid for tables (`frontend/lib/gridDatasource.ts`), shadcn components.
- **Definition of done:** gates green, plus the feature exercised via `/improve-cycle`-style verification (drive the endpoint, or the page in both themes), plus `/test` coverage check clean.
- **Docs:** update `docs/user/` if user-visible and `docs/dev/features/` when the feature has a spec there. Mirrors: the static export in `ts_admin/static/` is rebuilt only at release by `make build`; do not hand-edit it.
