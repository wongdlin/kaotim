"""Simulated hook payloads -> block/allow decisions (spec §18 'Hooks')."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spike_hook  # noqa: E402


class DecideTest(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project, ".kaotim-spike"))
        with open(os.path.join(self.project, ".kaotim-spike", "locked.txt"), "w") as fh:
            fh.write("tests/Unit/CountWordsTest.php\n")

    def test_write_to_locked_test_is_denied(self):
        payload = {"tool_name": "Write", "cwd": self.project,
                   "tool_input": {"path": "tests/Unit/CountWordsTest.php"}}
        self.assertEqual(spike_hook.decide("preToolUse", payload, self.project)["permission"], "deny")

    def test_absolute_path_to_locked_test_is_denied(self):
        path = os.path.join(self.project, "tests/Unit/CountWordsTest.php")
        payload = {"tool_name": "Write", "tool_input": {"file_path": path}}
        self.assertEqual(spike_hook.decide("preToolUse", payload, self.project)["permission"], "deny")

    def test_write_elsewhere_is_allowed(self):
        payload = {"tool_name": "Write", "tool_input": {"path": "app/Actions/CountWords.php"}}
        self.assertEqual(spike_hook.decide("preToolUse", payload, self.project)["permission"], "allow")

    def test_destructive_artisan_is_denied(self):
        payload = {"command": "php artisan migrate:fresh --seed"}
        self.assertEqual(spike_hook.decide("beforeShellExecution", payload, self.project)["permission"], "deny")

    def test_safe_shell_is_allowed(self):
        payload = {"command": "php artisan test"}
        self.assertEqual(spike_hook.decide("beforeShellExecution", payload, self.project)["permission"], "allow")

    def test_observational_events_return_empty_object(self):
        self.assertEqual(spike_hook.decide("afterFileEdit", {}, self.project), {})

    def test_cli_round_trip_logs_and_prints_valid_json(self):
        env = dict(os.environ, CURSOR_PROJECT_DIR=self.project, CURSOR_PLUGIN_ROOT=os.path.dirname(HERE))
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "spike_hook.py"), "beforeShellExecution"],
            input=json.dumps({"command": "php artisan db:wipe"}), capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["permission"], "deny")
        with open(os.path.join(self.project, ".kaotim-spike", "hooks.jsonl")) as fh:
            self.assertEqual(json.loads(fh.readline())["event"], "beforeShellExecution")


if __name__ == "__main__":
    unittest.main()
