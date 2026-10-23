"""Load and merge config.defaults.yaml with .kaotim/config.yaml."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .paths import kaotim_dir, plugin_root
from .yaml_util import load_yaml_file

# Built-in wrong-reason markers for text-mode verify-red (language-agnostic).
DEFAULT_WRONG_REASON = [
    "SyntaxError",
    "IndentationError",
    "ImportError",
    "ModuleNotFoundError",
    "Cannot find module",
    "Cannot find package",
    "error TS",
    "ParseError",
    "FATAL ERROR",
    "compilation failed",
    "compile error",
]


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def load_config(repo: Path | None = None) -> dict[str, Any]:
    defaults_path = plugin_root() / "config.defaults.yaml"
    defaults = load_yaml_file(defaults_path) if defaults_path.exists() else {}
    if not isinstance(defaults, dict):
        defaults = {}
    override_path = kaotim_dir(repo) / "config.yaml"
    if override_path.exists():
        overlay = load_yaml_file(override_path)
        if isinstance(overlay, dict):
            return _deep_merge(defaults, overlay)
    return defaults


def get_commands(repo: Path | None = None) -> dict[str, str]:
    cfg = load_config(repo)
    raw = cfg.get("commands") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v).strip() if v is not None else "" for k, v in raw.items()}


def test_command(repo: Path | None = None) -> str:
    return (get_commands(repo).get("test") or "").strip()


def has_test_command(repo: Path | None = None) -> bool:
    return bool(test_command(repo))


def wrong_reason_signatures(repo: Path | None = None) -> list[str]:
    cfg = load_config(repo)
    extra = (cfg.get("verify") or {}).get("wrong_reason_signatures") or []
    if not isinstance(extra, list):
        extra = []
    out: list[str] = []
    seen: set[str] = set()
    for s in [*DEFAULT_WRONG_REASON, *[str(x) for x in extra if x]]:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def git_settings(repo: Path | None = None) -> dict[str, Any]:
    cfg = load_config(repo)
    g = cfg.get("git") or {}
    return g if isinstance(g, dict) else {}
