#!/bin/bash
# PostToolUse hook: remind about propagation after Write/Edit in worldsmith projects.
# Exits silently if not in a worldsmith project. The reminder is returned as
# hookSpecificOutput.additionalContext JSON: plain stdout from a PostToolUse
# hook goes only to the debug log and never reaches Claude.

set -euo pipefail

# Gate: only run in worldsmith projects (derived from disk; see worldsmith-env.sh)
source "$(dirname "$0")/worldsmith-env.sh"
worldsmith_load_env
if [ "$WORLDSMITH_PROJECT" != "1" ]; then
  exit 0
fi

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.filePath // empty' 2>/dev/null || true)
[ -n "$file_path" ] || exit 0

basename=$(basename "$file_path")
case "$(worldsmith_classify_path "$file_path")" in
  doc)
    reminder="Propagation check: $basename was edited. Check the project's CLAUDE.md for which other docs and manuscript sections may need updating." ;;
  manuscript)
    reminder="Manuscript edited: $basename. Verify this change is consistent with canonical docs. If this introduces a new fact, update the canonical doc first." ;;
  *)
    exit 0 ;;
esac

jq -n --arg ctx "$reminder" \
  '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
