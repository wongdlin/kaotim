"""M2: detect-stack on fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "kaotim.py"
FIX = ROOT / "fixtures"


def run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo", str(cwd), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class M2Tests(unittest.TestCase):
    def test_detect_laravel(self) -> None:
        r = run_cli(["detect-stack"], FIX / "laravel-app")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        digest = json.loads(r.stdout)["digest"]
        adapters = {e.get("adapter") for e in digest["detected_ecosystems"]}
        self.assertIn("php-laravel", adapters)
        self.assertLessEqual(digest.get("approx_tokens", 0), 2000)

    def test_detect_python(self) -> None:
        r = run_cli(["detect-stack"], FIX / "python-app")
        self.assertEqual(r.returncode, 0, r.stdout)
        adapters = {
            e.get("adapter") for e in json.loads(r.stdout)["digest"]["detected_ecosystems"]
        }
        self.assertIn("python", adapters)

    def test_validate_rejects_two_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            kd = repo / ".kaotim"
            kd.mkdir()
            (kd / "stack.yaml").write_text(
                """version: 1
packages:
  - name: a
    path: "."
    stacks:
      - name: backend
        adapter: python
        scope: ["src/**"]
        testing: {commands: {all: "echo"}}
  - name: b
    path: "other"
    stacks:
      - name: backend
        adapter: python
        scope: ["other/**"]
        testing: {commands: {all: "echo"}}
""",
                encoding="utf-8",
            )
            r = run_cli(["validate-stack"], repo)
            self.assertEqual(r.returncode, 1)
            self.assertIn("v2", json.loads(r.stdout)["summary"].lower() + str(json.loads(r.stdout)))

    def test_init_writes_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            # copy minimal pyproject signal
            (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            (repo / "tests").mkdir()
            r = run_cli(["init", "--force"], repo)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((repo / ".kaotim" / "project-profile.md").exists())
            self.assertTrue((repo / ".kaotim" / "bin" / "kaotim.py").exists())


if __name__ == "__main__":
    unittest.main()
