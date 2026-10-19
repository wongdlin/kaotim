"""JSON CLI output helpers and atomic file writes (Windows-safe)."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def emit(payload: dict[str, Any], exit_code: int = 0) -> int:
    # ensure_ascii avoids Windows console charmap failures on arrows etc.
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=True) + "\n")
    return exit_code


def ok(summary: str, **extra: Any) -> int:
    payload = {"ok": True, "summary": summary, "details_path": None}
    payload.update(extra)
    return emit(payload, 0)


def fail(summary: str, exit_code: int = 1, **extra: Any) -> int:
    payload = {"ok": False, "summary": summary, "details_path": None}
    payload.update(extra)
    return emit(payload, exit_code)


def usage(summary: str, **extra: Any) -> int:
    return fail(summary, exit_code=2, **extra)


def atomic_write_text(path: Path, text: str, retries: int = 8) -> None:
    """Atomic write. Uses open(..., newline) for Python 3.9 (Path.write_text newline= is 3.10+)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            return
        except OSError as exc:
            last_err = exc
            time.sleep(0.02 * (attempt + 1))
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
    raise OSError(f"atomic_write failed for {path}: {last_err}")


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, event: dict[str, Any], retries: int = 16) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n"
    lock_path = path.with_suffix(path.suffix + ".lock")
    last_err: Exception | None = None
    for attempt in range(retries):
        lock_fh = None
        try:
            lock_fh = open(lock_path, "a+", encoding="utf-8")
            if os.name == "nt":
                import msvcrt

                lock_fh.seek(0)
                msvcrt.locking(lock_fh.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            with open(path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
            return
        except OSError as exc:
            last_err = exc
            time.sleep(0.03 * (attempt + 1))
        finally:
            if lock_fh is not None:
                try:
                    if os.name == "nt":
                        import msvcrt

                        lock_fh.seek(0)
                        msvcrt.locking(lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
                lock_fh.close()
    raise OSError(f"append_jsonl failed for {path}: {last_err}")


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4) if text else 0
