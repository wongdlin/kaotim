"""Run completion: archive plan, clear state for next feature."""

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


CONFIG = """git: {pr_cli: none}
commands:
  test: "echo ok"
"""

PLAN = """---
id: PLAN-042
title: demo feature
status: approved
---
## 1. Goal
- **Done when:** shipped
"""


class CompleteRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        kd = self.repo / ".kaotim"
        kd.mkdir()
        (kd / "config.yaml").write_text(CONFIG, encoding="utf-8")
        (kd / "plan.md").write_text(PLAN, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_state_complete_archives_and_clears(self) -> None:
        kd = self.repo / ".kaotim"
        run_cli(["state", "init", "--plan-id", "PLAN-042"], self.repo)
        (kd / "handoffs").mkdir(exist_ok=True)
        (kd / "gates").mkdir(exist_ok=True)
        (kd / "handoffs" / "x.json").write_text("{}", encoding="utf-8")
        (kd / "gates" / "y.json").write_text("{}", encoding="utf-8")

        r = run_cli(["state", "complete"], self.repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["plan_id"], "PLAN-042")
        self.assertFalse((kd / "state.json").exists())
        self.assertFalse((kd / "plan.md").exists())
        archived = kd / "plans" / "PLAN-042.md"
        self.assertTrue(archived.exists())
        text = archived.read_text(encoding="utf-8")
        self.assertIn("status: completed", text)
        self.assertFalse(any((kd / "handoffs").iterdir()))
        self.assertFalse(any((kd / "gates").iterdir()))

        # next feature: init without --force
        again = run_cli(["state", "init", "--plan-id", "PLAN-043"], self.repo)
        self.assertEqual(again.returncode, 0, again.stdout)

    def test_next_stage_final_gate_completes_without_pr(self) -> None:
        """Completion is before PR; pr_created is not required."""
        kd = self.repo / ".kaotim"
        run_cli(["state", "init", "--plan-id", "PLAN-042"], self.repo)
        run_cli(
            [
                "state",
                "set",
                "--json",
                json.dumps(
                    {
                        "stage": "final_gate",
                        "approvals": {"pr": "2026-10-23T00:00:00Z"},
                        "gates": {"last_run": {"ok": True}},
                    }
                ),
            ],
            self.repo,
        )
        r = run_cli(["next-stage"], self.repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("advanced"))
        self.assertTrue(data.get("completed"))
        self.assertEqual(data.get("stage"), "done")
        self.assertFalse((kd / "state.json").exists())
        self.assertTrue((kd / "plans" / "PLAN-042.md").exists())

    def test_legacy_pr_stage_completes_without_pr_created(self) -> None:
        kd = self.repo / ".kaotim"
        run_cli(["state", "init", "--plan-id", "PLAN-042"], self.repo)
        run_cli(
            ["state", "set", "--json", json.dumps({"stage": "pr"})],
            self.repo,
        )
        r = run_cli(["next-stage"], self.repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(json.loads(r.stdout).get("completed"))
        self.assertFalse((kd / "state.json").exists())

    def test_check_plan_rejects_completed_status(self) -> None:
        kd = self.repo / ".kaotim"
        (kd / "plan.md").write_text(
            PLAN.replace("status: approved", "status: completed"),
            encoding="utf-8",
        )
        r = run_cli(["check-plan"], self.repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("completed", r.stdout.lower())


if __name__ == "__main__":
    unittest.main()
