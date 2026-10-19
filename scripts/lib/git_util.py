"""Git helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def git_root(cwd: Path | None = None) -> Path | None:
    code, out, _ = _run(["git", "rev-parse", "--show-toplevel"], cwd)
    if code != 0 or not out:
        return None
    return Path(out)


def head_sha(cwd: Path | None = None) -> str | None:
    code, out, _ = _run(["git", "rev-parse", "HEAD"], cwd)
    return out if code == 0 and out else None


def changed_files(since: str | None = None, cwd: Path | None = None) -> list[str]:
    if since:
        code, out, _ = _run(["git", "diff", "--name-only", since], cwd)
    else:
        code, out, _ = _run(["git", "diff", "--name-only", "HEAD"], cwd)
        if code != 0 or not out:
            code, out, _ = _run(["git", "status", "--porcelain"], cwd)
            if code != 0:
                return []
            files = []
            for line in out.splitlines():
                if len(line) >= 4:
                    files.append(line[3:].strip().strip('"'))
            return files
    if code != 0:
        return []
    return [ln for ln in out.splitlines() if ln.strip()]


def diff_summary(since: str | None = None, cwd: Path | None = None) -> dict:
    files = changed_files(since=since, cwd=cwd)
    code, out, _ = _run(
        ["git", "diff", "--numstat", since or "HEAD"],
        cwd,
    )
    additions = deletions = 0
    tests_added = 0
    if code == 0:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                a, d, path = parts[0], parts[1], parts[2]
                if a.isdigit():
                    additions += int(a)
                if d.isdigit():
                    deletions += int(d)
                if "test" in path.lower():
                    tests_added += 1
    return {
        "files": files,
        "file_count": len(files),
        "additions": additions,
        "deletions": deletions,
        "tests_added": tests_added,
    }


def run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    return _run(["git", *args], cwd)
