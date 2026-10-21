#!/bin/bash
# Sourced (not executed) by every worldsmith hook script.
#
# Hooks run as separate processes and never inherit variables the SessionStart
# hook writes to $CLAUDE_ENV_FILE (that file only feeds Claude's later Bash tool
# calls). So each hook derives project state from disk on every run, using the
# same signal as detect-worldsmith-project.sh: the .worldsmith/ directory.
#
# After `worldsmith_load_env`:
#   WORLDSMITH_PROJECT=1 inside a worldsmith project, 0 otherwise
#   WORLDSMITH_UNIVERSE, WORLDSMITH_LORE_DIR, WORLDSMITH_WORK_COUNT,
#   WORLDSMITH_WORK_N_{NAME,TYPE,MANUSCRIPT,MASTER,FILETYPES,LORE}
#     set from .worldsmith/project.yaml when it exists (multi-work mode)
#   WORLDSMITH_YAML_ERROR  non-empty when project.yaml exists but could not be
#     parsed (bad YAML, or no python3 with PyYAML); hooks then fall back to the
#     single-work heuristics, and SessionStart surfaces the error.

WORLDSMITH_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Conventional filenames of role docs (the doc roles in the
# worldsmith-methodology skill), recognized anywhere in the project when no
# project.yaml path claims the file. The single list both hooks use.
WORLDSMITH_ROLE_DOC_NAMES=(
  lore.md worldbuilding.md characters.md timeline.md themes.md
  style-guide.md outline.md future-ideas.md
)

# Print the first python3 that can import yaml (PATH first, then system
# interpreters, since an activated venv often lacks PyYAML). Returns 1 if none.
worldsmith_python() {
  local py
  for py in "$(command -v python3 2>/dev/null)" /usr/bin/python3 /usr/local/bin/python3; do
    [ -n "$py" ] && [ -x "$py" ] || continue
    if "$py" -c 'import yaml' 2>/dev/null; then
      printf '%s\n' "$py"
      return 0
    fi
  done
  return 1
}

worldsmith_load_env() {
  local project_dir="${CLAUDE_PROJECT_DIR:-.}"
  WORLDSMITH_PROJECT=0
  WORLDSMITH_YAML_ERROR=""
  [ -d "$project_dir/.worldsmith" ] || return 0
  WORLDSMITH_PROJECT=1

  local yaml="$project_dir/.worldsmith/project.yaml"
  [ -f "$yaml" ] || return 0
  local py env_out
  if ! py=$(worldsmith_python); then
    WORLDSMITH_YAML_ERROR="no python3 with PyYAML found (pip install pyyaml)"
    return 0
  fi
  WORLDSMITH_PYTHON="$py"
  # parse-project-yaml.py shell-quotes every value, so eval is inert
  if ! env_out=$("$py" "$WORLDSMITH_SCRIPTS_DIR/parse-project-yaml.py" "$yaml" --env 2>&1); then
    WORLDSMITH_YAML_ERROR="$env_out"
    return 0
  fi
  eval "$env_out"
}

# Classify a path as manuscript, doc, or other. Call after worldsmith_load_env.
# 1. A parsed project.yaml's manuscript and lore paths win when they match.
# 2. Otherwise (single-work, or a multi-work file outside the configured
#    paths) fall back to heuristics. Doc: directly inside docs/, lore/, or
#    worldbuilding/ (so docs/plans/ is not a doc), or a role-doc filename from
#    WORLDSMITH_ROLE_DOC_NAMES anywhere. Manuscript: inside chapters/,
#    manuscript/, scenes/, or stories/. Doc takes precedence, so
#    chapters/outline.md is a doc.
worldsmith_classify_path() {
  local file_path="$1"
  local project_dir="${CLAUDE_PROJECT_DIR:-.}"
  local i var rel abs

  if [ "${WORLDSMITH_WORK_COUNT:-0}" -gt 0 ] 2>/dev/null; then
    for i in $(seq 0 $((WORLDSMITH_WORK_COUNT - 1))); do
      var="WORLDSMITH_WORK_${i}_MANUSCRIPT"
      rel="${!var:-}"
      [ -n "$rel" ] || continue
      abs="$project_dir/${rel%/}"
      case "$file_path" in "$abs"|"$abs"/*) echo manuscript; return ;; esac
    done
    local lore_dirs=("${WORLDSMITH_LORE_DIR:-}")
    for i in $(seq 0 $((WORLDSMITH_WORK_COUNT - 1))); do
      var="WORLDSMITH_WORK_${i}_LORE"
      lore_dirs+=("${!var:-}")
    done
    for rel in "${lore_dirs[@]}"; do
      [ -n "$rel" ] || continue
      abs="$project_dir/${rel%/}"
      case "$file_path" in "$abs"|"$abs"/*) echo doc; return ;; esac
    done
  fi

  local dirpath base name
  dirpath=$(dirname "$file_path")
  base=$(basename "$file_path")
  case "$(basename "$dirpath")" in
    docs|lore|worldbuilding) echo doc; return ;;
  esac
  for name in "${WORLDSMITH_ROLE_DOC_NAMES[@]}"; do
    [ "$base" = "$name" ] && { echo doc; return; }
  done
  case "/$dirpath/" in
    */chapters/*|*/manuscript/*|*/scenes/*|*/stories/*) echo manuscript; return ;;
  esac
  echo other
}
