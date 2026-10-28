# Perf

## Method
1. **Measure before touching anything.** A perf claim without a number is a guess. Use the
   inspection tools in `/test` plus a real run (`make dev`, or the `run` skill): a trace, a profile, timings over N runs (report the
   median and spread), bundle size, query count.
2. **Find the dominant cost** in the measurement. Fix that, not what looks slow in the code.
3. **One change at a time**, re-measuring after each.
4. **Prove it held:** same measurement, same conditions, before and after, in the report. A change
   that doesn't move the number gets reverted, however elegant it is.
5. **Guard it** where cheap: a budget, a query-count assertion, a size limit, so it can't regress
   silently.

## In this project
- **Measure with:**
  - Timings: `pytest <file> --durations=10`, or a small script over N runs against a scratch SQLite DB; report median and spread.
  - Query plans: `EXPLAIN QUERY PLAN` on a **realistically sized** scratch DB (tens of thousands of `ts_metadata` rows, not a test fixture). CLAUDE.md makes this mandatory for any new correlated subquery or join, and the Review Board stays mandatory for it.
  - CPU: `python -m cProfile -o out.prof -m pytest <file>` or `cProfile` around the service call; read it with `pstats`.
  - Frontend: `cd frontend && npm run build` output (route/bundle sizes); AG Grid row counts via the datasource in `frontend/lib/gridDatasource.ts`.
- **Hot paths:** lineage build and purge (`ts_admin/services/lineage_service.py`), sync (`ts_admin/services/sync_service.py`, `ts_admin/api/sync.py`), metadata listing (`ts_admin/services/metadata_service.py`), dashboard aggregates (`ts_admin/services/dashboard_service.py`), TS API paging/throttle (`ts_admin/ts_client/client.py`, `retry.py`, `throttle.py`).
- **Known traps:**
  - `CachedMetadata` (`ts_admin/models/cache/ts_metadata.py`) has no composite `(cluster_id, org_id, ts_guid)` index; a join on it measured 50,589 ms vs 72.6 ms with one. The app never runs `ANALYZE` and sets no pragmas, so SQLite picks the least selective index.
  - `metadata.create_all` does not add an index to an existing table; a new index needs explicit `CREATE INDEX IF NOT EXISTS` in `init_db()` (`ts_admin/database.py`) or existing user DBs keep the old plan.
  - Sync tasks run on the event loop (not a threadpool): slow blocking DB work freezes `/health` and job polling. No WAL.
  - A `NOT IN` purge cannot be chunked with `_chunks`; use correlated `NOT EXISTS`. Guard `not_in(<empty>)`.
  - The unit suite cannot catch a quadratic plan; green tests prove nothing about performance.
- **Budgets:** none enforced. Add a query-count or plan assertion where cheap.
- **Environment:** scratch DB and mocked TS client only. Never measure against a real customer cluster.
