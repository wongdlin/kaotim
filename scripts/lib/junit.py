"""Parse JUnit XML into normalized test results."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def parse_junit(
    path: Path,
    runner: str,
    assertion_sigs: list[str],
    wrong_sigs: list[str],
) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {
            "runner": runner,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "failures": [
                {
                    "test": "(suite)",
                    "kind": "wrong_reason",
                    "message": "empty or missing JUnit output",
                    "file": str(path),
                    "line": 0,
                }
            ],
            "structured": False,
            "raw_path": str(path),
        }

    tree = ET.parse(path)
    root = tree.getroot()
    # root may be testsuites or testsuite
    suites = []
    if root.tag.endswith("testsuites"):
        suites = list(root)
    else:
        suites = [root]

    passed = failed = errors = skipped = 0
    failures: list[dict[str, Any]] = []

    for suite in suites:
        for case in suite.iter():
            if not case.tag.endswith("testcase"):
                continue
            name = case.attrib.get("name") or ""
            classname = case.attrib.get("classname") or ""
            test_id = f"{classname}::{name}" if classname else name
            fail_node = None
            err_node = None
            for child in list(case):
                tag = child.tag.split("}")[-1]
                if tag == "failure":
                    fail_node = child
                elif tag == "error":
                    err_node = child
                elif tag == "skipped":
                    skipped += 1
            if err_node is not None:
                errors += 1
                msg = (err_node.attrib.get("message") or "") + " " + (err_node.text or "")
                failures.append(
                    {
                        "test": test_id,
                        "kind": _kind(msg, assertion_sigs, wrong_sigs, prefer_wrong=True),
                        "message": msg.strip()[:500],
                        "file": classname,
                        "line": 0,
                    }
                )
            elif fail_node is not None:
                failed += 1
                msg = (fail_node.attrib.get("message") or "") + " " + (fail_node.text or "")
                # D12: ImportError inside failure still wrong_reason
                failures.append(
                    {
                        "test": test_id,
                        "kind": _kind(msg, assertion_sigs, wrong_sigs, prefer_wrong=False),
                        "message": msg.strip()[:500],
                        "file": classname,
                        "line": 0,
                    }
                )
            else:
                passed += 1

    return {
        "runner": runner,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "failures": failures,
        "structured": True,
        "raw_path": str(path),
    }


def _kind(
    msg: str,
    assertion_sigs: list[str],
    wrong_sigs: list[str],
    prefer_wrong: bool,
) -> str:
    if any(s in msg for s in wrong_sigs):
        return "wrong_reason"
    if prefer_wrong:
        return "wrong_reason"
    if any(s in msg for s in assertion_sigs):
        return "assertion"
    return "other"


def ids_in_text(text: str, pattern: str = r"(AC|EC)-?\d+") -> set[str]:
    found = set()
    for m in re.finditer(pattern, text, re.IGNORECASE):
        raw = m.group(0).upper().replace("_", "-")
        raw = re.sub(r"(AC|EC)(\d+)", r"\1-\2", raw)
        if "-" not in raw[2:]:
            raw = raw[:2] + "-" + raw[2:]
        found.add(raw)
    return found
