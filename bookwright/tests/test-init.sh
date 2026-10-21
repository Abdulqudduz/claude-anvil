#!/usr/bin/env bash
# Structure test: manifest, required directories, and every hook script that
# hooks.json references exists and is executable. Derived from the files on
# disk, so no hand-kept component lists.

set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$PLUGIN_ROOT/hooks/scripts/find_python.sh"
find_python || { echo "FAIL: no python3 with PyYAML (set \$PYTHON, pip install pyyaml, or install uv)"; exit 1; }

"${PY_CMD[@]}" - "$PLUGIN_ROOT" <<'PYEOF'
import json, os, shlex, sys
from pathlib import Path

root = Path(sys.argv[1])
failures = []

manifest = root / ".claude-plugin/plugin.json"
try:
    data = json.loads(manifest.read_text())
    if data.get("name") != "bookwright":
        failures.append(f"plugin.json name is {data.get('name')!r}, not 'bookwright'")
    for key in ("version", "description", "author"):
        if key not in data:
            failures.append(f"plugin.json missing {key!r}")
except (OSError, json.JSONDecodeError) as e:
    failures.append(f"plugin.json unreadable or invalid: {e}")

for rel in ("README.md", "CLAUDE.md", "commands", "agents", "skills", "hooks/hooks.json", "tests"):
    if not (root / rel).exists():
        failures.append(f"{rel} missing")

for kind, pattern in (("command", "commands/*.md"), ("agent", "agents/*.md"), ("skill", "skills/*/SKILL.md")):
    if not list(root.glob(pattern)):
        failures.append(f"no {kind} files match {pattern}")

hooks = json.loads((root / "hooks/hooks.json").read_text())
scripts = 0
for groups in hooks.get("hooks", {}).values():
    for group in groups:
        for hook in group.get("hooks", []):
            if hook.get("type") != "command":
                continue
            for arg in shlex.split(hook["command"]):
                if "${CLAUDE_PLUGIN_ROOT}" not in arg:
                    continue
                scripts += 1
                path = Path(arg.replace("${CLAUDE_PLUGIN_ROOT}", str(root)))
                if not path.is_file():
                    failures.append(f"hook script missing: {arg}")
                elif not os.access(path, os.X_OK):
                    failures.append(f"hook script not executable: {arg}")
if scripts == 0:
    failures.append("hooks.json references no plugin scripts")

for f in failures:
    print(f"FAIL: {f}")
if failures:
    sys.exit(1)
print("PASS: bookwright plugin structure check")
PYEOF
