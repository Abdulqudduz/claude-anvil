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

# --- Interpreter selection ---------------------------------------------------
# Multi-work mode needs a python3 with PyYAML. Hooks pick one via
# worldsmith_python (PATH first, then system interpreters); the tests use the
# same function, and skip the YAML-dependent cases with a clear message when
# no interpreter has PyYAML, rather than passing vacuously.
source "$SCRIPTS/worldsmith-env.sh"
if PY=$(worldsmith_python); then
  HAVE_YAML=1
else
  HAVE_YAML=0
  echo "SKIP: no python3 with PyYAML found; skipping multi-work and eval-safety tests (pip install pyyaml)"
fi

# --- Single-work classification edge cases --------------------------------
run_hook propagation-reminder.sh "$SINGLE" "$SINGLE/timeline.md" "x"
ctx=$(printf '%s' "$OUT" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null)
check "single-work: root-level timeline.md is a role doc (by filename)" \
  "$([[ "$ctx" == *"Propagation check: timeline.md"* ]] && echo 1)"

run_hook propagation-reminder.sh "$SINGLE" "$SINGLE/docs/plans/x-design.md" "x"
check "propagation reminder ignores docs/plans/ (not a canonical doc)" \
  "$([ "$CODE" = 0 ] && [ -z "$OUT" ] && echo 1)"

run_hook check-fiction-cliches.sh "$SINGLE" "$SINGLE/chapters/02.md" '"Fine," she said, amused by the undeclared war.'
check "cliche hook matches on word boundaries (amused, undeclared pass)" \
  "$([ "$CODE" = 0 ] && echo 1)"

run_hook check-fiction-cliches.sh "$SINGLE" "$SINGLE/chapters/03.md" '"Fine," she mused.'
check "cliche hook flags a fancy dialogue tag on a dialogue line" \
  "$([ "$CODE" = 2 ] && [[ "$ERR" == *mused* ]] && echo 1)"

# Project override that drops a phrase from the hook-enforced list
OVR="$WORK/override"
mkdir -p "$OVR/.worldsmith" "$OVR/chapters"
cat > "$OVR/.worldsmith/patterns.md" <<'MD'
## Fancy Dialogue Tags
<!-- hook: block -->
<!-- scope: dialogue-lines -->
exclaimed
MD
run_hook check-fiction-cliches.sh "$OVR" "$OVR/chapters/01.md" '"War," the king declared.'
check "project .worldsmith/patterns.md overrides the hook phrase list" \
  "$([ "$CODE" = 0 ] && echo 1)"

if [ "$HAVE_YAML" = 1 ]; then
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

OUT=$(env -u WORLDSMITH_PROJECT CLAUDE_PROJECT_DIR="$MULTI" bash "$SCRIPTS/detect-worldsmith-project.sh" 2>&1)
check "SessionStart reports the parsed work count and work list" \
  "$([[ "$OUT" == *"with 1 work(s)"* ]] && [[ "$OUT" == *"Book One"* ]] && echo 1)"

# Role docs by filename and directory heuristics still apply in multi-work
# mode when no project.yaml path claims the file (no lore: configured here)
NOLORE="$WORK/nolore"
mkdir -p "$NOLORE/.worldsmith" "$NOLORE/text" "$NOLORE/chapters"
cat > "$NOLORE/.worldsmith/project.yaml" <<'YAML'
universe: Nolore
works:
  - name: Only
    type: novella
    manuscript: text
YAML
run_hook propagation-reminder.sh "$NOLORE" "$NOLORE/timeline.md" "x"
ctx=$(printf '%s' "$OUT" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null)
check "multi-work without lore: root-level timeline.md is a role doc" \
  "$([[ "$ctx" == *"Propagation check: timeline.md"* ]] && echo 1)"
run_hook propagation-reminder.sh "$NOLORE" "$NOLORE/chapters/extra.md" "x"
ctx=$(printf '%s' "$OUT" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null)
check "multi-work: directory heuristics apply outside project.yaml paths" \
  "$([[ "$ctx" == *"Manuscript edited"* ]] && echo 1)"
run_hook check-fiction-cliches.sh "$NOLORE" "$NOLORE/text/ch1.md" "$CLICHE"
check "multi-work: project.yaml manuscript path still wins" \
  "$([ "$CODE" = 2 ] && echo 1)"

# A project.yaml value with a newline survives the trip through $CLAUDE_ENV_FILE
NL="$WORK/newline"
mkdir -p "$NL/.worldsmith"
printf 'universe: U\nworks:\n  - name: "Line one\\nLine two"\n    type: novel\n    manuscript: text\n' > "$NL/.worldsmith/project.yaml"
: > "$WORK/envfile"
env -u WORLDSMITH_PROJECT CLAUDE_PROJECT_DIR="$NL" CLAUDE_ENV_FILE="$WORK/envfile" \
  bash "$SCRIPTS/detect-worldsmith-project.sh" >/dev/null 2>&1
name=$( set +u; source "$WORK/envfile"; printf '%s' "$WORLDSMITH_WORK_0_NAME" )
check "multi-line project.yaml value round-trips through CLAUDE_ENV_FILE" \
  "$([ "$name" = "$(printf 'Line one\nLine two')" ] && echo 1)"

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
env_out=$("$PY" "$SCRIPTS/parse-project-yaml.py" "$EVIL/.worldsmith/project.yaml" --env)
parse_code=$?
check "parse-project-yaml --env succeeds and emits assignments (guards the eval tests below)" \
  "$([ "$parse_code" = 0 ] && [[ "$env_out" == *WORLDSMITH_UNIVERSE=* ]] && echo 1)"
( eval "$env_out" )
check "parse-project-yaml --env output is inert under eval" \
  "$([ ! -e "$WORK/pwned" ] && [ ! -e "$WORK/pwned2" ] && echo 1)"
universe=$( eval "$env_out"; printf '%s' "${WORLDSMITH_UNIVERSE:-}" )
check "parse-project-yaml --env round-trips values literally" \
  "$([ "$universe" = "\$(touch $WORK/pwned)" ] && echo 1)"
fi

# --- Malformed project.yaml is surfaced, not swallowed ----------------------
BAD="$WORK/bad"
mkdir -p "$BAD/.worldsmith" "$BAD/chapters"
printf 'universe: X\nworks: not-a-list\n' > "$BAD/.worldsmith/project.yaml"
OUT=$(env -u WORLDSMITH_PROJECT CLAUDE_PROJECT_DIR="$BAD" bash "$SCRIPTS/detect-worldsmith-project.sh" 2>&1)
check "SessionStart warns when project.yaml cannot be parsed" \
  "$([[ "$OUT" == *"could not parse .worldsmith/project.yaml"* ]] && echo 1)"
run_hook check-fiction-cliches.sh "$BAD" "$BAD/chapters/01.md" "$CLICHE"
check "hooks fall back to single-work heuristics when project.yaml is broken" \
  "$([ "$CODE" = 2 ] && echo 1)"

echo
echo "Tests: $PASS passed, $FAIL failed"
[ "$FAIL" = "0" ]
