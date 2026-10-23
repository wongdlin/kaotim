#!/usr/bin/env python3
"""Kaotim CLI — python scripts/kaotim.py <subcommand> [options]. Plugin v0.1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as script from scripts/ or .kaotim/bin/
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lib.io_util import fail, ok, usage  # noqa: E402
from lib.paths import find_repo_root  # noqa: E402


def _repo(args) -> Path:
    if getattr(args, "repo", None):
        return Path(args.repo).resolve()
    return find_repo_root()


def cmd_state(args) -> int:
    from lib import state as st

    repo = _repo(args)
    if args.action == "init":
        try:
            data = st.init_state(
                plan_id=args.plan_id or "PLAN-001",
                package=args.package or "default",
                repo=repo,
                force=bool(args.force),
            )
        except ValueError as exc:
            return fail(str(exc), exit_code=2)
        return ok("state initialized", state=data)
    if args.action == "show":
        data = st.read_state(repo)
        if not data:
            return fail("state.json missing", exit_code=1)
        return ok("state", state=data)
    if args.action == "set":
        if not args.json:
            return usage("state set requires --json '{...}'")
        try:
            updates = json.loads(args.json)
        except json.JSONDecodeError as exc:
            return usage(f"invalid json: {exc}")
        try:
            data = st.set_state_fields(updates, repo)
        except ValueError as exc:
            return fail(str(exc), exit_code=2)
        return ok("state updated", state=data)
    if args.action == "complete":
        data = st.complete_run(repo)
        return ok("run completed; state cleared", **data)
    return usage(f"unknown state action: {args.action}")


def cmd_get_package(args) -> int:
    from lib.stack import get_package

    try:
        pkg = get_package(_repo(args), file=args.file)
    except Exception as exc:
        return fail(str(exc), exit_code=1)
    return ok("package", package=pkg)


def cmd_get_stack(args) -> int:
    from lib.stack import get_stack_for_file

    if not args.file:
        return usage("get-stack requires --file")
    try:
        st = get_stack_for_file(_repo(args), args.file)
    except Exception as exc:
        return fail(str(exc), exit_code=1)
    return ok("stack", stack=st)


def cmd_check_handoff(args) -> int:
    from lib.handoff import check_handoff_file, save_handoff, validate_handoff

    if args.save:
        try:
            data = json.loads(args.save)
        except json.JSONDecodeError as exc:
            return usage(f"invalid handoff json: {exc}")
        try:
            path = save_handoff(data, _repo(args), filename=args.out)
        except ValueError as exc:
            return fail(str(exc), exit_code=1)
        return ok("handoff saved", path=str(path))
    if args.file:
        result = check_handoff_file(Path(args.file))
        if not result["ok"]:
            return fail("handoff invalid", exit_code=1, errors=result["errors"])
        return ok("handoff valid", handoff=result["handoff"])
    if args.json:
        try:
            data = json.loads(args.json)
        except json.JSONDecodeError as exc:
            return usage(f"invalid json: {exc}")
        errors = validate_handoff(data)
        if errors:
            return fail("handoff invalid", exit_code=1, errors=errors)
        return ok("handoff valid", handoff=data)
    return usage("check-handoff requires --file, --json, or --save")


def cmd_trim_output(args) -> int:
    from lib.trim import trim_output

    text = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
    trimmed = trim_output(text, max_chars=args.max_chars)
    return ok("trimmed", text=trimmed, chars=len(trimmed))


def cmd_log_event(args) -> int:
    from lib.metrics import log_event

    fields = {}
    if args.json:
        try:
            fields = json.loads(args.json)
        except json.JSONDecodeError as exc:
            return usage(f"invalid json: {exc}")
    event = log_event(args.event, repo=_repo(args), run=args.run, **fields)
    return ok("event logged", event=event)


def cmd_adapter(args) -> int:
    from lib.adapters.registry import (
        get_adapter,
        list_adapters,
        test_signatures,
        validate_declarative,
    )
    from lib.paths import kaotim_dir
    from lib.yaml_util import load_yaml_file

    repo = _repo(args)
    extra = [kaotim_dir(repo) / "adapters", Path(__file__).resolve().parents[1] / "adapters"]
    if args.action == "list":
        return ok("adapters", adapters=list_adapters(extra))
    if args.action == "validate":
        if not args.file:
            return usage("adapter validate requires --file")
        data = load_yaml_file(Path(args.file))
        errors = validate_declarative(data if isinstance(data, dict) else {})
        if errors:
            return fail("adapter invalid", exit_code=1, errors=errors)
        return ok("adapter valid", adapter=data)
    if args.action == "test":
        if not args.id:
            return usage("adapter test requires --id")
        try:
            ad = get_adapter(args.id, search_dirs=extra)
        except KeyError as exc:
            return fail(str(exc), exit_code=1)
        lines = args.lines or []
        if args.file:
            lines = Path(args.file).read_text(encoding="utf-8").splitlines()
        return ok("signature test", **test_signatures(ad, lines))
    return usage(f"unknown adapter action: {args.action}")


def cmd_detect_stack(args) -> int:
    from lib.detect import detect_stack

    digest = detect_stack(_repo(args))
    return ok("detect-stack", digest=digest)


def cmd_validate_stack(args) -> int:
    from lib.validate_stack import validate_stack

    result = validate_stack(_repo(args), dry_run_commands=bool(args.dry_run_commands))
    if not result["ok"]:
        return fail("stack invalid", exit_code=1, **result)
    return ok("stack valid", **result)


def cmd_check_plan(args) -> int:
    from lib.plan import check_plan

    result = check_plan(_repo(args))
    if not result["ok"]:
        return fail("plan invalid", exit_code=1, **result)
    return ok("plan valid", **result)


def cmd_next_stage(args) -> int:
    from lib.metrics import log_event
    from lib.next_stage import advance, evaluate

    repo = _repo(args)
    if args.dry_run:
        ev = evaluate(repo)
        return ok("next-stage dry-run", **ev) if ev.get("can_advance") else fail(ev.get("reason") or "blocked", exit_code=1, **ev)
    result = advance(repo)
    run_id = result.get("plan_id")  # set when complete_run cleared state
    log_event(
        "stage_end" if result.get("advanced") else "stage_blocked",
        repo=repo,
        run=run_id,
        stage=result.get("stage"),
    )
    if result.get("advanced"):
        if result.get("completed"):
            log_event("run_complete", repo=repo, run=run_id, stage="done")
        else:
            log_event("stage_start", repo=repo, run=run_id, stage=result.get("stage"))
        return ok("advanced", **result)
    return fail(result.get("reason") or "not advanced", exit_code=1, **result)


def cmd_gate(args) -> int:
    from lib.gate import run_gate

    only = args.only.split(",") if args.only else None
    result = run_gate(_repo(args), stage=args.stage, task=args.task, scope=args.scope or "full", only=only)
    if not result["ok"]:
        return fail("gate failed", exit_code=1, **result)
    return ok("gate passed", **result)


def cmd_run_tests(args) -> int:
    from lib.gate import run_tests

    files = args.files.split(",") if args.files else None
    result = run_tests(_repo(args), mode=args.mode or "all", task=args.task, files=files)
    if not result["ok"]:
        return fail("tests failed", exit_code=1, **result)
    return ok("tests passed", **result)


def cmd_verify_red(args) -> int:
    from lib.gate import verify_red

    if not args.task:
        return usage("verify-red requires --task")
    result = verify_red(_repo(args), args.task)
    if not result["ok"]:
        return fail("verify-red failed", exit_code=1, **result)
    return ok("verify-red ok", **result)


def cmd_lock_tests(args) -> int:
    from lib.locks import lock_tests

    files = [f for f in (args.files or "").split(",") if f]
    if not args.task or not files:
        return usage("lock-tests requires --task and --files")
    try:
        result = lock_tests(args.task, files, _repo(args))
    except Exception as exc:
        return fail(str(exc), exit_code=1)
    return ok("tests locked", **result)


def cmd_verify_lock(args) -> int:
    from lib.locks import verify_lock

    result = verify_lock(_repo(args), path=args.path, task_id=args.task)
    if not result["ok"]:
        return fail("lock verify failed", exit_code=1, **result)
    return ok("locks ok", **result)


def cmd_unlock_tests(args) -> int:
    from lib.locks import unlock_tests

    if not args.task:
        return usage("unlock-tests requires --task")
    try:
        result = unlock_tests(args.task, _repo(args))
    except Exception as exc:
        return fail(str(exc), exit_code=1)
    from lib.metrics import log_event

    log_event("test_unlocked", repo=_repo(args), task=args.task, reason=args.reason or "manual")
    return ok("unlocked", **result)


def cmd_check_ownership(args) -> int:
    from lib.ownership import check_ownership

    if not args.task:
        return usage("check-ownership requires --task")
    result = check_ownership(_repo(args), args.task)
    if not result["ok"]:
        return fail("ownership violated", exit_code=1, **result)
    return ok("ownership ok", **result)


def cmd_check_layers(args) -> int:
    from lib.layers import check_layers

    result = check_layers(_repo(args))
    if not result["ok"]:
        return fail("layer violations", exit_code=1, **result)
    return ok("layers ok", **result)


def cmd_diff_summary(args) -> int:
    from lib.git_util import diff_summary

    result = diff_summary(since=args.since, cwd=_repo(args))
    return ok("diff", **result)


def cmd_worktree(args) -> int:
    from lib.worktree import worktree_add, worktree_remove

    if not args.task:
        return usage("worktree requires --task")
    if args.action == "add":
        result = worktree_add(_repo(args), args.task)
        return ok("worktree add", **result) if result.get("ok") else fail(result.get("error") or "failed", exit_code=1, **result)
    if args.action == "remove":
        result = worktree_remove(_repo(args), args.task)
        return ok("worktree remove", **result) if result.get("ok") else fail("remove failed", exit_code=1, **result)
    return usage("worktree action must be add|remove")


def cmd_merge_tasks(args) -> int:
    from lib.worktree import merge_tasks

    result = merge_tasks(_repo(args))
    if not result.get("ok"):
        return fail(result.get("error") or "merge failed", exit_code=1, **result)
    return ok("merged", **result)


def cmd_check_regression(args) -> int:
    from lib.ownership import check_regression_tests

    result = check_regression_tests(_repo(args))
    if not result["ok"]:
        return fail("no regression tests", exit_code=1, **result)
    return ok("regression tests present", **result)


def cmd_metrics_summary(args) -> int:
    from lib.metrics import metrics_summary

    result = metrics_summary(run_id=args.run, trend=args.trend or 0, repo=_repo(args))
    return ok("metrics summary", **result)


def cmd_doctor(args) -> int:
    from lib.doctor import doctor

    result = doctor(_repo(args), self_check=bool(args.self_check))
    if not result["ok"]:
        return fail("doctor found issues", exit_code=1, **result)
    return ok("doctor ok", **result)


def cmd_hook(args) -> int:
    from lib.hooks import handle_hook, read_stdin_payload

    payload = read_stdin_payload()
    result = handle_hook(args.name, payload)
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


def cmd_stack_write(args) -> int:
    from lib.init_ops import write_stack_from_detect

    result = write_stack_from_detect(_repo(args), force=bool(args.force))
    if not result.get("ok"):
        return fail("stack write/validation failed", exit_code=1, **result)
    return ok("stack written", **result)


def cmd_init(args) -> int:
    from lib.init_ops import copy_cli_to_bin, write_profile, write_stack_from_detect

    repo = _repo(args)
    copy_cli_to_bin(repo)
    stack_result = write_stack_from_detect(repo, force=bool(args.force))
    profile = write_profile(repo)
    return ok("initialized", stack=stack_result, profile=str(profile))


def cmd_refresh(args) -> int:
    from lib.init_ops import refresh_proposals

    return ok("refresh proposals", **refresh_proposals(_repo(args)))


def cmd_create_pr(args) -> int:
    from lib.pr import create_pr

    result = create_pr(_repo(args), draft=not args.no_draft)
    if not result.get("ok"):
        return fail(result.get("error") or "pr failed", exit_code=1, **result)
    return ok("pr ready", **result)


def cmd_retro(args) -> int:
    from lib.metrics import metrics_summary, read_events
    from lib.state import read_state

    repo = _repo(args)
    state = read_state(repo) or {}
    rid = args.run or state.get("plan_id") or "NO-PLAN"
    summary = metrics_summary(run_id=rid, trend=args.trend or 10, repo=repo)
    events = read_events(rid, repo)
    proposals = []
    rejects = sum(1 for e in events if e.get("event") == "loop_increment" and e.get("counter") == "supervisor_rejects")
    if rejects >= 2:
        proposals.append(
            {
                "metric": "supervisor_rejects",
                "file": "skills/kaotim-plan/SKILL.md",
                "suggestion": "Tighten AC mapping and explorer reuse checks.",
            }
        )
    findings = sum(1 for e in events if e.get("event") == "finding")
    if findings >= 5:
        proposals.append(
            {
                "metric": "findings",
                "file": "agents/bug-reviewer.md",
                "suggestion": "Expand edge-case checklist coverage.",
            }
        )
    if not proposals:
        proposals.append(
            {
                "metric": "baseline",
                "file": "config.defaults.yaml",
                "suggestion": "Not enough history yet; keep defaults.",
            }
        )
    return ok("retro", run=rid, proposals=proposals, summary=summary.get("stats"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kaotim.py", description="Kaotim pipeline CLI")
    p.add_argument("--repo", help="Repository root (default: cwd discovery)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("state")
    sp.add_argument("action", choices=["init", "show", "set", "complete"])
    sp.add_argument("--plan-id")
    sp.add_argument("--package")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--json")
    sp.set_defaults(func=cmd_state)

    sp = sub.add_parser("get-package")
    sp.add_argument("--file")
    sp.set_defaults(func=cmd_get_package)

    sp = sub.add_parser("get-stack")
    sp.add_argument("--file", required=True)
    sp.set_defaults(func=cmd_get_stack)

    sp = sub.add_parser("check-handoff")
    sp.add_argument("--file")
    sp.add_argument("--json")
    sp.add_argument("--save")
    sp.add_argument("--out")
    sp.set_defaults(func=cmd_check_handoff)

    sp = sub.add_parser("trim-output")
    sp.add_argument("--file")
    sp.add_argument("--max-chars", type=int, default=2000)
    sp.set_defaults(func=cmd_trim_output)

    sp = sub.add_parser("log-event")
    sp.add_argument("event")
    sp.add_argument("--run")
    sp.add_argument("--json")
    sp.set_defaults(func=cmd_log_event)

    sp = sub.add_parser("adapter")
    sp.add_argument("action", choices=["list", "validate", "test"])
    sp.add_argument("--file")
    sp.add_argument("--id")
    sp.add_argument("--lines", nargs="*")
    sp.set_defaults(func=cmd_adapter)

    sp = sub.add_parser("detect-stack")
    sp.set_defaults(func=cmd_detect_stack)

    sp = sub.add_parser("validate-stack")
    sp.add_argument("--dry-run-commands", action="store_true")
    sp.set_defaults(func=cmd_validate_stack)

    sp = sub.add_parser("check-plan")
    sp.set_defaults(func=cmd_check_plan)

    sp = sub.add_parser("next-stage")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_next_stage)

    sp = sub.add_parser("gate")
    sp.add_argument("--stage", required=True)
    sp.add_argument("--task")
    sp.add_argument("--scope", choices=["full", "task"])
    sp.add_argument("--only")
    sp.set_defaults(func=cmd_gate)

    sp = sub.add_parser("run-tests")
    sp.add_argument("--mode", choices=["single", "affected", "all"])
    sp.add_argument("--task")
    sp.add_argument("--files")
    sp.set_defaults(func=cmd_run_tests)

    sp = sub.add_parser("verify-red")
    sp.add_argument("--task", required=True)
    sp.set_defaults(func=cmd_verify_red)

    sp = sub.add_parser("lock-tests")
    sp.add_argument("--task", required=True)
    sp.add_argument("--files", required=True)
    sp.set_defaults(func=cmd_lock_tests)

    sp = sub.add_parser("verify-lock")
    sp.add_argument("--path")
    sp.add_argument("--task")
    sp.set_defaults(func=cmd_verify_lock)

    sp = sub.add_parser("unlock-tests")
    sp.add_argument("--task", required=True)
    sp.add_argument("--reason")
    sp.set_defaults(func=cmd_unlock_tests)

    sp = sub.add_parser("check-ownership")
    sp.add_argument("--task", required=True)
    sp.set_defaults(func=cmd_check_ownership)

    sp = sub.add_parser("check-layers")
    sp.set_defaults(func=cmd_check_layers)

    sp = sub.add_parser("diff-summary")
    sp.add_argument("--since")
    sp.set_defaults(func=cmd_diff_summary)

    sp = sub.add_parser("worktree")
    sp.add_argument("action", choices=["add", "remove"])
    sp.add_argument("--task", required=True)
    sp.set_defaults(func=cmd_worktree)

    sp = sub.add_parser("merge-tasks")
    sp.set_defaults(func=cmd_merge_tasks)

    sp = sub.add_parser("check-regression-tests")
    sp.set_defaults(func=cmd_check_regression)

    sp = sub.add_parser("metrics-summary")
    sp.add_argument("--run")
    sp.add_argument("--trend", type=int)
    sp.set_defaults(func=cmd_metrics_summary)

    sp = sub.add_parser("doctor")
    sp.add_argument("--self", dest="self_check", action="store_true")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("hook")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_hook)

    sp = sub.add_parser("stack-write")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_stack_write)

    sp = sub.add_parser("init")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("refresh")
    sp.set_defaults(func=cmd_refresh)

    sp = sub.add_parser("create-pr")
    sp.add_argument("--no-draft", action="store_true")
    sp.set_defaults(func=cmd_create_pr)

    sp = sub.add_parser("retro")
    sp.add_argument("--run")
    sp.add_argument("--trend", type=int)
    sp.set_defaults(func=cmd_retro)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        return fail(f"internal error: {exc}", exit_code=2)


if __name__ == "__main__":
    sys.exit(main())
