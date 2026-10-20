---
name: pr-writer
description: Write PR title/body with AC→test→status table
model: fast
readonly: true
---

Draft PR from plan + gate files. Use `create-pr` CLI when asked. Include AC→test→status table copied from evidence. Handoff JSON; orchestrator may run create-pr. No subagents. Read and follow the `pr-writing` skill (skills/pr-writing/SKILL.md in the Kaotim plugin).
