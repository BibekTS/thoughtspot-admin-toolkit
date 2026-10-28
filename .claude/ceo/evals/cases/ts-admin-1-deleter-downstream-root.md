---
id: ts-admin-1
agent: implementer
kind: fix-the-bug
base: f780b6c59e1d0e39eff2d41892c41fc86b5bb9ef
---
## Task
Symptom: in the Bulk Deleter, "downstream" resolve mode on a root GUID that has no dependents (e.g. a liveboard or answer) returns an empty list, so the admin has nothing to select and no way to delete the root, even though the UI says the root will be deleted. Fix the backend in `ts_admin/services/deleter_service.py` (`resolve_downstream`; docstrings in `ts_admin/api/deleter.py`) and add tests in the same change. Dry-run behavior must not change.
## Expected
`resolve_downstream` excluded the root and early-returned an empty result when there were no dependents. Fix: fetch the root plus its dependents, list the root first, still drop system-owned rows. Tests from the real fix (commit f3f2c2c) in `tests/unit/test_deleter_downstream.py`: `test_leaf_root_resolves_to_itself`, `test_root_is_listed_first_with_its_dependents`, `test_system_owned_root_is_still_excluded` must pass after the fix.
## Rubric
- Leaf root (no dependents) now resolves to itself; root appears first (0/1/2)
- System-owned rows still excluded; no change to dry-run/execute paths (0/1/2)
- Added tests in the same change, matching tests-follow-code, and ran ruff + unit tests (0/1/2)
- No fabricated file:line references (0 = any invented path/line; 2 = every reference verifiable)
- Followed the report contract (evidence, CONFIRMED/PLAUSIBLE grading or verbatim gate output, deviations stated)
