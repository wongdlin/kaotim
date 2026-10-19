---
description: Run or resume the full Kaotim pipeline for a feature request
---

Run Kaotim for: $ARGUMENTS

1. Prefer a fresh chat for long runs. CLI: `python .kaotim/bin/kaotim.py` (or `python scripts/kaotim.py` in the plugin repo).
2. If `.kaotim/state.json` exists and stage ≠ done: continue from that stage (`/kaotim-resume` flow).
3. Else ensure `.kaotim/stack.yaml` + `project-profile.md` (run stack/init if missing).
4. Plan with `kaotim-planning` skill; write `.kaotim/plan.md`; `check-plan`; get user approvals; `state set` approvals; `next-stage`.
5. Orchestrate only via state, script JSON, and handoffs — never read app source yourself.
6. Spawn specialists per stage (test-writer → feature-dev → supervisor → structure → bug → cleaner → pr-writer).
7. Every transition: `next-stage`. Caps → escalate with summary. Before PR: `metrics-summary` then user `approvals.pr`.
