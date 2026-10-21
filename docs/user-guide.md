# Kaotim: User Guide

## 1. What it does

Kaotim is a Cursor plugin that runs: plan → test-first build → layered review → cleanup → pull request. Deterministic Python scripts decide stage completion; specialist subagents write and review code.

## 2. Before you start

- Cursor with plugin support
- **Python 3.9+** on `PATH` as `python` (Windows) or `python3` (macOS/Linux)
- Git; safe local test database
- Optional: `gh` or `glab` for draft PRs

## 3. First-time setup

```powershell
# Install plugin (IDE): copy repo into local plugins, reload window
Copy-Item -Recurse D:\path\to\kaotim $HOME\.cursor\plugins\local\kaotim

# In your project chat:
# /kaotim-init
# or:
python path\to\kaotim\scripts\kaotim.py --repo . init
```

Review `.kaotim/stack.yaml` and `.kaotim/project-profile.md`, then commit them.

## 4. Everyday workflow

1. `/kaotim <request>` or `/kaotim-plan <request>`
2. Answer planning questions (goal/AC, I/O, SPEC S→P→E→C; clickable AskQuestion when available; ask until clear); approve the plan
3. After failing tests are written and locked, review them (assertions, coverage gaps); approve tests to start implementation (disable with `approvals.require_tests: false` in `.kaotim/config.yaml`)
4. Pipeline continues TDD green, reviews, cleanup
5. Read metrics summary; approve PR creation

CLI used throughout: `python .kaotim/bin/kaotim.py <subcommand>` after init.

## 5. Commands

| Command | Purpose |
|---|---|
| `/kaotim` | Full pipeline |
| `/kaotim-plan` | Planning only |
| `/kaotim-resume` | Resume from `state.json` |
| `/kaotim-stack` | Generate stack.yaml |
| `/kaotim-init` | Bin copy + stack + profile |
| `/kaotim-doctor` | Validate wiring |
| `/kaotim-refresh` | Propose updates |
| `/kaotim-metrics` | Metrics summary |
| `/kaotim-retro` | Improvement proposals |

## 6. When it stops

Human checkpoints: planning, test approval after `tdd_red` (default on), escalations (caps), PR approval after metrics. Fast lane requires explicit confirmation and stays within file limits.

## 7. What lives where

Committed: `stack.yaml`, `project-profile.md`, optional `config.yaml`. Runtime (gitignored): `state.json`, `handoffs/`, `gates/`, `worktrees/`, most metrics JSONL.

## 8. Troubleshooting

- `python` not found: install Python 3.9+ and ensure it is on PATH (not the Windows Store stub alone).
- Gate failures: open `.kaotim/gates/` raw logs.
- Locked tests: `unlock-tests` only with a reason after human approval.
- Resume: fresh chat + `/kaotim-resume`.
