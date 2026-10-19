"""Handoff schema validation and optional save."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io_util import atomic_write_json, estimate_tokens
from .paths import ensure_kaotim_dirs

REQUIRED = {"agent", "task", "attempt", "status", "summary"}
STATUSES = {"done", "blocked", "failed"}
MAX_SUMMARY_CHARS = 1200  # ~300 tokens


def validate_handoff(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["handoff must be an object"]
    for key in REQUIRED:
        if key not in data:
            errors.append(f"missing field: {key}")
    status = data.get("status")
    if status and status not in STATUSES:
        errors.append(f"invalid status: {status}")
    summary = data.get("summary") or ""
    if isinstance(summary, str) and len(summary) > MAX_SUMMARY_CHARS:
        errors.append(
            f"summary exceeds {MAX_SUMMARY_CHARS} characters (~300 tokens); got {len(summary)}"
        )
    if isinstance(summary, str) and estimate_tokens(summary) > 300:
        errors.append(f"summary exceeds 300 tokens (est {estimate_tokens(summary)})")
    if status == "blocked" and not data.get("question"):
        errors.append("blocked handoff requires question")
    findings = data.get("findings")
    if findings is not None and not isinstance(findings, list):
        errors.append("findings must be a list")
    return errors


def check_handoff_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "errors": [str(exc)], "handoff": None}
    errors = validate_handoff(data)
    return {"ok": not errors, "errors": errors, "handoff": data}


def save_handoff(data: dict[str, Any], repo: Path | None = None, filename: str | None = None) -> Path:
    errors = validate_handoff(data)
    if errors:
        raise ValueError("; ".join(errors))
    root = ensure_kaotim_dirs(repo)
    name = filename or f"{data.get('task') or 'stage'}-{data.get('agent')}-{data.get('attempt')}.json"
    path = root / "handoffs" / name
    atomic_write_json(path, data)
    return path
