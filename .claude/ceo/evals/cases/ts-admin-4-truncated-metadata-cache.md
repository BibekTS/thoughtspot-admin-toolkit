---
id: ts-admin-4
agent: bug-hunter
kind: find-the-bug
base: 7d43581a3002a8b104179f374895b4bac78056d2
---
## Task
Lens: data-integrity. Audit the metadata sync path in `ts_admin/services/sync_service.py` (`_sync_metadata`) and its readers (`ts_admin/services/metadata_service.py`, `ts_admin/services/deleter_service.py`, `ts_admin/services/user_management_service.py`, `ts_admin/services/bulk_sharing_service.py`). Consider what the cache and the sync_log look like if a metadata sync is interrupted partway. Report findings with failure scenarios and drafted acceptance criteria.
## Expected
`_sync_metadata` commits a DELETE-all for the org then re-pages `search_metadata` in spec order (LIVEBOARD, ANSWER, then logical-table subtypes), committing per page. An interruption leaves the cache non-empty but truncated (liveboards/answers present, models/tables missing) while the previous SUCCESS sync_log row survives, so deleter downstream resolution, transfer/share previews and the metadata stats read a partial cache as authoritative. Real fix (6662afd): write-ahead IN_PROGRESS marker before the delete, `sync_status` completeness helper, readers fail closed (`StaleCacheError` -> 409). Tests from the fix: `tests/unit/test_sync_service.py::test_interrupted_metadata_sync_is_not_reported_as_synced`, `tests/unit/test_stale_cache_guard.py`.
## Rubric
- Identifies truncated-but-authoritative cache after interrupted sync in sync_service (0/1/2)
- Names at least one downstream consumer that acts on the partial set (deleter/transfer/share) (0/1/2)
- Failure scenario concrete (ordering of delete, commits, surviving SUCCESS row) and graded CONFIRMED/PLAUSIBLE honestly (0/1/2)
- No fabricated file:line references (0 = any invented path/line; 2 = every reference verifiable)
- Followed the report contract (evidence, CONFIRMED/PLAUSIBLE grading or verbatim gate output, deviations stated)
