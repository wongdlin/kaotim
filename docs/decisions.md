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
| D5 | §10 hooks "plugin-root variable?" | Plugin hooks get `CURSOR_PLUGIN_ROOT`; cwd = plugin dir except `stop`/`subagentStop` | Hook commands: `python3 "${CURSOR_PLUGIN_ROOT}/scripts/kaotim.py" hook <name>` | Adopted (Windows unverified) |
| D6 | §11 "One CLI: python scripts/kaotim.py" from commands/agents | No plugin-root variable in prompts (V5) | Spec fallback: `/kaotim-init` copies scripts to `.kaotim/bin/` with a version stamp; prompts call `python3 .kaotim/bin/kaotim.py`; `doctor` checks the version | Adopted; commit-or-ignore is Q4 |
| D7 | §4.4 readonly reviewers save their handoff file | `readonly` forbids file edits and state-changing shell | Readonly agents return the handoff block only; the orchestrator saves and validates it (`check-handoff --save`). Structure-reviewer gets `check-layers` output in its packet | Proposed (Q3) |
| D8 | §12.6 token capture | No token counts in hooks or CLI output; model, durations, counts available | Tokens `estimated`; model/duration/counts `measured` from `subagentStart`/`subagentStop` when hooks run | Adopted |
| D9 | §6 commands | Commands are documented, but Cursor is moving slash commands to skills (`disable-model-invocation: true`); no first-party plugin ships `commands/` | Keep `commands/`; write bodies that work with or without `$ARGUMENTS` substitution | Adopted; switch is Q2 |
| D10 | Appendix C.3 affected tests: Pest `--dirty`/`--changed` | Pest 5.3 has only `--dirty`, which selects changed **test** files | Mirror strategy primary; `--dirty` only adds edited tests | Adopted |
| D11 | Appendix C.3 JUnit rule | Syntax errors leave an empty JUnit file | Empty/missing JUnit or unexpected exit code = wrong-reason red | Adopted |
| D12 | Appendix E.3 "`<failure>` = assertion" | pytest reports an `ImportError` inside a test body as `<failure>` | Apply wrong-reason signatures to `<failure>` messages too | Adopted |
| D13 | V13 env managers | `uv run --project` keeps the caller's cwd | Adapters run `cd <root> && <cmd>` (or `uv run --directory`) | Adopted |
| D14 | Laravel output parsing | Laravel 13 `laravel/pao` prints JSON when `CURSOR_AGENT=1` | JUnit is authoritative; treat pao JSON as optional stdout; `doctor` reports pao | Adopted |
| D15 | §2.2 `.kaotim/worktrees/` | Must be gitignored or the main checkout is dirty | `/kaotim-init` ensures the ignore entries (already in §2.2) | Adopted |
| D16 | §3.1 runtime | Python is missing on native Windows (and Herd on Windows) | No change; recommendation in findings V10 | Waiting for user (Q1) |

### Fixture notes
- Laravel fixtures are the Laravel 13 skeleton (spec examples say 11) with one Action
  (`CountWords`), a `/health` route and AC/EC-named tests. Boost `AGENTS.md`/`CLAUDE.md` removed.
  `phpunit.xml` sets a fixed dummy `APP_KEY` so HTTP tests run without `.env`.
- Still missing for Appendix C.8 (M2): Form Request, Resource, Model + factory, migration,
  `pint.json`, `phpstan.neon` with Larastan, GitHub workflow. Python fixture still needs a
  repository layer for E.8 layer checks (M6).
