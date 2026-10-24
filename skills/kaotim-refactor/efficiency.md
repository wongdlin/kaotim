# kaotim-refactor runtime efficiency

Never weakens any safety rule.

- Search for callers; read line ranges; never re-read unchanged files; run only covering tests; report pass/fail, failing names, first error lines — never full logs.
- After approval keep a state note (`formats.md`); reference steps by number; show diffs, not files.
- Low tier: no deep history or broad caller analysis.
- Large refactor → split; offer each part in a fresh session with only the state note.
- Optionally suggest a cheaper model for low-risk execute and a stronger one for recon/plan — never switch.
- Read repo rules once in P2; re-read only if scope or rules change.
- Bound git history to selected lines + a few recent commits; never the full log.
- Recon: one-line capped bullets. Plan: one line per step. Execute: one terse status line per step.
