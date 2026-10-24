---
name: kaotim-refactor
description: >-
  Use when running /kaotim-refactor to refactor attached or referenced code
  like a careful senior engineer: scoped, tested, incremental, reviewable,
  behavior-preserving. Explicit invocation only.
disable-model-invocation: true
---

Refactor goal: $ARGUMENTS

**Never guess.** Anything not verifiable by reading code or running a command: ask. If findable in the repo (code, config, docs, history), find it and cite `file:line`. Batch questions: one message per gate.

Not for bug fixes, features, formatting/linting, or big-bang rewrites (push back; propose an incremental path). Behavior changes are never in scope: if one seems needed, stop and add it to the follow-up list.

## Start
- Selection = code attached or referenced in the message (starting scope, not final). None → ask what to refactor. No goal → propose one, ask to confirm.
- Run `git status`. Uncommitted changes → stop and ask.

## Phases (never guess at any gate)
1. **Scope** — goal in one sentence; in-scope; explicit out-of-scope; ambiguities. Gate: user confirms.
2. **Recon** (read-only) — cheap first pass: selection, direct callers, covering tests (always allowed; ask before widening). Check tests exist (run if cheap). Locate repo rules by search (Cursor rules, AGENTS.md, contributing guides — never assume a filename); read fully once; write a short rules checklist and reuse it. Bounded git history for selected lines. Flag odd/load-bearing logic and ask — never assume dead. Mark public vs internal surface. Propose tier with reason. Output: recon report (`formats.md`).
3. **Safety net** — find the test command (`.kaotim/config.yaml` `commands.test` if present, else config/scripts/docs/CI, else ask). Run covering tests for a green baseline. Thin coverage → propose characterization tests (`techniques.md`), user confirms. Infeasible → say so, propose fallback, get explicit waiver. Gate: green, approved tests, or waiver.
4. **Plan** — small ordered behavior-preserving steps (`formats.md`). >~10 steps or ~15 files → recommend split, ask. Gate: user approves. No source edits before.
5. **Execute** — per step: exactly one change; run covering tests; keep the step's diff so it can be undone. Green → one-line status + commit suggestion (`commits.md`). Red → STOP; never edit tests to pass; report, ask revert or investigate. Discoveries → noticed-not-touched list, never fixed.
6. **Wrap-up** — medium/high: run full suite once (low: follow repo rules). Output wrap-up (`formats.md`). Offer a PR description via the `pr-writing` skill.

## Risk tiers
Propose after recon; user confirms or overrides; never silent. "strict" forces full gates.
- **Low** — internal-only, few files, tests exist → one combined confirmation (scope + safety net + plan), green confirmed in P3, then execute. Never load `high-risk.md`.
- **Medium** — multiple files/callers or thin coverage → full gates, short plan.
- **High** — public interface, shared module, no tests, data formats/schemas → full gates, read `high-risk.md`.

## Hard rules (every tier)
- No source edits before plan approval (exception: confirmed P3 tests; tests for newly extracted units may be added freely).
- Never continue past a failing test. A failing test means behavior may have changed.
- Never edit existing tests without confirmation (test-change summary, `formats.md`).
- No public API/schema/serialized-format change without a user-approved compat/migration plan.
- No new abstraction without two concrete use cases; else ask.
- Never delete or simplify logic you can't explain; flag and ask.
- Never expand scope; follow-up list or ask to widen.
- Every step complies with repo rules. Conflict, missing, ambiguous, contradictory → ask. Skill vs repo rule → stop, ask which wins.
- Stack-agnostic: discover language, idioms, and commands; never hardcode.

## Stop and ask
Tests fail or can't run; scope grows; public surface would change; existing test needs editing; step conflicts with a rule; rules unclear; can't verify; plan too large; unexplainable logic.

## Efficiency
Read `efficiency.md` at start (never weakens safety).
