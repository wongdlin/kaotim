"""check-layers: import parsing vs architecture.layers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .stack import get_package, load_stack


def _layer_for_path(path: str, layers: list[dict[str, Any]]) -> str | None:
    from .stack import file_matches_scope

    for layer in layers:
        pat = layer.get("path") or ""
        if file_matches_scope(path, [pat]):
            return layer.get("name")
    return None


def _php_imports(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*use\s+([^;]+);", text, re.M)]


def _py_imports(text: str) -> list[str]:
    out = []
    for m in re.finditer(r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))", text, re.M):
        out.append(m.group(1) or m.group(2))
    return out


def check_layers(repo: Path) -> dict[str, Any]:
    stack = load_stack(repo)
    if not stack:
        return {"ok": False, "errors": ["stack.yaml missing"], "violations": []}
    pkg = get_package(repo)
    violations = []
    unsupported = []
    for st in pkg.get("stacks") or []:
        layers = (st.get("architecture") or {}).get("layers") or []
        if not layers:
            continue
        adapter = st.get("adapter") or ""
        scope = st.get("scope") or []
        # scan files under repo matching scope roughly
        for path in repo.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(repo)).replace("\\", "/")
            if rel.startswith(".kaotim/") or "/vendor/" in rel or "/node_modules/" in rel:
                continue
            from .stack import file_matches_scope

            if not file_matches_scope(rel, scope):
                continue
            src_layer = _layer_for_path(rel, layers)
            if not src_layer:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "php" in adapter or rel.endswith(".php"):
                imports = _php_imports(text)
                lang = "php"
            elif "python" in adapter or rel.endswith(".py"):
                imports = _py_imports(text)
                lang = "python"
            else:
                unsupported.append(rel)
                continue
            may = []
            for layer in layers:
                if layer.get("name") == src_layer:
                    may = layer.get("may_depend_on") or []
                    break
            for imp in imports:
                # map import to a file heuristically
                target_rel = _resolve_import(imp, lang, repo)
                if not target_rel:
                    continue
                tgt_layer = _layer_for_path(target_rel, layers)
                if tgt_layer and tgt_layer != src_layer and tgt_layer not in may:
                    violations.append(
                        {
                            "file": rel,
                            "layer": src_layer,
                            "import": imp,
                            "target_layer": tgt_layer,
                            "allowed": may,
                        }
                    )
    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "unsupported": unsupported[:20],
        "errors": [],
    }


def _resolve_import(imp: str, lang: str, repo: Path) -> str | None:
    if lang == "php":
        # App\Http\Controllers\X -> app/Http/Controllers/X.php
        if imp.startswith("App\\"):
            rel = "app/" + imp[4:].replace("\\", "/") + ".php"
            if (repo / rel).exists():
                return rel
    if lang == "python":
        # app.services.words -> src/app/services/words.py or app/services/words.py
        parts = imp.replace(".", "/")
        for cand in (f"src/{parts}.py", f"{parts}.py", f"src/{parts}/__init__.py"):
            if (repo / cand).exists():
                return cand
    return None
