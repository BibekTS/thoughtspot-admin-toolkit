# Security fix

## Method
1. **Write the exploit as a test first**: the failing input (injection string, cross-user id,
   hostile file) that demonstrates the hole. It must fail before the fix.
2. **Fix at the boundary**, using the project's canonical helper (validator, sanitizer, auth
   check). Never invent a new one, and never fix only the one call site you were shown: grep for
   every path that reaches the same sink.
3. **Fail closed** unless `CLAUDE.md`/`RULES.md` documents a deliberate fail-open.
4. **No secrets in the test, the commit, or the report.** Use obvious fakes.
5. The security engineer re-reviews the diff before it ships, whatever the gates say.

## In this project
- **Canonical helpers (reuse, never reinvent):**
  - SSRF / URL validation: `validate_cluster_url` in `ts_admin/services/cluster_service.py` (HTTPS only; rejects loopback, private IPv4/IPv6, IPv4-mapped IPv6). Tested in `tests/unit/test_cluster_service.py`.
  - CORS: allow-list in `ts_admin/main.py` is `http://localhost:{port}` only; never `*`.
  - Credentials: OS keychain via `keyring` in `ts_admin/config.py` (`get`/`set`/`delete` around lines 348-377); env-var fallback only. No secrets in logs, responses, tests, or reports.
  - Bind address: 127.0.0.1 only, in `ts_admin/cli.py`.
  - Cluster scoping: every query filters by `cluster_id`; `tests/integration/test_cluster_isolation.py`.
  - Write safety: dry-run, verify-live, audit-log (`tests/integration/test_dryrun_safety.py`, `tests/integration/test_audit_log_writes.py`). Error text goes through `ts_admin/services/error_formatter.py` / `ts_admin/api/error_handlers.py`.
- **Sinks to grep:** every `httpx` call and URL construction in `ts_admin/ts_client/`; every place a cluster URL is saved or used (`ts_admin/services/cluster_service.py`, `ts_admin/services/connection_service.py`); raw SQL / `text(` in `ts_admin/services/`; `FileResponse`/path joins in `ts_admin/main.py` (static serving) and `ts_admin/api/csv_export.py`; logging calls that might print tokens (`ts_admin/logging_config.py`).
- **Protected:** `ts_admin/main.py`, `ts_admin/services/cluster_service.py`, `ts_admin/cli.py`, `ts_admin/config.py` and the guard tests are protected paths: a fix there ends at an open PR needing the `human-approved` label. Agents never add it.
- **Documented fail-open / exemptions:** none for security checks. The only lint exemption is BLE001 for `ts_admin/main.py` and `ts_admin/config.py` in `pyproject.toml` (backlog M16); do not extend it, and never add `except Exception` elsewhere.
- Run `/security-review` on the diff before handing back.
