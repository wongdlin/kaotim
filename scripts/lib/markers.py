"""Marker-delimited merge for generated blocks."""

from __future__ import annotations

import re

START = "<!-- kaotim:generated:start:{name} -->"
END = "<!-- kaotim:generated:end:{name} -->"


def merge_marked(existing: str, name: str, generated: str) -> str:
    start = START.format(name=name)
    end = END.format(name=name)
    block = f"{start}\n{generated.rstrip()}\n{end}"
    pat = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    if pat.search(existing):
        return pat.sub(block, existing)
    if existing.strip():
        return existing.rstrip() + "\n\n" + block + "\n"
    return block + "\n"


def extract_marked(text: str, name: str) -> str | None:
    start = START.format(name=name)
    end = END.format(name=name)
    pat = re.compile(
        re.escape(start) + r"(.*?)" + re.escape(end),
        re.DOTALL,
    )
    m = pat.search(text)
    return m.group(1).strip() if m else None
