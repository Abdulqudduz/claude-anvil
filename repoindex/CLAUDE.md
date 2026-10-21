# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin for the [repoindex](https://github.com/queelius/repoindex) local git catalog: two agents, five slash commands, and a `workflows` router skill on top of the repoindex MCP server.

**Prerequisite**: repoindex CLI **2.2 or newer** installed and on PATH (e.g. `uv tool install -e <repoindex checkout>`), database populated (`repoindex refresh --external`), and the repoindex MCP server configured at user scope (`claude mcp add -s user repoindex -- repoindex mcp`). 2.2 is the floor because the plugin relies on view re-sync on open (`v_repo_stats`, `v_stale_repos`) and on the MCP server running the CLI through its own interpreter (`python -m repoindex`), so its `refresh`/`tag`/`export` tools do not depend on PATH. PATH is still needed for the Bash commands (`repo-polish`, `/repo-sprint`, `/repo-audit`, `/repo-week`, `/repo-mirror`).

**Why no `.mcp.json`**: the plugin is disabled at user scope and enabled per repo, but the MCP tools should be available everywhere, so the server is configured at user scope instead; a plugin `.mcp.json` would vanish whenever the plugin is disabled, rename the tools to `mcp__plugin_repoindex_repoindex__*` (breaking every `mcp__repoindex__*` grant here), and duplicate the user-scope server when both exist.

## Architecture

MCP tools are the primary read path. Single questions go straight to `run_sql`; slash commands cover fixed-shape recurring tasks; agents cover multi-step work that needs judgment or writes files.

Agents:

1. **`repo-polish`** (inherit): single-repo release preparation. Audits a repo, generates boilerplate via `repoindex ops generate`, writes prose (README, forge description, topics) with AI judgment, re-audits.
2. **`repo-explorer`** (sonnet): open-ended multi-query analysis with narrative synthesis. Not for one-query questions.

Slash commands: `/repo-sprint` (the triage entry point), `/repo-status`, `/repo-audit`, `/repo-week`, `/repo-mirror`.

### Tool access

repoindex MCP tools:
- `get_manifest()`: database overview, including precomputed health counts (`dirty`, `unpushed`, `stale`, `published`, `unpublished`, `doi_count`) and `refresh_stale` (last refresh older than 7 days). Prefer these over recomputing them by hand.
- `get_schema(table?)`: SQL DDL introspection
- `run_sql(query)`: read-only SQL (SELECT/WITH, max 500 rows, no bind parameters: inline values with single quotes doubled)
- `tag(repo, action, tag)`: manage user-assigned tags (`action`: add, remove, list)
- `export(output_dir, language?, dirty?, tag?, recent?)`: produce arkiv archives
- `refresh(github?, pypi?, cran?, external?, forge_events?, full?)`: trigger metadata refresh (all flags default false; local sources always run)

The tool descriptions in the live session are authoritative; re-check them (and `get_schema()`) before editing prompts.

CLI through Bash, where no MCP equivalent exists: `ops generate` / `ops set-*` (repo-polish), `ops audit --json` (/repo-sprint, /repo-audit), `digest --json` (/repo-week), `ops mirror` (/repo-mirror). Scope each command's `allowed-tools` to the exact subcommand (`Bash(repoindex ops audit:*)`), never bare `Bash`. `ops` commands select repos with `--language`/`--tag`/`--recent`/`--dirty`; positional query strings error.

### Design principle

Reuse upstream definitions instead of re-deriving them. Stale is the `v_stale_repos` view; quality gaps are `ops audit` checks (with their own `check_id`, category, severity); activity rollups are `repoindex digest`. Do not hand-code parallel versions in SQL. Delegate deterministic file generation to `ops generate`; use AI judgment only for prose.

Known gap: there is no version-drift check (published registry version vs latest git tag). Comparing version strings in SQL was noise (zenodo snapshot versions, `0.8` vs `v0.8.0`, older tags), so it was removed. A proper check needs an upstream view or manifest field computed with `packaging.version`.

## Editing Conventions

- Agent frontmatter needs `name`, `description` (with `<example>` blocks), `tools`, `model`, `color`
- The `description` field contains trigger phrases for auto-detection; be specific
- MCP tools use the `mcp__repoindex__*` prefix
- Commit messages use conventional prefixes: `feat(repoindex):`, `fix(repoindex):`, `docs(repoindex):`

## SQL Data Model (for reference when editing prompts)

Main tables in `~/.repoindex/index.db`, all joined through `repo_id`:

- **repos**: identity (`name`, `path`; names are not unique), git status (`is_clean`, `ahead`, `behind`), metadata (`language`, `description`, `keywords`), `has_*` asset flags, citation metadata (`citation_*`), and forge metadata abstracted across GitHub/Gitea (`forge_id`, `forge_owner`, `forge_name`, `forge_description`, `stars`, `topics`, `is_archived`, `is_fork`, `is_private`)
- **publications**: one row per repo+registry: `registry`, `package_name`, `current_version`, `published`, `doi`, `concept_doi`, `downloads_total`, `downloads_30d`
- **events**: `type`, `timestamp`, `ref`, `message`, `author`. Count releases as `type IN ('git_tag', 'release')`; forge events appear only after `refresh(forge_events=true)`
- **tags**: `tag`, `source`
- Also: `repos_fts` (FTS5; use `MATCH`), `refresh_log`, `scan_errors`, and the views `v_active_repos`, `v_stale_repos`, `v_repo_stats`

Do not hard-code enumerations (registries, event types, tag sources, tag prefixes) in prompts; tell the model to query them (`SELECT DISTINCT registry FROM publications`, etc.). Stale means `v_stale_repos` (no commit in 180 days); the manifest's `stale` count is `COUNT(*)` over it.
