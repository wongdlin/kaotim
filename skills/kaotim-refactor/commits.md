# kaotim-refactor commits

## Default: suggest and draft
- After each green step: say it's a good commit point; give a ready message describing the structural change and stating no behavior change, e.g. `refactor: extract parseHeader from loadConfig (no behavior change)`.
- The user commits. Keep refactor commits separate from behavior commits.
- Revert: keep each step's diff so the user can undo that step.

## Opt-in: only if the user explicitly says e.g. "commit as you go"
- Never commit to main/default branch. Confirm the branch, or create a dedicated branch only with approval.
- Never push. Never amend or rewrite history.
- Commit only when green. One logical step per commit.
- Revert uses the per-step commit.
