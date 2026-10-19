# Kaotim M0 spike (throwaway)

Exercises the Cursor platform questions V1–V13 from the build spec (§16). Results are recorded in
[`docs/platform-findings.md`](../docs/platform-findings.md). Delete this folder after M1 starts
relying on the findings; nothing here is product code.

| Path | What it probes |
|---|---|
| `kaotim-spike/` | Minimal Cursor plugin: 4 rule types (V7), auto + explicit-only skills, a command with `$ARGUMENTS`/`$1` (V9), a `readonly` + `model: fast` agent and a writer agent (V2, V8, V4, V11), hooks on 11 events that log payloads and block a locked test file / `migrate:fresh` (V3, V6), plugin-root discovery (V5) |
| `kaotim-spike/scripts/test_spike_hook.py` | Simulated hook payloads → allow/deny (runs anywhere: `python3 -m unittest -v test_spike_hook`) |
| `run_cli_spike.sh` | Headless runtime run of the spike with the Cursor CLI (needs `agent login`) |
| `v11/worktree.sh` | Git worktrees under `.kaotim/worktrees/`, per-stack setup, merge/conflict (V11, V13) |
| `v13/laravel_red.sh`, `v13/python_red.sh` | How Pest/PHPUnit/pytest report right- vs wrong-reason reds (Appendix C.3, E.3) |
| `evidence/` | Captured outputs referenced by the findings |

## What still needs a human with Cursor (runtime items)

This box has the Cursor CLI installed but **not authenticated**, so nothing that needs a model
call could run. Please run one of the two options below and send back the results folder or
the answers to the checklist.

### Option A: headless (fastest, ~10 short agent runs)
```bash
agent login
spike/run_cli_spike.sh            # writes spike/results/<timestamp>/
```

### Option B: in the Cursor IDE
1. Copy (do not symlink) `spike/kaotim-spike` to `~/.cursor/plugins/local/kaotim-spike`.
2. Developer: Reload Window. Open **Customize**: confirm 4 rules, 2 skills, 2 agents, 1 command, hooks listed.
3. Open a throwaway git repo (for example a copy of `fixtures/laravel-app` with `composer install`).
   Create `.kaotim-spike/locked.txt` containing `tests/Unit/CountWordsTest.php`.
4. In a new Agent chat, send each prompt from `run_cli_spike.sh` (`01`…`09`) and note the result.
5. Send back `.kaotim-spike/hooks.jsonl` and `.kaotim-spike/probe.jsonl` from that repo.

### Checklist (what to record)
- [ ] V1 All components appear in Customize; plugin loads from `~/.cursor/plugins/local` (and via `--plugin-dir` in CLI).
- [ ] V2 `spike-readonly` runs on the `fast` model (task card / `subagentStart.subagent_model`).
- [ ] V3 Editing the locked test is **denied** by `preToolUse` (Write); `sed -i` via shell is **not** caught (expected); `migrate:fresh` is denied by `beforeShellExecution`.
- [ ] V3 `hooks.jsonl` shows `cwd` = plugin install dir and `CURSOR_PLUGIN_ROOT` set; `sessionEnd`/`afterShellExecution` (relative `./scripts/...` command) also ran.
- [ ] V4 Two `spike-writer` subagents ran concurrently (overlapping `subagentStart`/`subagentStop` timestamps).
- [ ] V5 `/kaotim-spike-args` output: is `CURSOR_PLUGIN_ROOT` visible in the agent shell? (expected: no)
- [ ] V6 Do any payloads contain token counts? (`subagentStop`, `stop`, `preCompact`)
- [ ] V7 Which `RULE-*-OK` tokens the agent sees: ALWAYS always; GLOB only with a `*.kspike` file; DESC when asked about "purple-elephant"; MANUAL only with `@spike-manual`.
- [ ] V8 `spike-readonly` could not write the file or `touch`.
- [ ] V9 `/kaotim-spike-args alpha beta` → `ARGS=[alpha beta] FIRST=[alpha] SECOND=[beta]`? Same for `/kaotim-spike-cmd one two` (skill).
- [ ] V11 Each `spike-writer` wrote into its own worktree and reported the right branch.
- [ ] Laravel pao: `php artisan test` prints JSON inside the Cursor agent shell (`CURSOR_AGENT=1`).
