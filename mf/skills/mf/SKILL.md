---
name: mf
description: Use mf (metafunctor) to manage papers, projects, series, and content for the metafunctor.com Hugo site. Also covers site architecture, taxonomies, front matter conventions. For cross-posting, use the crier plugin. Invoke from ANY repo; mf works globally.
argument-hint: "[intent, e.g. 'new post about X', 'sync papers', 'health check']"
---

# mf — Metafunctor Site Management

A CLI toolkit + site architecture guide for metafunctor.com. Works from any directory.

**Division of labor:**
- **mf** does mechanics: database CRUD, Hugo content generation, metadata operations
- **Claude** does judgment: choosing commands, interpreting intent, sequencing workflows, writing content

**Install location:** `~/github/repos/mf` (install on PATH: `uv tool install -e ~/github/repos/mf`)
**Site root:** `~/github/repos/metafunctor`
**Site URL:** `https://metafunctor.com` (mirror: `https://queelius.github.io/`)
**Engine:** Hugo with Ananke theme
**Deployment:** `docs/` committed to master, served by GitHub Pages

## Preflight: make sure `mf` is the right binary

TeX Live ships a `/usr/bin/mf` (Metafont) that shadows the metafunctor CLI when the latter is not earlier on PATH. Before the first `mf` command in a session, run `mf --version` and expect `mf, version ...`. Anything else (Metafont prints a `This is METAFONT` banner or waits for input) means the metafunctor mf CLI is not on PATH: stop and tell the user to install it with `uv tool install -e ~/github/repos/mf` (which puts it in `~/.local/bin`), rather than running commands against the wrong program.

## Site Architecture

### Content Sections

| Directory | Type | Notes |
|-----------|------|-------|
| `content/post/` | Blog posts | Date-prefixed dirs: `YYYY-MM-DD-slug/index.md` (what `mf posts create` writes; older posts use the legacy `YYYY-MM-slug` form) |
| `content/papers/` | Research papers | Generated from paper_db via `mf papers generate` |
| `content/publications/` | Publication lifecycle registry | Independent pubs_db managed via `mf pubs` (add, update, log, pull); NOT derived from paper_db at runtime |
| `content/projects/` | Software projects | Generated from projects_db via `mf projects generate` |
| `content/series/` | Multi-part series | Landing pages with `_index.md` |
| `content/writing/` | Long-form fiction and books | `writing_type` values in use: `novel`, `novella`, `novelette`, `nonfiction`, `short-story-collection` (check `content/writing/` before adding a new one) |
| `content/essays/` | Essays | Essays live here, not under `writing/` |
| `content/medical/` | Medical records | Custom sidebar layout, Chart.js for labs |
| `content/research/` | Research overviews | |
| `content/probsets/` | Problem sets | Organized by course |
| `content/media/` | Book/resource reviews | |

Other sections exist (`computer-science/`, `reading/`, `arcade/`, `youtube/`, `packages/`, `featured/`, `infinigram/`, plus site pages like `about/`). `ls content/` in the site root is the authoritative list; read a section's `_index.md` before adding to it.

**Content type separation is strict:** fiction goes in `/writing`, not `/papers`.

### Taxonomies

| Taxonomy | URL | Purpose |
|----------|-----|---------|
| `tags` | `/tags/` | Technical keywords (kebab-case) |
| `categories` | `/categories/` | Broad content categories |
| `genres` | `/genres/` | Document types (paper, novel, etc.) |
| `series` | `/series/` | Multi-part content grouping |
| `linked_project` | `/linked_project/` | Links content to projects |
| `linked_book` | `/linked-books/` | Links posts to books in `content/writing/` |

**Critical:** Use `linked_project` (NOT `projects`) — URL must not conflict with `content/projects/`.
Use slugs, not paths:
```yaml
# Correct
linked_project: ["likelihood.model"]
# Wrong — causes Hugo panic
linked_project: ["/projects/likelihood.model/"]
```

### Front Matter Patterns

**Posts:**
```yaml
title: "Post Title"
date: 2026-02-13
description: "Card preview text"
categories: ["Computer Science"]
tags: ["algorithms", "data-structures"]
series: ["series-slug"]
series_weight: 5
featured: true
featured_image: "cover.png"   # checked by `mf health images`
toc: true
```

**Papers:** `stars` (1-5), `pdf_file` (filename in `static/latex/`), `html_path`, `authors`, `abstract`
**Projects:** run `mf projects fields` for the authoritative field list, types, and allowed values (it includes newer fields such as `documentation_url`); `mf papers fields`, `mf series fields`, and `mf packages fields` do the same for their databases.
**Series membership (in posts):** `series: ["slug"]`, `series_weight: N`

