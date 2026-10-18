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

WORLDSMITH_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

worldsmith_load_env() {
  local project_dir="${CLAUDE_PROJECT_DIR:-.}"
  WORLDSMITH_PROJECT=0
  [ -d "$project_dir/.worldsmith" ] || return 0
  WORLDSMITH_PROJECT=1

  local yaml="$project_dir/.worldsmith/project.yaml"
  [ -f "$yaml" ] || return 0
  local env_out
  # parse-project-yaml.py shell-quotes every value, so eval is inert
  env_out=$(python3 "$WORLDSMITH_SCRIPTS_DIR/parse-project-yaml.py" "$yaml" --env 2>/dev/null) || return 0
  eval "$env_out"
}
