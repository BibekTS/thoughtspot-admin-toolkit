---
id: ts-admin-5
agent: bug-hunter
kind: find-the-bug
base: 4c827646ef08beba0a558230731ed6e6744dcd81
---
## Task
Lens: correctness / regression. Audit the background job targets in `ts_admin/services/bulk_sharing_service.py` (`execute_share`, `dryrun_share`) and `ts_admin/services/user_management_service.py` (`execute_transfer`, `execute_transfer_sharing`, `execute_delete`, `dryrun_transfer`, `dryrun_delete`) for job-lifecycle bugs, with `ts_admin/services/job_service.py` as reference. Report findings with failure scenarios and drafted acceptance criteria.
## Expected
Each target's error handling (outer try) begins after its preamble work (cache reads, `mark_running`, record writes), so a non-refusal exception there escapes the handler and leaves the Job QUEUED/RUNNING (stranded until `_recover_stuck_jobs` reaps it at next restart) instead of FAILED; in the transfer handler already-committed records stay PENDING. Real fix (fb69503, S49): move the try up to just after the function-local imports; tests: classes `TestPreambleExceptionsMarkFailed` in `tests/unit/test_bulk_sharing_service.py` and `tests/unit/test_user_management_service.py` (e.g. `test_execute_transfer_preamble`, `test_dryrun_share_fails_the_job_when_mark_running_raises`).
## Rubric
- Finds the preamble-outside-try stranding in both service files (0/1/2)
- Failure scenario traces a concrete exception (e.g. mark_running or cache read raising) to a job stuck non-terminal (0/1/2)
- Mentions or accounts for the dead-DB limit / does not over-claim (0/1/2)
- No fabricated file:line references (0 = any invented path/line; 2 = every reference verifiable)
- Followed the report contract (evidence, CONFIRMED/PLAUSIBLE grading or verbatim gate output, deviations stated)
