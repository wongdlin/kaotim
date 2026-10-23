"""M5 ownership hooks + M6 list-rules (agent layer enforcement)."""

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


class M5M6Tests(unittest.TestCase):
    def test_list_rules_discovers_cursor_and_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".kaotim").mkdir()
            (repo / ".kaotim" / "config.yaml").write_text(
                'commands:\n  test: "echo ok"\n', encoding="utf-8"
            )
            cdir = repo / ".cursor" / "rules"
            cdir.mkdir(parents=True)
            (cdir / "arch.md").write_text("controllers may not import models\n", encoding="utf-8")
            rdir = repo / "rules"
            rdir.mkdir()
            (rdir / "layers.mdc").write_text("---\nalwaysApply: false\n---\n# layers\n", encoding="utf-8")
            r = run_cli(["list-rules"], repo)
            self.assertEqual(r.returncode, 0, r.stdout)
            data = json.loads(r.stdout)
            self.assertTrue(data["ok"])
            self.assertGreaterEqual(data["count"], 2)
            joined = " ".join(data["files"])
            self.assertIn(".cursor/rules/arch.md", joined)
            self.assertIn("rules/layers.mdc", joined)

    def test_hook_denies_locked_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "config.yaml").write_text(
                'commands:\n  test: "echo ok"\n', encoding="utf-8"
            )
            tdir = repo / "tests"
            tdir.mkdir()
            tf = tdir / "test_a.py"
            tf.write_text("assert False\n", encoding="utf-8")
            run_cli(["state", "init"], repo)
            run_cli(
                ["state", "set", "--json", json.dumps({"tasks": {"T1": {"status": "red"}}})],
                repo,
            )
            run_cli(["lock-tests", "--task", "T1", "--files", "tests/test_a.py"], repo)
            payload = json.dumps(
                {
                    "tool_name": "Write",
                    "file_path": str(tf),
                }
            )
            proc = subprocess.run(
                [sys.executable, str(CLI), "--repo", str(repo), "hook", "preToolUse"],
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=str(repo),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            decision = json.loads(proc.stdout)
            self.assertEqual(decision.get("permission"), "deny")


if __name__ == "__main__":
    unittest.main()
