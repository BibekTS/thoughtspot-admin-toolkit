# Bug fix

## Method
1. **Reproduce first** on your branch's base with `/test` plus a real run (`make dev`, or the `run` skill). No repro, no fix: report
   CAN'T REPRODUCE with what you tried.
2. **Write the failing test** that captures the bug, and watch it fail for the reported reason.
3. **Find the root cause**, not the symptom: why was the wrong value possible at all? Check every
   caller of the function you're about to change.
4. **Smallest fix** that makes the test pass. No drive-by refactors.
5. **Look for siblings**: the same mistake elsewhere (grep the pattern). Fix them in scope, or list
   them as `FACT:` lines for new backlog items.
6. Re-run the repro: it must now behave correctly, with evidence.

## In this project
- **Runner:** `pytest tests/unit/ -v` and `pytest tests/integration/ -v` (also `make test-unit`, `make test-integration`). Services get `tests/unit/test_<service>.py` (StaticPool in-memory engine + `monkeypatch get_engine`, e.g. `tests/unit/test_group_service.py`); routers get `tests/integration/test_<router>_api.py` (TestClient, e.g. `tests/integration/test_deleter_api.py`); ThoughtSpot client bugs go in `tests/unit/test_client_*.py` with `respx`/`_FakeClient`. Frontend helper bugs: `frontend/lib/*.test.ts` (vitest, not in CI, so run `cd frontend && npm test` yourself).
- **Fixtures:** drive the real writer and assert what it leaves behind; never hand-seed a state no writer produces (`docs/dev/TESTING.md`, "A green test is not evidence until you know it can go red"). Revert your fix and confirm the new test goes red.
- **Traps:**
  - sqlmodel>=0.0.45 rejects naive datetimes (W7): every bound or written datetime is aware UTC; a Python-side fallback compared to a DB read must be aware (`datetime.min.replace(tzinfo=timezone.utc)`). Grep `tzinfo=None|utcnow|datetime.now()` for siblings.
  - Tests that `monkeypatch` a name the code no longer reads (module-level dispatch dicts) pass vacuously; sync handlers are built per call via `sync_service.sync_handlers()`.
  - CI runs `TZ=UTC`, which hides timezone bugs; pin the timezone in timestamp tests.
  - A new column on a cache model needs a `_REBUILDABLE_SENTINELS` bump in `ts_admin/database.py` (`create_all` is additive only and alembic is not wired).
  - Never `except Exception`; name the class (ruff `BLE` enforces it).
  - A bug in a write path: check dry-run, verify-live, and audit-log still hold (`tests/integration/test_dryrun_safety.py`, `tests/integration/test_audit_log_writes.py`).
- **Gates:** `ruff check ts_admin/ tests/` ∧ `ruff format --check ts_admin/ tests/` ∧ both pytest dirs ∧ `cd frontend && npx tsc --noEmit` ∧ `cd frontend && npm run build` when frontend files changed.
