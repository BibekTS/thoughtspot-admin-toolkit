# Upstream outbox

Template findings: problems this org hit that would happen in **any** org built from the same
agent-org templates (a template defect, a doctor false positive, an ambiguous CEO instruction, a
guard rule that blocked the wrong thing). The CEO appends one entry per finding at the micro-retro.
Project-specific findings do not go here: they get fixed in this project's own org files.

This file is local. Nothing in it leaves the machine unless feedback is enabled in `org.json`
(`"feedback": {"enabled": true}`) and you run `/org-feedback` and approve the drafts.

Entry format:

```
## <YYYY-MM-DD> <short title>
- status: new | sent <url> | fixed-upstream (<why>) | wontfix (<why>)
- agent-org version: <org.json agent_org_version>
- template: <agent-org path, e.g. skills/org-init/templates/ceo/SKILL.md>
- what happened: <the mechanism>
- evidence: <command output, test, eval score>
- proposed change: <what the template should say or do instead>
- local workaround: <what this project did meanwhile, if anything>
```

## Entries

## 2026-10-27 org-doctor can't see unprefixed agents in an adopted org
- status: new
- agent-org version: 0.1.0
- template: skills/org-doctor/scripts/org_doctor.py (check_ceo)
- what happened: `check_ceo` only recognizes agents named `<slug>-*` as "mentioned" by the CEO skill. An adopted org whose agents are unprefixed (`implementer`, `reviewer`, ...) gets a "never mentioned by the CEO skill" warning for every agent, though the skill dispatches all of them.
- evidence: `/org-doctor` on this repo after `/org-init adopt`.
- proposed change: match the declared agent names from org.json (backticked or in a dispatch line) rather than a slug-prefix regex.
- local workaround: accept the warnings; renaming agents would break the existing workflow.

## 2026-10-27 gate_files can't protect a gate that lives in a shared file
- status: new
- agent-org version: 0.1.0
- template: skills/org-init/templates/hooks/org_guard.py (check_edit)
- what happened: Python gate config (`[tool.ruff]`, `[tool.pytest.ini_options]`) lives in `pyproject.toml`, which also holds dependencies. Listing it in `gate_files` would block every dependency upgrade; leaving it out leaves the ruff/pytest config unguarded.
- evidence: `pyproject.toml` sections at lines 64-90.
- proposed change: let a gate_files entry name a TOML table (`pyproject.toml#tool.ruff`) and diff only that table in the edit guard.
- local workaround: `pyproject.toml` not listed; the review board's regression lens covers gate-config edits there.