### Bundle Types

- **Leaf bundle** (`index.md`): Most content. Self-contained page.
- **Branch bundle** (`_index.md`): Rich projects, series landing pages. Can have child pages.

Rich projects use `_index.md`. Regular projects use `index.md`.

### Build & Deploy

```bash
make serve          # Dev server with drafts (localhost:1313)
make build          # Build to docs/ (the production output dir, per hugo.toml publishDir)
make deploy         # Build to docs/ for production (also refreshes static/CNAME and docs/.nojekyll)
make push           # deploy, then commit docs/ and git push to GitHub Pages
```

There is no separate test output dir: `make build` overwrites `docs/`. Use `make serve` (or `hugo --gc --minify --destination /tmp/<dir>`) to check a build without touching `docs/`.

`relativeURLs = false`: the production build uses `baseURL = https://metafunctor.com/`. The `queelius.github.io` mirror is built separately by the site's GitHub Action (`.github/workflows/mirror-to-user-site.yml`) with its own `--baseURL`.

### Content Source Model

| Content | Ground Truth | mf Role | Has Database? |
|---------|-------------|---------|---------------|
| Projects | GitHub repos | DB + overrides + generate | Yes (projects_db.json) |
| Papers | LaTeX sources | DB + sync + generate | Yes (paper_db.json) |
| Series | mf series_db | DB + sync + landing pages | Yes (series_db.json) |
| Publications | Venue lifecycle (submissions, acceptances, DOIs) | `mf pubs` add/update/log/pull/check | Yes (pubs_db.json, independent of paper_db) |
| Packages | PyPI/CRAN registries | DB + sync + generate | Yes (packages_db.json) |
| Posts | The .md file | `mf posts` (list, create, set, tag, feature) | No |
| Writing | The .md file | None | No |
| Medical | The .md file | None | No |

**Key principle:** Databases exist only for content whose ground truth lives elsewhere.

## Intent Mapping

When users describe what they want, map to the right mf workflow:

| User says... | Workflow |
|-------------|----------|
| "new paper", "add a paper" | Paper workflow (below) |
| "new project", "add repo" | Project workflow (below) |
| "new post", "write about X" | Post workflow (below) |
| "health check", "audit site" | Health pass (below) |
| "deploy", "push to prod" | Pre-deploy (below) |
| "feature X", "star this paper" | `mf {type} feature <slug>` |
| "tag X with Y" | `mf {type} tag <slug> --add Y` |
| "sync papers" | `mf papers status` (staleness), then `mf papers ingest <slug>` + `mf papers generate --slug <slug>` |
| "sync projects" | `mf projects sync` |
| "cross-post", "share on socials" | Use `/crier` skill instead |
| "what content do I have" | `mf analytics summary` |
| "find broken links" | `mf health links` |
| "clean up tags" | `mf taxonomy audit`, then `mf taxonomy normalize --from <old> --to <new> [--field tags\|categories] --dry-run`, then rerun without `--dry-run` |

### New Paper
1. Build the paper in its own repo first (`make html pdf` there); the slug must already exist in paper_db
2. `mf papers ingest <slug>` (pulls the built HTML/PDF into the site)
3. `mf papers set <slug> stars 5` (and any other metadata)
4. `mf papers generate --slug <slug>`
5. If peer-reviewed, register it in the independent publications registry: `mf pubs add <slug>` / `mf pubs update`, then `mf pubs generate` (the registry does not render on its own)
6. `make deploy`
7. Cross-post: use `/crier`

Check staleness anytime with `mf papers status`; preview drift with `mf papers diff`.

### New Project
1. Add to `.mf/projects_db.json` (or `mf projects import`)
2. `mf projects sync`
3. `hugo --gc --minify` (verify)
4. `make deploy`

### New Post
1. `mf posts create --title "Title" --tag x --category Y`
2. Edit `content/post/YYYY-MM-DD-slug/index.md` — write content
3. `mf posts set <slug> draft false` (when ready)
4. `make deploy`
5. Cross-post: use `/crier`

### Health Pass
1. `mf health links` — broken internal links
2. `mf health descriptions` — missing descriptions
3. `mf health images` — missing featured images
4. `mf health stale` — content diverged from DB
5. `mf integrity check` — database consistency
6. `mf content audit --extended` — pluggable content checks
7. `mf taxonomy audit` — near-duplicate terms

