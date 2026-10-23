# Platform findings (Milestone 0)

Recorded 2026-10-19 for spec v1.0 §16 (V1–V13) and the `VERIFY` items in Appendices C and E.

**Environment.** Debian 13 x86_64 box; Cursor CLI `2026.10.16-e3cb207` installed with
`curl https://cursor.com/install -fsS | bash`. PHP 8.4.26, Composer 2.8.8 (apt), Laravel 13.37.0,
Pest 5.3, PHPUnit 12.5, Python 3.13.5 (system) and 3.9 (uv-managed), uv 0.13.1, git 2.47.3,
Node 20.19.2.

**Confidence levels.**
- `verified`: observed by running something on this box (command output in `spike/evidence/`).
- `docs-only`: stated in official Cursor docs, shown in Cursor's own plugin repos
  (`cursor/plugin-template`, `cursor/plugins`), or read from the installed CLI's shipped JavaScript.
  Not observed at runtime.
- `unverified`: no source found. The spec's fallback applies.

**Cursor runtime could not be exercised.** The CLI installs and starts headless, but every agent
command stops at authentication (no `CURSOR_API_KEY`; none was requested):

```
$ agent status
Not logged in
$ agent -p "say hi" --output-format json
Error: Authentication required. Please run 'agent login' first, or set CURSOR_API_KEY environment variable.
$ agent --plugin-dir spike/kaotim-spike -p "/kaotim-spike-args a b"
Error: Authentication required. ...
```
(`spike/evidence/cli/cli-probe.txt`). So every Cursor runtime behaviour below is `docs-only` at
best. `spike/run_cli_spike.sh` (after `agent login`) or the IDE checklist in `spike/README.md`
upgrades them to `verified`.

