"""check-ownership against task owns globs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .git_util import changed_files
from .stack import file_matches_scope
from .state import read_state


def check_ownership(repo: Path, task: str) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        return {"ok": False, "errors": ["state.json missing"], "violations": []}
    t = (state.get("tasks") or {}).get(task)
    if not t:
        return {"ok": False, "errors": [f"unknown task {task}"], "violations": []}
    owns = t.get("owns") or []
    files = changed_files(cwd=repo)
    # also include unstaged
    violations = []
    for f in files:
        rel = f.replace("\\", "/")
        if rel.startswith(".kaotim/"):
            continue
        if not file_matches_scope(rel, owns):
            violations.append(rel)
    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "owns": owns,
        "changed": files,
        "errors": [],
    }


def check_regression_tests(repo: Path) -> dict[str, Any]:
    files = changed_files(cwd=repo)
    test_files = [f for f in files if "test" in f.lower()]
    return {
        "ok": len(test_files) > 0,
        "test_files": test_files,
        "errors": [] if test_files else ["no test files changed in fix round"],
    }
