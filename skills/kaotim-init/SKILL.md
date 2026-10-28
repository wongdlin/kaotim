---
name: kaotim-init
description: >-
  Use when running /kaotim-init to copy the CLI into .kaotim/bin and create
  config + project profile stubs for a target repo.
disable-model-invocation: true
---

Run `python scripts/kaotim.py init` from the plugin or copied CLI. Ensures `.kaotim/bin/kaotim.py`, `.kaotim/config.yaml` stub (`commands.*`), `project-profile.md`, and a single `.kaotim/` gitignore entry (whole directory). Idempotent; leaves older selective `.kaotim/...` lines alone. Review with the user. Do not invent language stacks. Fill `commands.test` after plan approve, before TDD. Teammates who clone the target repo must run `/kaotim-init` themselves — config, profile, and bin stay local under the ignored `.kaotim/`.
