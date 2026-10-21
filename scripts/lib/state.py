"""Atomic state.json management."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import PLUGIN_VERSION
from .config import load_config
from .io_util import atomic_write_json
from .paths import ensure_kaotim_dirs, kaotim_dir

STAGES = [
    "recon",
    "plan",
    "plan_approved",
    "contracts",
    "tdd_red",
    "tdd_green",
    "integrate",
    "supervisor",
    "structure_review",
    "bug_review",
    "cleanup",
    "final_gate",
    "pr",
    "done",
    "escalated",
    "aborted",
]

ALLOWED_SET_FIELDS = {
    "stage",
    "stage_status",
    "fast_lane",
    "approvals",
    "tasks",
    "loops",
    "gates",
    "escalation",
    "base_sha",
    "plan_id",
    "package",
}


def state_path(repo: Path | None = None) -> Path:
    return kaotim_dir(repo) / "state.json"


def default_state(plan_id: str = "PLAN-001", package: str = "default") -> dict[str, Any]:
    cfg = load_config()
    caps = cfg.get("caps") or {}
    return {
        "schema": 1,
        "plan_id": plan_id,
        "package": package,
        "plugin_version": PLUGIN_VERSION,
        "base_sha": None,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stage": "recon",
        "stage_status": "in_progress",
        "fast_lane": False,
        "approvals": {"plan": None, "architecture": None, "tests": None, "pr": None},
        "tasks": {},
        "loops": {
            "supervisor_rejects": 0,
            "structure_refactors": 0,
            "bug_fix_rounds": 0,
        },
        "caps": {
            "green_attempts": caps.get("green_attempts", 5),
            "supervisor_rejects": caps.get("supervisor_rejects", 3),
            "structure_refactors": caps.get("structure_refactors", 2),
            "bug_fix_rounds": caps.get("bug_fix_rounds", 2),
        },
        "gates": {"last_run": None},
        "escalation": None,
    }


def read_state(repo: Path | None = None) -> dict[str, Any] | None:
    path = state_path(repo)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(state: dict[str, Any], repo: Path | None = None) -> Path:
    ensure_kaotim_dirs(repo)
    path = state_path(repo)
    atomic_write_json(path, state)
    return path


def init_state(
    plan_id: str = "PLAN-001",
    package: str = "default",
    repo: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    ensure_kaotim_dirs(repo)
    path = state_path(repo)
    if path.exists() and not force:
        raise ValueError("state.json already exists (use --force to replace)")
    state = default_state(plan_id=plan_id, package=package)
    write_state(state, repo)
    return state


def set_state_fields(updates: dict[str, Any], repo: Path | None = None) -> dict[str, Any]:
    state = read_state(repo)
    if state is None:
        raise ValueError("state.json missing; run state init first")
    illegal = [k for k in updates if k not in ALLOWED_SET_FIELDS]
    if illegal:
        raise ValueError(f"illegal state fields: {', '.join(illegal)}")
    if "stage" in updates and updates["stage"] not in STAGES:
        raise ValueError(f"unknown stage: {updates['stage']}")
    new_state = deepcopy(state)
    for key, value in updates.items():
        if key in {"approvals", "tasks", "loops", "gates", "caps"} and isinstance(value, dict):
            base = new_state.get(key) or {}
            if not isinstance(base, dict):
                base = {}
            merged = deepcopy(base)
            merged.update(value)
            new_state[key] = merged
        else:
            new_state[key] = value
    write_state(new_state, repo)
    return new_state
