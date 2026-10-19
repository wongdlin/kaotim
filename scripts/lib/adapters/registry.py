"""Built-in and declarative adapter registry."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

VALID_CAP_VERIFY_RED = {"structured", "text", "none"}
VALID_CAP_LAYERS = {"approximate", "none", "full"}

PHP_LARAVEL: dict[str, Any] = {
    "adapter_version": 1,
    "id": "php-laravel",
    "kind": "builtin",
    "detect": {
        "manifests": ["composer.json"],
        "any_dependency": ["laravel/framework"],
        "files": ["artisan"],
    },
    "default_scope": [
        "app/**",
        "routes/**",
        "database/**",
        "config/**",
        "tests/**",
        "bootstrap/**",
    ],
    "tests": {
        "results": {
            "format": "junit",
            "flag": "--log-junit={path}",
        },
        "assertion_signatures": [
            "Failed asserting that",
            "Failed asserting",
            "ExpectationFailedException",
        ],
        "wrong_reason_signatures": [
            'Class "',
            "Call to undefined method",
            "Call to undefined function",
            "syntax error, unexpected",
            "Target class [",
            "Undefined constant",
            "Unable to locate factory",
            "no such table",
            "Route [",
            "not found",
        ],
        "id_pattern": r"(AC|EC)-?\d+",
        "affected": {"strategy": "mirror", "native": ""},
    },
    "imports": {
        "regex": r"^\s*use\s+([^;]+);",
        "resolve": "psr4",
    },
    "checklists": {
        "bug": [
            "mass assignment / $fillable",
            "missing authorization",
            "SQL injection via raw",
            "N+1 queries",
        ],
        "dynamic_usage": ["string-based class references", "config()->get dynamic keys"],
    },
    "capabilities": {"verify_red": "structured", "check_layers": "full"},
    "defaults": {
        "testing": {
            "framework": "pest",
            "location": "mirrored",
            "naming": "*Test.php",
            "commands": {
                "all": "php artisan test",
                "single": "php artisan test {file}",
                "affected": "php artisan test {files}",
            },
        },
        "quality": {
            "lint": "vendor/bin/pint --test",
            "typecheck": "vendor/bin/phpstan analyse",
            "build": "",
            "deadcode": "",
        },
        "worktree": {"setup": "composer install --no-interaction --prefer-dist"},
    },
}

PYTHON: dict[str, Any] = {
    "adapter_version": 1,
    "id": "python",
    "kind": "builtin",
    "detect": {
        "manifests": ["pyproject.toml", "requirements.txt", "Pipfile"],
        "any_dependency": ["pytest", "django", "fastapi", "flask"],
        "files": [],
    },
    "default_scope": ["src/**", "tests/**", "app/**"],
    "tests": {
        "results": {
            "format": "junit",
            "flag": "--junitxml={path}",
        },
        "assertion_signatures": [
            "AssertionError",
            "assert ",
            "DID NOT RAISE",
        ],
        "wrong_reason_signatures": [
            "ModuleNotFoundError",
            "ImportError",
            "SyntaxError",
            "IndentationError",
            "NameError",
            "AttributeError: module",
            "fixture '",
            "ERROR collecting",
            "unexpected keyword argument",
        ],
        "id_pattern": r"(AC|EC)-?\d+",
        "affected": {"strategy": "mirror", "native": ""},
    },
    "imports": {
        "regex": r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))",
        "resolve": "relative",
    },
    "checklists": {
        "bug": [
            "bare except",
            "mutable default argument",
            "unclosed resource",
            "path traversal",
        ],
        "dynamic_usage": ["importlib", "getattr string names", "__import__"],
    },
    "capabilities": {"verify_red": "structured", "check_layers": "full"},
    "defaults": {
        "testing": {
            "framework": "pytest",
            "location": "mirrored",
            "naming": "test_*.py",
            "commands": {
                "all": "uv run pytest",
                "single": "uv run pytest {file}",
                "affected": "uv run pytest {files}",
            },
        },
        "quality": {
            "lint": "uv run ruff check .",
            "typecheck": "uv run mypy .",
            "build": "",
            "deadcode": "",
        },
        "worktree": {"setup": "uv sync"},
    },
}

_BUILTINS = {
    "php-laravel": PHP_LARAVEL,
    "python": PYTHON,
}


def builtin_adapters() -> dict[str, dict[str, Any]]:
    return {k: deepcopy(v) for k, v in _BUILTINS.items()}


def list_adapters(extra_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    items = []
    for ad in builtin_adapters().values():
        items.append(
            {
                "id": ad["id"],
                "kind": "builtin",
                "capabilities": ad.get("capabilities"),
            }
        )
    for d in extra_dirs or []:
        if not d.exists():
            continue
        for path in sorted(d.glob("*.yaml")):
            items.append({"id": path.stem, "kind": "declarative", "path": str(path)})
    return items


def get_adapter(adapter_id: str, search_dirs: list[Path] | None = None) -> dict[str, Any]:
    if adapter_id.startswith("generated:"):
        adapter_id = adapter_id.split(":", 1)[1]
    if adapter_id in _BUILTINS:
        return deepcopy(_BUILTINS[adapter_id])
    for d in search_dirs or []:
        path = d / f"{adapter_id}.yaml"
        if path.exists():
            from ..yaml_util import load_yaml_file

            data = load_yaml_file(path)
            if isinstance(data, dict):
                data = deepcopy(data)
                data["kind"] = "declarative"
                data["path"] = str(path)
                return data
    raise KeyError(f"unknown adapter: {adapter_id}")


def validate_declarative(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["adapter must be a mapping"]
    if data.get("adapter_version") != 1:
        errors.append("adapter_version must be 1")
    if not data.get("id"):
        errors.append("id is required")
    detect = data.get("detect")
    if not isinstance(detect, dict):
        errors.append("detect must be a mapping")
    caps = data.get("capabilities") or {}
    if caps.get("verify_red") not in VALID_CAP_VERIFY_RED:
        errors.append(f"capabilities.verify_red must be one of {sorted(VALID_CAP_VERIFY_RED)}")
    if caps.get("check_layers") not in VALID_CAP_LAYERS and caps.get("check_layers") is not None:
        errors.append(f"capabilities.check_layers must be one of {sorted(VALID_CAP_LAYERS)}")
    tests = data.get("tests") or {}
    for key in ("assertion_signatures", "wrong_reason_signatures"):
        sigs = tests.get(key)
        if sigs is not None and not isinstance(sigs, list):
            errors.append(f"tests.{key} must be a list")
    # compile id_pattern if present
    import re

    pat = (tests.get("id_pattern") if isinstance(tests, dict) else None) or ""
    if pat:
        try:
            re.compile(pat)
        except re.error as exc:
            errors.append(f"invalid id_pattern: {exc}")
    imports = data.get("imports") or {}
    if imports.get("regex"):
        try:
            re.compile(imports["regex"])
        except re.error as exc:
            errors.append(f"invalid imports.regex: {exc}")
    return errors


def test_signatures(adapter: dict[str, Any], lines: list[str]) -> dict[str, Any]:
    """Classify sample lines against assertion/wrong_reason signatures."""
    tests = adapter.get("tests") or {}
    assertion = tests.get("assertion_signatures") or []
    wrong = tests.get("wrong_reason_signatures") or []
    results = []
    for line in lines:
        kind = "other"
        if any(s in line for s in wrong):
            kind = "wrong_reason"
        elif any(s in line for s in assertion):
            kind = "assertion"
        results.append({"line": line, "kind": kind})
    return {"results": results}
