#!/bin/bash
# Launch the kdp-cover MCP server. stdout is the MCP stdio channel, so every
# diagnostic goes to stderr. See launcher-lib.sh for where the server runs from.
#
#   run.sh                 start the server (installing deps first if needed)
#   run.sh --install-only  install deps into CLAUDE_PLUGIN_DATA and exit
set -euo pipefail

KDP_MCP_SRC="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=launcher-lib.sh
. "$KDP_MCP_SRC/launcher-lib.sh"

if ! dir="$(kdp_ready_dir)"; then
  if [ -z "${CLAUDE_PLUGIN_DATA:-}" ]; then
    echo "kdp: MCP dependencies are missing. Run 'npm install' in $KDP_MCP_SRC first" >&2
    exit 1
  fi
  kdp_install_data || exit 1
  dir="$(kdp_ready_dir)" || {
    echo "kdp: dependency install finished but the server is still not runnable" >&2
    exit 1
  }
fi

[ "${1:-}" = "--install-only" ] && exit 0

# Mark this build as in use so the week-old pruning never removes it.
if [ "$dir" != "$KDP_MCP_SRC" ]; then
  touch "$dir" "$(dirname "$(readlink "$dir/node_modules")")" 2>/dev/null || true
fi

# Node uses tsx's package entrypoint directly: Codex's plugin cache does not
# preserve npm's node_modules/.bin symlinks.
exec node "$dir/$KDP_TSX_REL" "$dir/src/index.ts"
