# ThoughtSpot Admin Toolkit org rules

The authoritative rules are in `CLAUDE.md` (sections "Critical rules", "Verification bar",
"Protected paths", "How the org works"). This file is the org's index of them, not a second copy;
when the two disagree, `CLAUDE.md` wins. Changes are rule changes: the CEO proposes, the human merges.

CEO: `/improve-cycle`. Agents: `.claude/agents/`. State: `.claude/ceo/`. Kill switch:
`touch .claude/ceo/PAUSE`.

**Verification bar for ANY change:** `ruff check ts_admin/ tests/` · `ruff format --check ts_admin/ tests/` ·
`pytest tests/unit/ -v` · `pytest tests/integration/ -v` · `cd frontend && npx tsc --noEmit` ·
`cd frontend && npm run build` · the row's feature check. Never weaken a gate to pass.

**Protected paths:** see `CLAUDE.md` and `org.json` → `protected_paths`. A PR touching one needs the
`human-approved` label, which only a human adds (CI `guard` job).

**User data:** `~/.ts-admin/` (config + SQLite cache). Agents never read or write it; tests use fixtures.

**Memory:** `CLAUDE.md` = rules · `BACKLOG.md` = tasks · `docs/org-memory/` = facts.
