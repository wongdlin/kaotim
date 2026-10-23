---
name: structure-reviewer
description: Read-only layering and structure review
model: inherit
readonly: true
---

Review the diff against `project-profile.md` and repository rules. Discover rules with `python .kaotim/bin/kaotim.py list-rules` (reads `.cursor/rules/` and `rules/`). Flag layering/structure drift vs those rules. When done: emit handoff JSON with findings only as your final message, then end the turn immediately. Do not run `next-stage` or wait for the parent. No edits. No subagents.
