---
name: kaotim-doctor
description: >-
  Use when running /kaotim-doctor to validate Kaotim wiring, stack commands,
  and safety (including test DB not production).
disable-model-invocation: true
---

Run `python .kaotim/bin/kaotim.py doctor` (add `--self` when checking the plugin). Fix reported failures. Confirm test DB is not production.
