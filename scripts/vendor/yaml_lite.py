"""Minimal YAML 1.1 subset loader/dumper for Kaotim configs (stdlib only)."""

from __future__ import annotations

import re
from typing import Any


class YamlError(ValueError):
    pass


def load(text: str) -> Any:
    lines = _preprocess(text)
    if not lines:
        return None
    value, _ = _parse_block(lines, 0, 0)
    return value


def dump(data: Any) -> str:
    return _dump_value(data, 0).rstrip() + "\n"


def _preprocess(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if " #" in line:
            line = _strip_comment(line)
        out.append((indent, line))
    return out


def _strip_comment(line: str) -> str:
    in_q = False
    q = ""
    cleaned: list[str] = []
    for i, ch in enumerate(line):
        if ch in "'\"" and not in_q:
            in_q = True
            q = ch
            cleaned.append(ch)
        elif in_q and ch == q:
            in_q = False
            cleaned.append(ch)
        elif not in_q and ch == "#" and i > 0 and line[i - 1].isspace():
            break
        else:
            cleaned.append(ch)
    return "".join(cleaned).rstrip()


def _parse_block(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[Any, int]:
    if idx >= len(lines):
        return None, idx
    _, line = lines[idx]
    if line.startswith("- ") or line == "-":
        return _parse_list(lines, idx, indent)
    return _parse_map(lines, idx, indent)


def _parse_map(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while idx < len(lines):
        ind, line = lines[idx]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError(f"Unexpected indent: {line}")
        if line.startswith("- ") or line == "-":
            break
        if ":" not in line:
            raise YamlError(f"Expected key: value, got: {line}")
        key, rest = line.split(":", 1)
        key = key.strip().strip("'\"")
        rest = rest.strip()
        idx += 1
        if rest in ("", "|", ">"):
            if idx < len(lines) and lines[idx][0] > indent:
                child_indent = lines[idx][0]
                if rest == "|":
                    value, idx = _parse_literal(lines, idx, child_indent)
                else:
                    value, idx = _parse_block(lines, idx, child_indent)
            else:
                value = None
        else:
            value = _parse_scalar(rest)
        result[key] = value
    return result, idx


def _parse_list(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while idx < len(lines):
        ind, line = lines[idx]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError(f"Unexpected indent in list: {line}")
        if not (line.startswith("- ") or line == "-"):
            break
        item_body = "" if line == "-" else line[2:]
        idx += 1
        if item_body == "":
            if idx < len(lines) and lines[idx][0] > indent:
                value, idx = _parse_block(lines, idx, lines[idx][0])
            else:
                value = None
        elif ":" in item_body and not item_body.lstrip().startswith(("{", "[", "'", '"')):
            # mapping entry starting on the dash line
            key, rest = item_body.split(":", 1)
            obj: dict[str, Any] = {}
            rest = rest.strip()
            child_indent = indent + 2  # conventional 2-space
            if rest in ("", "|", ">"):
                if idx < len(lines) and lines[idx][0] > indent:
                    child_indent = lines[idx][0]
                    if rest == "|":
                        obj[key.strip().strip("'\"")], idx = _parse_literal(
                            lines, idx, child_indent
                        )
                    else:
                        obj[key.strip().strip("'\"")], idx = _parse_block(
                            lines, idx, child_indent
                        )
                else:
                    obj[key.strip().strip("'\"")] = None
            else:
                obj[key.strip().strip("'\"")] = _parse_scalar(rest)
            # continue sibling keys of this list item
            while idx < len(lines):
                nind, nline = lines[idx]
                if nind <= indent:
                    break
                if nline.startswith("- ") or nline == "-":
                    break
                nested, idx = _parse_map(lines, idx, nind)
                obj.update(nested)
            value = obj
        else:
            value = _parse_scalar(item_body)
        result.append(value)
    return result, idx


def _parse_literal(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[str, int]:
    parts: list[str] = []
    while idx < len(lines) and lines[idx][0] >= indent:
        ind, line = lines[idx]
        parts.append((" " * (ind - indent)) + line)
        idx += 1
    return "\n".join(parts), idx


def _parse_scalar(s: str) -> Any:
    if s == "" or s in ("null", "~", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip()) for p in _split_flow(inner)]
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        if not inner:
            return {}
        out: dict[str, Any] = {}
        for part in _split_flow(inner):
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            out[k.strip().strip("'\"")] = _parse_scalar(v.strip())
        return out
    return s


def _split_flow(inner: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_q = False
    q = ""
    for ch in inner:
        if ch in "'\"" and not in_q:
            in_q = True
            q = ch
            buf.append(ch)
        elif in_q and ch == q:
            in_q = False
            buf.append(ch)
        elif not in_q and ch in "[{":
            depth += 1
            buf.append(ch)
        elif not in_q and ch in "]}":
            depth -= 1
            buf.append(ch)
        elif not in_q and ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def _dump_value(data: Any, indent: int) -> str:
    sp = "  " * indent
    if isinstance(data, dict):
        if not data:
            return f"{sp}{{}}\n" if indent else "{}\n"
        lines = []
        for k, v in data.items():
            if isinstance(v, (dict, list)) and v != [] and v != {}:
                lines.append(f"{sp}{k}:\n{_dump_value(v, indent + 1)}")
            elif v == []:
                lines.append(f"{sp}{k}: []\n")
            elif v == {}:
                lines.append(f"{sp}{k}: {{}}\n")
            else:
                lines.append(f"{sp}{k}: {_dump_scalar(v)}\n")
        return "".join(lines)
    if isinstance(data, list):
        if not data:
            return f"{sp}[]\n"
        lines = []
        for item in data:
            if isinstance(item, dict):
                keys = list(item.items())
                if not keys:
                    lines.append(f"{sp}- {{}}\n")
                    continue
                first_k, first_v = keys[0]
                if isinstance(first_v, (dict, list)) and first_v:
                    lines.append(f"{sp}- {first_k}:\n{_dump_value(first_v, indent + 2)}")
                else:
                    lines.append(f"{sp}- {first_k}: {_dump_scalar(first_v)}\n")
                rest = dict(keys[1:])
                if rest:
                    lines.append(_dump_value(rest, indent + 1))
            else:
                lines.append(f"{sp}- {_dump_scalar(item)}\n")
        return "".join(lines)
    return f"{sp}{_dump_scalar(data)}\n"


def _dump_scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "" or any(c in s for c in ":#{}[],&*!|>%@`'\"\n") or s.strip() != s:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s
