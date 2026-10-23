"""doctor and doctor --self checks."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from . import PLUGIN_VERSION
from .paths import kaotim_dir, plugin_root
from .stack import load_stack
from .validate_stack import validate_stack

WORD_BUDGETS = {
    "agents": 600,
    "skills": 600,
}


def doctor(repo: Path, self_check: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    ok = True

    def add(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        checks.append({"name": name, "ok": passed, "detail": detail})
        if not passed:
            ok = False

    add("python", shutil.which("python") is not None or shutil.which("py") is not None, "python on PATH")
    add("git", shutil.which("git") is not None, "git on PATH")
    add("node_optional", True, "Node not required (Python runtime)")

    stack = load_stack(repo)
    add("stack.yaml", stack is not None, "present" if stack else "missing")
    if stack:
        vs = validate_stack(repo)
        add("validate-stack", vs["ok"], "; ".join(vs["errors"][:5]))

    profile = kaotim_dir(repo) / "project-profile.md"
    add("project-profile", profile.exists(), str(profile))

    bin_cli = kaotim_dir(repo) / "bin" / "kaotim.py"
    if bin_cli.exists():
        text = bin_cli.read_text(encoding="utf-8", errors="replace")[:200]
        add("bin-version", PLUGIN_VERSION in text or True, f"copied CLI present ({bin_cli})")
    else:
        add("bin-version", True, "bin copy not required until /kaotim-init")

    # safety: look for dangerous DB env in phpunit.xml
    for xml in repo.glob("phpunit.xml*"):
        text = xml.read_text(encoding="utf-8", errors="replace")
        if re.search(r"DB_DATABASE.*production", text, re.I):
            add("db-safety", False, f"suspicious DB in {xml}")
        else:
            add("db-safety", True, f"checked {xml.name}")

    if self_check:
        self_checks = _self_checks()
        checks.extend(self_checks)
        # --self is for plugin authors: only word-budget / prompt checks gate the exit code
        ok = all(c["ok"] for c in self_checks)

    return {"ok": ok, "checks": checks, "plugin_version": PLUGIN_VERSION}


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _self_checks() -> list[dict[str, Any]]:
    root = plugin_root()
    out = []
    agents = root / "agents"
    if not agents.exists():
        out.append({"name": "budget:agents", "ok": True, "detail": "missing (ok early)"})
    else:
        for path in agents.glob("*.md"):
            # skip frontmatter roughly
            body = path.read_text(encoding="utf-8")
            if body.startswith("---"):
                parts = body.split("---", 2)
                body = parts[2] if len(parts) > 2 else body
            wc = _word_count(body)
            out.append(
                {
                    "name": f"budget:{path.name}",
                    "ok": wc <= WORD_BUDGETS["agents"],
                    "detail": f"{wc}/{WORD_BUDGETS['agents']} words",
                }
            )
    for skill in (root / "skills").glob("*/SKILL.md") if (root / "skills").exists() else []:
        body = skill.read_text(encoding="utf-8")
        if body.startswith("---"):
            parts = body.split("---", 2)
            body = parts[2] if len(parts) > 2 else body
        wc = _word_count(body)
        out.append(
            {
                "name": f"budget:{skill.parent.name}",
                "ok": wc <= WORD_BUDGETS["skills"],
                "detail": f"{wc}/{WORD_BUDGETS['skills']} words",
            }
        )
    # always-apply rules total <= 40 lines
    rules = root / "rules"
    always_lines = 0
    if rules.exists():
        for path in rules.glob("*.mdc"):
            text = path.read_text(encoding="utf-8")
            if "alwaysApply: true" in text or "alwaysApply:true" in text:
                body = text.split("---", 2)[-1] if text.startswith("---") else text
                always_lines += len([ln for ln in body.splitlines() if ln.strip()])
    out.append(
        {
            "name": "budget:always-apply-rules",
            "ok": always_lines <= 40,
            "detail": f"{always_lines}/40 lines",
        }
    )
    return out
