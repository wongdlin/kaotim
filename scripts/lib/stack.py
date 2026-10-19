"""stack.yaml loading, get-package, get-stack."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from .paths import kaotim_dir
from .yaml_util import load_yaml_file


def stack_path(repo: Path | None = None) -> Path:
    return kaotim_dir(repo) / "stack.yaml"


def load_stack(repo: Path | None = None) -> dict[str, Any] | None:
    path = stack_path(repo)
    if not path.exists():
        return None
    data = load_yaml_file(path)
    return data if isinstance(data, dict) else None


def packages(stack: dict[str, Any]) -> list[dict[str, Any]]:
    pkgs = stack.get("packages") or []
    return [p for p in pkgs if isinstance(p, dict)]


def get_package(repo: Path | None = None, file: str | None = None) -> dict[str, Any]:
    stack = load_stack(repo)
    if not stack:
        raise FileNotFoundError("stack.yaml missing")
    pkgs = packages(stack)
    if not pkgs:
        raise ValueError("stack.yaml has no packages")
    if len(pkgs) > 1:
        # v1: reject multi-package
        raise ValueError(
            "v1 supports exactly one package; multi-package monorepos are v2"
        )
    pkg = pkgs[0]
    result = {
        "name": pkg.get("name", "default"),
        "path": pkg.get("path", "."),
        "stacks": pkg.get("stacks") or [],
        "git": stack.get("git") or {},
        "conventions": stack.get("conventions") or {},
        "version": stack.get("version", 1),
    }
    if file:
        # still return the single package; routing by file is v2
        result["requested_file"] = file
    return result


def _norm(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def file_matches_scope(file_path: str, scope: list[str]) -> bool:
    rel = _norm(file_path)
    for pattern in scope or []:
        pat = _norm(pattern)
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat.rstrip("/**")):
            return True
        # directory prefix patterns like app/**
        if pat.endswith("/**") and (rel.startswith(pat[:-3]) or rel + "/" == pat[:-2]):
            return True
    return False


def get_stack_for_file(repo: Path | None, file_path: str) -> dict[str, Any]:
    pkg = get_package(repo)
    stacks = pkg.get("stacks") or []
    matches = []
    for st in stacks:
        if not isinstance(st, dict):
            continue
        scope = st.get("scope") or []
        if file_matches_scope(file_path, scope):
            matches.append(st)
    if not matches:
        raise ValueError(f"file not in any stack scope: {file_path}")
    if len(matches) > 1:
        names = [m.get("name") for m in matches]
        raise ValueError(f"file matched multiple stacks: {names}")
    st = matches[0]
    return {
        "package": pkg.get("name"),
        "name": st.get("name"),
        "adapter": st.get("adapter"),
        "scope": st.get("scope") or [],
        "root": st.get("root", "."),
        "languages": st.get("languages") or [],
        "frameworks": st.get("frameworks") or [],
        "architecture": st.get("architecture") or {},
        "testing": st.get("testing") or {},
        "quality": st.get("quality") or {},
        "worktree": st.get("worktree") or {},
    }


def scopes_overlap(a: list[str], b: list[str]) -> bool:
    """Conservative overlap check using literal prefixes and identical patterns."""
    for pa in a or []:
        for pb in b or []:
            if pa == pb:
                return True
            na, nb = _norm(pa), _norm(pb)
            if na.rstrip("/**") and nb.rstrip("/**"):
                base_a = na[:-3] if na.endswith("/**") else na
                base_b = nb[:-3] if nb.endswith("/**") else nb
                if base_a.startswith(base_b) or base_b.startswith(base_a):
                    return True
    return False
