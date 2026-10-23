"""Path glob helpers (plan owns / ownership). Stack.yaml removed — config.yaml owns commands."""

from __future__ import annotations

import fnmatch
from typing import Any


def _norm(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def file_matches_scope(file_path: str, scope: list[str]) -> bool:
    rel = _norm(file_path)
    for pattern in scope or []:
        pat = _norm(pattern)
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat.rstrip("/**")):
            return True
        if pat.endswith("/**") and (rel.startswith(pat[:-3]) or rel + "/" == pat[:-2]):
            return True
    return False


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
