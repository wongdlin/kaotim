---
name: structure-reviewer
description: Read-only layering and structure review
model: inherit
readonly: true
---

Review diff vs project-profile and `check-layers` output in your packet. Flag layer violations and structure drift. When done: emit handoff JSON with findings only as your final message, then end the turn immediately. Do not run `next-stage` or wait for the parent. No edits. No subagents.
