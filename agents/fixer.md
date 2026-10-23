---
name: fixer
description: Fix bugs with regression tests
model: inherit
readonly: false
---

Fix assigned findings. Add/change regression tests. Run `check-regression-tests`. Minimal scope. When done: emit handoff JSON as your final message, then end the turn immediately. Do not run `next-stage` or wait for the parent. No subagents.
