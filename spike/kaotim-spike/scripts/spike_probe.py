#!/usr/bin/env python3
"""Kaotim M0 spike: prove a script inside the plugin can be located and run.

Prints where it lives and the interpreter, and appends a line to
<cwd>/.kaotim-spike/probe.jsonl.
"""
import json
import os
import sys

entry = {
    "caller": sys.argv[1] if len(sys.argv) > 1 else "unknown",
    "script": os.path.abspath(__file__),
    "cwd": os.getcwd(),
    "python": sys.version.split()[0],
    "CURSOR_PLUGIN_ROOT": os.environ.get("CURSOR_PLUGIN_ROOT"),
}
os.makedirs(".kaotim-spike", exist_ok=True)
with open(os.path.join(".kaotim-spike", "probe.jsonl"), "a", encoding="utf-8") as fh:
    fh.write(json.dumps(entry) + "\n")
print(json.dumps(entry))
