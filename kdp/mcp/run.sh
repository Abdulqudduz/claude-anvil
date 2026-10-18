#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
TSX_CLI="$DIR/node_modules/tsx/dist/cli.mjs"
[ -f "$TSX_CLI" ] || { echo "Run 'npm install' in $DIR first" >&2; exit 1; }
# Invoke the pinned package entrypoint directly. Codex's plugin cache copies package files but
# does not preserve the node_modules/.bin symlinks created by npm.
exec node "$TSX_CLI" "$DIR/src/index.ts"
