#!/usr/bin/env python3
"""Kaotim M0 spike hook: log every payload, and exercise block decisions.

Usage (from hooks.json): python3 spike_hook.py <event>
Writes one JSON line per call to <project>/.kaotim-spike/hooks.jsonl.
Blocks (preToolUse) writes/deletes of paths listed in <project>/.kaotim-spike/locked.txt
and (beforeShellExecution) destructive artisan commands. Stdlib only, Python 3.9+.
"""
import datetime
import json
import os
import re
import sys

PERMISSION_EVENTS = {"preToolUse", "beforeShellExecution", "subagentStart", "beforeReadFile"}
DESTRUCTIVE = re.compile(r"\b(migrate:(fresh|refresh|reset)|db:wipe)\b")
PATH_KEYS = ("path", "file_path", "target_file", "filePath", "targetFile")


def project_dir(payload):
    roots = payload.get("workspace_roots") or []
    return os.environ.get("CURSOR_PROJECT_DIR") or (roots[0] if roots else os.getcwd())


def truncate(value, limit=300):
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "...<truncated>"
    if isinstance(value, dict):
        return {k: truncate(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [truncate(v, limit) for v in value[:20]]
    return value


def locked_paths(project):
    try:
        with open(os.path.join(project, ".kaotim-spike", "locked.txt"), encoding="utf-8") as fh:
            lines = [line.strip() for line in fh if line.strip()]
    except OSError:
        return set()
    return {os.path.normpath(os.path.join(project, line)) for line in lines}


def tool_paths(tool_input, cwd):
    if not isinstance(tool_input, dict):
        return []
    found = [tool_input[k] for k in PATH_KEYS if isinstance(tool_input.get(k), str)]
    return [os.path.normpath(os.path.join(cwd, p)) for p in found]


def decide(event, payload, project):
    """Return the JSON response for this event (pure; unit-tested)."""
    if event == "preToolUse":
        cwd = payload.get("cwd") or project
        hits = sorted(set(tool_paths(payload.get("tool_input"), cwd)) & locked_paths(project))
        if hits:
            msg = "kaotim-spike: %s is locked (test-lock probe)." % ", ".join(hits)
            return {"permission": "deny", "user_message": msg, "agent_message": msg}
        return {"permission": "allow"}
    if event == "beforeShellExecution":
        if DESTRUCTIVE.search(payload.get("command") or ""):
            msg = "kaotim-spike: destructive database command blocked (guard probe)."
            return {"permission": "deny", "user_message": msg, "agent_message": msg}
        return {"permission": "allow"}
    if event in PERMISSION_EVENTS:
        return {"permission": "allow"}
    if event == "sessionStart":
        root = os.environ.get("CURSOR_PLUGIN_ROOT", "")
        return {
            "env": {"KAOTIM_SPIKE_ROOT": root},
            "additional_context": "kaotim-spike plugin root: %s" % (root or "UNKNOWN"),
        }
    return {}


def log(event, payload, project, response):
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": event,
        "cwd": os.getcwd(),
        "python": sys.version.split()[0],
        "env": {k: os.environ.get(k) for k in (
            "CURSOR_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT", "CURSOR_PROJECT_DIR",
            "CURSOR_VERSION", "KAOTIM_SPIKE_ROOT", "CURSOR_AGENT")},
        "payload_keys": sorted(payload.keys()),
        "payload": truncate(payload),
        "response": response,
    }
    out = os.path.join(project, ".kaotim-spike")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "hooks.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def main(argv):
    event = argv[1] if len(argv) > 1 else "unknown"
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    project = project_dir(payload)
    response = decide(event, payload, project)
    try:
        log(event, payload, project, response)
    except OSError:
        pass
    sys.stdout.write(json.dumps(response))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
