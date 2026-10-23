"""M7 metrics/PR + M8 word budgets."""

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


class M7M8Tests(unittest.TestCase):
    def test_metrics_summary_and_pr_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "config.yaml").write_text(
                """git: {pr_cli: none}
commands:
  test: "echo ok"
""",
                encoding="utf-8",
            )
            (kd / "plan.md").write_text(
                """---
id: PLAN-001
title: demo feature
status: approved
---
## 3. Acceptance criteria
| ID | Criterion | Task |
|---|---|---|
| AC-1 | works | T1 |
""",
                encoding="utf-8",
            )
            run_cli(["state", "init"], repo)
            run_cli(["log-event", "run_start", "--json", '{"status":"done"}'], repo)
            run_cli(["log-event", "finding", "--json", '{"severity":"low"}'], repo)
            s = run_cli(["metrics-summary", "--run", "PLAN-001", "--trend", "2"], repo)
            self.assertEqual(s.returncode, 0, s.stdout)
            self.assertTrue((kd / "metrics" / "PLAN-001-summary.md").exists())
            pr = run_cli(["create-pr"], repo)
            self.assertEqual(pr.returncode, 0, pr.stdout)
            body = (kd / "pr.md").read_text(encoding="utf-8")
            self.assertIn("AC-1", body)
            self.assertIn("AC -> test -> status", body)

    def test_doctor_self_budgets(self) -> None:
        # run against plugin root
        r = run_cli(["doctor", "--self"], ROOT)
        data = json.loads(r.stdout)
        # may fail if agents missing early — after prompts exist should pass
        budget_checks = [c for c in data.get("checks", []) if c["name"].startswith("budget:")]
        self.assertTrue(budget_checks)
        failing = [c for c in budget_checks if not c["ok"]]
        self.assertEqual(failing, [], failing)


if __name__ == "__main__":
    unittest.main()
