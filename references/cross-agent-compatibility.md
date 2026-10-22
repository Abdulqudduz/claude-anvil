# Cross-Agent Compatibility and Runtime Guide

This document specifies the discovery mechanisms, configuration conventions, tool mappings, and runtime adaptations across all supported AI coding agent platforms, with priority focus on **Google Antigravity** and **OpenCode**.

---

## 1. Compatibility Matrix

| Feature / Convention | Google Antigravity | OpenCode | Claude Code | Codex / Cursor |
|----------------------|--------------------|----------|-------------|----------------|
| **Skill Discovery**  | `.agents/skills/<name>/SKILL.md`<br>`~/.gemini/config/skills/<name>/` | `.opencode/skills/<name>/`<br>`~/.config/opencode/skills/`<br>`.agents/skills/<name>/` | `.claude-plugin/`<br>`~/.claude/plugins/` | `.cursor/rules/`<br>Workspace root |
| **Manifest Format**  | `SKILL.md` YAML frontmatter (`name`, `description`) | `SKILL.md` YAML frontmatter | `plugin.json` + `marketplace.json` | Prompts / JSON |
| **Progressive Disclosure** | Native (Name & description injected first) | Native (On-demand skill activation) | Manifest loaded; skills on-demand | Manual / Context injection |
| **Lifecycle Hooks**  | `hooks.json` (PreToolUse, PostToolUse, etc.) | Script execution / Git hooks | `hooks/hooks.json` (SessionStart, PostToolUse) | Pre-commit / Tasks |
| **MCP Integration**  | `mcp_config.json` | `.opencode/mcp.json` | `.mcp.json` | `cursor_settings.json` |
| **Subagent Execution**| Delegated tasks / Specialized agent personas | Subagent task runner / Persona phases | `Agent(subagent_type=...)` | Multi-agent prompts |

---

## 2. Google Antigravity Integration

### A. Skill Location and Discovery
Google Antigravity automatically discovers skills during its workspace traversal. To make the Anvil skill available:
- **Project Scope**: Place the repository at `.agents/skills/anvil/` within the project root.
- **Global Scope**: Place the repository at `~/.gemini/config/skills/anvil/` to enable Anvil capabilities across all projects on your machine.
- **In-Repo Development**: In the cloned `claude-anvil` repository itself, the workspace root contains `.agents/skills/anvil` pointing directly to the skill, allowing Antigravity to discover it natively upon opening the repository.

### B. Frontmatter Convention
Antigravity parses the YAML frontmatter block at the top of `SKILL.md`:
```yaml
---
name: anvil
description: >-
  Universal forge for academic research, fiction worldbuilding, technical textbook authoring,
  software package publishing, Amazon KDP book releases, and content operations.
---
```
Antigravity injects only the `name` and `description` into its primary context. The full instructions and supporting references are loaded progressively only when the user's intent matches the description.

### C. Antigravity Tool Mapping

| Conceptual Operation | Claude Code Native Tool | Google Antigravity Native Tool |
|----------------------|-------------------------|--------------------------------|
| Read file content    | `Read(file_path)`       | `view_file(AbsolutePath)`      |
| Create new file      | `Write(file_path, ...)` | `write_to_file(TargetFile, ...)`|
| Edit existing file   | `Edit(file_path, ...)`  | `replace_file_content` / `multi_replace_file_content` |
| Execute shell command| `Bash(command)`         | `run_command(CommandLine, Cwd)`|
| Search directory     | `Glob(pattern)`         | `list_dir` / `run_command`     |
| Text pattern search  | `Grep(pattern)`         | `grep_search(Query, SearchPath)`|
| Web search           | `WebSearch(query)`      | `search_web(query)`            |

### D. Lifecycle Hooks (`hooks.json`)
Antigravity supports lifecycle hooks in `.agents/hooks.json`. To run Anvil's automated checkers (LaTeX macro leak detection and fiction craft cliche audits):
```json
{
  "anvil-craft-guard": {
    "PostToolUse": [
      {
        "matcher": "write_to_file|replace_file_content",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/check_fiction_cliches.py --hook",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "python3 ./scripts/check_latex_macro_leak.py --hook",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

---

## 3. OpenCode Integration

### A. Skill Location and Discovery
OpenCode conforms to standard open-source Agent Skills conventions. Install Anvil via any of:
- **Project Directory**: `.opencode/skills/anvil/` or `.agents/skills/anvil/`
- **Global User Directory**: `~/.config/opencode/skills/anvil/`

### B. OpenCode Invocation
When the user requests an academic research task, textbook chapter drafting, fiction worldbuilding, or package release, OpenCode matches the `description` in `SKILL.md`, reads the primary instructions, and accesses `references/` and `workflows/` via relative paths.

### C. MCP Integration in OpenCode
Configure Anvil's bundled MCP servers (Vista, KDP, Crier) in `.opencode/mcp.json`:
```json
{
  "mcpServers": {
    "vista": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/claude-anvil/vista", "vista-mcp"]
    },
    "kdp-cover": {
      "command": "bash",
      "args": ["/path/to/claude-anvil/kdp/mcp/run.sh"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}"
      }
    }
  }
}
```

---

## 4. Claude Code Backwards Compatibility

The repository retains full backward compatibility with Claude Code:
- The `.claude-plugin/marketplace.json` manifest remains intact and validated.
- All 11 individual plugins (`papermill`, `worldsmith`, `bookwright`, `pub-pipeline`, `kdp`, `vista`, `crier`, `research-agent`, `repoindex`, `mf`, `alex-confidential`) remain in place with their existing `.claude-plugin/plugin.json`, commands, and hooks.
- Claude Code users can continue installing via `/plugin marketplace add queelius/claude-anvil` and `/plugin install <name>@queelius-plugins`.
- Upstream verification scripts (`scripts/check-plugins.py`) and CI workflows continue to pass with 0 errors.

---

## 5. Universal State and Configuration Resolution Order

To avoid hardcoded platform dependencies (like `.claude/`), all Anvil scripts and instructions resolve project state and author configuration using the following fallback cascade:

```
┌────────────────────────────────────────────────────────┐
│ 1. Project-Local Anvil Config (Preferred)              │
│    `.anvil/config.local.md` or `.anvil/state.md`       │
└───────────────────────────┬────────────────────────────┘
                            │ (If not found)
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. Legacy Platform-Specific State Files                │
│    `.claude/pub-pipeline.local.md`                     │
│    `.claude/kdp.local.md`                              │
│    `.papermill/state.md` / `.research/state.md`        │
└───────────────────────────┬────────────────────────────┘
                            │ (If not found)
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. Global User Fallback & Environment Variables        │
│    `~/.config/anvil/config.md`                         │
│    `ANVIL_AUTHOR_NAME`, `ANVIL_AUTHOR_EMAIL`, etc.     │
│    `deets show --format json`                          │
└────────────────────────────────────────────────────────┘
```
