"""M1 acceptance: state, handoff, metrics, get-package, adapter, exit codes."""

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
        # minimal stack
        stack = """version: 1
git: {base_branch: main, commit_convention: conventional, pr_cli: none}
packages:
  - name: default
    path: "."
    stacks:
      - name: backend
        adapter: php-laravel
        scope: ["app/**", "tests/**"]
        root: "."
        testing:
          framework: pest
          commands: {all: "echo ok", single: "echo ok", affected: "echo ok"}
        quality: {lint: "", typecheck: "", build: ""}
"""
        (self.repo / ".kaotim" / "stack.yaml").write_text(stack, encoding="utf-8")

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

    def test_get_package(self) -> None:
        r = run_cli(["get-package"], self.repo)
        self.assertEqual(r.returncode, 0, r.stdout)
        pkg = json.loads(r.stdout)["package"]
        self.assertEqual(pkg["name"], "default")
        self.assertEqual(len(pkg["stacks"]), 1)

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
            json.loads(line)  # must be valid JSONL

    def test_adapter_list_and_validate(self) -> None:
        r = run_cli(["adapter", "list"], self.repo)
        self.assertEqual(r.returncode, 0)
        ids = {a["id"] for a in json.loads(r.stdout)["adapters"]}
        self.assertIn("php-laravel", ids)
        self.assertIn("python", ids)
        decl = self.repo / "decl.yaml"
        decl.write_text(
            """adapter_version: 1
id: js-ts
detect: {manifests: ["package.json"]}
capabilities: {verify_red: text, check_layers: approximate}
tests:
  assertion_signatures: ["AssertionError"]
  wrong_reason_signatures: ["Cannot find module"]
  id_pattern: "(AC|EC)-\\\\d+"
""",
            encoding="utf-8",
        )
        v = run_cli(["adapter", "validate", "--file", str(decl)], self.repo)
        self.assertEqual(v.returncode, 0, v.stdout)

    def test_trim_and_exit_codes(self) -> None:
        r = run_cli(["trim-output"], self.repo, input_text="ok\nFAIL something\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("FAIL", json.loads(r.stdout)["text"])


if __name__ == "__main__":
    unittest.main()
