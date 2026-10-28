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


    def test_init_gitignores_whole_kaotim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            r = run_cli(["init", "--force"], repo)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            gi = (repo / ".gitignore").read_text(encoding="utf-8")
            lines = [ln.strip() for ln in gi.splitlines() if ln.strip() and not ln.strip().startswith("#")]
            self.assertIn(".kaotim/", lines)
            # Selective runtime paths must not be added anymore.
            for old in (
                ".kaotim/handoffs/",
                ".kaotim/gates/",
                ".kaotim/worktrees/",
                ".kaotim/plans/",
                ".kaotim/metrics/*.jsonl",
                ".kaotim/state.json",
            ):
                self.assertNotIn(old, lines)

    def test_init_gitignore_idempotent_and_keeps_old_selective(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".gitignore").write_text(
                ".kaotim/handoffs/\n.kaotim/worktrees/\n", encoding="utf-8"
            )
            r1 = run_cli(["init", "--force"], repo)
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            gi1 = (repo / ".gitignore").read_text(encoding="utf-8")
            self.assertIn(".kaotim/handoffs/", gi1)
            self.assertIn(".kaotim/worktrees/", gi1)
            whole = [ln.strip() for ln in gi1.splitlines() if ln.strip() in {".kaotim/", ".kaotim"}]
            self.assertEqual(len(whole), 1, gi1)
            # Second init must not duplicate `.kaotim/`.
            r2 = run_cli(["init", "--force"], repo)
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            gi2 = (repo / ".gitignore").read_text(encoding="utf-8")
            self.assertEqual(gi1, gi2)

    def test_refresh_proposes_whole_kaotim_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "config.yaml").write_text("commands:\n  test: npm test\n", encoding="utf-8")
            (kd / "project-profile.md").write_text("# profile\n", encoding="utf-8")
            (repo / ".gitignore").write_text(".kaotim/handoffs/\n", encoding="utf-8")
            r = run_cli(["refresh"], repo)
            self.assertEqual(r.returncode, 0, r.stdout)
            proposals = json.loads(r.stdout)["proposals"]
            gi_props = [p for p in proposals if p.get("file") == ".gitignore"]
            self.assertEqual(len(gi_props), 1)
            self.assertEqual(gi_props[0].get("action"), "add")
            self.assertIn(".kaotim/", gi_props[0].get("note", ""))

    def test_refresh_skips_gitignore_when_whole_kaotim_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "config.yaml").write_text("commands:\n  test: npm test\n", encoding="utf-8")
            (kd / "project-profile.md").write_text("# profile\n", encoding="utf-8")
            (repo / ".gitignore").write_text(".kaotim/\n", encoding="utf-8")
            r = run_cli(["refresh"], repo)
            self.assertEqual(r.returncode, 0, r.stdout)
            proposals = json.loads(r.stdout)["proposals"]
            self.assertFalse(any(p.get("file") == ".gitignore" for p in proposals))


if __name__ == "__main__":
    unittest.main()
