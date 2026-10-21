#!/bin/bash
# Detect crier CLI availability on SessionStart.
# Warns if the CLI is missing, or installed without the mcp extra, so the crier
# MCP server and the /crier:crier skill fail loudly, not silently.
# Hook contract: never block, never crash, stay fast (no `crier --version`, ~0.5s).
set -uo pipefail

INSTALL_HINT="Install via: uv tool install 'crier[mcp]'"

crier_bin=$(command -v crier 2>/dev/null) || {
  echo "crier: CLI not found on PATH. $INSTALL_HINT"
  echo "  The crier MCP server, /crier:crier skill, and crier agents all require the crier CLI."
  exit 0
}

# Resolve crier's own interpreter from its entry-point shebang and check that
# both the crier package and the mcp extra are importable there (~30ms).
# find_spec locates modules without importing them.
first_line=""
IFS= read -r first_line < "$crier_bin" 2>/dev/null || true
interp="${first_line#\#!}"
if [[ "$first_line" == '#!'* && "$interp" != *" "* && -x "$interp" ]]; then
  if ! "$interp" -c 'import importlib.util as u, sys; sys.exit(u.find_spec("crier") is None)' 2>/dev/null; then
    echo "crier: CLI found at $crier_bin but its Python environment cannot find the crier package. Reinstall: uv tool install --force 'crier[mcp]'"
  elif ! "$interp" -c 'import importlib.util as u, sys; sys.exit(u.find_spec("mcp") is None)' 2>/dev/null; then
    echo "crier: installed without the mcp extra, so 'crier mcp' (the MCP server) will fail. Reinstall: uv tool install --force 'crier[mcp]'"
  fi
fi
# A shebang we cannot resolve (e.g. '/usr/bin/env python') skips the check
# rather than paying for a full `crier` startup.

exit 0
