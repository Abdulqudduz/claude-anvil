# mf — Claude Code Plugin

Metafunctor site management for Claude Code. Manage papers, projects, series,
and content for metafunctor.com, a Hugo site, with blog architecture and content
workflows. Cross-posting is handed off to the separate crier plugin.

**Requires**: the [mf](https://github.com/queelius/mf) CLI on PATH, ahead of TeX
Live's `/usr/bin/mf` (Metafont): `uv tool install -e <path-to-mf-checkout>`.

## Components

| Type | Name | Purpose |
|------|------|---------|
| Skill | `mf` | Site architecture guide, mf CLI reference, content workflows |
| Skill | `scribe` | Discover latent themes across the corpus (a proposal, not a draft) |
| Command | `/mf` | Site management (new posts, sync papers, health checks) |
| Command | `/scribe` | Trigger the scribe theme-discovery skill |

Cross-posting lives in the separate **crier** plugin (`/crier`), not here: mf
creates and updates content, crier distributes it. The `scribe` skill reads the
corpus via `mf posts list --json`, with crier's `crier_search` and a
self-contained Glob path as fallbacks.

## Install

```bash
# From the marketplace
/plugin install mf@queelius
```

## Workflows

- **Content creation**: Draft posts, sync academic papers into blog format, manage series
- **Site health**: Taxonomy audits, broken link checks, metadata validation
- **Cross-posting hand-off**: After content changes, route distribution to the crier plugin (`/crier`); mf itself never cross-posts

The mf skill works from any directory: it resolves the site root automatically.

## License

MIT
