"""M1 acceptance: state, handoff, metrics, config, exit codes."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "kaotim.py"

CONFIG = """git: {base_branch: main, pr_cli: none}
commands:
  test: "echo ok"
  lint: ""
  typecheck: ""
  build: ""
"""


def run_cli(args: list[str], cwd: Path, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo", str(cwd), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        input=input_text,
    )


class M1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / ".kaotim").mkdir()
        (self.repo / ".kaotim" / "config.yaml").write_text(CONFIG, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_state_init_and_illegal_set(self) -> None:
        r = run_cli(["state", "init", "--plan-id", "PLAN-T"], self.repo)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        bad = run_cli(["state", "set", "--json", '{"schema": 99}'], self.repo)
        self.assertEqual(bad.returncode, 2)
        self.assertFalse(json.loads(bad.stdout)["ok"])

    def test_init_writes_config_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            r = run_cli(["init", "--force"], repo)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((repo / ".kaotim" / "config.yaml").exists())
            self.assertTrue((repo / ".kaotim" / "project-profile.md").exists())
            self.assertTrue((repo / ".kaotim" / "bin" / "kaotim.py").exists())
            self.assertFalse((repo / ".kaotim" / "stack.yaml").exists())

    def test_handoff_size_rejected(self) -> None:
        big = "x" * 1300
        payload = {
            "agent": "feature-dev",
            "task": "T1",
            "attempt": 1,
            "status": "done",
            "summary": big,
        }
        r = run_cli(["check-handoff", "--json", json.dumps(payload)], self.repo)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["ok"])

    def test_log_event_parallel(self) -> None:
        run_cli(["state", "init"], self.repo)
        errors = []

        def worker(i: int) -> None:
            rr = run_cli(
                ["log-event", "gate", "--json", json.dumps({"attempt": i, "task": "T1"})],
                self.repo,
            )
            if rr.returncode != 0:
                errors.append(rr.stdout + rr.stderr)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        metrics = list((self.repo / ".kaotim" / "metrics").glob("*.jsonl"))
        self.assertTrue(metrics)
        lines = metrics[0].read_text(encoding="utf-8").strip().splitlines()
        self.assertGreaterEqual(len(lines), 12)
        for line in lines:
            json.loads(line)

    def test_list_rules(self) -> None:
        rules = self.repo / ".cursor" / "rules"
        rules.mkdir(parents=True)
        (rules / "layers.md").write_text("# no domain in UI\n", encoding="utf-8")
        r = run_cli(["list-rules"], self.repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        self.assertIn(".cursor/rules/layers.md", data["files"])

    def test_doctor_rejects_stack_yaml(self) -> None:
        (self.repo / ".kaotim" / "stack.yaml").write_text("version: 1\n", encoding="utf-8")
        (self.repo / ".kaotim" / "project-profile.md").write_text("# p\n", encoding="utf-8")
        r = run_cli(["doctor"], self.repo)
        self.assertEqual(r.returncode, 1)
        detail = json.dumps(json.loads(r.stdout))
        self.assertIn("no-stack.yaml", detail)

    def test_trim_and_exit_codes(self) -> None:
        r = run_cli(["trim-output"], self.repo, input_text="ok\nFAIL something\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("FAIL", json.loads(r.stdout)["text"])


if __name__ == "__main__":
    unittest.main()
