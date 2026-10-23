"""doctor and doctor --self checks."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from . import PLUGIN_VERSION
from .config import has_test_command, load_config
from .paths import kaotim_dir, plugin_root

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

    stack = kaotim_dir(repo) / "stack.yaml"
    add(
        "no-stack.yaml",
        not stack.exists(),
        "remove leftover .kaotim/stack.yaml (hard cut; use config.yaml commands)"
        if stack.exists()
        else "absent",
    )

    cfg_path = kaotim_dir(repo) / "config.yaml"
    add("config.yaml", cfg_path.exists(), str(cfg_path) if cfg_path.exists() else "missing (run /kaotim-init)")
    if cfg_path.exists():
        load_config(repo)  # ensure merges
        add(
            "commands.test",
            True,
            "set" if has_test_command(repo) else "empty (required after plan approve, before TDD)",
        )

    profile = kaotim_dir(repo) / "project-profile.md"
    add("project-profile", profile.exists(), str(profile))

    bin_cli = kaotim_dir(repo) / "bin" / "kaotim.py"
    if bin_cli.exists():
        add("bin-version", True, f"copied CLI present ({bin_cli})")
    else:
        add("bin-version", True, "bin copy not required until /kaotim-init")

    for xml in repo.glob("phpunit.xml*"):
        text = xml.read_text(encoding="utf-8", errors="replace")
        if re.search(r"DB_DATABASE.*production", text, re.I):
            add("db-safety", False, f"suspicious DB in {xml}")
        else:
            add("db-safety", True, f"checked {xml.name}")

    if self_check:
        self_checks = _self_checks()
        checks.extend(self_checks)
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
