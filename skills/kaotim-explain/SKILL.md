---
name: kaotim-explain
description: >-
  Explain a selected or attached code chunk in precise, simple terms. Prefer
  accuracy over polished grammar. Use when the user selects code and asks what
  it does, wants a plain walkthrough, or runs /kaotim-explain.
---

Explain the selected / attached code. Extra focus if given: $ARGUMENTS

Explain the **selected or attached code only**. Aim: precise understanding, not pretty prose. Prefer precision over grammar. Do not change the code.

## Rules

1. Say what the code does. Walk execution order when that makes the behavior clearer.
2. Use simple words. Drop polish if needed — short fragments OK. Accuracy first; grammar second.
3. Name concrete identifiers (functions, variables, types, constants) when they matter to the behavior.
4. Call out side effects: writes, network, DB, throws, mutates caller state, schedules work.
5. Do not rewrite, refactor, fix, or improve the code unless the user asks.
6. Do not invent behavior outside the selection. If missing context blocks a precise claim, state the unknown in one short line — or Read nearby lines only when needed for that claim.
7. No tutorials, style opinions, or “good/bad pattern” commentary unless asked.

## Output shape

1. **In short** — one or two sentences: what this chunk does overall.
2. **Step by step** — bullets; each bullet one action or decision the code makes.
3. **Gotchas** — only real ones (edge paths, silent failures, surprising returns). Omit if none.
