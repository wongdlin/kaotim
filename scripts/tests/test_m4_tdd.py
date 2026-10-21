"""M4: junit parse, verify-red heuristics, locks."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "kaotim.py"
sys.path.insert(0, str(ROOT / "scripts"))

from lib.junit import parse_junit  # noqa: E402


def run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo", str(cwd), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


JUNIT_ASSERT = """<?xml version="1.0"?>
<testsuites>
  <testsuite name="x" tests="1" failures="1" errors="0">
    <testcase name="AC-1 rejects fourth" classname="Tests\\\\Feature\\\\Rate">
      <failure message="Failed asserting that 200 matches expected 429."/>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_IMPORT = """<?xml version="1.0"?>
<testsuites>
  <testsuite name="x" tests="1" failures="1" errors="0">
    <testcase name="AC-1" classname="t">
      <failure message="ImportError: No module named missing"/>
    </testcase>
  </testsuite>
</testsuites>
"""


class M4Tests(unittest.TestCase):
    def test_junit_assertion_vs_wrong(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.xml"
            p.write_text(JUNIT_ASSERT, encoding="utf-8")
            r = parse_junit(
                p,
                "pest",
                ["Failed asserting"],
                ["ImportError", "Class "],
            )
            self.assertEqual(r["failed"], 1)
            self.assertEqual(r["failures"][0]["kind"], "assertion")
            p.write_text(JUNIT_IMPORT, encoding="utf-8")
            r2 = parse_junit(p, "pytest", ["AssertionError"], ["ImportError"])
            self.assertEqual(r2["failures"][0]["kind"], "wrong_reason")

    def test_empty_junit_wrong_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.xml"
            p.write_text("", encoding="utf-8")
            r = parse_junit(p, "pest", [], [])
            self.assertEqual(r["failures"][0]["kind"], "wrong_reason")

    def test_lock_detects_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "stack.yaml").write_text(
                """version: 1
packages:
  - name: default
    path: "."
    stacks:
      - name: backend
        adapter: python
        scope: ["tests/**"]
        testing: {commands: {all: "echo"}}
""",
                encoding="utf-8",
            )
            tests = repo / "tests"
            tests.mkdir()
            tf = tests / "test_x.py"
            tf.write_text("def test_ac1():\n    assert False\n", encoding="utf-8")
            run_cli(["state", "init"], repo)
            run_cli(
                [
                    "state",
                    "set",
                    "--json",
                    json.dumps({"tasks": {"T1": {"status": "red", "owns": ["tests/**"]}}}),
                ],
                repo,
            )
            r = run_cli(["lock-tests", "--task", "T1", "--files", "tests/test_x.py"], repo)
            self.assertEqual(r.returncode, 0, r.stdout)
            ok = run_cli(["verify-lock", "--task", "T1"], repo)
            self.assertEqual(ok.returncode, 0)
            tf.write_text("def test_ac1():\n    assert True\n", encoding="utf-8")
            bad = run_cli(["verify-lock", "--task", "T1"], repo)
            self.assertEqual(bad.returncode, 1)

    def test_next_stage_requires_tests_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "stack.yaml").write_text(
                """version: 1
packages:
  - name: default
    path: "."
    stacks:
      - name: backend
        adapter: python
        scope: ["tests/**"]
        testing: {commands: {all: "echo"}}
""",
                encoding="utf-8",
            )
            (kd / "project-profile.md").write_text("# profile\n", encoding="utf-8")
            run_cli(["state", "init"], repo)
            run_cli(
                [
                    "state",
                    "set",
                    "--json",
                    json.dumps(
                        {
                            "stage": "tdd_red",
                            "tasks": {
                                "T1": {
                                    "status": "red",
                                    "owns": ["tests/**"],
                                    "red_verified": True,
                                    "test_lock": {"files": {"tests/test_x.py": "sha256:abc"}},
                                }
                            },
                        }
                    ),
                ],
                repo,
            )
            blocked = run_cli(["next-stage"], repo)
            self.assertEqual(blocked.returncode, 1, blocked.stdout)
            self.assertIn("approvals.tests", blocked.stdout)
            run_cli(
                [
                    "state",
                    "set",
                    "--json",
                    json.dumps({"approvals": {"tests": "2026-10-21T00:00:00Z"}}),
                ],
                repo,
            )
            ok = run_cli(["next-stage"], repo)
            self.assertEqual(ok.returncode, 0, ok.stdout)
            self.assertEqual(json.loads(ok.stdout)["stage"], "tdd_green")

    def test_next_stage_skips_tests_approval_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "stack.yaml").write_text(
                """version: 1
packages:
  - name: default
    path: "."
    stacks:
      - name: backend
        adapter: python
        scope: ["tests/**"]
        testing: {commands: {all: "echo"}}
""",
                encoding="utf-8",
            )
            (kd / "config.yaml").write_text(
                "approvals:\n  require_tests: false\n",
                encoding="utf-8",
            )
            (kd / "project-profile.md").write_text("# profile\n", encoding="utf-8")
            run_cli(["state", "init"], repo)
            run_cli(
                [
                    "state",
                    "set",
                    "--json",
                    json.dumps(
                        {
                            "stage": "tdd_red",
                            "tasks": {
                                "T1": {
                                    "status": "red",
                                    "owns": ["tests/**"],
                                    "red_verified": True,
                                    "test_lock": {"files": {"tests/test_x.py": "sha256:abc"}},
                                }
                            },
                        }
                    ),
                ],
                repo,
            )
            ok = run_cli(["next-stage"], repo)
            self.assertEqual(ok.returncode, 0, ok.stdout)
            self.assertEqual(json.loads(ok.stdout)["stage"], "tdd_green")


if __name__ == "__main__":
    unittest.main()
