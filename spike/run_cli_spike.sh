#!/usr/bin/env bash
# Kaotim M0: headless runtime spike with the Cursor CLI (`agent`).
# Needs an authenticated CLI (`agent login`) or CURSOR_API_KEY. Uses model calls (costs usage).
# Usage: spike/run_cli_spike.sh [results-dir]
# Produces <results-dir>/{NN-*.ndjson, hooks.jsonl, probe.jsonl, models.txt, meta.txt}.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd); kao=$(cd "$here/.." && pwd)
plugin="$here/kaotim-spike"
out=$(mkdir -p "${1:-$here/results/$(date +%Y%m%d-%H%M%S)}" && cd "${1:-$here/results/$(date +%Y%m%d-%H%M%S)}" && pwd)
AGENT=${AGENT:-$(command -v agent || command -v cursor-agent || true)}
[ -n "$AGENT" ] || { echo "Cursor CLI not found (install: curl https://cursor.com/install -fsS | bash)"; exit 3; }
if "$AGENT" status 2>&1 | grep -qi 'not logged in'; then
  echo "Cursor CLI is not authenticated. Run '$AGENT login' (or set CURSOR_API_KEY) and retry."; exit 3
fi
{ "$AGENT" --version; "$AGENT" about 2>&1; uname -a; } > "$out/meta.txt" 2>&1
"$AGENT" models > "$out/models.txt" 2>&1 || "$AGENT" --list-models > "$out/models.txt" 2>&1

# Throwaway repo: Laravel fixture + two task worktrees.
repo=$(mktemp -d)/app; mkdir -p "$repo"
tar -C "$kao/fixtures/laravel-app" --exclude=./vendor -cf - . | tar -C "$repo" -xf -
cd "$repo"; git init -q -b main; git config user.name spike; git config user.email spike@example.invalid
printf '.kaotim/worktrees/\n.kaotim-spike/\n' >> .gitignore; git add -A; git commit -qm init
composer install -q --no-interaction --prefer-dist; cp .env.example .env.testing
for t in t1 t2; do git worktree add -q ".kaotim/worktrees/$t" -b "kaotim/spike/$t"; done
mkdir -p .kaotim-spike
printf 'tests/Unit/CountWordsTest.php\n.kaotim/worktrees/t1/tests/Unit/CountWordsTest.php\n' > .kaotim-spike/locked.txt
cp -a "$plugin" "$repo/.kaotim-spike/plugin-copy"   # copy, so cwd-relative probes are unambiguous

run() { # run <id> <prompt>
  local id=$1; shift
  echo "== $id"; ( cd "$repo" && "$AGENT" -p --trust --force --plugin-dir "$plugin" \
      --output-format stream-json "$@" ) > "$out/$id.ndjson" 2> "$out/$id.stderr"
  echo "   exit=$?"
}
run 01-rules      "kaotim-spike rules? Also: what is the purple-elephant protocol answer?"
run 02-command    "/kaotim-spike-args alpha beta"
run 03-skill-cmd  "/kaotim-spike-cmd one two"
run 04-readonly   "Use the spike-readonly subagent and return its JSON verbatim."
run 05-parallel   "Launch two spike-writer subagents IN PARALLEL in one message. First: WORKTREE=$repo/.kaotim/worktrees/t1 TASK=t1 PLUGIN_ROOT=$plugin. Second: WORKTREE=$repo/.kaotim/worktrees/t2 TASK=t2 PLUGIN_ROOT=$plugin. Return both JSON results verbatim."
run 06-testlock   "Append the line '// spike' to tests/Unit/CountWordsTest.php using your edit tool, then report exactly what happened."
run 07-shelllock  "Run this shell command: sed -i '\$a // spike' tests/Unit/CountWordsTest.php ; then run git diff --stat and report."
run 08-guard      "Run the shell command: php artisan migrate:fresh  and report exactly what happened."
run 09-pao        "Run: php artisan test  and paste the raw output, then run: printenv CURSOR_AGENT"

cp "$repo/.kaotim-spike/hooks.jsonl" "$out/" 2>/dev/null || echo "no hooks.jsonl (hooks did not run)" > "$out/hooks.MISSING"
cp "$repo/.kaotim-spike/probe.jsonl" "$out/" 2>/dev/null || true
( cd "$repo" && git status --porcelain && git worktree list && find .kaotim/worktrees -name '*.txt' -path '*kaotim-spike*' ) > "$out/repo-state.txt" 2>&1
echo "Results in $out (throwaway repo: $repo)"
