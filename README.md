# Kaotim

<p align="center">
  <img src="assets/logo.png" alt="Kaotim" width="420" />
</p>

> *kautim* (Malaysian slang): settled, sorted, done.

**Kaotim is a Cursor plugin that turns an AI coding agent into a disciplined engineering pipeline:
plan → test-first build → layered review → cleanup → pull request.** A main orchestrator agent
talks to you and delegates to ten specialist subagents, while deterministic Python scripts, not
LLM opinion, decide when each stage is done.

> **Status:** M0–M8 implemented (v0.1.0). Install locally and run `/kaotim-init` in a target repo.

---

## Why it exists

AI-generated code fails in predictable ways: it guesses requirements, edits tests until they
pass, touches files it shouldn't, reinvents existing helpers, leaves debug code behind, and
declares victory without evidence. Kaotim answers with **structure plus enforcement**.

## How it works

Hub-and-spoke orchestration; shared memory under `.kaotim/`; scripts decide stage transitions.
See the state machine and agent roster in earlier design notes; commands live in `commands/`.

### Specialist subagents

| Agent | Mode | Job |
|---|---|---|
| `explorer` | read-only | Find existing utilities and entry points |
| `test-writer` | tests only | Write failing tests per AC/EC |
| `feature-dev` | write (owned files) | Make locked tests pass |
| `supervisor` | read-only | Check acceptance criteria |
| `structure-reviewer` | read-only | Flag layering/structure issues |
| `refactorer` | write | Behaviour-preserving structure fixes |
| `bug-reviewer` | read-only | Find bugs by severity |
| `fixer` | write | Fix bugs with regression tests |
| `cleaner` | write (diff only) | Remove debug leftovers |
| `pr-writer` | read-only | PR body with AC → test → status |

## Commands

| Command | Purpose |
|---|---|
| `/kaotim <request>` | Full pipeline (or resume) |
| `/kaotim-plan <request>` | Planning only |
| `/kaotim-resume` | Continue from `state.json` |
| `/kaotim-explain` | Explain selected code in precise, simple terms |
| `/kaotim-tree` | Call-flow tree of selected code (upstream + 1 downstream) |
| `/kaotim-stack` | Generate `.kaotim/stack.yaml` |
| `/kaotim-init` | Copy CLI, stack draft, profile |
| `/kaotim-doctor` | Validate wiring and safety |
| `/kaotim-refresh` | Propose updates (diff only) |
| `/kaotim-metrics` | Metrics summary / trends |
| `/kaotim-retro` | Improvement proposals from history |

CLI: `python scripts/kaotim.py <subcommand>` (after init: `python .kaotim/bin/kaotim.py`).

### Skills

| Skill | Used for |
|---|---|
| `kaotim-planning` | Plan / SPEC / approvals |
| `tdd` | Red → lock → green |
| `edge-cases` | EC enumeration and bug review |
| `arch-comparison` | Architecture options during planning |
| `pr-writing` | PR title/body from plan + gates |
| `stack-detection` | Infer stack for `stack.yaml` |
| `retro` | Improvement proposals from history |
| `explain-code` | Precise plain-language walkthrough of selected code |
| `kaotim-tree` | Call-flow tree: all upstream, one downstream, snippets/branches |

## Supported stacks

| Stack | Support |
|---|---|
| **PHP / Laravel** (`php-laravel`) | Built-in: Pest/PHPUnit JUnit, wrong-reason detection, layers, guards |
| **Python** (`python`) | Built-in: pytest JUnit, ruff/mypy defaults, layers |
| Anything else | Declarative adapter or commands-only |

## Requirements

- Cursor with plugin support
- **Python 3.9+** on `PATH` (`python` on Windows, `python3` on macOS/Linux)
- Git; safe local test database
- Optional: `gh` / `glab` for draft PRs

## Install for local development

```powershell
# IDE (Windows): copy into local plugins, then Reload Window
Copy-Item -Recurse D:\Plugin\kaotim $HOME\.cursor\plugins\local\kaotim

# CLI agent
agent --plugin-dir D:\Plugin\kaotim
```

```bash
# macOS / Linux
cp -r /path/to/kaotim ~/.cursor/plugins/local/kaotim
```

Run plugin self-tests:

```powershell
py -3 -m unittest discover -s scripts/tests -p "test_*.py"
```

## Repository layout

| Path | Status | Contents |
|---|---|---|
| `.cursor-plugin/plugin.json` | present | Plugin manifest |
| `assets/logo.png` | present | Plugin / marketplace logo |
| `scripts/kaotim.py`, `scripts/lib/` | present | CLI and libraries (Python) |
| `commands/`, `agents/`, `skills/`, `rules/` | present | Slash commands, subagents, skills, rules |
| `hooks/hooks.json` | present | Test-lock, shell guard, stage-guard |
| `adapters/`, `templates/` | present | Ecosystem adapters, templates |
| `config.defaults.yaml` | present | Caps, budgets, model tiers |
| `fixtures/` | present | Laravel (Pest/PHPUnit), Python |
| `docs/` | present | Findings, decisions, user guide |
| `spike/` | historical | M0 throwaway probes |

## Roadmap

- [x] **M0 – Platform spikes**
- [x] **M1 – Foundations** (Python CLI)
- [x] **M2 – Stack generation**
- [x] **M3 – Planning**
- [x] **M4 – Single-task TDD**
- [x] **M5 – Multi-task & integration**
- [x] **M6 – Review chain**
- [x] **M7 – PR, metrics, resume, fast lane**
- [x] **M8 – Hardening**

## Docs

- [User guide](docs/user-guide.md)
- [Decisions](docs/decisions.md)
- [Platform findings](docs/platform-findings.md)

## License

TBD. No license has been chosen yet; until one is added, all rights are reserved.

## Author

Dong Lin Wong ([@wongdlin](https://github.com/wongdlin))
