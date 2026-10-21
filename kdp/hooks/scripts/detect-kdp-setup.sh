#!/bin/bash
# SessionStart: report kdp-cover MCP readiness, but only in book projects, so
# kdp (enabled globally) adds nothing to the context of unrelated sessions.
# Readiness is decided by mcp/launcher-lib.sh, the same code mcp/run.sh uses.
# Hook contract: never block, never fail.
set -uo pipefail

[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || exit 0
KDP_MCP_SRC="$CLAUDE_PLUGIN_ROOT/mcp"
[ -f "$KDP_MCP_SRC/launcher-lib.sh" ] || exit 0

project="${CLAUDE_PROJECT_DIR:-$PWD}"

# A book project has a kdp config, or a manuscript-like file at its top level.
is_book_project() {
  [ -f "$1/.claude/kdp.local.md" ] && return 0
  compgen -G "$1/*.kpf" >/dev/null && return 0
  compgen -G "$1/*.epub" >/dev/null && return 0
  compgen -G "$1/manuscript*" >/dev/null && return 0
  return 1
}
is_book_project "$project" || exit 0

# shellcheck source=../../mcp/launcher-lib.sh
. "$KDP_MCP_SRC/launcher-lib.sh"

if ! command -v node >/dev/null 2>&1; then
  echo "kdp: node is not on PATH, so the kdp-cover MCP tools (kdp_cover_specs, kdp_validate_cover, kdp_generate_cover, kdp_generate_full_wrap) are unavailable. Install Node.js."
  exit 0
fi

if ! kdp_ready_dir >/dev/null; then
  if [ -z "${CLAUDE_PLUGIN_DATA:-}" ]; then
    echo "kdp: kdp-cover MCP dependencies are not installed, so the kdp_* cover tools are unavailable. Run: (cd \"$KDP_MCP_SRC\" && npm install)"
  elif ! command -v npm >/dev/null 2>&1; then
    echo "kdp: npm is not on PATH, so the kdp-cover MCP dependencies cannot be installed and the kdp_* cover tools are unavailable."
  else
    # Prewarm in the background so a slow first install does not outlast the
    # MCP startup timeout; run.sh waits on the same lock.
    mkdir -p "$CLAUDE_PLUGIN_DATA"
    nohup bash "$KDP_MCP_SRC/run.sh" --install-only </dev/null >/dev/null 2>>"$CLAUDE_PLUGIN_DATA/install.log" &
    disown 2>/dev/null || true
    echo "kdp: installing kdp-cover MCP dependencies into $CLAUDE_PLUGIN_DATA (first use after an update). If the kdp_* cover tools are missing, run /mcp to reconnect kdp-cover once it finishes; errors go to $CLAUDE_PLUGIN_DATA/install.log."
  fi
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "kdp: OPENAI_API_KEY is not set, so kdp_generate_cover will fail (the other cover tools work). Set it in your shell environment."
fi

exit 0
