# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code **plugin** (not a software project) that automates publication workflows:
- **R packages**: CRAN (and R-universe), then JOSS, then optionally JSS
- **Python packages**: PyPI publishing via trusted publishers

There is no build system, test suite, or compiled code. The plugin is Markdown files with YAML frontmatter.

## Architecture

```
.claude-plugin/plugin.json    # Plugin manifest
skills/                       # 5 skills, each also a slash command (/pub-pipeline:<name>)
agents/                       # 5 agents: the JOSS multi-agent system
docs/                         # Reference docs, exemplar, config template
```

### Skills

| Skill | Role |
|---|---|
| `r-publish` | R pipeline orchestrator (CRAN, R-universe status, JOSS, JSS) |
| `cran-audit` | Inline CRAN policy audit and gap report |
| `joss-draft` | Thin launcher for the `joss-writer` agent |
| `joss-audit` | Thin launcher for the `joss-reviewer` agent |
| `pypi-publish` | PyPI audit, build, trusted-publisher release |

There are no `commands/` files: skills are slash-invocable on their own, and inside a plugin a same-name command shadows the skill entirely (the skill never loads). Do not add a command that shares a skill's name. There is no router skill either: the `r-publish` and `pypi-publish` descriptions carry the routing hints (including "a standalone LaTeX paper belongs to papermill").

### Multi-Agent Architecture (JOSS)

The JOSS workflows live only in the agents; the `joss-draft` and `joss-audit` skills just gather config, dispatch, and handle the agents' **Decisions Needed** blocks in the main session (subagents cannot ask the user), re-dispatching with an `<answers>` block.

```
joss-writer (inherit, blue)        joss-reviewer (inherit, red)
  ├─ field-scout (sonnet, cyan)      ├─ software-auditor (sonnet, yellow)
  └─ [writes paper.md + paper.bib]   ├─ community-auditor (haiku, green)
                                     ├─ field-scout (sonnet, cyan)
                                     └─ [synthesizes JOSS checklist report]
```

- **joss-writer**: discovers existing manuscripts, gathers author metadata (dispatcher input, CITATION, DESCRIPTION, config, `deets` CLI), spawns field-scout, drafts, validates with pandoc citeproc and the `openjournals/inara` build.
- **joss-reviewer**: read-only; spawns the three specialists in parallel, reviews the paper itself, synthesizes the checklist report.
- **field-scout**: finds competitors (CRAN, R-universe search API, PyPI JSON, web). BibTeX must come from DOI content negotiation or `citation()`; anything else is labeled `UNVERIFIED`.
- **software-auditor**: tests, coverage, installation, docs, CI, R CMD check.
- **community-auditor**: LICENSE, CONTRIBUTING, issue tracker, development history, the single-author evidence rule. A code of conduct is informational only (JOSS does not require one).

Orchestrators dispatch specialists with the Agent tool by qualified name (`pub-pipeline:field-scout`) and pass context in XML tags.

### Shared User Config

Skills read `.claude/pub-pipeline.local.md` in the target project. The template is `docs/user-config-template.md`: YAML frontmatter (`author`, `coauthors`, `r`, `ai_usage`, `related_work`, `funding`) plus free-form notes. If missing, skills offer to create it from `${CLAUDE_PLUGIN_ROOT}/docs/user-config-template.md`. Author metadata falls back to the global `deets` CLI (`deets show --format json`).

### Reference Docs (`${CLAUDE_PLUGIN_ROOT}/docs/`)

- `cran-reference.md`: CRAN Repository Policy, submission checklist
- `joss-reference.md`: JOSS requirements, reviewer checklist, paper format (verified 2026-10-21)
- `joss-exemplars.md`: one paper verified to use the current JOSS format; add more only after checking their source `paper.md`
- `pypi-reference.md`: PyPI metadata, trusted publisher workflow template

KDP publishing lives in the sibling `kdp/` plugin, not here.

## Conventions

- Skills: frontmatter `name`, `description` (with routing hints), optional `argument-hint`; numbered steps with tool annotations `(Read tool)`, `(Bash tool)`.
- Audit output uses Critical (Must Fix) / Warnings (Should Fix) / Passed, plus Recommended Next Steps. `pypi-publish` step 7 follows the same pattern.
- Never instruct a Bash command that prompts interactively (credentials, `devtools::submit_cran()`). Use env-var tokens or hand the command to the user as `! <command>`.
- Prefer structured sources over scraping: PyPI JSON API, R-universe JSON API, DOI content negotiation, pandoc citeproc warnings.
- No em-dashes in prose.

## Validation

```bash
for f in skills/*/SKILL.md; do echo "=== $f ===" && head -8 "$f"; done
for f in agents/*.md; do echo "=== $f ===" && head -12 "$f"; done
grep -roh '\${CLAUDE_PLUGIN_ROOT}/[^`"*]*' skills/ agents/ | sort -u | while read ref; do
  f="${ref/\$\{CLAUDE_PLUGIN_ROOT\}/.}"; [ -f "$f" ] || echo "BROKEN: $ref"; done
grep -rho 'pub-pipeline:[a-z-]*' skills/ agents/ | sort -u   # each must be a skill or agent name
grep -rnP '\x{2014}' --include=*.md . && echo "EM-DASHES FOUND"
```
