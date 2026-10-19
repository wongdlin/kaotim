"""Repo and plugin path resolution."""

from __future__ import annotations

import os
from pathlib import Path


def plugin_root() -> Path:
    env = os.environ.get("CURSOR_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    # scripts/kaotim.py -> scripts -> plugin root
    return Path(__file__).resolve().parents[2]


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists() or (candidate / ".kaotim").exists():
            return candidate
        if (candidate / "composer.json").exists() or (candidate / "pyproject.toml").exists():
            # fixture / project root without .git
            if (candidate / ".kaotim").exists() or candidate.name in {
                "laravel-app",
                "laravel-app-phpunit",
                "python-app",
                "mixed",
            }:
                return candidate
    return cur


def kaotim_dir(repo: Path | None = None) -> Path:
    return (repo or find_repo_root()) / ".kaotim"


def ensure_kaotim_dirs(repo: Path | None = None) -> Path:
    root = kaotim_dir(repo)
    for name in ("handoffs", "gates", "metrics", "worktrees", "adapters", "bin"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root
