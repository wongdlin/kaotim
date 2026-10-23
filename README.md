# Kaotim

<p align="center">
  <img src="assets/logo.png" alt="Kaotim" width="420" />
</p>

> *kautim* (Malaysian slang): settled, sorted, done.

**Kaotim is a Cursor plugin that turns an AI coding agent into a disciplined engineering pipeline:
plan → test-first build → structure review → cleanup → pull request.** A main orchestrator
talks to you and delegates to specialist subagents, while a small Python CLI — not LLM opinion —
decides when each stage is done.

It is **language-agnostic**: you point Kaotim at your repo’s real test/lint commands in
`.kaotim/config.yaml`. There are no built-in language adapters or `stack.yaml`.

> **Status:** Pipeline M0–M8 + generic config pivot. Install locally and run `/kaotim-init`.

---

## Why it exists

AI-generated code fails in predictable ways: it guesses requirements, edits tests until they
pass, touches files it shouldn't, reinvents existing helpers, leaves debug code behind, and
declares victory without evidence. Kaotim answers with **structure plus enforcement**.

## How it works

Hub-and-spoke orchestration; shared memory under `.kaotim/`; scripts decide stage transitions.
Slash entry points are skills under `skills/` (type `/` in Agent chat).

### Specialist subagents

| Agent | Mode | Job |
|---|---|---|
| `explorer` | read-only | Find existing utilities and entry points |
| `test-writer` | tests only | Write failing tests per AC/EC |
| `feature-dev` | write (owned files) | Make locked tests pass |
| `supervisor` | read-only | Check acceptance criteria |
| `structure-reviewer` | read-only | Flag structure issues vs repo rules |
| `refactorer` | write | Behaviour-preserving structure fixes |
| `bug-reviewer` | read-only | Find bugs by severity |
| `fixer` | write | Fix bugs with regression tests |
| `cleaner` | write (diff only) | Remove debug leftovers |
| `pr-writer` | read-only | PR body with AC → test → status |

## Skills (slash entry)

Type `/` in Agent chat and pick a skill. Entry skills are slash-only except `kaotim-explain`
(also auto when you ask to explain selected code).

| Skill | Purpose |
|---|---|
| `/kaotim <request>` | Full pipeline (or resume) |
| `/kaotim-plan <request>` | Planning only |
| `/kaotim-resume` | Continue from `state.json` |
| `/kaotim-explain` | Explain selected code in precise, simple terms |
| `/kaotim-tree` | Call-flow tree of selected code (upstream + 1 downstream) |
| `/kaotim-init` | Copy CLI, config stub, profile |
| `/kaotim-doctor` | Validate wiring and safety |
| `/kaotim-refresh` | Propose config/profile updates (diff only) |
| `/kaotim-metrics` | Metrics summary / trends |
| `/kaotim-retro` | Improvement proposals from history |

CLI: `python scripts/kaotim.py <subcommand>` (after init: `python .kaotim/bin/kaotim.py`).

### Supporting skills

| Skill | Used for |
|---|---|
| `tdd` | Red → lock → green |
| `edge-cases` | EC enumeration and bug review |
| `arch-comparison` | Architecture options during planning |
| `pr-writing` | PR title/body from plan + gates |

## Configure your repo

After `/kaotim-init`, edit `.kaotim/config.yaml`:

```yaml
git:
  base_branch: main
  pr_cli: gh          # or glab / none

commands:
  test: "npm test"    # required after plan approve, before TDD
  test_file: ""       # optional; {file} / {files}
  lint: ""
  typecheck: ""
  build: ""
  worktree_setup: ""
  junit_flag: ""      # optional; e.g. --junitxml={path}
```

Put architecture / layering conventions in **`.cursor/rules/`** or **`rules/`**. Structure review
is agent-enforced (structure-reviewer reads those files via `list-rules`).

## Requirements

- Cursor with plugin support
- **Python 3.9+** on `PATH` (`python` on Windows, `python3` on macOS/Linux)
- Git; safe local test database when your suite needs one
- Optional: `gh` / `glab` for draft PRs

## How to install

Clone the repo, then install into Cursor’s local plugins folder (Reload Window after):

```powershell
# Windows
git clone https://github.com/wongdlin/kaotim.git
Copy-Item -Recurse .\kaotim $HOME\.cursor\plugins\local\kaotim

# CLI agent
agent --plugin-dir $HOME\.cursor\plugins\local\kaotim
```

```bash
# macOS / Linux
git clone https://github.com/wongdlin/kaotim.git
cp -r kaotim ~/.cursor/plugins/local/kaotim

# CLI agent
agent --plugin-dir ~/.cursor/plugins/local/kaotim
```

Run plugin self-tests from the cloned repo:

```powershell
py -3 -m unittest discover -s scripts/tests -p "test_*.py"
```

## Repository layout

| Path | Contents |
|---|---|
| `.cursor-plugin/plugin.json` | Plugin manifest |
| `assets/logo.png` | Plugin / marketplace logo |
| `scripts/kaotim.py`, `scripts/lib/` | CLI and libraries (Python) |
| `agents/`, `skills/`, `rules/` | Subagents, slash/supporting skills, plugin rules |
| `hooks/hooks.json` | Test-lock, shell guard, stage-guard |
| `templates/` | Plan and related templates |
| `config.defaults.yaml` | Caps, budgets, model tiers, empty `commands.*` |
| `docs/` | Findings, decisions, user guide |

## Docs

- [User guide](docs/user-guide.md) — how to use Kaotim day to day
- [Decisions](docs/decisions.md)
- [Platform findings](docs/platform-findings.md)

## License

[MIT](LICENSE) © 2026 Dong Lin Wong

## Author

Dong Lin Wong ([@wongdlin](https://github.com/wongdlin))
