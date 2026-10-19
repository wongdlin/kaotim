"""Load and merge config.defaults.yaml with .kaotim/config.yaml."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .paths import kaotim_dir, plugin_root
from .yaml_util import load_yaml_file


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
