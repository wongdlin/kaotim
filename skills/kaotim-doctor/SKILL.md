---
name: kaotim-doctor
description: >-
  Use when running /kaotim-doctor to validate Kaotim wiring, config commands,
  and safety (including leftover stack.yaml hard-cut).
disable-model-invocation: true
---

Run `python .kaotim/bin/kaotim.py doctor` (add `--self` when checking the plugin). Fix reported failures. If leftover `.kaotim/stack.yaml` exists, move commands into `config.yaml` and delete it. Confirm test DB is not production when applicable.
