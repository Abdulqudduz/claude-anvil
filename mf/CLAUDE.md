# CLAUDE.md (mf plugin)

Editing guidance for the mf Claude Code plugin. Read before editing this plugin.

## What this is

mf drives the `mf` CLI (a separate package at github.com/queelius/mf) to manage
metafunctor.com Hugo content: papers, projects, posts, and series. The plugin
ships no code of its own; it is the judgment layer (intent to workflow), and the
CLI is the mechanics. The skill turns a natural-language request into the right
`mf` CLI invocations.

## Components

- **`skills/mf/SKILL.md`**: `mf` CLI workflows (intent mapping, command groups,
  dry-run semantics, site-root resolution). It is the source of truth for CLI
  usage only. Keep it factual: verify against `mf --help`, `mf <group> --help`,
  and `mf <group> fields`, and prefer pointing at those over hardcoding lists
  that will drift. The preflight exists because TeX Live's `/usr/bin/mf`
  (Metafont) can shadow the CLI; keep it.
- **`skills/scribe/SKILL.md`**: latent-theme discovery across the corpus, its
  own skill (not part of `mf`).
- **No `commands/`.** Both skills are invoked directly as `/mf` and `/scribe`.
  Do not add same-name command wrappers: inside a plugin a command with the
  same name as a skill wins, and the skill never loads. Put `argument-hint` in
  the skill frontmatter instead.

## Site facts live in the site repo, not here

Taxonomies and their front-matter keys (e.g. `linked-books`, not
`linked_book`), front matter fields, bundle types, build/deploy, and site
gotchas are documented once, in the site repo's `CLAUDE.md`
(`~/github/repos/metafunctor/CLAUDE.md`). The skill's preflight tells Claude to
Read it. Do not copy those facts back into the skill: the previous copy drifted
(wrong deploy host, a removed section, a wrong taxonomy key). Fix site facts in
the site repo.

## Boundary with the crier plugin

mf creates and updates content; the separate **crier** plugin distributes it.
The pipeline is mf to Hugo to crier. Never reimplement cross-posting here; point
at `/crier` instead. The `scribe` skill reads the corpus via `mf posts list --json`
first (the CLI includes `description` as of 2026-06-09), with crier's
`crier_search` and a self-contained Glob path as fallbacks, so it works when
crier is not installed. If you add a hard crier dependency
anywhere, declare it explicitly.

## Conventions to preserve when editing the skill

- `generate` verbs (e.g. `mf papers generate`) are read-only on the database;
  `sync` verbs (e.g. `mf projects sync`) mutate it. Neither is a top-level
  command. Databases exist only for content whose ground truth lives elsewhere
  (projects, papers, series, pubs, packages), not for posts/writing.
- The global `mf -n` is not honored by every group (`posts` ignores it). Keep
  the skill's per-group dry-run list accurate when the CLI changes.
- Site-root resolution order: `MF_SITE_ROOT`, then walk up for a `.mf/`
  directory, then `~/.config/mf/config.yaml`. This is why the skill "works from
  any directory." The `~/github/...` paths shown in the skill are the author's
  own environment, not portable references.

## Version bumps

Keep `.claude-plugin/plugin.json` and the `mf` entry in the root
`.claude-plugin/marketplace.json` in sync (check both before bumping). Never bump one
without the other.

## Validation

```bash
# Skill frontmatter
for f in skills/*/SKILL.md; do echo "=== $f ===" && head -5 "$f"; done
```
