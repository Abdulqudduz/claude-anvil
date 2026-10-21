#!/usr/bin/env bash
# Component test: every command, agent, and skill (globbed, not listed) has valid
# YAML frontmatter with its required fields, plus cross-file contract asserts:
#   - agents never list AskUserQuestion (Claude Code strips it from subagents)
#   - agents pin `inherit`, `sonnet`, or `haiku` (never an explicit premium model)
#   - every `bookwright:<name>` reference names a real agent, command, or skill
#   - every ${CLAUDE_PLUGIN_ROOT}/... reference resolves to a file
#   - every *-auditor ends its report with the shared verdict enum
#   - every command that points at the decision-handoff procedure can ask
# All failures are collected and reported; exit 1 if any.

set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$PLUGIN_ROOT/hooks/scripts/find_python.sh"
find_python || { echo "FAIL: no python3 with PyYAML (set \$PYTHON, pip install pyyaml, or install uv)"; exit 1; }

"${PY_CMD[@]}" - "$PLUGIN_ROOT" <<'PYEOF'
import re, sys
from pathlib import Path
import yaml

root = Path(sys.argv[1])
failures = []
VERDICT = "VERDICT: PASS / MINOR / SUBSTANTIVE / BLOCKING"
ALLOWED_MODELS = {"inherit", "sonnet", "haiku"}
HANDOFF = "references/decision-handoff.md"


def frontmatter(path):
    text = path.read_text()
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        failures.append(f"{path.relative_to(root)}: no YAML frontmatter")
        return None, text
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        failures.append(f"{path.relative_to(root)}: frontmatter not closed")
        return None, text
    try:
        fm = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as e:
        failures.append(f"{path.relative_to(root)}: invalid YAML frontmatter: {e}")
        return None, text
    if not isinstance(fm, dict):
        failures.append(f"{path.relative_to(root)}: frontmatter is not a mapping")
        return None, text
    return fm, text


def tool_list(value):
    if isinstance(value, list):
        return [str(t).strip() for t in value]
    return [t.strip() for t in str(value or "").split(",") if t.strip()]


def need(path, fm, keys):
    for key in keys:
        if not fm.get(key):
            failures.append(f"{path.relative_to(root)}: missing frontmatter field {key!r}")


agents, commands, skills = {}, {}, {}
for path in sorted(root.glob("agents/*.md")):
    fm, text = frontmatter(path)
    agents[path.stem] = (path, fm, text)
for path in sorted(root.glob("commands/*.md")):
    fm, text = frontmatter(path)
    commands[path.stem] = (path, fm, text)
for path in sorted(root.glob("skills/*/SKILL.md")):
    fm, text = frontmatter(path)
    skills[path.parent.name] = (path, fm, text)

for name, (path, fm, text) in agents.items():
    if fm is None:
        continue
    need(path, fm, ("name", "description", "tools", "model"))
    if fm.get("name") != name:
        failures.append(f"{path.relative_to(root)}: name {fm.get('name')!r} != file stem {name!r}")
    if "AskUserQuestion" in tool_list(fm.get("tools")):
        failures.append(f"{path.relative_to(root)}: agents must not list AskUserQuestion")
    if fm.get("model") not in ALLOWED_MODELS:
        failures.append(f"{path.relative_to(root)}: model {fm.get('model')!r} not in {sorted(ALLOWED_MODELS)}")
    if name.endswith("-auditor") and VERDICT not in text:
        failures.append(f"{path.relative_to(root)}: auditor report lacks the shared '{VERDICT}' line")

for name, (path, fm, text) in commands.items():
    if fm is None:
        continue
    need(path, fm, ("description",))
    if HANDOFF in text and "AskUserQuestion" not in tool_list(fm.get("allowed-tools")):
        failures.append(f"{path.relative_to(root)}: uses the decision handoff but cannot AskUserQuestion")

for name, (path, fm, text) in skills.items():
    if fm is None:
        continue
    need(path, fm, ("name", "description"))
    if fm.get("name") != name:
        failures.append(f"{path.relative_to(root)}: name {fm.get('name')!r} != directory {name!r}")

known = set(agents) | set(commands) | set(skills)
plugin_ref = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"')]+)")
qualified_ref = re.compile(r"\bbookwright:([a-z][a-z0-9-]*)")
for group in (agents, commands, skills):
    for path, _fm, text in group.values():
        for ref in sorted(set(qualified_ref.findall(text))):
            if ref not in known:
                failures.append(f"{path.relative_to(root)}: unknown component bookwright:{ref}")
        for rel in sorted(set(plugin_ref.findall(text))):
            if not (root / rel).is_file():
                failures.append(f"{path.relative_to(root)}: broken reference ${{CLAUDE_PLUGIN_ROOT}}/{rel}")

for f in failures:
    print(f"FAIL: {f}")
if failures:
    print(f"FAIL: {len(failures)} problem(s)")
    sys.exit(1)
print(f"PASS: {len(agents)} agents, {len(commands)} commands, {len(skills)} skills: frontmatter and contracts OK")
PYEOF
