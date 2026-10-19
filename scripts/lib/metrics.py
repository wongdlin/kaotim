"""Metrics event logging and summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import PLUGIN_VERSION
from .io_util import append_jsonl, atomic_write_text
from .paths import ensure_kaotim_dirs, kaotim_dir
from .state import read_state


def metrics_dir(repo: Path | None = None) -> Path:
    return ensure_kaotim_dirs(repo) / "metrics"


def log_event(
    event: str,
    repo: Path | None = None,
    run: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    state = read_state(repo)
    run_id = run or (state or {}).get("plan_id") or "NO-PLAN"
    payload = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run": run_id,
        "event": event,
        "plugin_version": PLUGIN_VERSION,
    }
    payload.update({k: v for k, v in fields.items() if v is not None})
    path = metrics_dir(repo) / f"{run_id}.jsonl"
    append_jsonl(path, payload)
    return payload


def read_events(run_id: str, repo: Path | None = None) -> list[dict[str, Any]]:
    path = kaotim_dir(repo) / "metrics" / f"{run_id}.jsonl"
    if not path.exists():
        return []
    import json

    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    # dedupe by (run, task, attempt, event)
    seen: set[tuple] = set()
    out = []
    for ev in events:
        key = (ev.get("run"), ev.get("task"), ev.get("attempt"), ev.get("event"), ev.get("ts"))
        if key in seen:
            continue
        seen.add(key)
        out.append(ev)
    return out


def metrics_summary(run_id: str | None = None, trend: int = 0, repo: Path | None = None) -> dict[str, Any]:
    state = read_state(repo)
    rid = run_id or (state or {}).get("plan_id") or "NO-PLAN"
    events = read_events(rid, repo)

    stage_times: dict[str, float] = {}
    human_wait_ms = 0.0
    tokens_est = 0
    orch_tokens = 0
    findings = 0
    gate_fails = 0

    wait_start = None
    for ev in events:
        name = ev.get("event")
        if name == "human_wait_start":
            wait_start = ev.get("ts")
        elif name == "human_wait_end" and wait_start:
            # coarse: count events only; duration optional
            human_wait_ms += 0
            wait_start = None
        if name == "orchestrator_tokens":
            tok = (ev.get("tokens") or {})
            if isinstance(tok, dict):
                orch_tokens += int(tok.get("total") or tok.get("in") or 0)
            else:
                orch_tokens += int(tok or 0)
        if name == "subagent_end":
            tok = ev.get("tokens") or {}
            if isinstance(tok, dict):
                tokens_est += int(tok.get("total") or 0)
                if tok.get("source") != "measured":
                    pass
        if name == "finding":
            findings += 1
        if name == "gate":
            for k in ("lint", "typecheck", "build", "tests"):
                res = ev.get(k)
                if isinstance(res, dict) and res.get("ok") is False:
                    gate_fails += 1
        if name in {"stage_start", "stage_end"}:
            stage_times.setdefault(ev.get("stage") or "?", 0)

    md_lines = [
        f"{rid}   plugin v{PLUGIN_VERSION}",
        f"Events {len(events)} | Est. tokens {tokens_est} (orchestrator {orch_tokens})",
        f"Findings {findings} | Gate fails {gate_fails}",
        f"Human wait tracked separately from active agent time.",
        "",
        "Quality signals shown beside cost (estimated tokens tagged estimated).",
    ]
    summary_md = "\n".join(md_lines) + "\n"
    out_path = metrics_dir(repo) / f"{rid}-summary.md"
    atomic_write_text(out_path, summary_md)

    history_line = {
        "run": rid,
        "plugin_version": PLUGIN_VERSION,
        "events": len(events),
        "tokens_est": tokens_est,
        "orchestrator_tokens": orch_tokens,
        "findings": findings,
        "gate_fails": gate_fails,
        "status": (state or {}).get("stage"),
    }
    hist_path = metrics_dir(repo) / "history.jsonl"
    append_jsonl(hist_path, history_line)

    trend_data = []
    if trend and hist_path.exists():
        import json

        lines = [ln for ln in hist_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        for ln in lines[-trend:]:
            try:
                trend_data.append(json.loads(ln))
            except json.JSONDecodeError:
                pass

    return {
        "run": rid,
        "summary_path": str(out_path),
        "markdown": summary_md,
        "stats": history_line,
        "trend": trend_data,
    }
