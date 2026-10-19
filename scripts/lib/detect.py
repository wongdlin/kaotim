"""detect-stack: scan repo and produce a digest JSON."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from .adapters.registry import builtin_adapters

SKIP_DIRS = {
    "vendor",
    "node_modules",
    ".venv",
    "venv",
    ".git",
    ".kaotim",
    "__pycache__",
    "dist",
    "build",
    ".tox",
}


def _iter_depth(root: Path, max_depth: int = 3):
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        depth = 0 if str(rel) == "." else len(rel.parts)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        if depth > max_depth:
            dirnames[:] = []
            continue
        yield depth, Path(dirpath), filenames


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _composer_deps(path: Path) -> set[str]:
    data = _read_json(path)
    if not isinstance(data, dict):
        return set()
    deps = set()
    for key in ("require", "require-dev"):
        block = data.get(key) or {}
        if isinstance(block, dict):
            deps.update(block.keys())
    return deps


def _pyproject_deps(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    deps: set[str] = set()
    for token in ("pytest", "django", "fastapi", "flask", "ruff", "mypy"):
        if token in text:
            deps.add(token)
    return deps


def _match_adapter(root: Path, directory: Path, filenames: set[str]) -> dict[str, Any] | None:
    adapters = builtin_adapters()
    # framework-specific first
    order = ["php-laravel", "python"]
    for aid in order:
        ad = adapters[aid]
        detect = ad.get("detect") or {}
        manifests = detect.get("manifests") or []
        files_need = detect.get("files") or []
        any_dep = detect.get("any_dependency") or []
        has_manifest = any(m in filenames for m in manifests)
        if not has_manifest and not any(f in filenames for f in files_need):
            continue
        deps: set[str] = set()
        if "composer.json" in filenames:
            deps |= _composer_deps(directory / "composer.json")
        if "pyproject.toml" in filenames:
            deps |= _pyproject_deps(directory / "pyproject.toml")
        if any_dep and not (deps & set(any_dep)):
            # php-laravel also accepts artisan + composer
            if aid == "php-laravel" and "artisan" in filenames and "composer.json" in filenames:
                pass
            elif aid == "python" and (
                "pyproject.toml" in filenames
                or "requirements.txt" in filenames
                or "Pipfile" in filenames
            ):
                pass
            else:
                continue
        rel = "." if directory == root else str(directory.relative_to(root)).replace("\\", "/")
        return {
            "adapter": aid,
            "root": rel,
            "evidence": {
                "manifests": [m for m in manifests if m in filenames],
                "files": [f for f in files_need if f in filenames],
                "deps": sorted(deps & set(any_dep)) if any_dep else sorted(deps)[:12],
            },
            "default_scope": ad.get("default_scope") or [],
            "capabilities": ad.get("capabilities") or {},
        }
    # unrecognized package.json etc.
    if "package.json" in filenames and "composer.json" not in filenames:
        rel = "." if directory == root else str(directory.relative_to(root)).replace("\\", "/")
        return {
            "adapter": None,
            "suggested": "generated:js-ts",
            "root": rel,
            "evidence": {"manifests": ["package.json"]},
            "default_scope": ["src/**", "resources/js/**"],
            "capabilities": {"verify_red": "text", "check_layers": "approximate"},
        }
    return None


def detect_stack(repo: Path) -> dict[str, Any]:
    root = repo.resolve()
    ecosystems: list[dict[str, Any]] = []
    ext_counts: Counter[str] = Counter()
    test_files: list[str] = []
    tree_sample: list[str] = []
    workspaces: list[str] = []
    seen_roots: set[str] = set()

    for depth, directory, filenames in _iter_depth(root, 3):
        rel_dir = "." if directory == root else str(directory.relative_to(root)).replace("\\", "/")
        if depth <= 2:
            tree_sample.append(rel_dir + "/")
        for name in filenames:
            suf = Path(name).suffix.lower()
            if suf:
                ext_counts[suf] += 1
            lower = name.lower()
            if "test" in lower and suf in {".php", ".py", ".ts", ".js"}:
                rel = str((directory / name).relative_to(root)).replace("\\", "/")
                if len(test_files) < 40:
                    test_files.append(rel)
        match = _match_adapter(root, directory, set(filenames))
        if match and match["root"] not in seen_roots:
            # avoid matching nested vendor-like; already skipped
            # for php-laravel at root and python in services/ml both OK
            ecosystems.append(match)
            seen_roots.add(match["root"])

    # workspaces hint
    pkg = root / "package.json"
    if pkg.exists():
        data = _read_json(pkg)
        if isinstance(data, dict) and data.get("workspaces"):
            workspaces.append("package.json:workspaces")

    # token budget: keep digest compact
    digest = {
        "repo": str(root),
        "detected_ecosystems": ecosystems,
        "file_counts_by_extension": dict(ext_counts.most_common(20)),
        "test_files_sample": test_files[:12],
        "tree_sample": tree_sample[:40],
        "workspaces": workspaces,
        "notes": [
            "Confirm adapters before writing stack.yaml.",
            "Unrecognized ecosystems can use generated declarative adapters or commands-only.",
        ],
    }
    # rough size
    raw = json.dumps(digest, separators=(",", ":"))
    digest["approx_tokens"] = max(1, len(raw) // 4)
    return digest


def digest_to_stack_draft(digest: dict[str, Any]) -> dict[str, Any]:
    from .adapters.registry import get_adapter

    stacks = []
    for i, eco in enumerate(digest.get("detected_ecosystems") or []):
        aid = eco.get("adapter")
        if not aid:
            continue
        ad = get_adapter(aid)
        defaults = ad.get("defaults") or {}
        name = "backend" if aid == "php-laravel" else ("ml" if eco.get("root") != "." else "python")
        if aid == "python" and eco.get("root") == ".":
            name = "python"
        if aid == "php-laravel":
            name = "backend"
        scope = list(ad.get("default_scope") or [])
        root = eco.get("root") or "."
        if root != ".":
            scope = [f"{root.rstrip('/')}/{s}" if not s.startswith(root) else s for s in scope]
            # simpler: prefix
            scope = [f"{root}/{s}" if "**" in s or s.endswith("/**") else f"{root}/{s}" for s in ad.get("default_scope") or []]
        stacks.append(
            {
                "name": name if len(digest.get("detected_ecosystems") or []) > 1 or i == 0 else f"{name}{i}",
                "adapter": aid,
                "scope": scope if root == "." else [f"{root}/{p}" for p in (ad.get("default_scope") or [])],
                "root": root,
                "languages": (
                    [{"name": "php", "version": "8.x"}]
                    if aid == "php-laravel"
                    else [{"name": "python", "version": "3.x"}]
                ),
                "frameworks": (
                    [{"name": "laravel", "version": "detected"}]
                    if aid == "php-laravel"
                    else []
                ),
                "architecture": {"style": "detected", "layers": []},
                "testing": defaults.get("testing") or {},
                "quality": defaults.get("quality") or {},
                "worktree": defaults.get("worktree") or {},
            }
        )
    # unique names
    used = set()
    for st in stacks:
        base = st["name"]
        n = base
        i = 2
        while n in used:
            n = f"{base}{i}"
            i += 1
        st["name"] = n
        used.add(n)

    return {
        "version": 1,
        "git": {"base_branch": "main", "commit_convention": "conventional", "pr_cli": "gh"},
        "conventions": {"notes": "Generated by kaotim detect-stack; review before commit."},
        "packages": [{"name": "default", "path": ".", "stacks": stacks}],
    }
