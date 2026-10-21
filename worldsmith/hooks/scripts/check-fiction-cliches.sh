#!/bin/bash
# PostToolUse hook on Write|Edit: flag fiction cliches in manuscript prose.
#
# The phrase lists live in scripts/patterns.md (categories marked
# `<!-- hook: block -->`), overridable per project via .worldsmith/patterns.md.
# This script only scopes the check to manuscript files and hands the written
# text to `count_patterns.py --check-text`, which matches on word boundaries.
# On a match it reports on stderr and exits 2, which Claude Code feeds back to
# Claude (the write itself has already happened; PostToolUse cannot block it).
set -euo pipefail

# Gate: only run in worldsmith projects (derived from disk; see worldsmith-env.sh)
source "$(dirname "$0")/worldsmith-env.sh"
worldsmith_load_env
if [ "$WORLDSMITH_PROJECT" != "1" ]; then
  exit 0
fi

input=$(cat)
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // ""')
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')

case "$file_path" in
  *.tex|*.md|*.mdx|*.txt) ;;
  *) exit 0 ;;
esac

# Skip files inside the plugin itself (patterns.md and the skills quote these phrases)
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [[ "$file_path" == "$CLAUDE_PLUGIN_ROOT"* ]]; then
  exit 0
fi

# Manuscript files only: README, CLAUDE.md, docs/plans/ and lore are not held
# to fiction-craft standards.
[ "$(worldsmith_classify_path "$file_path")" = "manuscript" ] || exit 0

case "$tool_name" in
  Write) field=content ;;
  Edit) field=new_string ;;
  *) exit 0 ;;
esac

printf '%s' "$input" | jq -r --arg f "$field" '.tool_input[$f] // ""' \
  | python3 "$WORLDSMITH_SCRIPTS_DIR/../../scripts/count_patterns.py" --check-text \
      --project-dir "${CLAUDE_PROJECT_DIR:-.}" --label "$file_path"
