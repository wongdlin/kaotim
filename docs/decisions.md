# Decisions

One entry per milestone (spec §17). Deviations from the spec are listed with their reason and
status. "Proposed" items wait for the user's answer to the numbered question in the M0 report.

## M0: Platform spikes (2026-10-19)

**Delivered.** Throwaway spike plugin and probes (later removed; see note below),
`docs/platform-findings.md`, `config.defaults.yaml` (tier draft), fixtures
`fixtures/laravel-app` (Laravel 13, Pest), `fixtures/laravel-app-phpunit`,
`fixtures/python-app` (uv, pytest, ruff, mypy).

**Acceptance.** Every `VERIFY` item has a finding and a decided fallback. Cursor runtime items are
`docs-only` because the CLI is not authenticated on the build box.

**Note (2026-10-23):** The `spike/` tree was deleted. M0 findings remain in
`docs/platform-findings.md`.

### Deviations and design adjustments

| # | Spec text | Finding | Decision | Status |
|---|---|---|---|---|
| D1 | §2.1 "Subagents cannot spawn subagents" | Since Cursor 2.5 a direct subagent can launch one more level | Keep hub-and-spoke as a **policy**: every agent prompt forbids spawning; optional `subagentStart` deny for nested spawns (M5) | Adopted |
| D2 | §8.1 frontmatter "model tier, read-only flag, tool restrictions" | Fields are `model`, `readonly`, `is_background`; no tool-restriction field | Agent files use `name`, `description`, `model`, `readonly`; tool limits stay in prompts + gates. One-line frontmatter values | Adopted |
| D3 | §10 test-lock "before-edit hook" | No before-edit event; `preToolUse` (matcher `Write\|Delete`) can deny; shell writes are not covered | test-lock = `preToolUse` deny + `afterFileEdit`/`afterShellExecution` hash check + `verify-lock` in every gate (already the fallback). Map worktree paths to repo paths | Adopted |
| D4 | §10 stage-guard "prevent finishing a turn" | `stop` cannot block; it can auto-submit `followup_message` (bounded) | **Revised 2026-10-23:** do **not** emit `followup_message` from `stop`/`subagentStop`. Auto-continue trapped Task specialists while `stage_status` stayed `in_progress`, leaving the parent on "waiting for subagent". Stage progress stays in orchestrator prompts + `next-stage` gates; use `awaiting_user` / `awaiting_specialist`; `loop_limit: 1` on stop as belt-and-suspenders | Adopted |
| D5 | §10 hooks "plugin-root variable?" | Plugin hooks get `CURSOR_PLUGIN_ROOT`; cwd = plugin dir except `stop`/`subagentStop` | Hook commands: `python "${CURSOR_PLUGIN_ROOT}/scripts/kaotim.py" hook <name>` (Windows-friendly `python`) | Adopted |
| D6 | §11 "One CLI: python scripts/kaotim.py" from commands/agents | No plugin-root variable in prompts (V5) | `/kaotim-init` copies scripts to `.kaotim/bin/`; prompts call `python .kaotim/bin/kaotim.py` | Adopted |
| D7 | §4.4 readonly reviewers save their handoff file | `readonly` forbids file edits and state-changing shell | Readonly agents return the handoff block only; orchestrator saves via `check-handoff --save` | Adopted |
| D8 | §12.6 token capture | No token counts in hooks or CLI output; model, durations, counts available | Tokens `estimated`; model/duration/counts `measured` from `subagentStart`/`subagentStop` when hooks run | Adopted |
| D9 | §6 commands | Commands are documented, but Cursor is moving slash commands to skills (`disable-model-invocation: true`); no first-party plugin ships `commands/` | **Q2 closed 2026-10-23:** migrate slash entry points to skills under `skills/` (preserve `/kaotim-*` names); delete `commands/`. Bodies still worded for `$ARGUMENTS` with or without substitution | Adopted |
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

**Delivered.** Unit acceptance suite across M1–M8, `doctor --self` word budgets, `docs/user-guide.md`, README install for Windows Python.

## Skill wiring (2026-10-20; revised 2026-10-23)

**Decided.** Agents and the `/kaotim` orchestrator name skills explicitly (`Read and follow the `X` skill (skills/X/SKILL.md in the Kaotim plugin)`) because subagent skill visibility is unverified (see platform-findings). Skill descriptions start with "Use when ...". Slash entry skills use `disable-model-invocation: true` except `kaotim-explain` (auto + slash). Entry skills: `kaotim`, `kaotim-plan`, `kaotim-resume`, `kaotim-explain`, `kaotim-tree`, `kaotim-refactor`, `kaotim-init`, `kaotim-doctor`, `kaotim-refresh`, `kaotim-metrics`, `kaotim-retro`. Supporting: `pr-writing` (explicit-only); `tdd`, `edge-cases`, `arch-comparison` stay auto-invocable. `commands/` removed (D9/Q2). `/kaotim-stack` removed in the generic config pivot (below).

## Run completion clears state (2026-10-23)

**Decided.** Do not leave `stage: done` requiring `state init --force` for every feature. On `final_gate` → complete (`next-stage` or `state complete`): archive `.kaotim/plan.md` → `.kaotim/plans/<plan_id>.md` with `status: completed`, delete `state.json`, clear `handoffs/` and `gates/`. Completion is **before** PR open — `create-pr` is best-effort; if it fails, the human opens the PR (e.g. from `.kaotim/pr.md`). `pr_created` is not a stage gate. Next run is a normal `state init` + new plan.

## Generic config pivot (no adapters / stack.yaml)

**Decided.** Kaotim is language-agnostic skills + CLI gates. Removed built-in adapters (`php-laravel`, `python`), `stack.yaml`, detect/validate-stack, `/kaotim-stack`, and language fixtures.

| Topic | Choice |
|-------|--------|
| Shell runners | `.kaotim/config.yaml` → `commands.*` |
| Planning | Does not require `commands.test` |
| Before TDD | Non-empty `commands.test` after plan approve |
| verify-red | Engine: exit ≠ 0 = red; optional `junit_flag`; generic wrong-reason list |
| Structure | Agent (structure-reviewer) vs `.cursor/rules` or `rules/`; `list-rules` CLI |
| Worktrees | Kept; `commands.worktree_setup` |
| Migration | Hard cut — leftover `stack.yaml` fails doctor |
| Init | Minimal: bin + config stub + profile |

Pipeline stage order unchanged.
