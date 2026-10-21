---
description: Planning only — produce an approvable .kaotim/plan.md
---

Plan only for: $ARGUMENTS

Follow `kaotim-planning`. Clarify goal/AC, inputs/outputs, then SPEC (S→P→E→C). Prefer Grep/Glob/Read yourself for reuse; spawn `explorer` only for broad unknown areas (it uses `model: fast`). Do not block planning on a hung subagent — if the parent card shows no progress, cancel and continue with what you have. Ask batched lettered-table questions until no material doubts remain — never assume, no round limit. Write `.kaotim/plan.md` from template. Run `python .kaotim/bin/kaotim.py check-plan`. Do not implement code. Stop after user can approve.
