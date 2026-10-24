# kaotim-refactor output formats

Short, skimmable, fixed. One line per bullet. Reference code as `file:line`.

## Recon report
- **What it does** — 2–4 bullets
- **Dependents** — callers/importers (`file:line`)
- **Surface** — public (exported APIs, schemas, serialized formats) vs internal
- **Repo rules** — relevant rule → source file
- **Suspicious / load-bearing logic** — each with a question
- **Proposed tier** — low | medium | high, and why
- **Open questions**

## Plan
```
1. <technique> — files: <a, b> — verify: <tests> — risk: low|medium|high — rule: <ok | rule ref>
2. ...
```
Then: public interfaces / shared modules / data formats touched; out-of-scope reminders; open questions.

## Test-change summary
- Test name + location
- Why it must change
- Exact before / after
- Why it does not weaken verification
- "Confirm this test change? (yes/no)" — never proceed without explicit yes.

## Execute status (per step)
`Step N: <technique> — tests <pass|FAIL: names + first error lines> — commit point: "<message>"`

## State note (after plan approval)
Goal · scope · tier · approved steps (numbered) · current step · rules checklist · noticed-not-touched.

## Wrap-up
- Structural changes
- Behavior unchanged + how verified
- Tests added
- Noticed, not touched (follow-ups, incl. any needed behavior changes)
- Commits made or suggested
- Offer: draft PR description with the `pr-writing` skill
