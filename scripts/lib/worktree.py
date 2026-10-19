"""Git worktree helpers for parallel tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .git_util import run_git
from .paths import ensure_kaotim_dirs
from .stack import get_package
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
    # create branch from HEAD
    code, out, err = run_git(["worktree", "add", "-b", branch, str(wt)], cwd=repo)
    if code != 0:
        # branch may exist
        code, out, err = run_git(["worktree", "add", str(wt), branch], cwd=repo)
        if code != 0:
            return {"ok": False, "error": err or out, "path": str(wt), "branch": branch}

    # run setup per stack
    setup_logs = []
    try:
        pkg = get_package(repo)
        for st in pkg.get("stacks") or []:
            setup = (st.get("worktree") or {}).get("setup")
            if not setup:
                continue
            import subprocess

            root = wt / (st.get("root") or ".")
            proc = subprocess.run(
                setup,
                cwd=str(root),
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
            setup_logs.append(
                {"stack": st.get("name"), "exit": proc.returncode, "cmd": setup}
            )
            if proc.returncode != 0:
                return {
                    "ok": False,
                    "error": f"worktree.setup failed for {st.get('name')}",
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
    # dependency order: C0 first, then others by depends_on if present
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
        code, out, err = run_git(["merge", "--no-ff", branch, "-m", f"kaotim: merge {tid}"], cwd=repo)
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
