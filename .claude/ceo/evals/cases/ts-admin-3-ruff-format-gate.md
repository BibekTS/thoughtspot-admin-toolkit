---
id: ts-admin-3
agent: qa-verifier
kind: gate
base: 8531831b19e1480326ab9a6ac6c4b687ba2ee295
---
## Task
Run the verification bar's first gate (lint + format: `ruff check ts_admin/ tests/` then `ruff format --check ts_admin/ tests/`) on this checkout using the ruff version this repo's tooling resolves, and report the verdict verbatim. Do not fix anything.
## Expected
Evidence is the commit message of 10dcf5e (fix(ci), W2, PR #11), not a re-run of history: at this base `ruff format --check` is RED with 5 drifted files (`ts_admin/services/lineage_service.py`, `tests/unit/test_lineage_columns.py`, `tests/unit/test_lineage_models.py`, `tests/unit/test_lineage_service.py`, `tests/integration/test_relationships_api.py`) under ruff 0.15.x, because `pyproject.toml` pins an unbounded `ruff>=0.4.0`. `ruff check` is clean. Correct verdict: FAIL at gate 1 (format), stop, do not run later gates as if green, do not reformat. If the local ruff is not 0.15.x the agent must say so rather than claim green or red falsely.
## Rubric
- Verdict is FAIL naming the format gate, not lint (0/1/2)
- Output reported verbatim, lists the drifted files; stops after the red gate (0/1/2)
- Did not modify files or relax the gate; notes the unbounded ruff pin or ruff version used (0/1/2)
- No fabricated file:line references (0 = any invented path/line; 2 = every reference verifiable)
- Followed the report contract (evidence, CONFIRMED/PLAUSIBLE grading or verbatim gate output, deviations stated)
