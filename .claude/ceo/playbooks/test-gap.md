# Test gap

## Method
1. **Test the invariant, not the current behaviour.** A test that mirrors whatever the code does
   today is not a guard. Write what *should* be true, from the docs, the contract, or the item.
2. **Prove each test has teeth**: break the code on purpose (in your worktree only), watch the test
   fail, then restore it. A test that can't fail is decoration.
3. **Behaviour over shape.** A test against a stub that doesn't execute the behaviour (ordering,
   filtering, auth, caching) proves a call was made, not that it's right. Prefer real fixtures.
4. **Fast and deterministic**: no network, no wall-clock sleeps, no order dependence.
5. Wire the new tests into the gate that CI runs, or they don't exist.

## In this project
- **Framework and layout:** pytest. `tests/unit/` (41 files: services, client, models; in-memory SQLite via StaticPool + `monkeypatch get_engine`; `respx`/`pytest-httpx` or a `_FakeClient` for TS calls, see `tests/unit/test_deletion_service.py`) and `tests/integration/` (FastAPI TestClient, one file per router). `tests/e2e/` is empty; Playwright specs live in `frontend/tests/e2e/`. Frontend unit tests are vitest, colocated as `frontend/lib/*.test.ts`.
- **Gate that runs them in CI:** `.github/workflows/ci.yml` runs `pytest tests/unit/ -v` and `pytest tests/integration/ -v`. Vitest and Playwright are NOT in CI; a frontend test only counts once someone runs it, so say so in the report. Wiring either into CI means editing `.github/workflows/*`, a protected path: hand it to the human.
- **Registries (protected files; appending a row needs `human-approved`, never relax an existing assertion):** `DRYRUN_ENDPOINTS` in `tests/integration/test_dryrun_safety.py`, `READ_ENDPOINTS` in `tests/integration/test_cluster_isolation.py`, `BACKGROUND_DISPATCH_SITES` in `tests/unit/test_background_dispatch_sites.py`, plus `tests/integration/test_audit_log_writes.py` and `tests/unit/test_cluster_service.py`.
- **Teeth:** `docs/dev/TESTING.md` lists five ways tests here were vacuous (never asserts the predicate, impossible fixture, disarming environment such as `TZ=UTC`, patching a stale name, no failing dependency). Check all five. Mutation harness rules for lineage and delete-confirmation are in that doc.
- **Fixtures:** drive the real writer (e.g. `_write_sync_log` upserts one row per `(cluster_id, org_id, entity_type)`); do not hand-insert shapes it cannot produce. Pin the timezone for timestamp tests; use aware-UTC datetimes (W7).
- `/test` flags untested services/routers, unregistered destructive endpoints, and tables missing `cluster_id`; run it before handing back.
