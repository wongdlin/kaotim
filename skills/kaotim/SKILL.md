---
name: kaotim
description: >-
  Use when running /kaotim to run or resume the full Kaotim pipeline for a
  feature request (plan → TDD → review → cleanup → PR).
disable-model-invocation: true
---

Run Kaotim for: $ARGUMENTS

1. Prefer a fresh chat for long runs. CLI: `python .kaotim/bin/kaotim.py` (or `python scripts/kaotim.py` in the plugin repo).
2. If `.kaotim/state.json` exists: continue (`/kaotim-resume`). If missing: fresh run — `state init` (no `--force` after a prior complete).
3. Ensure `.kaotim/stack.yaml` + `project-profile.md` (stack/init if missing). Do not reuse `.kaotim/plans/`; write a new `.kaotim/plan.md`.
4. Plan with `kaotim-plan` (skills/kaotim-plan/SKILL.md); write `.kaotim/plan.md`; `check-plan`; get approvals; `state set` approvals; `next-stage`.
5. Orchestrate only via state, script JSON, and handoffs — never read app source yourself.
6. Spawn specialists per stage (test-writer → feature-dev → supervisor → structure → bug → cleaner → pr-writer). Skills: test-writer/feature-dev → `tdd`; bug-reviewer → `edge-cases`; pr-writer → `pr-writing`; planning → `kaotim-plan` (+ `edge-cases`, `arch-comparison`). Name skill + path (`skills/<name>/SKILL.md`) in each Task prompt. Before spawn: `state set` `stage_status=awaiting_specialist`; after handoff: `in_progress`. If a subagent shows no progress for several minutes, cancel it and continue from written files/handoffs.
7. Every transition: `next-stage`. Caps → escalate. After `tdd_red` (if `approvals.require_tests`): list locked tests + AC/EC; set `awaiting_user`; on approve set `approvals.tests` + `in_progress` then `next-stage`. At `final_gate`: `metrics-summary`, `awaiting_user` for `approvals.pr`, draft PR (`pr-writer` / `create-pr` best-effort — human can open PR if CLI fails), then `next-stage` archives plan → `.kaotim/plans/` and clears state/handoffs/gates.
