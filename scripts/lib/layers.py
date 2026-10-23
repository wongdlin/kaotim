"""list-rules: discover repository rule files for structure-reviewer (agent enforcement)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

RULE_DIRS = (".cursor/rules", "rules")
RULE_GLOBS = ("*.md", "*.mdc", "*.txt")


def list_rules(repo: Path) -> dict[str, Any]:
    """Return rule file paths under .cursor/rules and/or rules/ (no import graph checks)."""
    files: list[str] = []
    dirs_found: list[str] = []
    for rel in RULE_DIRS:
        d = repo / rel
        if not d.is_dir():
            continue
        dirs_found.append(rel.replace("\\", "/"))
        for pattern in RULE_GLOBS:
            for path in sorted(d.rglob(pattern)):
                if path.is_file():
                    files.append(str(path.relative_to(repo)).replace("\\", "/"))
    # de-dupe preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return {
        "ok": True,
        "dirs": dirs_found,
        "files": unique,
        "count": len(unique),
        "note": "Structure review is agent-enforced; pass these paths to structure-reviewer.",
    }


# Back-compat alias for callers that still name check-layers
def check_layers(repo: Path) -> dict[str, Any]:
    return list_rules(repo)
