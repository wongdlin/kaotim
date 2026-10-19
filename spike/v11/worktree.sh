#!/usr/bin/env bash
# Spike V11 + V13: per-task git worktrees under .kaotim/worktrees/, per-stack
# setup, running each stack's commands from its root, merging task branches.
# Builds a throwaway "mixed" repo: Laravel app at the root + Python service in services/ml.
# Usage: spike/v11/worktree.sh <kaotim-repo> <out-dir>
set -uo pipefail
kao=$(cd "$1" && pwd); out=$(mkdir -p "$2" && cd "$2" && pwd)
repo=$(mktemp -d)/app; mkdir -p "$repo"
log() { echo "+ $*" | tee -a "$out/log.txt"; }
run() { log "$@"; ( eval "$@" ) >>"$out/log.txt" 2>&1; local rc=$?; echo "  -> exit $rc" | tee -a "$out/log.txt"; return 0; }

copy() { tar -C "$1" --exclude=./vendor --exclude=./.venv --exclude=./.env.testing -cf - . | tar -C "$2" -xf -; }
copy "$kao/fixtures/laravel-app" "$repo"
mkdir -p "$repo/services/ml"; copy "$kao/fixtures/python-app" "$repo/services/ml"
cd "$repo"
git init -q -b main && git config user.name spike && git config user.email spike@example.invalid
git add -A && git commit -qm init || { echo "fixture copy failed"; exit 1; }

log "## A. worktree inside the repo, NOT gitignored"
run "git worktree add -q .kaotim/worktrees/t1 -b kaotim/plan-001/t1"
run "git status --porcelain"
log "## B. add .kaotim/worktrees/ to .gitignore"
printf '.kaotim/worktrees/\n' >> .gitignore && git commit -qam 'ignore worktrees'
run "git status --porcelain"
run "git worktree list"

log "## C. per-stack setup in the worktree (timed)"
wt="$repo/.kaotim/worktrees/t1"
run "cd '$wt' && git merge -q main && time (composer install --no-interaction --prefer-dist -q && cp .env.example .env.testing)"
run "cd '$wt/services/ml' && time uv sync -q"

log "## D. run stack commands from their roots, invoked from an unrelated cwd"
run "cd /tmp && cd '$wt' && php artisan test"
run "cd /tmp && cd '$wt/services/ml' && uv run pytest -q"
run "cd /tmp && uv run --directory '$wt/services/ml' pytest -q"
run "cd /tmp && uv run --project '$wt/services/ml' pytest -q"
run "cd '$wt' && uv run pytest -q   # wrong root on purpose"
run "git -C '$wt' rev-parse --abbrev-ref HEAD"

log "## E. root-level tools in the MAIN checkout while a worktree exists"
run "composer install --no-interaction --prefer-dist -q && cp .env.example .env.testing"
run "vendor/bin/pint --test"
run "env -u CURSOR_AGENT vendor/bin/pint --test 2>&1 | tail -3"
run "php artisan test"
run "rg --files | grep -c '^.kaotim/worktrees/' || true"

log "## F. two parallel tasks with disjoint ownership, merged in order"
run "git worktree add -q .kaotim/worktrees/t2 -b kaotim/plan-001/t2"
run "cd '$wt' && echo '# t1' >> services/ml/src/app/services/words.py && git commit -qam 't1 change'"
run "cd '$repo/.kaotim/worktrees/t2' && echo '// t2' >> app/Actions/CountWords.php && git commit -qam 't2 change'"
run "git merge --no-ff -q -m 'merge t1' kaotim/plan-001/t1"
run "git merge --no-ff -q -m 'merge t2' kaotim/plan-001/t2"
run "git log --oneline --graph | head -8"

log "## G. conflicting tasks: merge must fail and be abortable"
run "git worktree add -q .kaotim/worktrees/t3 -b kaotim/plan-001/t3"
run "git worktree add -q .kaotim/worktrees/t4 -b kaotim/plan-001/t4"
run "cd '$repo/.kaotim/worktrees/t3' && sed -i 's/one/uno/' README.md 2>/dev/null; echo t3 > CONFLICT.txt && git add -A && git commit -qm t3"
run "cd '$repo/.kaotim/worktrees/t4' && echo t4 > CONFLICT.txt && git add -A && git commit -qm t4"
run "git merge --no-ff -q -m 'merge t3' kaotim/plan-001/t3"
run "git merge --no-ff -q -m 'merge t4' kaotim/plan-001/t4"
run "git diff --name-only --diff-filter=U"
run "git merge --abort && git status --porcelain"

log "## H. cleanup"
for t in t1 t2 t3 t4; do run "git worktree remove --force .kaotim/worktrees/$t"; done
run "git worktree prune && git worktree list"
rm -rf "$(dirname "$repo")"
