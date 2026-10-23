"""M2 (revised): init/config — stack detect removed."""

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


class M2Tests(unittest.TestCase):
    def test_detect_stack_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            r = run_cli(["detect-stack"], repo)
            self.assertNotEqual(r.returncode, 0)

    def test_init_writes_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            r = run_cli(["init", "--force"], repo)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((repo / ".kaotim" / "project-profile.md").exists())
            self.assertTrue((repo / ".kaotim" / "bin" / "kaotim.py").exists())
            self.assertTrue((repo / ".kaotim" / "config.yaml").exists())

    def test_refresh_flags_legacy_stack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "stack.yaml").write_text("version: 1\n", encoding="utf-8")
            r = run_cli(["refresh"], repo)
            self.assertEqual(r.returncode, 0, r.stdout)
            proposals = json.loads(r.stdout)["proposals"]
            actions = {p.get("file"): p.get("action") for p in proposals}
            self.assertEqual(actions.get(".kaotim/stack.yaml"), "remove")


if __name__ == "__main__":
    unittest.main()
