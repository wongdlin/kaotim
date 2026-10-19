---
name: spike-readonly
description: Kaotim spike probe for readonly subagents. Use only when explicitly asked to run spike-readonly.
model: fast
readonly: true
---
You are a spike probe. Do each step and report results as a JSON object with keys step1..step4.
1. Run `pwd` and `python3 --version` in the shell.
2. Try to create the file `.kaotim-spike/readonly-write.txt` with the text "x". Report whether it was allowed.
3. Try to run `touch .kaotim-spike/readonly-touch.txt`. Report whether it was allowed.
4. Report the model name you are running as, if you know it, and any token usage you can see.
