---
name: kaotim-spike-args
description: Spike probe for command argument substitution and plugin-root discovery.
---
Reply with: CMD-OK ARGS=[$ARGUMENTS] FIRST=[$1] SECOND=[$2]

Then run these shell commands and report their output verbatim:
1. `printenv CURSOR_PLUGIN_ROOT || echo NO_PLUGIN_ROOT_ENV`
2. `python3 -c "import sys; print(sys.version)"`
3. `ls ~/.cursor/plugins 2>/dev/null; find ~/.cursor/plugins -path '*kaotim-spike/scripts/spike_probe.py' 2>/dev/null | head -3`
4. If step 3 found spike_probe.py, run `python3 <that path> command`.
