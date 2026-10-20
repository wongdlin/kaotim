---
name: kaotim-planning
description: Use when running /kaotim or /kaotim-plan to produce an approvable .kaotim/plan.md through a structured planning conversation
disable-model-invocation: true
---

Produce `.kaotim/plan.md` from `templates/plan.md`.

Rules: ask, never assume. Batch questions (respect `caps.question_rounds`). Every AC/EC maps to one task. EC needs Decision; use the `edge-cases` skill for each EC. Record architecture Chosen if comparison required, using the `arch-comparison` skill. Disjoint owns. No blocking questions when approving. Use explorer for reuse. Fast lane only with user confirm and limits.
