# Eval results

| date | case | agent | agent model | judge model | score | pass | agent def sha | note |
|---|---|---|---|---|---|---|---|---|
| 2026-10-27 | ts-admin-1 | implementer | sonnet | opus | 8/10 | PASS | ad1f41101f | leaf root fixed; kept "exclude root when it has dependents" and wrote a test enforcing it, so the real fix's root-first test fails (1/3); gate output summarised, not verbatim |
| 2026-10-27 | ts-admin-2 | implementer | sonnet | opus | 9/10 | PASS | ad1f41101f | correct minimal fix, red-first test, guard test 6 passed with empty HOME; gate output paraphrased; 3 unrelated reds not checked against base |
| 2026-10-27 | ts-admin-3 | qa-verifier | haiku | sonnet | 10/10 | PASS | 19cc3aa4ad | NO-GO at gate 1 (format), exact 5 files verbatim, unbounded ruff pin noted, proved not a main regression |
| 2026-10-27 | ts-admin-4 | bug-hunter | opus | sonnet | 10/10 | PASS | aeeead1cc7 | INVALID AS DISCOVERY TEST: answer (S23) was in BACKLOG.md at base; agent cited it as filed and went deeper (stale SUCCESS sync_log after kill). Case revised to blind; re-run next time |
| 2026-10-27 | ts-admin-5 | bug-hunter | opus | sonnet | 8/10 | PASS | aeeead1cc7 | found preamble-outside-try stranding in all 4 executors; weak trigger example, dead-DB limit not stated. Also found F1 (cancelled dry-run still authorises execute), still present on main |
| 2026-10-27 | ts-admin-6 | reviewer | opus (correctness lens override) | sonnet | 9/10 | PASS | 031a8af211 | export-SUCCESS-as-deletion-proof found CONFIRMED with scenario + cluster scoping; missed archive-only job_type; except-Exception listed as CONFIRMED |
