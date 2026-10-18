# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin that provides MCP-driven agents for the [repoindex](https://github.com/queelius/repoindex) local git catalog. The plugin orchestrates multi-step workflows via three specialized agents; all metadata access goes through the repoindex MCP server.

**Prerequisite**: `repoindex` CLI installed and **on PATH** (e.g. `uv tool install -e <repoindex checkout>`), database populated (`repoindex refresh --external`), and the repoindex MCP server configured in `~/.claude.json` (this plugin ships no `.mcp.json`, so the tools appear as `mcp__repoindex__*`). PATH matters even for MCP-only use: the server's `refresh`, `tag`, and `export` tools shell out to the `repoindex` binary.

## Architecture

The plugin is agent-first. Claude Code's built-in MCP support is the primary interface for reading repoindex data; agents orchestrate multi-step workflows on top of those tools, and five slash commands plus a `workflows` router skill provide quick entry points for recurring tasks.

Three agents:

1. **`repo-doctor`** (sonnet): fixed triage workflow. "What needs attention across my repos?" Runs a health check across dirty repos, unpushed commits, quality gaps, stale repos, and publication gaps. Produces a prioritized action list.

2. **`repo-polish`** (inherit): single-repo release preparation. Audits a repo, generates boilerplate via `repoindex ops generate`, writes prose (README, descriptions) with AI judgment, re-audits.

3. **`repo-explorer`** (sonnet): open-ended analysis. "Which of my Python repos are on PyPI?" Cross-references tables with custom SQL and narrative synthesis.

### Tool access

All three agents use the repoindex MCP tools:
- `get_manifest()`: database overview, including precomputed health counts (`dirty`, `unpushed`, `stale`, `published`, `unpublished`, `doi_count`) and `refresh_stale` (last refresh older than 7 days). Prefer these over recomputing them by hand.
- `get_schema(table?)`: SQL DDL introspection
- `run_sql(query)`: read-only SQL queries
- `tag(repo, action, tag)`: manage user-assigned tags (`action`: add, remove, list)
- `export(output_dir, language?, dirty?, tag?, recent?)`: produce arkiv archives
- `refresh(github?, pypi?, cran?, external?, forge_events?, full?)`: trigger metadata refresh (all flags default false; local sources always run)

The tool descriptions in the live session are authoritative; re-check them (and `get_schema()`) before editing agent prompts.

`repo-polish` also uses Bash for `repoindex ops generate` commands (write operations that don't have MCP equivalents). `ops` commands select repos with `--language`/`--tag`/`--recent`/`--dirty`; positional query strings were removed in CLI v0.16 and now error.

### Design principle

Delegate deterministic work to the CLI (`ops generate` for citation files, licenses, GitHub topic sync). Use AI judgment only for prose (README writing, description copywriting, topic suggestions).

## Editing Conventions

- Agent frontmatter needs `name`, `description` (with `<example>` blocks), `tools`, `model`, `color`
- The `description` field contains trigger phrases for auto-detection; be specific
- Tools are listed by name; MCP tools use the `mcp__repoindex__*` prefix
- Commit messages use conventional prefixes: `feat(repoindex):`, `fix(repoindex):`, `docs(repoindex):`

## SQL Data Model (for reference when editing agents)

Four tables in `~/.repoindex/index.db`:

- **repos**: core identity (`name`, `path`), git status (`is_clean`, `ahead`, `behind`), metadata (`language`, `description`, `keywords`), boolean flags (`has_readme`, `has_license`, `has_ci`, `has_citation`, `has_codemeta`, `has_funding`, `has_contributors`, `has_changelog`), and forge metadata abstracted across GitHub/Gitea (`forge_owner`, `forge_name`, `forge_description`, `forge_id`, `stars`, `topics`, `is_archived`)
- **publications**: registry packages (`pypi`/`cran`/`zenodo`/`npm`/`cargo`/`docker`/`rubygems`/`go`), `published` flag, `downloads_total`/`downloads_30d`, `doi`
- **events**: local git activity (`commit`/`git_tag`/`branch`/`merge`), plus forge events (`release`/`pull_request`/`issue`) once `refresh(forge_events=true)` has run, and registry publish events (`pypi_publish`, `cran_publish`, ...). Count releases as `type IN ('git_tag', 'release')`
- **tags**: classification tags, auto-derived from metadata. Source attribution: `user`, `implicit`, `github`, `gitea`, `pyproject`, `pypi`, `cran`, `zenodo`, `go`, `npm`

All joins go through `repo_id` foreign key.

**Stale means one thing.** Upstream's `v_stale_repos` view (no commit in 180 days) is the definition, and the manifest's `stale` count is `COUNT(*)` over it. Agents use that view rather than inventing their own window. Avoid `v_repo_stats`: it still references the removed `github_stars` column and errors.

## Migration Note

Earlier versions had CLI-reference skills (and a user-level `~/.claude/commands/repoindex.md` from the 0.10 era; if one exists, it is stale and should be deleted) (`repoindex`, `repo-polish`) and a `/repo-query` slash command. With the repoindex MCP server providing full CLI parity, those were removed:
- CLI reference: covered by MCP tool descriptions plus `get_schema()`
- `/repo-query`: covered by `run_sql` directly
- `repo-polish` skill: converted to an agent

The plugin's current surface (plugin v2.x, versioned independently of the repoindex CLI) is three agents (`repo-doctor`, `repo-polish`, `repo-explorer`), a `workflows` router skill, and five slash commands (`/repo-week`, `/repo-status`, `/repo-audit`, `/repo-sprint`, `/repo-mirror`). `/repo-status` is a live command, not a removed one.