### Pre-Deploy
1. `mf status`: any render drift between DBs and generated pages?
2. `mf integrity check`: database ok?
3. `hugo --gc --minify`: Hugo build errors?
4. `mf health links`: no broken links?
5. `make deploy`: build to docs/
6. `make push`: push to GitHub Pages

## Decision Guidance

### Command Group Cheat Sheet

| Group | Key verbs | Notes |
|-------|-----------|-------|
Most DB groups share a CRUD core: `list`, `show`, `set`, `unset`, `feature`, `tag`, `fields`, `stats`, `diff`. The table lists each group's distinctive verbs on top of that core; `mf <group> --help` is authoritative.

| Group | Distinctive verbs | Notes |
|-------|-------------------|-------|
| `papers` | ingest, generate, status, zenodo, fetch-cff, cff-status | Built paper repo → DB → Hugo |
| `projects` | import, sync, generate, refresh, hide, make-rich, list-rich, clean, fetch-codemeta, codemeta-status, rate-limit | GitHub → DB → Hugo |
| `series` | create, sync, scan, add, remove, delete, add-featured, add-link, add-related, artifacts, audit, audit-nav, classify-frontmatter | DB → landing pages; `sync` pulls by default (`--push` to push, `--ours`/`--theirs` for conflicts, `--interactive`) |
| `packages` | add, remove, sync, generate | PyPI/CRAN → DB → Hugo |
| `posts` | create, list, set, unset, tag, feature | Direct front matter edits (no DB) |
| `pubs` | add, update, log, pull, check, generate, zenodo | Independent lifecycle registry (`migrate` is a one-time paper_db seed) |
| `content` | match-projects, about, list-projects, audit | Cross-content linking |
| `taxonomy` | audit, orphans, stats, normalize | Tag/category hygiene |
| `health` | links, descriptions, images, drafts, stale | Content quality checks |
| `analytics` | summary, gaps, tags, timeline, suggestions, projects | Content insights |
| `integrity` | check, fix, orphans | Database consistency |
| `backup` | list, rollback, clean, status | Backup management |
| `config` | show, get, set, path, reset | Configuration |
| (top level) | `init`, `status` | `init` creates `.mf/`; `status` is the read-only render-drift dashboard |

### Generate vs Sync

- **generate** = rebuild Hugo pages from database (safe, idempotent)
- **sync** = pull from external sources into database, then generate (may change DB)
- When in doubt, `generate` first; it's read-only on the database
- Preview drift before acting: `mf status` (render-drift dashboard across papers, projects, packages, pubs) or `mf <group> diff` for one group

### Ordering Rules

- Always `sync` before `generate` if you want fresh data
- Always `generate` (or `sync`) before `make deploy`
- Papers and publications are independent registries at runtime: a paper change does NOT auto-update pubs (use `mf pubs update`/`log` when venue status changes; `mf pubs migrate` exists only as a one-time seed from paper_db)

### Tips

- `--regenerate` (auto-rebuild Hugo pages after the edit) exists on `papers set` and `projects set` only
- Use `mf --help` and `mf <group> --help` at runtime for exact flags
- Dry-run is the global `mf -n`/`mf --dry-run` flag (plus select subcommands like `content audit`)
- `--json` output available on most `list` and health commands

## Cross-Repo Usage

The mf CLI resolves the site root in this order:
1. `MF_SITE_ROOT` environment variable (highest priority)
2. Walk up from cwd looking for `.mf/` directory
3. Global config at `~/.config/mf/config.yaml`

```bash
# One-time setup (from any directory; or run `mf init` in the site repo):
mkdir -p ~/.config/mf
echo "site_root: ~/github/repos/metafunctor" > ~/.config/mf/config.yaml

# Now all commands work from any directory:
cd ~/github/repos/likelihood.model
mf posts create --title "New release"     # Creates in metafunctor/content/post/
mf posts list --tag python                # Lists metafunctor posts
```

## Hand-off to crier

Content flows **mf (create/update) → Hugo (render) → crier (distribute)**. After content changes are deployed, suggest cross-posting and hand off to the crier plugin (`/crier`); it owns the publishing workflow, rewrites, and failure handling.

## Gotchas

- `docs/` is committed to git (GitHub Pages). Don't gitignore it.
- Rich projects use `_index.md` (branch bundle) vs regular use `index.md`.
- `linked_project` taxonomy, NOT `projects` — URL collision with content section.
- Series landing pages: external source takes priority over local `_index.md`.
- PyPI names sometimes differ from repo names (e.g., `soprano` → `soprano-tts`).
- R-universe URLs: `queelius.r-universe.dev/PACKAGE` (author subdomain, not package).
- Posts use `content/post` (singular), not `content/posts`.
