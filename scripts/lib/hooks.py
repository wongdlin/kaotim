"""Hook handlers for Cursor hook events (stdin JSON -> stdout JSON)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .locks import verify_lock
from .ownership import check_ownership
from .paths import find_repo_root
from .state import read_state


DESTRUCTIVE = [
    r"\bmigrate:fresh\b",
    r"\bdb:wipe\b",
    r"\bDROP\s+DATABASE\b",
    r"\brm\s+-rf\s+/",
    r"\bgit\s+push\s+--force\b",
]


def handle_hook(name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    repo = find_repo_root()
    if name in {"preToolUse", "test-lock"}:
        return _test_lock(payload, repo)
    if name in {"beforeShellExecution", "shell-guard"}:
        return _shell_guard(payload)
    if name in {"ownership", "afterFileEdit"}:
        return _ownership_hint(payload, repo)
    if name in {"stop", "stage-guard"}:
        return _stage_guard(repo, payload)
    if name == "subagentStop":
        # Never auto-continue specialists — they must return to the orchestrator.
        return {}
    if name == "subagentStart":
        # optional deny nested spawns — cannot always detect; allow
        return {"permission": "allow"}
    return {"permission": "allow", "note": f"unhandled hook {name}"}


def _test_lock(payload: dict[str, Any], repo: Path) -> dict[str, Any]:
    tool = payload.get("tool_name") or payload.get("toolName") or ""
    path = (
        payload.get("file_path")
        or payload.get("path")
        or (payload.get("tool_input") or {}).get("path")
        or ""
    )
    if tool and tool not in {"Write", "Delete", "StrReplace", "EditNotebook"}:
        return {"permission": "allow"}
    if not path:
        return {"permission": "allow"}
    # normalize to repo-relative
    try:
        rel = str(Path(path).resolve().relative_to(repo.resolve())).replace("\\", "/")
    except Exception:
        rel = path.replace("\\", "/")
    result = verify_lock(repo, path=rel)
    if not result["ok"] and any(rel in e or "mismatch" in e for e in result.get("errors") or []):
        return {
            "permission": "deny",
            "user_message": f"Kaotim test-lock: refusing edit to locked test {rel}",
        }
    # also deny if path is in any lock set (pre-edit)
    state = read_state(repo)
    if state:
        for tid, task in (state.get("tasks") or {}).items():
            files = ((task.get("test_lock") or {}).get("files") or {})
            if rel in files:
                return {
                    "permission": "deny",
                    "user_message": f"Kaotim test-lock: {rel} is locked for {tid}",
                }
    return {"permission": "allow"}


def _shell_guard(payload: dict[str, Any]) -> dict[str, Any]:
    cmd = payload.get("command") or payload.get("cmd") or ""
    for pat in DESTRUCTIVE:
        if re.search(pat, cmd, re.I):
            return {
                "permission": "deny",
                "user_message": f"Kaotim guard: blocked destructive command matching {pat}",
            }
    return {"permission": "allow"}


def _ownership_hint(payload: dict[str, Any], repo: Path) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        return {"permission": "allow"}
    # non-blocking hint via allow; gates enforce
    return {"permission": "allow"}


def _stage_guard(repo: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Allow clean stops — do not auto-continue via followup_message.

    Previous behaviour returned followup_message whenever stage_status was in_progress
    (the default after every next-stage). Cursor's stop hook can fire for nested Task
    agent loops as well as the hub; specialists were then auto-continued instead of
    returning, and the parent sat on \"waiting for subagent\" for many minutes.

    Stage progress is enforced by orchestrator prompts + next-stage gates, not by
    stop follow-ups. payload is accepted for forward compatibility / tests.
    """
    _ = (repo, payload)
    return {}


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
