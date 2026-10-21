"""plan.md parser and check-plan validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .paths import kaotim_dir
from .stack import get_stack_for_file, load_stack, scopes_overlap


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
TASK_HEADER_RE = re.compile(r"^###\s+(C0|T\d+):\s*(.+)$", re.MULTILINE)


def plan_path(repo: Path | None = None) -> Path:
    return kaotim_dir(repo) / "plan.md"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip("'\"")
    return meta, text[m.end() :]


def _table_rows(section: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = [ln.strip() for ln in section.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return rows
    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    for line in lines[2:]:
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) != len(headers):
            continue
        rows.append(dict(zip(headers, cols)))
    return rows


def _section(body: str, number: str, title_hint: str) -> str:
    # title_hint may appear anywhere after the number (e.g. "7. E — Execution Units")
    pat = re.compile(
        rf"^##\s+{number}\.\s+[^\n]*{re.escape(title_hint)}[^\n]*\n(.*?)(?=^##\s+\d+\.|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    m = pat.search(body)
    return m.group(1) if m else ""


def parse_plan(text: str) -> dict[str, Any]:
    meta, body = parse_frontmatter(text)
    goal_sec = _section(body, "1", "Goal") or _section(body, "1", "Purpose")
    io_sec = _section(body, "2", "Inputs")
    ac_sec = _section(body, "3", "Acceptance")
    ec_sec = _section(body, "4", "Edge")
    # S — Scope & Constraints (legacy: ## 5. Architecture)
    scope_sec = _section(body, "5", "Scope") or _section(body, "5", "Architecture")
    shapes_sec = _section(body, "6", "Precision") or _section(body, "6", "P")
    # E — Execution Units (legacy: ## 6. Tasks)
    tasks_sec = (
        _section(body, "7", "Execution")
        or _section(body, "7", "Tasks")
        or _section(body, "6", "Tasks")
    )
    cp_sec = _section(body, "8", "Checkpoints") or _section(body, "8", "C")
    open_sec = (
        _section(body, "11", "Open")
        or _section(body, "9", "Open")
    )

    ac_rows = _table_rows(ac_sec)
    ec_rows = _table_rows(ec_sec)
    cp_rows = _table_rows(cp_sec)

    tasks: dict[str, dict[str, Any]] = {}
    for m in TASK_HEADER_RE.finditer(tasks_sec):
        tid, name = m.group(1), m.group(2).strip()
        start = m.end()
        nxt = TASK_HEADER_RE.search(tasks_sec, start)
        block = tasks_sec[start : nxt.start() if nxt else None]
        owns = _field(block, "Owns files")
        depends = _field(block, "Depends on")
        covers = _field(block, "Covers")
        done_when = _field(block, "Done when")
        tasks[tid] = {
            "id": tid,
            "name": name,
            "owns": _split_list(owns),
            "depends_on": _split_list(depends),
            "covers": _split_list(covers),
            "done_when": done_when,
            "raw": block,
        }

    comparison_required = bool(
        re.search(r"Comparison required:\s*yes", scope_sec, re.IGNORECASE)
    )
    chosen = None
    cm = re.search(r"Chosen:\s*(.+)", scope_sec, re.IGNORECASE)
    if cm:
        chosen = cm.group(1).strip()

    blocking_questions = []
    for line in open_sec.splitlines():
        if re.search(r"\bBlocking\b", line, re.IGNORECASE) and line.strip().startswith(
            ("-", "*", "|")
        ):
            blocking_questions.append(line.strip())

    return {
        "meta": meta,
        "goal": goal_sec,
        "inputs_outputs": io_sec,
        "acceptance": ac_rows,
        "edge_cases": ec_rows,
        "checkpoints": cp_rows,
        "precision_shapes": shapes_sec,
        "tasks": tasks,
        "architecture": {
            "comparison_required": comparison_required,
            "chosen": chosen,
            "section": scope_sec,
        },
        "blocking_questions": blocking_questions,
        "body": body,
    }


def _field(block: str, label: str) -> str:
    m = re.search(rf"^\s*[-*]?\s*{re.escape(label)}:\s*(.+)$", block, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _split_list(value: str) -> list[str]:
    if not value or value.lower() in {"none", "-", "n/a"}:
        return []
    return [p.strip() for p in re.split(r"[,;]", value) if p.strip()]


def check_plan(repo: Path | None = None) -> dict[str, Any]:
    path = plan_path(repo)
    if not path.exists():
        return {"ok": False, "errors": ["plan.md missing"], "warnings": []}
    parsed = parse_plan(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    meta = parsed["meta"]
    status = (meta.get("status") or "draft").lower()
    tasks = parsed["tasks"]

    # Goal / Done when (SPEC entry)
    goal = parsed.get("goal") or ""
    if not re.search(r"Done when:\s*\S", goal, re.IGNORECASE):
        errors.append("Goal missing Done when")

    # Inputs / outputs
    io = parsed.get("inputs_outputs") or ""
    if not re.search(r"Inputs:\s*\S", io, re.IGNORECASE):
        errors.append("Inputs and outputs missing Inputs")
    if not re.search(r"Outputs:\s*\S", io, re.IGNORECASE):
        errors.append("Inputs and outputs missing Outputs")

    # AC mapping
    for row in parsed["acceptance"]:
        aid = row.get("ID") or row.get("Id") or row.get("id")
        task = row.get("Task") or row.get("task")
        criterion = row.get("Criterion") or row.get("criterion") or row.get("Acceptance")
        if not aid or not criterion:
            errors.append(f"AC row incomplete: {row}")
            continue
        if not task or task not in tasks:
            errors.append(f"{aid} not mapped to exactly one task")
        else:
            # count mappings
            pass

    # each AC/EC must map to exactly one task — also reverse
    ac_ids = []
    for row in parsed["acceptance"]:
        aid = row.get("ID") or row.get("Id") or row.get("id")
        task = row.get("Task") or row.get("task")
        if aid:
            ac_ids.append(aid)
            if task and task in tasks:
                covers = tasks[task].setdefault("_ac", [])
                covers.append(aid)

    for row in parsed["edge_cases"]:
        eid = row.get("ID") or row.get("Id") or row.get("id")
        decision = row.get("Decision") or row.get("decision")
        task = row.get("Task") or row.get("task")
        if not eid:
            errors.append(f"EC row missing ID: {row}")
            continue
        if not decision or decision.lower() in {"", "tbd", "?", "-"}:
            errors.append(f"{eid} missing Decision")
        if not task or task not in tasks:
            errors.append(f"{eid} not mapped to exactly one task")

    # C — Checkpoints & Tests: at least one; each maps to a task
    checkpoints = parsed.get("checkpoints") or []
    if not checkpoints:
        errors.append("Checkpoints & Tests missing (need at least one CP)")
    for row in checkpoints:
        cid = row.get("ID") or row.get("Id") or row.get("id")
        verify = (
            row.get("Command or assertion")
            or row.get("Verify")
            or row.get("verify")
            or row.get("Command")
            or ""
        )
        task = row.get("Task") or row.get("task")
        if not cid:
            errors.append(f"CP row missing ID: {row}")
            continue
        if not verify or verify.lower() in {"", "tbd", "?", "-"}:
            errors.append(f"{cid} missing Command or assertion")
        if not task or task not in tasks:
            errors.append(f"{cid} not mapped to exactly one task")

    # Tasks should declare Done when (maps to AC)
    for tid, t in tasks.items():
        if tid == "C0":
            continue
        if not (t.get("done_when") or "").strip():
            warnings.append(f"{tid} missing Done when")

    # ownership overlap
    task_ids = list(tasks.keys())
    for i, a in enumerate(task_ids):
        for b in task_ids[i + 1 :]:
            if scopes_overlap(tasks[a]["owns"], tasks[b]["owns"]):
                errors.append(f"overlapping owns between {a} and {b}")

    # dependency cycles + C0 ordering
    def deps_ok() -> None:
        graph = {tid: tasks[tid]["depends_on"] for tid in tasks}
        visiting: set[str] = set()
        seen: set[str] = set()

        def dfs(n: str) -> None:
            if n in seen:
                return
            if n in visiting:
                errors.append(f"cyclic task dependencies at {n}")
                return
            visiting.add(n)
            for d in graph.get(n, []):
                if d in graph:
                    dfs(d)
            visiting.remove(n)
            seen.add(n)

        for n in graph:
            dfs(n)

        if "C0" in tasks:
            for tid, t in tasks.items():
                if tid == "C0":
                    continue
                # dependents of contracts should list C0 or run after — soft check
                if t["depends_on"] and "C0" not in t["depends_on"] and tid.startswith("T"):
                    # only warn if C0 exists and T has no deps
                    pass

    deps_ok()

    # stack resolution for owns (except C0)
    if load_stack(repo):
        for tid, t in tasks.items():
            if tid == "C0":
                continue
            stacks_hit = set()
            for pattern in t["owns"]:
                # use pattern as file candidate for get-stack
                sample = pattern.replace("**", "x").replace("*", "x")
                try:
                    st = get_stack_for_file(repo, sample)
                    stacks_hit.add(st["name"])
                except Exception:
                    # try first scope file literal
                    try:
                        st = get_stack_for_file(repo, pattern.rstrip("/*"))
                        stacks_hit.add(st["name"])
                    except Exception as exc:
                        warnings.append(f"{tid} owns '{pattern}': {exc}")
            if len(stacks_hit) > 1:
                errors.append(f"{tid} owns files in multiple stacks: {sorted(stacks_hit)}")

    if status == "approved" and parsed["blocking_questions"]:
        errors.append("approved plan has blocking open questions")

    arch = parsed["architecture"]
    if arch["comparison_required"] and not arch["chosen"]:
        errors.append("comparison required but no Chosen architecture recorded")

    # fast lane limits
    if str(meta.get("fast_lane", "")).lower() in {"true", "yes", "1"}:
        total_files = sum(len(t["owns"]) for t in tasks.values())
        if total_files > 3:
            errors.append("fast lane: more than 3 owned file patterns")
        if "C0" in tasks:
            errors.append("fast lane: contracts (C0) not allowed")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "plan": {
            "id": meta.get("id"),
            "status": status,
            "tasks": list(tasks.keys()),
            "ac_count": len(parsed["acceptance"]),
            "ec_count": len(parsed["edge_cases"]),
            "cp_count": len(parsed.get("checkpoints") or []),
        },
    }
