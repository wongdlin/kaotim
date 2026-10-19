#!/usr/bin/env bash
# Spike V13 / Appendix E.3: pytest JUnit <failure> vs <error> for right/wrong-reason reds.
# Usage: spike/v13/python_red.sh <fixture-dir> <out-dir>
set -uo pipefail
src=$(cd "$1" && pwd); out=$2; mkdir -p "$out"
work=$(mktemp -d); cp -a "$src/." "$work/"; rm -rf "$work/.venv"; cd "$work"
cat > tests/test_red.py <<'PY'
from app.services.words import count_words

def test_ac_9_assertion_failure() -> None:
    assert count_words("a b") == 3

def test_ac_8_missing_symbol() -> None:
    from app.services.words import count_chars  # not implemented yet
    assert count_chars("ab") == 2
PY
printf 'import app.services.missing_module\n\ndef test_ac_7_collection():\n    assert True\n' > tests/test_collect.py
uv run -q pytest tests/test_red.py --junitxml "$out/junit.xml" > "$out/red.txt" 2>&1; echo "exit(red)=$?" >> "$out/exit.txt"
uv run -q pytest tests/test_collect.py --junitxml "$out/junit-collect.xml" > "$out/collect.txt" 2>&1; echo "exit(collect)=$?" >> "$out/exit.txt"
rm -rf "$work"
