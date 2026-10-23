---
name: kaotim-resume
description: >-
  Use when running /kaotim-resume to continue an interrupted Kaotim run from
  .kaotim/state.json without replaying finished stages.
disable-model-invocation: true
---

Resume Kaotim. Read `.kaotim/state.json` via `state show`. If state is missing, the prior run already completed (plan archived under `.kaotim/plans/`) — start a new `/kaotim` instead of resume. Do not replay finished stages. Continue from `stage` using script gates and handoffs under `.kaotim/handoffs/`. Prefer fresh chat. If escalated/aborted, summarize and ask the user. If a prior run left `stage_status` as `awaiting_specialist` with usable handoffs or test files already written, set `stage_status` to `in_progress` and continue from that evidence — do not re-spawn a specialist that already finished. If stage is `tdd_red` and `next-stage` reports `approvals.tests timestamp required`, list locked tests for review, set `awaiting_user`, and wait for user approve before `state set` + `next-stage`.
