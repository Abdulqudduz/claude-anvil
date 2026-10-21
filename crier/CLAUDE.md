# CLAUDE.md (crier plugin)

Editing guidance for the crier Claude Code plugin. Read before editing.

## What this is

crier cross-posts blog content (the blog is the source of truth) to multiple
platforms: Dev.to, Hashnode, Bluesky, Mastodon, Medium, Twitter, and more. The
plugin is the judgment layer; the mechanics live in an external `crier` CLI.

## External dependency: the MCP server is not in-tree

`.mcp.json` does NOT bundle a server. It shells out to a globally-installed
`crier` CLI run as `crier mcp` (`uv tool install 'crier[mcp]'`; installing
without the `[mcp]` extra omits the `mcp` package and `crier mcp` fails). The
SessionStart hook (`hooks/scripts/detect-crier-setup.sh`) warns the user if the
CLI is missing or its interpreter (resolved from the `crier` script's shebang)
cannot find the `mcp` package. It must stay fast: no `crier --version` (~0.5s).
Editors must not expect a bundled server, and must not add `${CLAUDE_PLUGIN_ROOT}`
to the `.mcp.json` command: invoking the global `crier` binary is correct by
design.

## Components

- **`skills/crier/SKILL.md`** (`/crier:crier [file]`): the single home of every
  rule: target and limit discovery, rewrites and their budget, the two-step
  publish, manual/import platforms, failures, agent dispatch. Never restate
  these elsewhere; point at the skill section instead.
- **Command**: `/crier:chronicler` (date-scoped batch catch-up). It adds only
  scope, proposal format, and batching, and follows the skill for rules. There is
  deliberately no `commands/crier.md`: inside a plugin a same-name command
  shadows the skill, which then never loads.
- **Agents**: `cross-poster` (autonomous bulk publishing), `auditor` (read-only
  gap, performance, staleness, and failure analysis). Each agent's `tools` list
  should grant only the crier MCP tools it uses, plus `Read`. Never grant
  `AskUserQuestion`: Claude Code removes it from every subagent. Agents return a
  `## Decisions Needed` section (or the auditor's recommendations menu) and the
  main session (the skill or command that dispatched them) does the asking.
  The cross-poster Reads `${CLAUDE_PLUGIN_ROOT}/skills/crier/SKILL.md` for its
  rules. IMPORTANT: because the server is plugin-bundled, the tools
  register as `mcp__plugin_crier_crier__crier_*` (NOT `mcp__crier__crier_*`);
  an allowlist with the short prefix matches nothing and locks the agent out.
  Do not grant `Bash`: the agents do not shell out, and the SessionStart hook
  runs outside the agents.

## MCP tool inventory and the count-drift trap

The `crier` MCP server exposes ~20 `crier_*` tools (archive, article,
campaign_plan, campaign_run, check, delete, doctor, failures, list_remote,
missing, publications, publish, query, reconcile, record, search, sql, stats,
stats_refresh, summary), surfaced in sessions under the
`mcp__plugin_crier_crier__` prefix. Do NOT hardcode a tool count in any description: an
earlier "17 tools" claim went stale. If you must reference the count, keep it in
sync or drop the number.

## Platform model and contracts

- **No hand-copied platform data.** Modes are per-user config (`api`, `manual`,
  `import`), not fixed per platform, and crier ships more platforms than any
  list here would track. Targets come from `crier_doctor()` (`status`), limits
  and short-form flags from the `crier://platforms` resource (`mode`,
  `max_content_length`, `is_short_form`). Do not add platform tables or limit
  numbers to any file.
- **Short-form rewrite contract**: Claude writes the rewrite and passes it via
  `rewrite_content`; crier appends the canonical URL, so the rewrite never
  includes it and its budget is `limit - (len(canonical_url) + 2)`.
- **Two-step confirmation** for destructive ops (publish, delete): call once
  without a token to get a preview plus token, then call again with the token to
  execute. The token carries all arguments; step-2 caller args are ignored.
- **Manual/import posts** are recorded with `crier_record` (with `platform_id`
  set, else crier still counts them missing) only after the user says they are
  live. Never suggest the CLI's `--yes`, which records them unposted.
- **Remote-published failures**: `crier_publish` can return
  `remote_published: true` (live on the platform, registry write failed). Since
  crier 2.1.0 the MCP path checks crier's recovery receipt before any remote
  write, so retrying `crier_publish` records the live post instead of reposting
  it; the preview's `unrecorded_publication` shows that this will happen. Every
  failure path in this plugin must confirm a retry only when that field is set,
  and otherwise fall back to `crier_record`. The canonical wording lives in the
  skill's "Failures" section.

## Boundary with the mf plugin

`mf` owns creating and updating metafunctor.com content (Hugo); crier owns
distribution. The pipeline is mf to Hugo to crier. Do not duplicate
site-management logic here.

## Version bumps

Follow "Version Bumps" in the root `CLAUDE.md`: the version lives in
`.claude-plugin/plugin.json`, and `.codex-plugin/plugin.json` tracks it with a
`+codex.<timestamp>` suffix.
