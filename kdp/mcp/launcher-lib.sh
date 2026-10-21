# Shared launcher logic for the kdp-cover MCP server. Sourced (never run) by
# mcp/run.sh and hooks/scripts/detect-kdp-setup.sh so both agree on what
# "ready" means. Callers set KDP_MCP_SRC to the plugin's mcp/ directory.
#
# Where the server runs from, in order:
#   1. $KDP_MCP_SRC itself, when it already has node_modules (a local
#      directory-source plugin, or a manual `npm install`).
#   2. $CLAUDE_PLUGIN_DATA/run-<key>/, a copy of src/ with node_modules
#      symlinked to $CLAUDE_PLUGIN_DATA/deps-<lock key>/node_modules. The
#      plugin root is a per-version cache dir that is replaced on update (and
#      may be read-only), while CLAUDE_PLUGIN_DATA survives updates, so deps are
#      reinstalled only when package.json/package-lock.json change. A real copy
#      of src/ (not NODE_PATH, which ESM ignores) lets Node resolve bare imports
#      by walking up to the symlinked node_modules.

KDP_TSX_REL="node_modules/tsx/dist/cli.mjs"

# Portable content hash of the named files (cksum is POSIX; no sha256sum on macOS).
kdp_hash_files() {
  local f
  for f in "$@"; do
    printf '%s\n' "${f#"$KDP_MCP_SRC"/}"
    cat "$f"
  done | cksum | awk '{print $1 "x" $2}'
}

kdp_lock_key() {
  kdp_hash_files "$KDP_MCP_SRC/package.json" "$KDP_MCP_SRC/package-lock.json"
}

kdp_src_key() {
  local files=()
  while IFS= read -r f; do files+=("$f"); done < <(
    find "$KDP_MCP_SRC/src" "$KDP_MCP_SRC/tsconfig.json" -type f | LC_ALL=C sort
  )
  kdp_hash_files "${files[@]}"
}

kdp_deps_dir() { printf '%s/deps-%s\n' "$CLAUDE_PLUGIN_DATA" "$(kdp_lock_key)"; }
kdp_run_dir() { printf '%s/run-%s-%s\n' "$CLAUDE_PLUGIN_DATA" "$(kdp_lock_key)" "$(kdp_src_key)"; }

# Print the directory to run the server from and return 0, or return 1.
kdp_ready_dir() {
  if [ -f "$KDP_MCP_SRC/$KDP_TSX_REL" ]; then
    printf '%s\n' "$KDP_MCP_SRC"
    return 0
  fi
  if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
    local run
    run="$(kdp_run_dir)"
    if [ -f "$run/.ready" ] && [ -f "$run/$KDP_TSX_REL" ]; then
      printf '%s\n' "$run"
      return 0
    fi
  fi
  return 1
}

# Hold an exclusive install lock while running "$@". A lock whose owner PID is
# gone (for example, a server killed mid-install) is taken over immediately.
kdp_with_lock() {
  local lock="$CLAUDE_PLUGIN_DATA/.install.lock" waited=0 owner rc
  until mkdir "$lock" 2>/dev/null; do
    owner="$(cat "$lock/pid" 2>/dev/null || true)"
    if [ -n "$owner" ] && ! kill -0 "$owner" 2>/dev/null; then
      rm -rf "$lock"
      continue
    fi
    if [ "$waited" -ge 600 ]; then
      echo "kdp: timed out waiting for another dependency install ($lock)" >&2
      return 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
  echo "$$" >"$lock/pid"
  "$@" && rc=0 || rc=$?
  rm -rf "$lock"
  return "$rc"
}

kdp_install_locked() {
  local deps run tmp
  deps="$(kdp_deps_dir)"
  run="$(kdp_run_dir)"

  if [ ! -f "$deps/.ready" ]; then
    command -v npm >/dev/null 2>&1 || {
      echo "kdp: npm is not on PATH; cannot install the kdp-cover MCP dependencies" >&2
      return 1
    }
    echo "kdp: installing kdp-cover MCP dependencies into $deps" >&2
    tmp="$(mktemp -d "$CLAUDE_PLUGIN_DATA/.tmp-deps.XXXXXX")"
    cp "$KDP_MCP_SRC/package.json" "$KDP_MCP_SRC/package-lock.json" "$tmp/"
    # npm output goes to stderr: stdout is the MCP protocol channel.
    if ! (cd "$tmp" && npm ci --omit=dev --no-audit --no-fund --loglevel=error) 1>&2; then
      rm -rf "$tmp"
      echo "kdp: npm ci failed; the kdp-cover MCP server cannot start" >&2
      return 1
    fi
    touch "$tmp/.ready"
    rm -rf "$deps"
    mv "$tmp" "$deps"
  fi

  if [ ! -f "$run/.ready" ]; then
    tmp="$(mktemp -d "$CLAUDE_PLUGIN_DATA/.tmp-run.XXXXXX")"
    cp -R "$KDP_MCP_SRC/src" "$KDP_MCP_SRC/package.json" "$KDP_MCP_SRC/tsconfig.json" "$tmp/"
    ln -s "$deps/node_modules" "$tmp/node_modules"
    touch "$tmp/.ready"
    rm -rf "$run"
    mv "$tmp" "$run"
  fi

  # Drop builds from older plugin versions that have not been used in a week.
  find "$CLAUDE_PLUGIN_DATA" -mindepth 1 -maxdepth 1 \
    \( -name 'deps-*' -o -name 'run-*' -o -name '.tmp-*' \) \
    ! -path "$deps" ! -path "$run" -mtime +7 -exec rm -rf {} + 2>/dev/null || true
}

# Install into CLAUDE_PLUGIN_DATA if needed. Returns non-zero on failure.
kdp_install_data() {
  [ -n "${CLAUDE_PLUGIN_DATA:-}" ] || return 1
  mkdir -p "$CLAUDE_PLUGIN_DATA"
  kdp_with_lock kdp_install_locked
}
