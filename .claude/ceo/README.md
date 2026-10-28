# .claude/ceo: org state

This repo's agent org was hand-built (2026-07, PR #13) and adopted into agent-org (`/org-init adopt`)
on 2026-10-27. The adoption kept every existing store and added structure around it:

| What | Where | Notes |
|---|---|---|
| CEO | `/improve-cycle` (`.claude/skills/improve-cycle/SKILL.md`) | unchanged name |
| Agents | `.claude/agents/` | researcher, architect, implementer (only editor), reviewer, qa-verifier (release-manager role), bug-hunter |
| Rules | `CLAUDE.md` ("The Org"), summarized in `RULES.md` | human-approved PRs only |
| Tasks | `BACKLOG.md` (`backlog.md` here is a pointer) | one tracker |
| Facts | `docs/org-memory/` (`memory/codebase.md`, `memory/retros.md` here are pointers) | |
| Trust | `org.json` (`autonomy_level`), `AUTONOMY.md`, `memory/scorecard.md` | only the human raises the level |
| Method | `playbooks/`, `PRINCIPLES.md` | one playbook per item kind |
| Evals | `evals/cases/` | run with `/org-eval` |
| Template findings | `upstream.md` | sent only via `/org-feedback`, with a human yes |
| Doctor | `bin/org_doctor.py` (or `/org-doctor`) | |

Kill switch: `touch .claude/ceo/PAUSE`. Run-active marker (binds the guard): `.claude/ceo/.cache/run-active`.
