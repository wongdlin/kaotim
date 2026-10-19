"""M3: check-plan and next-stage recon→plan_approved."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "kaotim.py"


def run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo", str(cwd), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


GOOD_PLAN = """---
id: PLAN-001
title: demo
status: draft
package: default
created: 2026-10-19
fast_lane: false
---

## 1. Purpose
- **What:** demo
- **Why now:** test
- **Expected outcome:** ok

## 2. Scope
- **In:** x
- **Non-goals:** y

## 3. Acceptance criteria
| ID | Criterion | Task |
|---|---|---|
| AC-1 | works | T1 |

## 4. Edge cases
| ID | Scenario | Options | Decision | Task |
|---|---|---|---|---|
| EC-1 | empty | A / B | A | T1 |

## 5. Architecture
- **Comparison required:** no
- **Chosen:** simple
- **Rejected:**
- **Contracts:**

## 6. Tasks
### T1: impl
- Depends on: none
- Owns files: app/Actions/**
- Covers: AC-1, EC-1
- Reuse: none

## 7. Risks and rollout
- none

## 8. Decision log
- chose simple

## 9. Open questions
- None
"""


class M3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        kd = self.repo / ".kaotim"
        kd.mkdir()
        (kd / "stack.yaml").write_text(
            """version: 1
packages:
  - name: default
    path: "."
    stacks:
      - name: backend
        adapter: php-laravel
        scope: ["app/**", "tests/**"]
        root: "."
        testing: {commands: {all: "echo"}}
        quality: {}
""",
            encoding="utf-8",
        )
        (kd / "project-profile.md").write_text("# profile\n", encoding="utf-8")
        (kd / "plan.md").write_text(GOOD_PLAN, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_check_plan_ok(self) -> None:
        r = run_cli(["check-plan"], self.repo)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_check_plan_missing_decision(self) -> None:
        bad = GOOD_PLAN.replace("| A | T1 |", "| TBD | T1 |")
        (self.repo / ".kaotim" / "plan.md").write_text(bad, encoding="utf-8")
        r = run_cli(["check-plan"], self.repo)
        self.assertEqual(r.returncode, 1)

    def test_next_stage_requires_approval(self) -> None:
        run_cli(["state", "init"], self.repo)
        # recon -> need stack+profile (have them)
        r = run_cli(["next-stage"], self.repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(json.loads(r.stdout)["stage"], "plan")
        # plan -> plan_approved needs approval
        blocked = run_cli(["next-stage"], self.repo)
        self.assertEqual(blocked.returncode, 1)
        run_cli(
            ["state", "set", "--json", json.dumps({"approvals": {"plan": "2026-10-19T00:00:00Z"}})],
            self.repo,
        )
        ok = run_cli(["next-stage"], self.repo)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertEqual(json.loads(ok.stdout)["stage"], "plan_approved")


if __name__ == "__main__":
    unittest.main()
