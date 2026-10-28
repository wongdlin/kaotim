# Kaotim: User Guide

## 1. What it does

Kaotim runs a disciplined pipeline in Cursor:

**plan → failing tests → implement → verify → structure review → bug review → cleanup → PR**

Specialist subagents do the writing and review. A Python CLI under `.kaotim/bin/` decides when
stages can advance (locks, verify-red, gates, `next-stage`). It is **not** tied to PHP, Python,
or any other ecosystem — you supply shell commands in `.kaotim/config.yaml`.

## 2. Before you start

- Cursor with plugin support
- **Python 3.9+** on `PATH` as `python` (Windows) or `python3` (macOS/Linux)
- Git
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

Init creates:

- `.kaotim/bin/` — copied CLI
- `.kaotim/config.yaml` — stub with empty `commands.*`
- `.kaotim/project-profile.md` — architecture / conventions for agents
- a single `.kaotim/` entry in `.gitignore` (whole directory)

The entire `.kaotim/` tree is gitignored — including `config.yaml`, `project-profile.md`,
and `bin/`. Teammates who clone the target repo must run `/kaotim-init` themselves (then
re-fill `commands.*` / the profile as needed). Older selective `.kaotim/...` ignore lines are
left alone if already present.

There is **no** `stack.yaml` and no `/kaotim-stack`. If an older install left `.kaotim/stack.yaml`,
move any test/lint commands into `config.yaml` and delete `stack.yaml` (`/kaotim-doctor` will fail
while it remains).

## 4. Configure commands

Edit `.kaotim/config.yaml`:

```yaml
git:
  base_branch: main
  pr_cli: gh

commands:
  test: "npm test"       # required after plan approve, before TDD
  test_file: ""          # optional; supports {file} and {files}
  lint: ""
  typecheck: ""
  build: ""
  worktree_setup: ""     # optional; run when adding a worktree
  junit_flag: ""         # optional; e.g. --junitxml={path}
```

- Planning does **not** require `commands.test`.
- Leaving plan-approved toward TDD **does** — set the real runner first.
- `verify-red` / `run-tests` use exit code (and optional JUnit when `junit_flag` is set).

Put layering and architecture conventions in **`.cursor/rules/`** or **`rules/`**. Structure
review is done by the structure-reviewer agent (see `list-rules` CLI).

## 5. Everyday workflow

1. `/kaotim <request>` or `/kaotim-plan <request>`
2. Answer planning questions; approve the plan
3. Ensure `commands.test` is set; continue to TDD
4. After failing tests are written and locked, review them; approve tests to start implementation
   (disable with `approvals.require_tests: false` in `.kaotim/config.yaml`)
5. Pipeline continues green → integrate → supervisor → structure (repo rules) → bug → cleanup
6. Read metrics summary; approve PR creation

CLI used throughout: `python .kaotim/bin/kaotim.py <subcommand>` after init.

## 6. Slash entry skills

Type `/` in Agent chat and select a skill.

| Skill | Purpose |
|---|---|
| `/kaotim` | Full pipeline |
| `/kaotim-plan` | Planning only |
| `/kaotim-resume` | Resume from `state.json` |
| `/kaotim-explain` | Explain selected code |
| `/kaotim-tree` | Call-flow tree of selected code |
| `/kaotim-init` | Bin copy + config stub + profile |
| `/kaotim-doctor` | Validate wiring |
| `/kaotim-refresh` | Propose config/profile updates |
| `/kaotim-metrics` | Metrics summary |
| `/kaotim-retro` | Improvement proposals |

## 7. When it stops

Human checkpoints: planning, test approval after `tdd_red` (default on), escalations (caps),
PR approval after metrics. Fast lane requires explicit confirmation and stays within file limits.

## 8. What lives where

**Committed:** only the `.kaotim/` gitignore entry (and any older selective lines left behind).
`config.yaml`, `project-profile.md`, and `bin/` stay local — each teammate runs `/kaotim-init`.

**Runtime (gitignored):** the whole `.kaotim/` directory (state, handoffs, gates, worktrees,
archived plans, metrics, config stub, project profile, and copied CLI).

After `final_gate` + `approvals.pr`, `next-stage` archives `plan.md` → `plans/<id>.md` and clears
state (before PR open). `create-pr` is best-effort; if it fails, open the PR yourself from
`.kaotim/pr.md`. Next feature: `state init` (no `--force`).

## 9. Troubleshooting

- `python` not found: install Python 3.9+ and ensure it is on PATH.
- `commands.test empty`: set it in `.kaotim/config.yaml` after plan approve.
- Leftover `stack.yaml`: doctor fails until you migrate commands and delete it (hard cut).
- Gate failures: open `.kaotim/gates/` raw logs.
- Locked tests: `unlock-tests` only with a reason after human approval.
- Resume: fresh chat + `/kaotim-resume`.
- Parent stuck on "waiting for subagent": cancel the subagent, check `.kaotim/handoffs/` and
  written files, then `/kaotim-resume` (set `stage_status` to `in_progress` if left as
  `awaiting_specialist`).

## 10. Migrating from stack.yaml

1. Copy `testing.commands` / `quality.*` / `git` / `worktree.setup` into `.kaotim/config.yaml`
   under `commands.*` and `git`.
2. Delete `.kaotim/stack.yaml`.
3. Drop any declarative adapters under `.kaotim/adapters/`.
4. Run `/kaotim-doctor`.
