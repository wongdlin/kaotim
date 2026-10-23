"""gate, run-tests, verify-red — config.yaml commands (no adapters)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .config import get_commands, has_test_command, wrong_reason_signatures
from .io_util import atomic_write_text
from .junit import ids_in_text, parse_junit
from .locks import verify_lock
from .metrics import log_event
from .paths import ensure_kaotim_dirs
from .plan import parse_plan, plan_path
from .state import read_state, write_state
from .trim import trim_output

# Soft assertion markers when classifying text output (optional; exit≠0 still counts as red).
DEFAULT_ASSERTION = [
    "AssertionError",
    "Failed asserting",
    "expect(",
    "Expected",
    "assert ",
]


def _run_cmd(cmd: str, cwd: Path, timeout: int = 120) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _resolve_test_cmd(cmds: dict[str, str], mode: str, files: list[str] | None) -> str:
    if mode == "single" and files:
        tmpl = cmds.get("test_file") or cmds.get("test") or ""
        return tmpl.replace("{file}", files[0]).replace("{files}", " ".join(files))
    if mode == "affected" and files:
        tmpl = cmds.get("test_file") or cmds.get("test") or ""
        return tmpl.replace("{files}", " ".join(files)).replace("{file}", files[0])
    return cmds.get("test") or ""


def _text_result(
    code: int,
    out: str,
    err: str,
    wrong_sigs: list[str],
) -> dict[str, Any]:
    blob = out + "\n" + err
    wrong = any(s in blob for s in wrong_sigs)
    if code == 0:
        return {
            "runner": "text",
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "failures": [],
            "structured": False,
            "ok": True,
            "exit_code": code,
        }
    kind = "wrong_reason" if wrong else "assertion"
    return {
        "runner": "text",
        "passed": 0,
        "failed": 0 if wrong else 1,
        "errors": 1 if wrong else 0,
        "skipped": 0,
        "failures": [
            {
                "test": "(suite)",
                "kind": kind,
                "message": trim_output(blob)[:500],
                "file": "",
                "line": 0,
            }
        ],
        "structured": False,
        "ok": False,
        "exit_code": code,
    }


def run_tests(
    repo: Path,
    mode: str = "all",
    task: str | None = None,
    files: list[str] | None = None,
) -> dict[str, Any]:
    ensure_kaotim_dirs(repo)
    cmds = get_commands(repo)
    cmd = _resolve_test_cmd(cmds, mode, files)
    if not cmd.strip():
        return {
            "ok": False,
            "results": [
                {
                    "ok": False,
                    "error": "commands.test is empty — set it in .kaotim/config.yaml",
                    "failed": 0,
                    "errors": 1,
                    "failures": [],
                }
            ],
        }

    junit_path = ensure_kaotim_dirs(repo) / "gates" / "junit.xml"
    junit_path.parent.mkdir(parents=True, exist_ok=True)
    if junit_path.exists():
        junit_path.unlink()

    flag = (cmds.get("junit_flag") or "").strip()
    run_cmd = cmd
    if flag:
        run_cmd = f"{cmd} {flag.replace('{path}', str(junit_path))}"

    try:
        code, out, err = _run_cmd(run_cmd, repo)
    except subprocess.TimeoutExpired:
        code, out, err = 1, "", "timeout"

    raw_path = ensure_kaotim_dirs(repo) / "gates" / "tests.txt"
    atomic_write_text(raw_path, out + "\n" + err)
    wrong_sigs = wrong_reason_signatures(repo)

    if flag and junit_path.exists() and junit_path.stat().st_size > 0:
        parsed = parse_junit(
            junit_path,
            runner="junit",
            assertion_sigs=DEFAULT_ASSERTION,
            wrong_sigs=wrong_sigs,
        )
        parsed["exit_code"] = code
        if code != 0 and parsed.get("failed", 0) == 0 and parsed.get("errors", 0) == 0:
            # JUnit green but process failed — treat as wrong-reason
            parsed["errors"] = 1
            parsed["failures"] = parsed.get("failures") or []
            parsed["failures"].append(
                {
                    "test": "(suite)",
                    "kind": "wrong_reason",
                    "message": trim_output(out + "\n" + err)[:500] or f"exit {code}",
                    "file": "",
                    "line": 0,
                }
            )
        ok = parsed["failed"] == 0 and parsed["errors"] == 0 and code == 0
        parsed["ok"] = ok
    elif flag and code == 0 and (not junit_path.exists() or junit_path.stat().st_size == 0):
        # Expected JUnit but missing while exit 0 — pass unstructured
        parsed = {
            "runner": "junit",
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "failures": [],
            "structured": False,
            "ok": True,
            "exit_code": code,
        }
    else:
        parsed = _text_result(code, out, err, wrong_sigs)

    parsed["raw_path"] = str(raw_path)
    parsed["trimmed"] = trim_output(out + "\n" + err)
    parsed["command"] = run_cmd
    overall_ok = bool(parsed.get("ok"))
    log_event("gate", repo=repo, stage="tests", tests=parsed)
    return {"ok": overall_ok, "results": [parsed]}


def verify_red(repo: Path, task: str) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        return {"ok": False, "errors": ["state.json missing"]}
    if not has_test_command(repo):
        return {
            "ok": False,
            "errors": ["commands.test is empty — set it in .kaotim/config.yaml before TDD"],
            "results": [],
        }
    result = run_tests(repo, mode="all", task=task)
    errors: list[str] = []
    total_failed = sum(r.get("failed", 0) + r.get("errors", 0) for r in result["results"])
    # Text mode: failed assertions count as red; wrong_reason errors are invalid red
    assertion_failed = sum(r.get("failed", 0) for r in result["results"])
    if assertion_failed <= 0 and total_failed <= 0:
        # also accept exit≠0 with assertion-kind failure already counted in failed
        errors.append("expected failing tests (red), got none")
    for r in result["results"]:
        for f in r.get("failures") or []:
            if f.get("kind") == "wrong_reason":
                errors.append(f"wrong-reason failure: {f.get('test')}: {f.get('message')}")
            # unclassified "other" only when structured junit left gaps
            if f.get("kind") == "other":
                errors.append(f"unclassified failure: {f.get('test')}")

    if plan_path(repo).exists():
        plan = parse_plan(plan_path(repo).read_text(encoding="utf-8"))
        needed = []
        for row in plan["acceptance"] + plan["edge_cases"]:
            tid = row.get("Task") or row.get("task")
            eid = row.get("ID") or row.get("Id") or row.get("id")
            if tid == task and eid:
                needed.append(eid.upper().replace("_", "-"))
        blob = ""
        for r in result["results"]:
            for f in r.get("failures") or []:
                blob += f.get("test", "") + " " + f.get("message", "") + "\n"
            blob += (r.get("trimmed") or "") + "\n"
        found = ids_in_text(blob)
        norm_needed = set()
        for n in needed:
            n = n.upper()
            if "-" not in n and len(n) > 2:
                n = n[:2] + "-" + n[2:]
            norm_needed.add(n)
        missing = [
            n
            for n in norm_needed
            if n not in found and n.replace("-", "") not in {x.replace("-", "") for x in found}
        ]
        if missing:
            errors.append(f"missing failing tests for: {', '.join(missing)}")

    has_assertion_red = any(
        f.get("kind") == "assertion"
        for r in result["results"]
        for f in (r.get("failures") or [])
    ) or any(r.get("failed", 0) > 0 for r in result["results"])
    if not has_assertion_red and "expected failing tests (red), got none" not in errors:
        # keep existing message if already added when total_failed was 0
        if not any(e.startswith("expected failing") for e in errors):
            errors.append("expected failing tests (red), got none")
    blocking = [
        e
        for e in errors
        if e.startswith("wrong-reason")
        or e.startswith("unclassified")
        or e.startswith("missing")
        or e.startswith("expected failing")
    ]
    ok = has_assertion_red and len(blocking) == 0

    if ok and state:
        tasks = state.setdefault("tasks", {})
        task_state = tasks.setdefault(task, {})
        task_state["red_verified"] = True
        task_state["status"] = "red"
        tasks[task] = task_state
        state["tasks"] = tasks
        write_state(state, repo)
    return {"ok": ok, "errors": errors, "results": result["results"]}


def run_gate(
    repo: Path,
    stage: str,
    task: str | None = None,
    scope: str = "full",
    only: list[str] | None = None,
) -> dict[str, Any]:
    only = only or ["lint", "types", "build", "tests"]
    ensure_kaotim_dirs(repo)
    lock = verify_lock(repo, task_id=task)
    if not lock["ok"]:
        return {"ok": False, "summary": "verify-lock failed", "lock": lock, "parts": {}}

    cmds = get_commands(repo)
    parts: dict[str, Any] = {}
    overall = True
    mapping = {
        "lint": cmds.get("lint"),
        "types": cmds.get("typecheck"),
        "build": cmds.get("build"),
    }
    quality_parts: dict[str, Any] = {}
    for key, cmd in mapping.items():
        if key not in only:
            continue
        if not cmd:
            quality_parts[key] = {"ok": True, "skipped": True}
            continue
        try:
            code, out, err = _run_cmd(cmd, repo)
        except subprocess.TimeoutExpired:
            code, out, err = 1, "", "timeout"
        raw = ensure_kaotim_dirs(repo) / "gates" / f"{stage}-{key}.txt"
        atomic_write_text(raw, out + "\n" + err)
        ok = code == 0
        quality_parts[key] = {
            "ok": ok,
            "exit_code": code,
            "trimmed": trim_output(out + "\n" + err),
            "raw_path": str(raw),
        }
        if not ok:
            overall = False
    parts["quality"] = quality_parts

    if "tests" in only:
        tr = run_tests(repo, mode="all" if scope == "full" else "affected", task=task)
        parts["tests"] = tr
        if not tr["ok"]:
            overall = False

    state = read_state(repo)
    if state:
        gates = state.setdefault("gates", {})
        gates["last_run"] = {"ok": overall, "stage": stage, "parts": _compact(parts)}
        state["gates"] = gates
        write_state(state, repo)
    log_event("gate", repo=repo, stage=stage, lint=None, tests=parts.get("tests"))
    return {"ok": overall, "stage": stage, "parts": parts, "lock": lock}


def _compact(parts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in parts.items():
        if k == "tests":
            out[k] = {"ok": v.get("ok")}
        elif k == "quality" and isinstance(v, dict):
            out[k] = {
                kk: {"ok": vv.get("ok"), "skipped": vv.get("skipped")}
                for kk, vv in v.items()
                if isinstance(vv, dict)
            }
        else:
            out[k] = v
    return out
