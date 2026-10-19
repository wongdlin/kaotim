"""YAML load/dump via vendored yaml_lite."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_VENDOR = Path(__file__).resolve().parents[1] / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

import yaml_lite  # type: ignore  # noqa: E402


def load_yaml_text(text: str) -> Any:
    return yaml_lite.load(text)


def load_yaml_file(path: Path) -> Any:
    return load_yaml_text(path.read_text(encoding="utf-8"))


def dump_yaml(data: Any) -> str:
    return yaml_lite.dump(data)
