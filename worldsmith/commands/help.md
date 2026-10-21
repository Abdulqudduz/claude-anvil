---
description: Show worldsmith commands, skills, and typical workflows
allowed-tools: Read
---

# /worldsmith:help

Read `${CLAUDE_PLUGIN_ROOT}/README.md`, the single source for this guide, and present a quick reference from it:

1. The Commands table (from "What's Included").
2. The Agents table and the two Skills, briefly.
3. The Hooks: say that they fire automatically in any project with a `.worldsmith/` directory, and that the cliche check flags phrases after a manuscript write (a PostToolUse hook cannot block the write).
4. The Workflows section, condensed to one line per workflow with its example command.

If `$ARGUMENTS` names a command or topic (for example `iterate` or `multi-work`), show only the README sections about it, in full. Do not add commands, hooks, or behavior the README does not describe.
