"""validate-stack against schema §4.1."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .adapters.registry import get_adapter
from .stack import load_stack, packages, scopes_overlap


def validate_stack(
    repo: Path | None = None,
    data: dict[str, Any] | None = None,
    dry_run_commands: bool = False,
) -> dict[str, Any]:
    stack = data or load_stack(repo)
    errors: list[str] = []
    warnings: list[str] = []
    if not stack:
        return {"ok": False, "errors": ["stack.yaml missing"], "warnings": []}

    if stack.get("version") != 1:
        errors.append("version must be 1")
    pkgs = packages(stack)
    if len(pkgs) == 0:
        errors.append("at least one package required")
    if len(pkgs) > 1:
        errors.append("v1 supports exactly one package; multi-package is v2")

    for pkg in pkgs[:1]:
        stacks = pkg.get("stacks") or []
        if not stacks:
            errors.append(f"package {pkg.get('name')} has no stacks")
        names = []
        for st in stacks:
            if not isinstance(st, dict):
                errors.append("stack entry must be a mapping")
                continue
            name = st.get("name")
            if not name:
                errors.append("stack missing name")
            if name in names:
                errors.append(f"duplicate stack name: {name}")
            names.append(name)
            if not st.get("adapter"):
                errors.append(f"stack {name}: adapter required")
            else:
                aid = st["adapter"]
                if aid != "none" and not str(aid).startswith("generated:"):
                    try:
                        get_adapter(str(aid).split(":")[-1] if str(aid).startswith("generated:") else aid)
                    except KeyError:
                        # generated adapters live in .kaotim/adapters
                        from .paths import kaotim_dir

                        try:
                            get_adapter(
                                str(aid).split(":")[-1],
                                search_dirs=[kaotim_dir(repo) / "adapters"],
                            )
                        except KeyError:
                            errors.append(f"stack {name}: unknown adapter {aid}")
            scope = st.get("scope") or []
            if not scope:
                warnings.append(f"stack {name}: empty scope")
            testing = st.get("testing") or {}
            cmds = (testing.get("commands") or {}) if isinstance(testing, dict) else {}
            if not cmds.get("all"):
                warnings.append(f"stack {name}: testing.commands.all missing")

        # scope overlaps
        for i, a in enumerate(stacks):
            for b in stacks[i + 1 :]:
                if not isinstance(a, dict) or not isinstance(b, dict):
                    continue
                if scopes_overlap(a.get("scope") or [], b.get("scope") or []):
                    errors.append(
                        f"overlapping scopes between stacks {a.get('name')} and {b.get('name')}"
                    )

        if dry_run_commands and repo is not None:
            for st in stacks:
                if not isinstance(st, dict):
                    continue
                root = repo / (st.get("root") or ".")
                quality = st.get("quality") or {}
                testing = st.get("testing") or {}
                cmds = []
                for key in ("lint", "typecheck", "build"):
                    c = quality.get(key)
                    if c:
                        cmds.append(c)
                all_cmd = (testing.get("commands") or {}).get("all")
                if all_cmd:
                    cmds.append(all_cmd)
                for cmd in cmds:
                    # only check that shell can start — use short timeout help/version if possible
                    try:
                        subprocess.run(
                            cmd,
                            cwd=str(root),
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=15,
                        )
                    except Exception as exc:
                        warnings.append(f"dry-run failed for `{cmd}`: {exc}")

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}
