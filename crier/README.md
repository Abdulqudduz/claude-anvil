# crier: Cross-Posting Plugin for Claude Code

Cross-post blog content to multiple platforms (Dev.to, Hashnode, Bluesky, Mastodon, Medium, Twitter, and more).

## Components

- **Skill** (`/crier:crier [file]`): publish one post, or find what needs cross-posting; holds the rewrite, approval, and failure rules
- **Command**: `/crier:chronicler [since]` (weekly date-scoped cross-posting catch-up)
- **Agents**: `cross-poster` (autonomous bulk publishing), `auditor` (read-only gap, performance, and failure analysis)

Crier is MCP-native: the bundled `.mcp.json` registers a `crier` MCP server (the
globally-installed `crier` CLI run as `crier mcp`), and the skill plus agents
drive it through `mcp__plugin_crier_crier__crier_*` tools.

## Requirements

- [crier](https://pypi.org/project/crier/) CLI installed (`uv tool install 'crier[mcp]'`); this is also the MCP server
- API keys configured via `crier config set`

## Quick Start

```
/crier:crier content/post/my-post/index.md   # Cross-post one post
/crier:chronicler 2w                          # Catch up on the last two weeks
```
