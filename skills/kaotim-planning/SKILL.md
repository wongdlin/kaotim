---
name: kaotim-planning
description: Use when running /kaotim or /kaotim-plan to produce an approvable .kaotim/plan.md through a structured planning conversation
disable-model-invocation: true
---

Produce `.kaotim/plan.md` from `templates/plan.md` using the SPEC frame. Ask, never assume — keep asking until every material doubt is resolved (no round limit, no silent defaults).

## Must clarify before drafting
1. **Goal & acceptance** — what success is; concrete AC so tasks know when they are done.
2. **Inputs / outputs** — payloads, events, UI actions in; responses, persisted state, side effects out.
3. **SPEC**
   - **S Scope & Constraints** — locked decisions, architectural boundaries, forbidden patterns.
   - **P Precision Shapes** — exact schemas, migrations, DTOs, enums, file paths, contracts.
   - **E Execution Units** — small disjoint tasks (single-file or single-feature owns).
   - **C Checkpoints & Tests** — exact commands or assertions to verify each unit.

## Question format (selectable)
Prefer the **AskQuestion** tool so options are clickable. Batch related fixed-choice questions in one AskQuestion call when the tool allows. Each question: short prompt; options a/b/c… as selectable choices; always include one freeform escape labeled **Other (specify)** (or "Something else (I will type it)"). Do not also dump a duplicate markdown option table when AskQuestion is used.

If AskQuestion is unavailable or the user skips it, fall back to this markdown table and wait for a letter:

```
**Q1. <question>**

| | Option |
|---|---|
| a | <answer A> |
| b | <answer B> |
| c | Other (specify) |
```

Wait for the selection (or letter + Other text) before deciding. Record choices in EC Decision / Decision log.

## Rules
Every AC/EC/CP maps to one task; each task has Done when → AC. EC needs Decision (`edge-cases`). Arch comparison → Chosen under S (`arch-comparison`). Disjoint owns. No blocking questions when approving. Prefer Grep/Glob/Read; spawn `explorer` only for broad unknown areas; cancel hung subagents. Fast lane only with user confirm and limits.
