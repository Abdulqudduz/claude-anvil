# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code **plugin** that automates Amazon KDP (Kindle Direct Publishing) workflows for book authors: manuscript auditing, listing craft, and the full publishing pipeline. It handles technical books (LaTeX, math-heavy), fiction, and general nonfiction.

Most of the plugin is Markdown with YAML frontmatter (skills and reference docs). The exception is the TypeScript MCP server in `mcp/`, which has a vitest suite: run `npm test` (and `npm run typecheck`) in `mcp/` after changing it or the launcher scripts.

## Architecture

### Plugin Structure

```
.claude-plugin/plugin.json    # Plugin manifest (name, version, metadata)
.codex-plugin/plugin.json     # Codex manifest (skills + MCP only)
skills/                       # 3 skills, invoked as /kdp:kdp-audit, /kdp:kdp-listing, /kdp:kdp-publish
docs/                         # Reference docs, audit report template, config template
hooks/                        # SessionStart readiness check (silent outside book projects)
mcp/                          # TypeScript MCP server for cover specs, generation, validation
.mcp.json                     # MCP server registration
```

There is no `commands/` directory on purpose: a same-name command shadows the skill inside a plugin, so the skills are the slash commands. Skills support `argument-hint` and `$ARGUMENTS` in their frontmatter and body.

### MCP Component

`mcp/` is the `kdp-cover` MCP server. Tools:
- `kdp_cover_specs`: paperback wrap dimensions, zone layout, bleed, and allowed page range from page count, trim size, and paper type
- `kdp_generate_cover`: front cover image via OpenAI `gpt-image-1`; `quality` (`low`/`medium`/`high`) sets the price, and the result reports `estimated_cost_usd`
- `kdp_generate_full_wrap`: full paperback wrap; returns `pdf_path`, the full-resolution `wrap_png_path` (validate this), and a half-resolution `preview_path` (show this)
- `kdp_validate_cover`: mechanical check of a cover image (eBook, paperback front, or full wrap) against KDP specs; reads images, not PDFs

`OPENAI_API_KEY` must be set in the environment for `kdp_generate_cover`; the other tools work without it.

**Single sources of truth.** Every KDP and pricing constant (paper types and spine rates, trim sizes and page ranges, bleed, DPI, spine-text rules, eBook cover limits, image prices) lives in `mcp/src/lib/kdp-specs.ts`. Tool input schemas live in `mcp/src/lib/schemas.ts`; `index.ts` registers those shapes and each handler parses its input with the same schema, so defaults and validation exist once and the TS types are inferred. When KDP changes a spec, edit `kdp-specs.ts`, update the matching line in `docs/kdp-reference.md`, and run the tests.

**Launcher.** `.mcp.json` runs `mcp/run.sh`, which sources `mcp/launcher-lib.sh`. It runs the server from the plugin root if `mcp/node_modules` exists (a local directory-source plugin, or a manual `npm install`). Otherwise it installs into `${CLAUDE_PLUGIN_DATA}`, which survives plugin updates, while the plugin root is a per-version cache dir that may be read-only:
- `deps-<hash of package.json + package-lock.json>/`: `npm ci --omit=dev`, redone only when those files change
- `run-<lock hash>-<src hash>/`: a copy of `src/` with `node_modules` symlinked to the deps dir (ESM ignores `NODE_PATH`, so the copy is what makes bare imports resolve)
- an install lock with PID takeover, and pruning of builds unused for a week

`tsx` is a runtime dependency for this reason, and the launcher calls `node node_modules/tsx/dist/cli.mjs` directly because Codex's plugin cache drops npm's `.bin` symlinks. stdout is the MCP channel, so all launcher output goes to stderr. The SessionStart hook sources the same library to decide readiness, prewarms the data-dir install in the background (`run.sh --install-only`), and stays silent unless the project has `.claude/kdp.local.md` or a top-level `*.kpf`, `*.epub`, or `manuscript*` file. `src/test/launcher.test.ts` covers the launcher and hook with a fake npm.

### User Config

All skills read `.claude/kdp.local.md` (in the user's target project, not this repo). `docs/user-config-template.md` is the only schema: skills name the fields they use but do not restate the schema. YAML frontmatter holds structured fields (`author`, `kdp`); the markdown body holds free-form notes. If the file is missing, a skill offers to create it from `${CLAUDE_PLUGIN_ROOT}/docs/user-config-template.md`.

### Reference Docs

Skills reference docs via `${CLAUDE_PLUGIN_ROOT}/docs/`:
- `kdp-reference.md`: KDP formatting, cover, metadata, pricing, and submission facts, each with its KDP help-page source
- `kdp-exemplars.md`: blurb examples, keyword strategies, category tactics, author bio conventions
- `audit-report-template.md`: the gap report skeleton `kdp-audit` fills in (the only copy of that structure)
- `user-config-template.md`: the `.claude/kdp.local.md` schema

## Conventions

- Skills (`skills/*/SKILL.md`) have YAML frontmatter (`name`, `description`, optional `argument-hint`), numbered workflow steps with tool annotations in parentheses (`(Read tool)`, `(Bash tool)`), and a "Reference Files" section.
- Skills cite numbers from `kdp-reference.md` or the MCP tools instead of copying them, so a spec change touches `kdp-specs.ts` and one doc line.
- No em-dashes in prose.

## Validation

```bash
# Skill frontmatter has name and description
for f in skills/*/SKILL.md; do echo "=== $f ===" && head -6 "$f" && echo; done

# ${CLAUDE_PLUGIN_ROOT} references point to existing files
grep -roh '\${CLAUDE_PLUGIN_ROOT}/[^`"]*' skills/ | sort -u | while read ref; do
  [ -f "${ref/\$\{CLAUDE_PLUGIN_ROOT\}/.}" ] || echo "BROKEN: $ref"
done

# MCP server and launcher
(cd mcp && npm run typecheck && npm test)
```
