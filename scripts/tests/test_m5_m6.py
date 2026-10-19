"""M5 ownership + M6 layers."""

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
    def test_check_layers_flags_violation(self) -> None:
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
        adapter: php-laravel
        scope: ["app/**"]
        architecture:
          style: controller-action-model
          layers:
            - {name: controller, path: "app/Http/Controllers/**", may_depend_on: [action]}
            - {name: action, path: "app/Actions/**", may_depend_on: [model]}
            - {name: model, path: "app/Models/**", may_depend_on: []}
        testing: {commands: {all: "echo"}}
""",
                encoding="utf-8",
            )
            ctrl = repo / "app" / "Http" / "Controllers"
            ctrl.mkdir(parents=True)
            # controller importing a model directly (skipping action) — also need model file
            models = repo / "app" / "Models"
            models.mkdir(parents=True)
            (models / "User.php").write_text("<?php\nnamespace App\\Models;\nclass User {}\n", encoding="utf-8")
            (ctrl / "UserController.php").write_text(
                "<?php\nnamespace App\\Http\\Controllers;\nuse App\\Models\\User;\nclass UserController {}\n",
                encoding="utf-8",
            )
            r = run_cli(["check-layers"], repo)
            self.assertEqual(r.returncode, 1, r.stdout)
            data = json.loads(r.stdout)
            self.assertTrue(data.get("violations"))

    def test_hook_denies_locked_path(self) -> None:
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
      - name: python
        adapter: python
        scope: ["tests/**"]
        testing: {commands: {all: "echo"}}
""",
                encoding="utf-8",
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
