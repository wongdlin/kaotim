"""Test file hash locks."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .state import read_state, write_state


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def lock_tests(task_id: str, files: list[str], repo: Path) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        raise ValueError("state.json missing")
    tasks = state.setdefault("tasks", {})
    task = tasks.setdefault(task_id, {"status": "red"})
    locked = {}
    for rel in files:
        path = repo / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        locked[rel.replace("\\", "/")] = file_hash(path)
    task["test_lock"] = {"files": locked}
    tasks[task_id] = task
    state["tasks"] = tasks
    write_state(state, repo)
    return {"task": task_id, "files": locked}


def verify_lock(repo: Path, path: str | None = None, task_id: str | None = None) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        return {"ok": False, "errors": ["state.json missing"]}
    errors: list[str] = []
    tasks = state.get("tasks") or {}
    items = []
    if task_id:
        items = [(task_id, tasks.get(task_id) or {})]
    else:
        items = list(tasks.items())
    for tid, task in items:
        lock = (task.get("test_lock") or {}).get("files") or {}
        for rel, expected in lock.items():
            if path and rel != path.replace("\\", "/"):
                continue
            fp = repo / rel
            if not fp.exists():
                errors.append(f"{tid}: missing locked file {rel}")
                continue
            actual = file_hash(fp)
            if actual != expected:
                errors.append(f"{tid}: lock mismatch {rel}")
    return {"ok": not errors, "errors": errors}


def unlock_tests(task_id: str, repo: Path) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        raise ValueError("state.json missing")
    task = (state.get("tasks") or {}).get(task_id)
    if not task:
        raise ValueError(f"unknown task {task_id}")
    task["test_lock"] = {"files": {}}
    state["tasks"][task_id] = task
    write_state(state, repo)
    return {"task": task_id, "unlocked": True}
