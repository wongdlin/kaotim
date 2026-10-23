---
name: kaotim-init
description: >-
  Use when running /kaotim-init to copy the CLI into .kaotim/bin and create
  config + project profile stubs for a target repo.
disable-model-invocation: true
---

Run `python scripts/kaotim.py init` from the plugin or copied CLI. Ensures `.kaotim/bin/kaotim.py`, `.kaotim/config.yaml` stub (`commands.*`), `project-profile.md`, and gitignore entries. Review with the user. Do not invent language stacks. Fill `commands.test` after plan approve, before TDD.
