"""Trim raw tool/test output to failures + short tail."""

from __future__ import annotations

FAILURE_MARKERS = (
    "FAIL",
    "FAILED",
    "ERROR",
    "Error:",
    "AssertionError",
    "Failed asserting",
    "FAILURES",
    "errors=",
)


def trim_output(text: str, max_chars: int = 2000, tail_lines: int = 20) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    interesting = [ln for ln in lines if any(m in ln for m in FAILURE_MARKERS)]
    if not interesting:
        interesting = lines[-tail_lines:]
    else:
        # keep some context: unique interesting + last tail
        seen = set()
        ordered = []
        for ln in interesting:
            if ln not in seen:
                seen.add(ln)
                ordered.append(ln)
        for ln in lines[-min(tail_lines, 10) :]:
            if ln not in seen:
                ordered.append(ln)
        interesting = ordered
    out = "\n".join(interesting)
    if len(out) > max_chars:
        out = out[: max_chars - 20] + "\n...[trimmed]..."
    return out
