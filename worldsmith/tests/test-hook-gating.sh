#!/bin/bash
# Regression tests for worldsmith hook gating and output contracts.
#
# Hooks run as separate processes and do NOT inherit variables that the
# SessionStart hook writes to $CLAUDE_ENV_FILE (that file only feeds Claude's
# later Bash commands). So every hook must derive "is this a worldsmith
# project?" from the .worldsmith/ directory itself. These tests run each hook
# with WORLDSMITH_* unset, exactly as Claude Code does.

set -uo pipefail

SCRIPTS="$(cd "$(dirname "$0")/../hooks/scripts" && pwd)"
PASS=0
FAIL=0

if ! command -v jq >/dev/null 2>&1; then
  echo "FATAL: jq not installed; cannot run hook test harness" >&2
  exit 1
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

check() {
  local desc="$1" ok="$2"
  if [ "$ok" = "1" ]; then
    echo "PASS: $desc"
    PASS=$((PASS+1))
  else
    echo "FAIL: $desc"
    FAIL=$((FAIL+1))
  fi
}

# Run a hook the way Claude Code does: JSON on stdin, project dir in the
# environment, no WORLDSMITH_* variables inherited. Sets OUT, ERR, CODE.
run_hook() {
  local script="$1" proj="$2" file_path="$3" content="$4"
  local input
  input=$(jq -n --arg p "$file_path" --arg c "$content" \
    '{hook_event_name: "PostToolUse", tool_name: "Write", tool_input: {file_path: $p, content: $c}}')
  OUT=$(env -u WORLDSMITH_PROJECT -u WORLDSMITH_WORK_COUNT -u WORLDSMITH_LORE_DIR \
    CLAUDE_PROJECT_DIR="$proj" bash "$SCRIPTS/$script" <<<"$input" 2>"$WORK/stderr")
  CODE=$?
  ERR=$(cat "$WORK/stderr")
}

CLICHE="Her heart raced as the door creaked open."

# --- Single-work worldsmith project -----------------------------------------
SINGLE="$WORK/single"
mkdir -p "$SINGLE/.worldsmith" "$SINGLE/chapters" "$SINGLE/docs"

run_hook check-fiction-cliches.sh "$SINGLE" "$SINGLE/chapters/01.md" "$CLICHE"
check "cliche hook fires in a .worldsmith project with no inherited env" \
  "$([ "$CODE" = 2 ] && echo 1)"

run_hook propagation-reminder.sh "$SINGLE" "$SINGLE/docs/timeline.md" "x"
ctx=$(printf '%s' "$OUT" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null)
event=$(printf '%s' "$OUT" | jq -r '.hookSpecificOutput.hookEventName // empty' 2>/dev/null)
check "propagation reminder emits PostToolUse additionalContext JSON for a doc edit" \
  "$([ "$CODE" = 0 ] && [ "$event" = PostToolUse ] && [[ "$ctx" == *timeline.md* ]] && echo 1)"

run_hook propagation-reminder.sh "$SINGLE" "$SINGLE/chapters/01.md" "x"
ctx=$(printf '%s' "$OUT" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null)
check "propagation reminder emits additionalContext for a manuscript edit" \
  "$([[ "$ctx" == *"Manuscript edited"* ]] && echo 1)"

run_hook propagation-reminder.sh "$SINGLE" "$SINGLE/README.md" "x"
check "propagation reminder is silent for a non-worldbuilding file" \
  "$([ "$CODE" = 0 ] && [ -z "$OUT" ] && echo 1)"

# --- Not a worldsmith project -----------------------------------------------
PLAIN="$WORK/plain"
mkdir -p "$PLAIN/chapters" "$PLAIN/docs"

run_hook check-fiction-cliches.sh "$PLAIN" "$PLAIN/chapters/01.md" "$CLICHE"
check "cliche hook is silent outside a worldsmith project" \
  "$([ "$CODE" = 0 ] && [ -z "$ERR" ] && echo 1)"

run_hook propagation-reminder.sh "$PLAIN" "$PLAIN/docs/timeline.md" "x"
check "propagation reminder is silent outside a worldsmith project" \
  "$([ "$CODE" = 0 ] && [ -z "$OUT" ] && echo 1)"

# --- Multi-work project (project.yaml) --------------------------------------
MULTI="$WORK/multi"
mkdir -p "$MULTI/.worldsmith" "$MULTI/books/one/text" "$MULTI/shared-lore"
cat > "$MULTI/.worldsmith/project.yaml" <<'YAML'
universe: Testverse
lore: shared-lore
works:
  - name: Book One
    type: novel
    manuscript: books/one/text
YAML

run_hook check-fiction-cliches.sh "$MULTI" "$MULTI/books/one/text/ch1.md" "$CLICHE"
check "cliche hook honors project.yaml manuscript path without inherited env" \
  "$([ "$CODE" = 2 ] && echo 1)"

run_hook propagation-reminder.sh "$MULTI" "$MULTI/shared-lore/magic.md" "x"
ctx=$(printf '%s' "$OUT" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null)
check "propagation reminder honors project.yaml lore dir without inherited env" \
  "$([[ "$ctx" == *magic.md* ]] && echo 1)"

# --- project.yaml values must not execute when eval'd -----------------------
EVIL="$WORK/evil"
mkdir -p "$EVIL/.worldsmith"
cat > "$EVIL/.worldsmith/project.yaml" <<YAML
universe: "\$(touch $WORK/pwned)"
works:
  - name: "\`touch $WORK/pwned2\`"
    type: novel
    manuscript: text
YAML
env_out=$(python3 "$SCRIPTS/parse-project-yaml.py" "$EVIL/.worldsmith/project.yaml" --env)
( eval "$env_out" )
check "parse-project-yaml --env output is inert under eval" \
  "$([ ! -e "$WORK/pwned" ] && [ ! -e "$WORK/pwned2" ] && echo 1)"
universe=$( eval "$env_out"; printf '%s' "$WORLDSMITH_UNIVERSE" )
check "parse-project-yaml --env round-trips values literally" \
  "$([ "$universe" = "\$(touch $WORK/pwned)" ] && echo 1)"

echo
echo "Tests: $PASS passed, $FAIL failed"
[ "$FAIL" = "0" ]
