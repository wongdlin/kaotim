"""Git worktree helpers for parallel tasks."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .config import get_commands
from .git_util import run_git
from .paths import ensure_kaotim_dirs
from .state import read_state, write_state


def worktree_add(repo: Path, task: str) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        raise ValueError("state.json missing")
    plan_id = (state.get("plan_id") or "plan").lower()
    branch = f"kaotim/{plan_id}/{task.lower()}"
    wt = ensure_kaotim_dirs(repo) / "worktrees" / task.lower()
    if wt.exists():
        return {"ok": True, "path": str(wt), "branch": branch, "exists": True}
    code, out, err = run_git(["worktree", "add", "-b", branch, str(wt)], cwd=repo)
    if code != 0:
        code, out, err = run_git(["worktree", "add", str(wt), branch], cwd=repo)
        if code != 0:
            return {"ok": False, "error": err or out, "path": str(wt), "branch": branch}

    setup_logs: list[dict[str, Any]] = []
    setup = (get_commands(repo).get("worktree_setup") or "").strip()
    if setup:
        try:
            proc = subprocess.run(
                setup,
                cwd=str(wt),
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
            setup_logs.append({"exit": proc.returncode, "cmd": setup})
            if proc.returncode != 0:
                return {
                    "ok": False,
                    "error": "commands.worktree_setup failed",
                    "path": str(wt),
                    "branch": branch,
                    "setup": setup_logs,
                }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "path": str(wt), "branch": branch}

    tasks = state.setdefault("tasks", {})
    t = tasks.setdefault(task, {})
    t["branch"] = branch
    t["worktree"] = str(wt.relative_to(repo)).replace("\\", "/")
    tasks[task] = t
    state["tasks"] = tasks
    write_state(state, repo)
    return {"ok": True, "path": str(wt), "branch": branch, "setup": setup_logs}


def worktree_remove(repo: Path, task: str) -> dict[str, Any]:
    state = read_state(repo) or {}
    t = (state.get("tasks") or {}).get(task) or {}
    wt = t.get("worktree")
    path = repo / wt if wt else ensure_kaotim_dirs(repo) / "worktrees" / task.lower()
    code, out, err = run_git(["worktree", "remove", "--force", str(path)], cwd=repo)
    return {"ok": code == 0, "stdout": out, "stderr": err, "path": str(path)}


def merge_tasks(repo: Path) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        return {"ok": False, "error": "state.json missing"}
    tasks = state.get("tasks") or {}
    order = []
    if "C0" in tasks:
        order.append("C0")
    for tid in sorted(tasks.keys()):
        if tid not in order:
            order.append(tid)

    merged = []
    for tid in order:
        t = tasks[tid]
        branch = t.get("branch")
        if not branch:
            continue
        code, out, err = run_git(
            ["merge", "--no-ff", branch, "-m", f"kaotim: merge {tid}"], cwd=repo
        )
        if code != 0:
            state["stage"] = "escalated"
            state["escalation"] = {
                "reason": f"merge conflict on {tid}",
                "stderr": err,
                "stdout": out,
            }
            write_state(state, repo)
            return {
                "ok": False,
                "error": f"merge conflict on {tid}",
                "merged": merged,
                "escalated": True,
            }
        merged.append(tid)
    return {"ok": True, "merged": merged}
