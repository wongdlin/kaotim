"""gate, run-tests, verify-red."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .adapters.registry import get_adapter
from .io_util import atomic_write_text
from .junit import ids_in_text, parse_junit
from .locks import verify_lock
from .metrics import log_event
from .paths import ensure_kaotim_dirs
from .plan import parse_plan, plan_path
from .stack import get_package, get_stack_for_file
from .state import read_state, write_state
from .trim import trim_output


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


def run_tests(
    repo: Path,
    mode: str = "all",
    task: str | None = None,
    files: list[str] | None = None,
) -> dict[str, Any]:
    ensure_kaotim_dirs(repo)
    pkg = get_package(repo)
    results = []
    overall_ok = True

    stacks = pkg.get("stacks") or []
    if task:
        state = read_state(repo) or {}
        t = (state.get("tasks") or {}).get(task) or {}
        owns = t.get("owns") or files or []
        stack_name = t.get("stack")
        if stack_name:
            stacks = [s for s in stacks if s.get("name") == stack_name]
        elif owns:
            try:
                st = get_stack_for_file(repo, owns[0].replace("**", "x").replace("*", "x"))
                stacks = [s for s in stacks if s.get("name") == st["name"]]
            except Exception:
                pass

    for st in stacks:
        adapter_id = st.get("adapter") or "none"
        if adapter_id == "none":
            continue
        try:
            adapter = get_adapter(
                str(adapter_id).split(":")[-1],
                search_dirs=[ensure_kaotim_dirs(repo) / "adapters"],
            )
        except KeyError:
            overall_ok = False
            results.append({"stack": st.get("name"), "ok": False, "error": "adapter missing"})
            continue
        testing = st.get("testing") or {}
        cmds = testing.get("commands") or {}
        root = repo / (st.get("root") or ".")
        junit_path = ensure_kaotim_dirs(repo) / "gates" / f"junit-{st.get('name')}.xml"
        junit_path.parent.mkdir(parents=True, exist_ok=True)
        if junit_path.exists():
            junit_path.unlink()

        if mode == "single" and files:
            cmd_t = cmds.get("single") or cmds.get("all")
            cmd = (cmd_t or "").replace("{file}", files[0]).replace("{files}", " ".join(files))
        elif mode == "affected" and files:
            cmd_t = cmds.get("affected") or cmds.get("all")
            cmd = (cmd_t or "").replace("{files}", " ".join(files)).replace("{file}", files[0])
        else:
            cmd = cmds.get("all") or ""

        flag = ((adapter.get("tests") or {}).get("results") or {}).get("flag") or ""
        if flag and cmd:
            cmd = f"{cmd} {flag.replace('{path}', str(junit_path))}"

        code, out, err = (1, "", "no command")
        if cmd:
            try:
                code, out, err = _run_cmd(cmd, root)
            except subprocess.TimeoutExpired:
                code, out, err = 1, "", "timeout"

        raw_path = ensure_kaotim_dirs(repo) / "gates" / f"tests-{st.get('name')}.txt"
        atomic_write_text(raw_path, out + "\n" + err)
        tests_meta = adapter.get("tests") or {}
        parsed = parse_junit(
            junit_path,
            runner=(testing.get("framework") or adapter_id),
            assertion_sigs=tests_meta.get("assertion_signatures") or [],
            wrong_sigs=tests_meta.get("wrong_reason_signatures") or [],
        )
        parsed["raw_path"] = str(raw_path)
        parsed["exit_code"] = code
        parsed["stack"] = st.get("name")
        parsed["trimmed"] = trim_output(out + "\n" + err)
        # if junit missing but exit 0, treat as pass with unstructured
        if not junit_path.exists() and code == 0:
            parsed.update(
                {
                    "passed": 1,
                    "failed": 0,
                    "errors": 0,
                    "structured": False,
                    "failures": [],
                }
            )
        ok = parsed["failed"] == 0 and parsed["errors"] == 0 and code == 0
        parsed["ok"] = ok
        if not ok:
            overall_ok = False
        results.append(parsed)
        log_event("gate", repo=repo, stage="tests", stack=st.get("name"), tests=parsed)

    return {"ok": overall_ok, "results": results}


def verify_red(repo: Path, task: str) -> dict[str, Any]:
    state = read_state(repo)
    if not state:
        return {"ok": False, "errors": ["state.json missing"]}
    tmeta = (state.get("tasks") or {}).get(task) or {}
    result = run_tests(repo, mode="all", task=task)
    errors: list[str] = []
    # must have failures
    total_failed = sum(r.get("failed", 0) + r.get("errors", 0) for r in result["results"])
    if total_failed <= 0:
        errors.append("expected failing tests (red), got none")
    for r in result["results"]:
        for f in r.get("failures") or []:
            if f.get("kind") == "wrong_reason":
                errors.append(f"wrong-reason failure: {f.get('test')}: {f.get('message')}")
            if f.get("kind") == "other":
                errors.append(f"unclassified failure: {f.get('test')}")
    # every AC/EC for task must appear in failing test names/messages
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
        found = ids_in_text(blob)
        # normalize needed
        norm_needed = set()
        for n in needed:
            n = n.upper()
            if not re_has_dash(n):
                n = n[:2] + "-" + n[2:]
            norm_needed.add(n)
        missing = [n for n in norm_needed if n not in found and n.replace("-", "") not in {x.replace("-", "") for x in found}]
        if missing:
            errors.append(f"missing failing tests for: {', '.join(missing)}")

    ok = len(errors) == 0 and total_failed > 0
    if ok and state:
        tasks = state.setdefault("tasks", {})
        task_state = tasks.setdefault(task, {})
        task_state["red_verified"] = True
        task_state["status"] = "red"
        tasks[task] = task_state
        state["tasks"] = tasks
        write_state(state, repo)
    return {"ok": ok, "errors": errors, "results": result["results"]}


def re_has_dash(n: str) -> bool:
    return "-" in n


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

    pkg = get_package(repo)
    parts: dict[str, Any] = {}
    overall = True
    stacks = pkg.get("stacks") or []

    for st in stacks:
        root = repo / (st.get("root") or ".")
        quality = st.get("quality") or {}
        stack_parts = {}
        mapping = {
            "lint": quality.get("lint"),
            "types": quality.get("typecheck"),
            "build": quality.get("build"),
        }
        for key, cmd in mapping.items():
            if key not in only:
                continue
            if not cmd:
                stack_parts[key] = {"ok": True, "skipped": True}
                continue
            try:
                code, out, err = _run_cmd(cmd, root)
            except subprocess.TimeoutExpired:
                code, out, err = 1, "", "timeout"
            raw = ensure_kaotim_dirs(repo) / "gates" / f"{stage}-{st.get('name')}-{key}.txt"
            atomic_write_text(raw, out + "\n" + err)
            ok = code == 0
            stack_parts[key] = {
                "ok": ok,
                "exit_code": code,
                "trimmed": trim_output(out + "\n" + err),
                "raw_path": str(raw),
            }
            if not ok:
                overall = False
        parts[st.get("name") or "?"] = stack_parts

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
    # keep state small
    out = {}
    for k, v in parts.items():
        if k == "tests":
            out[k] = {"ok": v.get("ok")}
        else:
            out[k] = {
                kk: {"ok": vv.get("ok"), "skipped": vv.get("skipped")}
                for kk, vv in v.items()
                if isinstance(vv, dict)
            }
    return out
