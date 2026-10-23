"""Stage-guard must not auto-continue agents (subagent hang regression)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "kaotim.py"


def run_hook(name: str, payload: dict, cwd: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(CLI), "--repo", str(cwd), "hook", name],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout or "{}")


class StageGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        kd = self.repo / ".kaotim"
        kd.mkdir()
        subprocess.run(
            [sys.executable, str(CLI), "--repo", str(self.repo), "state", "init"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        # Typical mid-pipeline: in_progress during tdd_red (historically triggered hang)
        subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--repo",
                str(self.repo),
                "state",
                "set",
                "--json",
                json.dumps({"stage": "tdd_red", "stage_status": "in_progress"}),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_stop_never_emits_followup(self) -> None:
        decision = run_hook(
            "stop",
            {"status": "completed", "loop_count": 0},
            self.repo,
        )
        self.assertNotIn("followup_message", decision)
        self.assertEqual(decision, {})

    def test_stop_empty_while_awaiting_specialist(self) -> None:
        subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--repo",
                str(self.repo),
                "state",
                "set",
                "--json",
                json.dumps({"stage_status": "awaiting_specialist"}),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        decision = run_hook("stop", {"status": "completed", "loop_count": 0}, self.repo)
        self.assertEqual(decision, {})

    def test_subagent_stop_never_emits_followup(self) -> None:
        decision = run_hook(
            "subagentStop",
            {
                "status": "completed",
                "subagent_type": "test-writer",
                "loop_count": 0,
                "summary": "wrote tests",
            },
            self.repo,
        )
        self.assertNotIn("followup_message", decision)
        self.assertEqual(decision, {})


if __name__ == "__main__":
    unittest.main()
