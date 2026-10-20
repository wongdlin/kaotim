# Decisions

One entry per milestone (spec §17). Deviations from the spec are listed with their reason and
status. "Proposed" items wait for the user's answer to the numbered question in the M0 report.

## M0: Platform spikes (2026-10-19)

**Delivered.** Throwaway spike plugin and probes (`spike/`), `docs/platform-findings.md`,
`config.defaults.yaml` (tier draft), fixtures `fixtures/laravel-app` (Laravel 13, Pest),
`fixtures/laravel-app-phpunit`, `fixtures/python-app` (uv, pytest, ruff, mypy).

**Acceptance.** Every `VERIFY` item has a finding and a decided fallback. Cursor runtime items are
`docs-only` because the CLI is not authenticated on the build box; `spike/run_cli_spike.sh`
upgrades them once the user runs it.

### Deviations and design adjustments

| # | Spec text | Finding | Decision | Status |
|---|---|---|---|---|
| D1 | §2.1 "Subagents cannot spawn subagents" | Since Cursor 2.5 a direct subagent can launch one more level | Keep hub-and-spoke as a **policy**: every agent prompt forbids spawning; optional `subagentStart` deny for nested spawns (M5) | Adopted |
| D2 | §8.1 frontmatter "model tier, read-only flag, tool restrictions" | Fields are `model`, `readonly`, `is_background`; no tool-restriction field | Agent files use `name`, `description`, `model`, `readonly`; tool limits stay in prompts + gates. One-line frontmatter values | Adopted |
| D3 | §10 test-lock "before-edit hook" | No before-edit event; `preToolUse` (matcher `Write\|Delete`) can deny; shell writes are not covered | test-lock = `preToolUse` deny + `afterFileEdit`/`afterShellExecution` hash check + `verify-lock` in every gate (already the fallback). Map worktree paths to repo paths | Adopted |
| D4 | §10 stage-guard "prevent finishing a turn" | `stop` cannot block; it can auto-submit `followup_message` (bounded) | stage-guard returns a `followup_message` while a stage is mid-flight, plus the prompt reminder | Adopted |
| D5 | §10 hooks "plugin-root variable?" | Plugin hooks get `CURSOR_PLUGIN_ROOT`; cwd = plugin dir except `stop`/`subagentStop` | Hook commands: `python "${CURSOR_PLUGIN_ROOT}/scripts/kaotim.py" hook <name>` (Windows-friendly `python`) | Adopted |
| D6 | §11 "One CLI: python scripts/kaotim.py" from commands/agents | No plugin-root variable in prompts (V5) | `/kaotim-init` copies scripts to `.kaotim/bin/`; prompts call `python .kaotim/bin/kaotim.py` | Adopted |
| D7 | §4.4 readonly reviewers save their handoff file | `readonly` forbids file edits and state-changing shell | Readonly agents return the handoff block only; orchestrator saves via `check-handoff --save` | Adopted |
| D8 | §12.6 token capture | No token counts in hooks or CLI output; model, durations, counts available | Tokens `estimated`; model/duration/counts `measured` from `subagentStart`/`subagentStop` when hooks run | Adopted |
| D9 | §6 commands | Commands are documented, but Cursor is moving slash commands to skills (`disable-model-invocation: true`); no first-party plugin ships `commands/` | Keep `commands/`; write bodies that work with or without `$ARGUMENTS` substitution | Adopted; switch is Q2 |
| D10 | Appendix C.3 affected tests: Pest `--dirty`/`--changed` | Pest 5.3 has only `--dirty`, which selects changed **test** files | Mirror strategy primary; `--dirty` only adds edited tests | Adopted |
| D11 | Appendix C.3 JUnit rule | Syntax errors leave an empty JUnit file | Empty/missing JUnit or unexpected exit code = wrong-reason red | Adopted |
| D12 | Appendix E.3 "`<failure>` = assertion" | pytest reports an `ImportError` inside a test body as `<failure>` | Apply wrong-reason signatures to `<failure>` messages too | Adopted |
| D13 | V13 env managers | `uv run --project` keeps the caller's cwd | Adapters run `cd <root> && <cmd>` (or `uv run --directory`) | Adopted |
| D14 | Laravel output parsing | Laravel 13 `laravel/pao` prints JSON when `CURSOR_AGENT=1` | JUnit is authoritative; treat pao JSON as optional stdout; `doctor` reports pao | Adopted |
| D15 | §2.2 `.kaotim/worktrees/` | Must be gitignored or the main checkout is dirty | `/kaotim-init` ensures the ignore entries (already in §2.2) | Adopted |
| D16 | §3.1 runtime | Python is missing on native Windows (and Herd on Windows) | **User chose Python** (not Node). Engine is `scripts/kaotim.py`, stdlib + vendored `yaml_lite`. Windows requires an installed Python on PATH (`python` / `py -3`). Hooks/commands use `python`. | Adopted |