**Sources** (fetched 2026-10-19):
[plugins](https://cursor.com/docs/plugins) ·
[plugins reference](https://cursor.com/docs/reference/plugins) ·
[rules](https://cursor.com/docs/context/rules) ·
[skills](https://cursor.com/docs/skills.md) ·
[subagents](https://cursor.com/docs/agent/subagents) ·
[hooks](https://cursor.com/docs/agent/hooks) ·
[worktrees](https://cursor.com/docs/configuration/worktrees.md) ·
[CLI output format](https://cursor.com/docs/cli/reference/output-format.md) ·
[models & pricing](https://cursor.com/docs/models-and-pricing.md) ·
[cursor/plugin-template @ 4621607](https://github.com/cursor/plugin-template) ·
[cursor/plugins @ d457567](https://github.com/cursor/plugins) (incl. `schemas/plugin.schema.json`).
`https://cursor.com/docs/context/commands` now serves the **Skills** page; there is no separate
commands page.

## Summary

| ID | Answer (short) | Confidence | Decided fallback / design impact |
|---|---|---|---|
| V1 | `.cursor-plugin/plugin.json`; only `name` required; default folders `rules/ skills/ agents/ commands/ hooks/hooks.json mcp.json`; optional path fields. Local dev: copy into `~/.cursor/plugins/local/<name>` and reload; CLI `--plugin-dir` | docs-only (spike manifest passes Cursor's schema validator: verified) | Use default discovery, no path fields. Copy, never symlink |
| V2 | Agent frontmatter: `name`, `description`, `model` (`inherit` or model ID, `[k=v]` params), `readonly`, `is_background`. No documented tool-restriction field | docs-only | Tiers → `model:` values (draft in `config.defaults.yaml`); one-line frontmatter values only |
| V3 | 18 agent hook events. Blocking: `preToolUse`, `beforeShellExecution`, `beforeMCPExecution`, `beforeReadFile`, `subagentStart` (deny / exit 2). No `beforeFileEdit`: block edits with `preToolUse` matcher `Write`. `stop` cannot block. Plugin hooks get `CURSOR_PLUGIN_ROOT`; cwd = plugin dir (except `stop`/`subagentStop`) | docs-only | test-lock: `preToolUse` deny **plus** gate `verify-lock` (shell writes are not caught). stage-guard: `stop` `followup_message` + prompt. Simulated payload tests: verified |
| V4 | Yes: several Task calls in one message run concurrently. No documented limit | docs-only | `parallel.max_agents: 4` (unverified), batch above it |
| V5 | Subagents inherit the parent's tools, shell included (`readonly` removes state-changing shell). No plugin-root variable in agent/command/skill text; only hooks and `mcp.json` get one | docs-only | Spec fallback: copy scripts into `.kaotim/bin/` at `/kaotim-init`; `doctor` checks the copy's version |
| V6 | Hooks expose `model`/`model_id` (all events), `subagent_model` (subagentStart), `duration_ms`, `message_count`, `tool_call_count` (subagentStop), `context_tokens` (preCompact). No per-call or per-subagent token counts anywhere (hooks, CLI JSON) | docs-only | Tokens `estimated` (chars ÷ 4); model, duration, counts `measured` from hooks when present |
| V7 | Always Apply (`alwaysApply: true`), Apply to Specific Files (`globs`), Apply Intelligently (`description` only), Apply Manually (none). Plugins ship `.mdc` in `rules/` with the same frontmatter | docs-only | Spec rule types map 1:1. Give every rule a `description` (marketplace validator requires it) |
| V8 | `readonly: true` exists. No path restriction | docs-only | Spec fallback: `check-ownership` + prompt; optional `preToolUse` ownership deny keyed by worktree path (M5) |
| V9 | Resume = new chat + `/kaotim-resume` reading `state.json` (no platform feature needed). CLI substitutes `$ARGUMENTS` and `$1…$99` in commands, else appends the arguments; the IDE behaviour is undocumented | docs-only | Command text must work whether or not `$ARGUMENTS` is substituted |
| V10 | macOS: `python3` 3.9.6 only with Xcode CLT (needed for git/Homebrew/Valet anyway). Linux/WSL/Sail: yes. Windows native: no (Store stub); Herd has no Python; Laragon bundles `python` | verified (box) + docs-only | Recommendation below; **runtime unchanged, user decides** |
| V11 | `git worktree` under `.kaotim/worktrees/` works for setup, tests, commits, ordered merges and conflict detection. Must be gitignored. Subagents share the parent checkout and must `cd <abs path>` | verified (git) / docs-only (subagent cwd) | Absolute worktree paths in task packets; each command as `cd <root> && …` |
| V12 | Answered in spec: built-in `php-laravel` and `python`; others declarative | n/a | none |
| V13 | All Laravel and Python commands run from their stack root, including in fresh worktrees. Must `cd` to root (`uv run --project` keeps the wrong cwd). Laravel 13 `laravel/pao` prints JSON when `CURSOR_AGENT=1` | verified | Adapters prefix `cd <root> &&`; JUnit is the authoritative result |

---

## V1. Manifest fields and local install

**Question.** Exact `plugin.json` fields (rules, skills, agents, commands, hooks, mcp paths); local
install path for development.

**Answer.**
- Manifest at `.cursor-plugin/plugin.json`. Only `name` is required (lowercase kebab-case,
  `^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$`). Optional: `displayName`, `description`, `version`, `author`
  `{name, email}`, `publisher`, `homepage`, `repository`, `license`, `logo`, `keywords`,
  `category`, `tags`, `minClientVersions`, `rules`, `agents`, `skills`, `commands`
  (string or array of paths/globs), `hooks` (path or inline object), `mcpServers` (path, object
  or array), `variables` (JSON Schema). The schema sets `additionalProperties: false`.
- Default discovery when a field is absent: `skills/*/SKILL.md`, `rules/*.{md,mdc,markdown}`,
  `agents/*.{md,mdc,markdown}`, `commands/*.{md,mdc,markdown,txt}`, `hooks/hooks.json`, `mcp.json`.
  Setting a field **replaces** discovery for that component.
- Local development: copy the plugin folder to `~/.cursor/plugins/local/<name>`, restart or run
  Developer: Reload Window, check **Customize**. Symlinks load only if the target is inside that
  folder. A marketplace install with the same name wins over the local copy. Team/Enterprise
  admins can disable local plugins (off by default on Enterprise).
- CLI: `agent --plugin-dir <path>` loads a local plugin directory (`agent --help`, verified).
- An "Agent Plugins" open-standard format (root `plugin.json`) also loads but only carries skills
  and MCP; rules, agents, commands and hooks need the Cursor format.

**Evidence.** [plugins reference](https://cursor.com/docs/reference/plugins) (manifest,
discovery, submission checklist); [plugins: test locally](https://cursor.com/docs/plugins);
`cursor/plugins/schemas/plugin.schema.json`; `spike/evidence/cli/agent-help.txt`. Spike manifest
checked with Cursor's validators:
```
$ node scripts/validate-plugins.mjs        # cursor/plugins, AJV against plugin.schema.json
All plugins validated successfully.
$ node scripts/validate-template.mjs       # cursor/plugin-template
- kaotim-spike: rule file missing "description" in frontmatter: .../rules/spike-manual.mdc
```
(the manual-rule probe has no `description` on purpose; see V7).

**Confidence.** docs-only (runtime loading not observed); manifest validity verified.

**Impact.** The spec's layout (§3) matches the default folders. No path fields needed.
Appendix D's install text ("place the plugin folder in `~/.cursor/plugins/local`") is correct;
add "copy, do not symlink" and the Enterprise admin setting.

**Decided fallback.** None needed. Use default discovery.

## V2. Subagent frontmatter and model names

**Question.** Subagent file frontmatter (name, description, model, read-only, tools) and how model
names are specified.

**Answer.**
- Fields: `name` (default: file name), `description` (used to decide delegation), `model`
  (default `inherit`; or a model ID such as `composer-2`, `gpt-5.6-sol`; per-model options in
  brackets, e.g. `claude-opus-5[effort=high,context=300k]`), `readonly` (boolean),
  `is_background` (boolean).
- No documented `tools` field. The installed CLI's parser also reads `tools` (comma list) and
  `force-default-model`, but that is undocumented, so Kaotim does not rely on it.
- The CLI parses frontmatter **line by line** (`key: value`), not as full YAML, so multi-line
  values (folded `description:`) would be cut. Keep each value on one line.
- `model: fast` appears in first-party Cursor plugins (`cursor-team-kit/agents/ci-watcher.md`,
  `agent-compatibility/agents/*.md`) but is not in the docs.
- Cursor falls back to another model if the named one is blocked by an admin, not on the plan, or
  needs Max Mode on legacy plans. On legacy request-based plans without Max Mode, subagents run
  on Composer whatever the `model` says.
- The parent agent can also name a model when it launches a subagent.

**Evidence.** [subagents: file format, configuration fields, model configuration](https://cursor.com/docs/agent/subagents);
`cursor/plugins` agents (`create-plugin/agents/plugin-architect.md`: `model: inherit`,
`readonly: true`); CLI bundle `~/.local/share/cursor-agent/versions/2026.10.16-e3cb207/` (frontmatter
parser `Mi()` reading `name, description, model, force-default-model, readonly, background|is_background, tools`).
The plugin reference lists only `name` and `description` for agents; the subagents page is the
fuller source.

**Confidence.** docs-only. Exact model IDs depend on the user's plan; `agent models` needs login.

**Impact.** Spec §8.1 field names map to `name`, `description`, `model`, `readonly`; there is no
tool-restriction field. Tier names must become literal `model:` values in agent files (see
`config.defaults.yaml`). A per-repo `config.yaml` tier override cannot change a plugin's static
agent files; it could only work if the orchestrator names the model at spawn time (question Q5).

**Decided fallback.** Draft mapping `strong: inherit`, `standard: inherit`, `fast: fast`
(`fast` docs-only). Confirm IDs with `agent models` before M3.

## V3. Hooks: events, blocking, payloads, plugin root

**Question.** Hook events available; which can block; payload contents; how to run a plugin
script from a hook.

**Answer.**
- Agent events: `sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`, `postToolUseFailure`,
  `subagentStart`, `subagentStop`, `beforeShellExecution`, `afterShellExecution`,
  `beforeMCPExecution`, `afterMCPExecution`, `beforeReadFile`, `afterFileEdit`,
  `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`, `afterAgentThought`; Tab:
  `beforeTabFileRead`, `afterTabFileEdit`; app: `workspaceOpen`.
- Can block: `preToolUse` (`permission: deny`; `ask` is not enforced there), `beforeShellExecution`
  and `beforeMCPExecution` (`allow|deny|ask`), `beforeReadFile`, `subagentStart` (deny),
  `beforeSubmitPrompt` (`continue: false`). Exit code 2 = deny. For permission hooks, invalid JSON
  output blocks; crashes, timeouts and other exit codes fail **open** unless `failClosed: true`.
- **There is no `beforeFileEdit`.** Edits are blocked with `preToolUse` and matcher `Write`
  (also `Delete`). `tool_input` is documented only for Shell; the CLI stream shows write args
  as `{path, fileText}`, so the hook must accept several path keys (the spike checks `path`,
  `file_path`, `target_file`, `filePath`, `targetFile`).
- Cannot block: `afterFileEdit`, `afterShellExecution`, `stop` (it may return `followup_message`,
  which auto-submits a new user message, capped by `loop_limit`, default 5), `sessionStart`
  (fire-and-forget; may return `env` for later hooks and `additional_context`), `preCompact`.
- Common payload: `conversation_id`, `generation_id`, `model`, `model_id`, `model_params`,
  `hook_event_name`, `cursor_version`, `workspace_roots`, `user_email`, `transcript_path`. Env:
  `CURSOR_PROJECT_DIR`, `CURSOR_VERSION`, `CURSOR_USER_EMAIL`, `CURSOR_TRANSCRIPT_PATH`.
- Plugin hooks: Cursor's own plugins call scripts as `bash "${CURSOR_PLUGIN_ROOT}/hooks/x.sh"`
  (`cursor/plugins/advisor/hooks/hooks.json`), and the template uses `./scripts/x.sh`. The CLI
  source sets `CURSOR_PLUGIN_ROOT` (and `CLAUDE_PLUGIN_ROOT`) in the hook environment and runs
  plugin hooks with cwd = plugin install path, except `stop` and `subagentStop`, which run in the
  workspace. Commands run through the shell (heredoc stdin on Unix, PowerShell on Windows).
- Hooks run in the IDE and CLI. Cloud Agents load project, team and enterprise hooks; user
  hooks are excluded and plugin hooks are not listed; `sessionStart`/`sessionEnd` do not run there.
- `subagentStart`/`subagentStop` matchers take the subagent type; Cursor's `advisor` plugin
  matches a custom agent by its name (`"matcher": "^advisor-subagent$"`).

**Evidence.** [hooks](https://cursor.com/docs/agent/hooks) (events, exit codes, schemas,
matchers, env); plugins reference (hooks format); `cursor/plugins` hooks.json files; CLI bundle
(`executeCommandScript`, `P.CURSOR_PLUGIN_ROOT=n`, plugin hook `cwd` selection). Simulated
payloads against the spike hook (`spike/kaotim-spike/scripts/test_spike_hook.py`), Python 3.13
and 3.9:
```
Ran 7 tests in 0.025s
OK        # locked test write denied (relative + absolute path), other writes allowed,
          # migrate:fresh / db:wipe denied, safe shell allowed, CLI round trip prints valid JSON
real 0m0.019s   # one hook invocation
```

**Confidence.** docs-only for runtime behaviour; hook decision logic verified by simulation.

**Impact on §10.**
| Hook | Result |
|---|---|
| `test-lock` | Primary works as designed but via `preToolUse` (Write, Delete), not a "before-edit" event. Shell writes (`sed -i`, `>`) are not caught, so `verify-lock` in every gate stays mandatory. Paths must be normalised from worktree paths (`.kaotim/worktrees/<t>/tests/...`) to repo paths, because `CURSOR_PROJECT_DIR` is the main checkout |
| `ownership` | No documented way to tell which subagent made a tool call. A worktree path does identify the task, so M5 can deny writes outside that task's `owns` (to verify). Fallback stays `check-ownership` |
| `manifest-change` | `afterFileEdit` / `afterShellExecution`, advisory. Fine |
| `stage-guard` | `stop` cannot block. **Do not** use `followup_message` for mid-flight stages — it also continues Task specialists and hangs the parent. Enforce via orchestrator prompts + gates; `awaiting_user` / `awaiting_specialist`; `loop_limit: 1` on stop |
| `subagent-metrics` | `subagentStart`/`subagentStop` give type, model, duration, message and tool-call counts, modified files; no tokens (V6) |
| Laravel/Python guards (C.5, E.5) | `beforeShellExecution` can deny destructive commands live |

Fail-open by default: set `failClosed: true` only on the test-lock and destructive-command hooks,
and keep them fast (< 200 ms; spike hook: 19 ms).

**Decided fallback.** As spec §10, with the changes in the table. Hook commands use
`python3 "${CURSOR_PLUGIN_ROOT}/scripts/kaotim.py" hook <name>` (Cursor's own pattern). Windows
native (PowerShell) is unverified: if `${CURSOR_PLUGIN_ROOT}` does not expand there, the hook
fails open and gates still enforce.

## V4. Parallel subagents

**Question.** Can the orchestrator spawn several subagents concurrently? Limit?

**Answer.** Yes. "Agent sends multiple Task tool calls in a single message, so subagents run
simultaneously." Foreground subagents block until they finish; `is_background: true` returns
at once. `subagentStart` has an `is_parallel_worker` flag. No concurrency limit is documented.
CLI changelog: "Subagents in the CLI. Parallel agents execute locally ... in interactive,
headless, and editor sessions". Each parallel subagent costs its own context ("five subagents
in parallel uses roughly five times the tokens").

**Evidence.** [subagents: parallel execution, performance and cost](https://cursor.com/docs/agent/subagents);
[hooks: subagentStart](https://cursor.com/docs/agent/hooks);
[CLI changelog](https://cursor.com/docs/cli/changelog.md).

**Confidence.** docs-only (concurrency); limit unverified.

**Impact.** Parallel `feature-dev` per task is supported. Foreground parallel spawns fit the
orchestrator loop (wait for all handoffs, then `next-stage`).

**Decided fallback.** `parallel.max_agents: 4`; spawn in batches of at most that many per
message. Lower it if `spike/run_cli_spike.sh` step 05 shows serialisation or errors.

## V5. Shell access and running `scripts/kaotim.py` from subagents

**Question.** Can subagents run shell commands, and can they run `scripts/kaotim.py` via a
plugin-root path?

**Answer.**
- Shell: yes. "Subagents inherit all tools from the parent." `readonly: true` restricts file edits
  and "state-changing shell commands" (the exact rule for what counts is not documented).
- Plugin root: **no** variable is documented for agent, command, skill or rule text.
  `${CURSOR_PLUGIN_ROOT}` is expanded only in `mcp.json` (`command`, `args`, `env`, `cwd`) and set
  as an env var for hooks. Whether it is present in the agent's shell environment is not
  documented (spike step 02 checks). Cursor's own `pstack` agent has to search
  `~/.cursor/plugins/` for its `SKILL.md`, which shows there is no better mechanism. Skills may
  reference scripts by paths relative to the skill folder, but the agent resolves them itself.

**Evidence.** [subagents FAQ: MCP tools / inherit tools; readonly field](https://cursor.com/docs/agent/subagents);
[plugins reference: MCP servers](https://cursor.com/docs/reference/plugins);
[skills: including scripts](https://cursor.com/docs/skills.md);
`cursor/plugins/pstack/agents/poteto-agent.md`.

**Confidence.** docs-only.

**Impact.** Commands, agents and skills cannot reliably name `scripts/kaotim.py` by an absolute
plugin path. **Conflict with the spec:** readonly reviewers (`supervisor`, `structure-reviewer`,
`bug-reviewer`, `explorer`, `pr-writer`) are told to save their handoff under
`.kaotim/handoffs/`, and some to run `kaotim.py` subcommands; `readonly` may forbid both
(question Q3).

**Decided fallback.** Spec fallback: `/kaotim-init` copies `scripts/` into `.kaotim/bin/` with a
version stamp; every prompt calls `python3 .kaotim/bin/kaotim.py …` from the repo root;
`doctor` fails if the copy's version differs from the plugin's. Hooks keep using
`CURSOR_PLUGIN_ROOT`. Proposed for readonly agents (pending Q3): they return the handoff block
only, and the orchestrator saves it with `kaotim.py check-handoff --save`.

## V6. Token usage and model name

**Question.** Do hooks or subagent results expose token usage and the model name?

**Answer.**
- Model: yes. Every agent hook payload has `model` and (when available) `model_id`,
  `model_params`; `subagentStart` has `subagent_model`. The CLI `stream-json` `init` event has
  the model display name.
- Tokens: **no** per-request or per-subagent counts. `subagentStop` gives `duration_ms`,
  `message_count`, `tool_call_count`, `modified_files`, `agent_transcript_path`. `preCompact`
  gives `context_tokens` and `context_window_size` (orchestrator context size at compaction
  only). CLI `json`/`stream-json` results have `duration_ms` but no usage fields.
- Cursor's usage dashboard lists the model per usage row (manual reconciliation only).

**Evidence.** [hooks reference: common schema, subagentStart, subagentStop, preCompact](https://cursor.com/docs/agent/hooks);
[CLI output format](https://cursor.com/docs/cli/reference/output-format.md);
[subagents: parent model and usage pools](https://cursor.com/docs/agent/subagents).

**Confidence.** docs-only.

**Impact.** §12.6 fallback applies. `subagent_end` events can still carry measured `ms`, model,
message and tool-call counts when the hook runs; tokens are `estimated`.

**Decided fallback.** Estimate tokens as characters ÷ 4 of task packets, handoffs and (if
transcripts are enabled) the subagent transcript file at `agent_transcript_path`; tag
`source: estimated`. Model names and durations from hooks tagged `measured`; when hooks did not
run, the orchestrator's `log-event` wrapper records `estimated`. Document reconciliation against
the Cursor usage dashboard in the user guide.

## V7. Rule types

**Question.** Rule types supported and how plugins declare them.

**Answer.** Four, set by frontmatter in `.mdc` files:

| Type | Frontmatter |
|---|---|
| Always Apply | `alwaysApply: true` |
| Apply to Specific Files | `alwaysApply: false` + `globs` (comma-separated string or list) |
| Apply Intelligently (description-triggered) | `alwaysApply: false` + `description`, no `globs` |
| Apply Manually (`@rule`) | `alwaysApply: false`, no `description`, no `globs` |

Plugins ship rules in `rules/` (`.md`, `.mdc`, `.markdown`); project rules in `.cursor/rules/`
must be `.mdc`. Users can switch a rule's mode in Customize. Cursor's plugin-template validator
requires `description` on every rule file, so a marketplace plugin cannot ship a manual-only rule.

**Evidence.** [rules: rule anatomy table](https://cursor.com/docs/context/rules);
plugins reference (rules format, discovery); validator output under V1.

**Confidence.** docs-only.

**Impact.** Spec §9 types map directly: `base-principles` and `minimal-diff` always-apply;
`tdd` description-triggered; generated stack rules glob-scoped (with a `description` too).
Installed plugin rules apply in every chat of the install scope, not only Kaotim runs (Q6).

**Decided fallback.** None needed.

## V8. Path-restricted or read-only subagents

**Question.** Can a subagent be restricted to specific paths or read-only?

**Answer.** Read-only: yes (`readonly: true`). Paths: no documented mechanism. A `preToolUse` hook
can deny writes by path, but it cannot tell which subagent is writing (V3).

**Evidence.** [subagents: configuration fields](https://cursor.com/docs/agent/subagents);
[hooks: preToolUse](https://cursor.com/docs/agent/hooks).

**Confidence.** docs-only.

**Impact / decided fallback.** Spec fallback: `check-ownership` at every handoff and in the gate,
plus the prompt. M5 can add a `preToolUse` deny for writes into `.kaotim/worktrees/<t>/` outside
task `<t>`'s `owns` (the worktree path identifies the task). Reviewers get `readonly: true`
subject to Q3.

## V9. Resuming across chats; command arguments

**Question.** Can a command start a flow that resumes across chats? Where do commands read
`$ARGUMENTS`?

**Answer.**
- Resume: nothing platform-specific is needed. `/kaotim-resume` in a fresh chat reads
  `.kaotim/state.json` through `kaotim.py state show`. The CLI also has `--resume [chatId]` and
  `--continue`; subagents can be resumed by agent ID. None of these is required.
- Arguments: the docs do not describe argument placeholders for commands or skills (`$ARGUMENTS`
  is documented only for prompt-based hooks). The installed CLI substitutes `$ARGUMENTS` (all
  arguments) and `$1`…`$99` in custom command content; with no placeholder it appends the
  arguments after the content. IDE behaviour is undocumented.
- Commands vs skills: the plugins reference still documents `commands/`, but the old commands
  docs page now redirects to Skills, `/migrate-to-skills` turns slash commands into skills with
  `disable-model-invocation: true`, and none of the 17 first-party plugins in `cursor/plugins`
  ships a `commands/` folder. Skills are also invoked with `/skill-name`.

**Evidence.** CLI bundle `src/commands/custom-commands.ts` (`$ARGUMENTS` / `$N` replacement);
[skills: disabling automatic invocation, migrating commands](https://cursor.com/docs/skills.md);
[hooks: prompt-based hooks](https://cursor.com/docs/agent/hooks); `find cursor/plugins -type d -name commands` → none.

**Confidence.** docs-only.

**Impact.** Command files must not depend on substitution. Write them so both cases read well,
e.g. "The feature request is the text after `/kaotim` ($ARGUMENTS)."

**Decided fallback.** Keep `commands/` as the spec says (documented and supported) and word
command bodies so they work with or without substitution. Moving to `disable-model-invocation`
skills is question Q2.

## V10. Python availability

**Question.** Is Python 3.9+ reliably available to the agent's shell on the target platforms?

**Answer.**
| Platform / setup | `python3` ≥ 3.9 on PATH by default? | Notes |
|---|---|---|
| macOS 12.3+ | Only after Xcode Command Line Tools (`/usr/bin/python3` = 3.9.6) | Without CLT the shim opens an install dialog. Git, Homebrew and therefore Valet need CLT, so a Mac with working `git` almost always has it |
| Linux (Debian/Ubuntu desktops, WSL2 Ubuntu) | Yes (distro `python3`) | Minimal containers may lack it. Box: 3.13.5 |
| Windows native | **No** | `python3`/`python` are Microsoft Store redirect stubs unless Python is installed; then often only `py` |
| Laravel Herd (macOS, Windows) | No (ships PHP, Composer, Node, nvm) | On macOS, CLT Python is there if CLT is installed (usual, for git) |
| Laravel Sail | In the container, yes (Sail runtime Dockerfile installs `python3`) | The agent shell runs on the host (macOS, Linux or WSL2), so host rules apply |
| Laravel Valet | Yes via CLT (Homebrew needs it) | macOS only |
| Laragon (Windows) | Bundled Python 3.13, as `python`, on PATH only after "Add Laragon to PATH" or in Laragon's terminal | Not `python3` |

The spike hook and tests run unchanged on Python 3.9 (uv-managed `cpython-3.9`) and 3.13. Note:
Python 3.9 is past upstream end of life, but it is the version macOS CLT ships.

**Evidence.** Box: `python3 --version` → 3.13.5; `uv python find 3.9` +
`python3.9 -m unittest test_spike_hook` → OK. macOS:
[mac.install.guide: system Python](https://mac.install.guide/python/system-default),
[msleigh.io: where is Python on macOS](https://www.msleigh.io/blog/2023/05/14/where-is-python-on-macos/).
Windows: [python-list: Store aliases](https://mail.python.org/pipermail/python-list/2022-August/907205.html),
[discuss.python.org: py launcher and python3 alias](https://discuss.python.org/t/possible-bug-with-py-exe-launcher-in-3-11/20844).
Herd: [herd.laravel.com](https://herd.laravel.com/),
[Herd Windows installation](https://herd.laravel.com/docs/windows/getting-started/installation).
Sail: `laravel/sail` `runtimes/8.4/Dockerfile` (apt installs `python3`). Laragon:
[download page](https://laragon.org/download), [docs](https://laragon.org/docs/easy-to-use).

**Confidence.** verified (Linux box, Python 3.9 compatibility); docs-only (macOS, Windows, Herd,
Valet, Laragon).

**Impact.** Python works without setup on macOS (with CLT), Linux, WSL2 and Sail hosts. Native
Windows is the gap, and Herd-on-Windows users (a common Laravel setup) have Node but not Python.

**Recommendation (not applied; the user decides).** Keep **Python 3.9+, stdlib only**, if native
Windows is not a v1 target or Windows users may be asked to install Python (or use WSL2). Then:
(1) one interpreter probe in `doctor` and in hook commands, trying `python3`, then `python`, then
`py -3`, requiring ≥ 3.9; (2) a clear install hint when none is found; (3) state "Windows: WSL2 or
an installed Python" in the user guide. If native Windows with Herd must work with no extra
install, Node (no dependencies, JSON config) is the alternative, at the cost of the YAML config the
spec assumes. Question Q1.

**Decided fallback.** **User chose Python** (2026-10-19): keep Python 3.9+ stdlib + vendored YAML
(`scripts/kaotim.py`). Native Windows must install Python (or use `py -3`); Node was considered and
rejected by the user after an earlier plan draft.

## V11. Git worktrees for parallel subagents

**Question.** Is a git worktree workflow usable by subagents (cwd handling)?

**Answer.**
- Git side, verified on a throwaway Laravel + `services/ml` Python repo (`spike/v11/worktree.sh`,
  log in `spike/evidence/v11/worktree-log.txt`):
  - `git worktree add .kaotim/worktrees/t1 -b kaotim/plan-001/t1` works. **Not gitignored, the
    main checkout shows `?? .kaotim/`**; with `.kaotim/worktrees/` ignored, `git status` is clean.
  - Fresh worktree setup: `composer install --no-interaction --prefer-dist` + `cp .env.example
    .env.testing` 2.5 s (warm Composer cache); `uv sync` 0.3 s. Then `php artisan test` and
    `uv run pytest` pass inside the worktree, started from an unrelated cwd.
  - Two tasks with disjoint files commit on their branches and merge `--no-ff` in order. Two
    tasks that add the same file: second merge exits 1 (`CONFLICT (add/add)`),
    `git diff --name-only --diff-filter=U` lists the file, `git merge --abort` restores a clean
    tree. `git worktree remove --force` + `prune` cleans up.
  - With a worktree present, main-checkout `pint --test` and `php artisan test` are unaffected,
    and `rg --files` lists no worktree files (gitignore respected).
- Cursor side: subagents share the parent's checkout by default; Cursor can give each subagent
  its own worktree when asked ("isolated project copies"), but the docs do not let you choose the
  path or branch name. Cursor's worktree cleanup (`cursor.worktreeMaxCount`, default 25 per
  machine) can delete "worktrees created outside the manager (for example ... `git worktree
  add`)"; whether that covers worktrees outside `~/.cursor/worktrees` is not stated.

**Evidence.** `spike/evidence/v11/worktree-log.txt`;
[subagents: isolated project copies](https://cursor.com/docs/agent/subagents);
[worktrees: cleanup](https://cursor.com/docs/configuration/worktrees.md).

**Confidence.** verified (git mechanics, setup, commands, merges); docs-only (subagent cwd);
unverified (cleanup scope, Cursor-managed subagent worktrees).

**Impact.** Keep Kaotim-managed worktrees (they give stable paths and branch names that
`state.json` needs). Each task packet carries the **absolute** worktree path; every command is
`cd <abs> && …`; file edits use absolute paths. `/kaotim-init` must add `.kaotim/worktrees/` to
`.gitignore` (already in spec §2.2; now known to be required). Hooks see the main checkout as
`CURSOR_PROJECT_DIR`, so path checks must map worktree paths back.

**Decided fallback.** Worktrees as designed. If a worktree disappears (cleanup), `worktree add`
re-creates it from the task branch (commits survive); `doctor` warns when
`cursor.worktreeMaxCount` is low. If subagents cannot work in a worktree in practice (spike step
05), use the spec fallback: sequential branches with file ownership only.

## V12. Built-in adapters

Answered in the spec: built-in `php-laravel` and `python`; other ecosystems get generated
declarative adapters (§4.6). No spike needed.

## V13. Running each stack's commands from its root

**Question.** Can the agent shell reliably run each detected stack's commands from the right
`root` (env managers such as `uv run`, `poetry run`, `composer`, `npx`)?

**Answer.** Yes, if the command is run **from the stack root**:
- `cd <root> && php artisan test`, `cd <root> && uv run pytest` and `uv run --directory <root>
  pytest` work from any cwd. `uv run --project <root> pytest` resolves the environment but keeps
  the caller's cwd, so pytest collected the wrong directory (exit 2). Running `uv run pytest`
  in the Laravel root fails with `Failed to spawn: pytest`.
- `uv run` creates and syncs a missing `.venv` itself (0.8 s on a fresh copy); `--locked` works.
- **Laravel 13 ships `laravel/pao`** ("agent-optimized output"). When `CURSOR_AGENT=1` is set
  (it is set in this box's agent shell; expected in Cursor agent shells, unverified), `php artisan test`, `vendor/bin/pest`, `vendor/bin/phpunit` and
  `vendor/bin/pint` print one line of JSON instead of the usual output. `PAO_DISABLE=1` restores
  normal output for test runners; Pint has its own agent detection (unset `CURSOR_AGENT`).
- Not run: `poetry`, `pipenv`, `npx` (not installed; no fixture yet). Covered when the mixed and
  JS fixtures arrive (M2).

**Evidence.** `spike/evidence/v11/worktree-log.txt` (section D), `spike/evidence/v13/*`, and:
```
$ php artisan test                       # CURSOR_AGENT=1
{"tool":"pest","result":"passed","tests":3,"passed":3,"assertions":4,"duration_ms":90}
$ cd /tmp && uv run --project <wt>/services/ml pytest -q
E   PermissionError: [Errno 13] Permission denied: '/tmp/sand-box-store-pack/conftest.py'   -> exit 2
```

**Confidence.** verified (Laravel, uv); unverified (poetry, pipenv, npx).

**Impact.** Adapters always run `cd <root> && <command>` (never `--project`). `run-tests` must not
depend on human-readable runner output: JUnit is authoritative (below); pao JSON is a compact
bonus for stdout. `doctor` should report whether pao is active.

**Decided fallback.** As spec: adapters prefix commands per environment manager; `doctor`
reports failures.

---

## Appendix C (`php-laravel`) VERIFY items

| Item | Finding | Confidence |
|---|---|---|
| C.2 `affected: php artisan test {files}` | Several file paths work: `php artisan test tests/Unit/CountWordsTest.php tests/Feature/HealthTest.php` ran 3 tests | verified |
| C.2/C.3 Pest `--dirty` / `--changed` | Pest 5.3 has `--dirty` only (no `--changed`). `--dirty` runs **test files** with uncommitted changes; a change in `app/Actions/CountWords.php` alone → "No dirty tests found". It is not a source→test mapping. Keep the mirror strategy as primary; `--dirty` adds edited tests | verified |
| C.2 `worktree.setup` | `composer install --no-interaction --prefer-dist && cp .env.example .env.testing` works. Without `.env`/`.env.testing`, tests pass with a phpdotenv warning; with an empty `APP_KEY`, HTTP tests error "No application encryption key has been specified" unless `phpunit.xml` sets `APP_KEY` (fixtures do) or setup runs `php artisan key:generate --env=testing` (Q11) | verified |
| C.3 single file through `artisan test` | `php artisan test tests/Unit/CountWordsTest.php` | verified (Pest, PHPUnit) |
| C.3 `--filter` through `artisan test` | `--filter 'EC-1'` and `--filter 'AC-1'` select the matching Pest test | verified (Pest) |
| C.3 `--log-junit <path>` through `artisan test` | Works for Pest and PHPUnit, also with pao active. Assertion → `<failure type="PHPUnit\Framework\ExpectationFailedException">`; missing class / undefined method → `<error type="Error">` with `Class "…" not found` / `Call to undefined method …`. **Syntax error: JUnit file is empty (0 bytes)**, exit 1 (Pest) / 255 (PHPUnit). Test failures exit 2 | verified |
| C.3 wrong-reason signatures | `Class "App\Actions\DoesNotExist" not found`, `Call to undefined method App\Actions\CountWords::nope()`, `syntax error, unexpected token "}"` (ParseError) appear as listed in the spec | verified |
| C.5 test DB isolation | Laravel 13 `phpunit.xml` defaults to `DB_CONNECTION=sqlite`, `DB_DATABASE=:memory:`, `APP_ENV=testing` | verified |
| Lint | `vendor/bin/pint --test` exit 1 on a style issue, 0 when clean | verified |
| Typecheck (Larastan) | Not installed in the fixture yet (M2 fixture work) | unverified |

`verify-red` rule for this ecosystem: every target test has `<failure>`; any `<error>`, an empty or
missing JUnit file, or exit code ≠ 1/2 is a wrong-reason red.

## Appendix E (`python`) VERIFY items

| Item | Finding | Confidence |
|---|---|---|
| E.2 `single: pytest {file}` | `uv run pytest tests/services/test_words.py`, node ids (`file::test`) and `-k ac_1` work | verified |
| E.2 `pytest-testmon` | Not installed in the fixture; behaviour not checked. Only used "when installed" per spec | unverified |
| E.2 worktree setup `uv sync` | 0.3 s in a fresh worktree; `uv run` also auto-syncs | verified |
| E.3 `--junitxml` `<failure>` vs `<error>` | Assertion → `<failure message="AssertionError: assert 2 == 3 …">`. Collection error (bad import at module level) → `<error message="collection failure">`, exit 2. **An `ImportError` raised inside a test body is a `<failure>`, not an `<error>`** (`ImportError: cannot import name 'count_chars'`). So JUnit kind alone is not enough for pytest: the wrong-reason signatures must also be checked against `<failure>` messages | verified |

## Other findings that affect the design

1. **Subagents can spawn subagents (one level).** Docs: "Since Cursor 2.5, subagents can launch
   child subagents ... a subagent launched by another subagent can't launch further ones."
   Spec §2.1 states the opposite as a platform fact. Hub-and-spoke stays a valid design choice;
   enforce it by prompt and optionally by a `subagentStart` hook. Recorded in `decisions.md`.
2. **Laravel 13 skeleton ships `AGENTS.md`/`CLAUDE.md` (Laravel Boost bootstrap)** that tell
   agents to run `composer require laravel/boost --dev` and remote PHP installers before any
   work. Cursor applies `AGENTS.md` automatically. This conflicts with "no new dependencies
   without asking". Removed from the fixtures; `doctor` could flag it (Q10).
3. **`CURSOR_AGENT=1`** is present in this box's agent shell and switches Laravel tools to JSON output
   (V13). Kaotim's parsers must expect that.
4. **Frontmatter**: one-line values only (CLI parser, V2); give every rule and skill a
   `description` (validator, V7). Skill `name` must match its folder name.
5. **Python fixture**: `count_words` and tests pass under pytest, ruff, `ruff format --check`,
   mypy `--strict`.
