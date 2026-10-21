# repoindex: Claude Code Plugin

Repository intelligence for Claude Code. MCP-driven access to a local git catalog, with slash commands for recurring workflows and agents for multi-step work. Backed by the [repoindex](https://github.com/queelius/repoindex) MCP server.

## Requirements

[repoindex](https://github.com/queelius/repoindex) 2.2 or newer, on PATH, with its MCP server configured at user scope:

```bash
uv tool install -e <repoindex checkout>      # or: uv tool install 'repoindex[mcp]'
repoindex refresh --external
claude mcp add -s user repoindex -- repoindex mcp
```

The plugin ships no `.mcp.json`: the server lives at user scope so its tools stay available even where the plugin is disabled. PATH is needed for the commands and the `repo-polish` agent, which run `repoindex` subcommands through Bash. `/repo-sprint` and `/repo-audit` also need `jq` to project the `ops audit --json` stream.

## Install

```bash
/plugin install repoindex@queelius-plugins
```

## Slash commands

| Command | Purpose |
|---------|---------|
| `/repo-sprint` | Triage and kickoff: dirty, unpushed, active, release candidates, audit gaps, stale, unpublished. Prioritized. |
| `/repo-status [name]` | Collection overview, or single-repo detail if a name is given. |
| `/repo-audit [filters]` | Read-only per-check summary of `repoindex ops audit`. |
| `/repo-week [window]` | Activity rollup via `repoindex digest`. Default 7 days. |
| `/repo-mirror [flags]` | Wrapper around `repoindex ops mirror`. Dry run by default; pass `--force-real` to push. |

## Agents

| Name | Purpose | Model |
|------|---------|-------|
| `repo-polish` | Single-repo release preparation (audit, generate, improve). Writes files. | inherit |
| `repo-explorer` | Open-ended multi-query analysis with narrative synthesis | sonnet |

## Skills

| Skill | When it fires |
|-------|---------------|
| `workflows` | Which tool (MCP call, slash command, agent) fits a given repoindex task, plus tag strategy. |

## Usage

Direct questions go through MCP tools:

- "Show me dirty repos"
- "Which of my Python repos are on PyPI?"
- "What are my most starred repos?"

Slash commands run fixed-shape workflows:

- `/repo-sprint`: what needs attention right now
- `/repo-week 30d`: monthly rollup
- `/repo-status repoindex`: detail view for one repo

Agents handle multi-step jobs:

- "Polish repoindex for release" invokes `repo-polish`.
- "How has my activity shifted between languages over the last six months, and which repos drove it?" invokes `repo-explorer`.

## License

MIT
