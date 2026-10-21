---
description: Run or resume the full Kaotim pipeline for a feature request
---

Run Kaotim for: $ARGUMENTS

1. Prefer a fresh chat for long runs. CLI: `python .kaotim/bin/kaotim.py` (or `python scripts/kaotim.py` in the plugin repo).
2. If `.kaotim/state.json` exists and stage ≠ done: continue from that stage (`/kaotim-resume` flow).
3. Else ensure `.kaotim/stack.yaml` + `project-profile.md` (run stack/init if missing).
4. Plan with `kaotim-planning` skill; write `.kaotim/plan.md`; `check-plan`; get user approvals; `state set` approvals; `next-stage`.
5. Orchestrate only via state, script JSON, and handoffs — never read app source yourself.
6. Spawn specialists per stage (test-writer → feature-dev → supervisor → structure → bug → cleaner → pr-writer). Skills per specialist: test-writer and feature-dev → `tdd`; bug-reviewer → `edge-cases`; pr-writer → `pr-writing`; planning → `kaotim-planning` (+ `edge-cases`, `arch-comparison`). Include the skill name and path (skills/<name>/SKILL.md in the Kaotim plugin) in each subagent task prompt.
7. Every transition: `next-stage`. Caps → escalate with summary. After `tdd_red` (when `approvals.require_tests` is true, default): list locked test files + AC/EC coverage summary; stop for user review of assertions/gaps; on approve `state set` `approvals.tests` timestamp then `next-stage` before spawning `feature-dev`. Before PR: `metrics-summary` then user `approvals.pr`.
