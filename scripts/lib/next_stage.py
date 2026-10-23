"""Evaluate and advance pipeline stages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_config
from .paths import kaotim_dir
from .plan import check_plan
from .stack import load_stack
from .state import complete_run, read_state, write_state
from .validate_stack import validate_stack

# Canonical stage names use underscores in state.json
TRANSITIONS = {
    "recon": "plan",
    "plan": "plan_approved",
    "plan_approved": "contracts",  # or tdd_red if no C0
    "contracts": "tdd_red",
    "tdd_red": "tdd_green",
    "tdd_green": "integrate",
    "integrate": "supervisor",
    "supervisor": "structure_review",
    "structure_review": "bug_review",
    "bug_review": "cleanup",
    "cleanup": "final_gate",
    "final_gate": "done",  # complete before optional PR; human can open PR if create-pr fails
    "pr": "done",  # legacy mid-run: still finish without requiring pr_created
}


def _profile_ok(repo: Path) -> bool:
    return (kaotim_dir(repo) / "project-profile.md").exists()


def evaluate(repo: Path | None = None) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        return {"ok": False, "can_advance": False, "reason": "state.json missing", "next": None}
    stage = state.get("stage")
    reasons: list[str] = []
    nxt = TRANSITIONS.get(stage)

    if stage == "recon":
        if not load_stack(repo):
            reasons.append("stack.yaml missing")
        else:
            vs = validate_stack(repo)
            if not vs["ok"]:
                reasons.extend(vs["errors"])
        if not _profile_ok(repo or Path.cwd()):
            reasons.append("project-profile.md missing")
        nxt = "plan"
    elif stage == "plan":
        cp = check_plan(repo)
        if not cp["ok"]:
            reasons.extend(cp["errors"])
        approvals = state.get("approvals") or {}
        if not approvals.get("plan"):
            reasons.append("approvals.plan timestamp required")
        nxt = "plan_approved"
    elif stage == "plan_approved":
        plan_path = kaotim_dir(repo) / "plan.md"
        has_c0 = False
        if plan_path.exists():
            has_c0 = "### C0:" in plan_path.read_text(encoding="utf-8")
        nxt = "contracts" if has_c0 else "tdd_red"
    elif stage == "contracts":
        tasks = state.get("tasks") or {}
        c0 = tasks.get("C0") or {}
        if c0.get("status") != "done":
            reasons.append("C0 not done")
        nxt = "tdd_red"
    elif stage == "tdd_red":
        tasks = state.get("tasks") or {}
        if not tasks:
            reasons.append("no tasks in state")
        for tid, t in tasks.items():
            if tid == "C0":
                continue
            if not t.get("red_verified"):
                reasons.append(f"{tid} red_verified false")
            lock = t.get("test_lock") or {}
            if not (lock.get("files") or lock):
                reasons.append(f"{tid} missing test_lock")
        cfg = load_config(repo)
        require_tests = (cfg.get("approvals") or {}).get("require_tests", True)
        if require_tests:
            approvals = state.get("approvals") or {}
            if not approvals.get("tests"):
                reasons.append("approvals.tests timestamp required")
        nxt = "tdd_green"
    elif stage == "tdd_green":
        tasks = state.get("tasks") or {}
        for tid, t in tasks.items():
            if tid == "C0":
                continue
            if t.get("status") != "done":
                reasons.append(f"{tid} status not done")
        nxt = "integrate"
    elif stage == "integrate":
        gates = state.get("gates") or {}
        last = gates.get("last_run") or {}
        if last.get("ok") is not True:
            reasons.append("full gate not green")
        nxt = "supervisor"
    elif stage == "supervisor":
        # advance when supervisor_status approved stored in gates or tasks
        if (state.get("gates") or {}).get("supervisor") != "approved":
            reasons.append("supervisor not approved")
        nxt = "structure_review"
    elif stage == "structure_review":
        if (state.get("gates") or {}).get("structure") not in {"ok", "approved", True}:
            # allow if explicitly set ok
            if (state.get("gates") or {}).get("structure_ok") is not True:
                reasons.append("structure review not cleared")
        nxt = "bug_review"
    elif stage == "bug_review":
        if (state.get("gates") or {}).get("bugs_ok") is not True:
            reasons.append("bugs not cleared")
        nxt = "cleanup"
    elif stage == "cleanup":
        if (state.get("gates") or {}).get("last_run", {}).get("ok") is not True:
            reasons.append("full gate after cleanup not green")
        nxt = "final_gate"
    elif stage == "final_gate":
        approvals = state.get("approvals") or {}
        if not approvals.get("pr"):
            reasons.append("approvals.pr required")
        if (state.get("gates") or {}).get("last_run", {}).get("ok") is not True:
            reasons.append("final gate not green")
        # Ship gate passed → complete run; PR open is optional (CLI or human)
        nxt = "done"
    elif stage == "pr":
        # Legacy: runs left in `pr` still complete without pr_created
        nxt = "done"
    elif stage in {"done", "escalated", "aborted"}:
        return {
            "ok": True,
            "can_advance": False,
            "reason": f"terminal stage: {stage}",
            "next": None,
            "stage": stage,
        }
    else:
        reasons.append(f"unknown stage: {stage}")

    # cap check
    loops = state.get("loops") or {}
    caps = state.get("caps") or {}
    for key in ("supervisor_rejects", "structure_refactors", "bug_fix_rounds"):
        if int(loops.get(key) or 0) >= int(caps.get(key) or 999):
            return {
                "ok": False,
                "can_advance": False,
                "reason": f"cap reached: {key}",
                "next": None,
                "escalate": True,
                "stage": stage,
            }

    can = len(reasons) == 0
    return {
        "ok": can,
        "can_advance": can,
        "reason": "; ".join(reasons) if reasons else "ready",
        "reasons": reasons,
        "next": nxt,
        "stage": stage,
    }


def advance(repo: Path | None = None) -> dict[str, Any]:
    ev = evaluate(repo)
    if ev.get("escalate"):
        state = read_state(repo)
        assert state
        state["stage"] = "escalated"
        state["escalation"] = {"reason": ev.get("reason")}
        write_state(state, repo)
        return {**ev, "advanced": False, "stage": "escalated"}
    if not ev.get("can_advance"):
        return {**ev, "advanced": False}
    # Successful PR finish: archive plan + clear runtime so the next feature starts clean
    if ev.get("next") == "done":
        finished = complete_run(repo)
        return {
            **ev,
            "advanced": True,
            "stage": "done",
            "completed": True,
            **finished,
        }
    state = read_state(repo)
    assert state
    state["stage"] = ev["next"]
    state["stage_status"] = "in_progress"
    write_state(state, repo)
    return {**ev, "advanced": True, "stage": state["stage"]}
