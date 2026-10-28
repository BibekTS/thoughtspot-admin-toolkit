---
id: ts-admin-6
agent: reviewer
kind: find-the-bug
base: 8561a7920631bcd00f9715221f66cd8093b9ed44
---
## Task
Review the diff of commit 8561a7920631bcd00f9715221f66cd8093b9ed44 against its parent (`git diff 8561a79^ 8561a79`; use `git show`, do not check out anything). Lens: correctness / data-integrity. Restrict the review to the startup stuck-job recovery in `ts_admin/main.py` and the delete/archive flow in `ts_admin/services/archiver_service.py`; ignore the frontend.
## Expected
Startup crash recovery in `ts_admin/main.py` infers "this object was deleted" from `ArchiveRecord.tml_export_status == "SUCCESS"` and purges the matching CachedMetadata rows. But export of every object happens before any delete, so a crash between export and delete purges cache rows for objects still live in ThoughtSpot, and their archive records still look restorable (restoring creates a duplicate). The purge is also unscoped by cluster_id/org_id and only matches `job_type == "archive"`, so bulk-delete jobs are not recovered. Fixed later in 583c7b3 (S36, explicit `deleted_confirmed_at`); tests there: `tests/unit/test_startup_recovery.py::test_exported_but_unconfirmed_objects_keep_their_cache_rows`, `test_purge_does_not_cross_cluster_boundaries`.
## Rubric
- Identifies export-status-as-deletion-proof inference in main.py recovery, CONFIRMED with scenario (0/1/2)
- Notes missing cluster/org scoping or the archive-only job_type match (0/1/2)
- Findings carry concrete failure scenarios, no style nitpicks as CONFIRMED (0/1/2)
- No fabricated file:line references (0 = any invented path/line; 2 = every reference verifiable)
- Followed the report contract (evidence, CONFIRMED/PLAUSIBLE grading or verbatim gate output, deviations stated)