### Fixture notes
- Laravel fixtures are the Laravel 13 skeleton (spec examples say 11) with one Action
  (`CountWords`), a `/health` route and AC/EC-named tests. Boost `AGENTS.md`/`CLAUDE.md` removed.
  `phpunit.xml` sets a fixed dummy `APP_KEY` so HTTP tests run without `.env`.
- Python fixture includes `src/app/repositories/words_repo.py` for layer-check samples.

## M1: Foundations (2026-10-19)

**Delivered.** `.cursor-plugin/plugin.json`, `scripts/kaotim.py` + `scripts/lib/`, vendored YAML, atomic state, handoff checks, `log-event` (locked JSONL appends), `get-package`/`get-stack`, adapter registry + declarative validate, templates.

**Acceptance.** `python -m unittest discover -s scripts/tests` (M1 cases) green.

## M2: Stack generation (2026-10-19)

**Delivered.** `detect-stack`, `validate-stack`, `stack-write`, `init`, `refresh`, `doctor`, commands `/kaotim-stack|init|doctor|refresh`, `stack-detection` skill, marker merge.

## M3: Planning (2026-10-19)

**Delivered.** Planning/edge/arch skills, `explorer`, plan template, `check-plan`, `/kaotim-plan`, `next-stage` for recon→plan→plan_approved.

## M4: Single-task TDD (2026-10-19)

**Delivered.** `test-writer`/`feature-dev`, `tdd` skill/rule, `run-tests`, `verify-red`, locks, `gate`, JUnit parsers + wrong-reason signatures, test-lock hook.

## M5: Multi-task and integration (2026-10-19)

**Delivered.** `worktree add|remove`, `merge-tasks`, `check-ownership`, ownership/stage hooks, integrate stage wiring via `next-stage`.

## M6: Review chain (2026-10-19)

**Delivered.** Reviewer/fixer/cleaner agents, `check-layers`, `check-regression-tests`, caps/escalation in `next-stage`.

## M7: PR, metrics, resume, fast lane (2026-10-19)

**Delivered.** `pr-writer`, `create-pr`, `metrics-summary`, `/kaotim-metrics|resume|retro`, `retro` CLI, fast-lane checks in `check-plan`.

## M8: Hardening (2026-10-19)

**Delivered.** Unit acceptance suite across M1–M8, `doctor --self` word budgets, `docs/user-guide.md`, README install for Windows Python. Spike retained as historical M0 evidence.

## Skill wiring (2026-10-20)

**Decided.** Commands and agents name skills explicitly (`Read and follow the `X` skill (skills/X/SKILL.md in the Kaotim plugin)`) because subagent skill visibility is unverified (see platform-findings). Skill descriptions start with "Use when ...". `disable-model-invocation: true` (confirmed in Cursor skills docs) on retro, pr-writing, kaotim-planning, stack-detection; tdd, edge-cases, arch-comparison stay auto-invocable.
