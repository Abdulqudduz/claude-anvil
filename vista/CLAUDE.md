# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Vista is a **dual-mode application** packaged as one Python project:

1. A **standalone CLI** (`vista`) that builds a bulk catalog of research
   directions by mining the Future Work / Limitations / Discussion / Conclusion
   sections of highly-cited papers from OpenAlex.
2. A **Claude Code plugin / MCP server** (`vista-mcp`) that exposes the same
   pipeline as on-demand tools so the in-conversation Claude can fetch raw
   section text and synthesize directions inline.

Both modes share one SQLite store, one `vista` package, and one config. They
diverge only at the entry points (`vista.cli:app` vs `vista.mcp_server:main`).

The plugin manifest (`.claude-plugin/plugin.json`) and MCP registration
(`.mcp.json`) ship in the repo. `.mcp.json` resolves `${CLAUDE_PLUGIN_ROOT}` to
this directory at runtime so `uv run --project ... vista-mcp` finds the package.

## Common commands

```bash
# Install (editable, with the API extra for the unattended analyzer path)
uv venv && uv pip install -e '.[api]'

# Run the test suite (pytest comes from the `dev` dependency group)
uv run pytest -q

# Run a single test file or test
uv run pytest tests/test_extract.py -q
uv run pytest tests/test_extract.py::test_dedup_keeps_longer

# CLI: end-to-end build of the catalog (idempotent; resumes per-stage)
vista pipeline --fields ml,ai,stats,ransomware --per-field 25
vista pipeline --skip-analyze    # discover/fetch/extract/render only (no API key needed)
vista status                      # counts table by field/track

# CLI: individual stages (each is idempotent and only touches unfinished work)
vista discover --fields ml --per-field 10
vista fetch --max-papers 5
vista extract
vista analyze --premium           # uses PREMIUM_MODEL (claude-fable-5-1)
vista render
vista seed-bib path/to/refs.bib --field stats

# Run the MCP server manually (for debugging; normally invoked by Claude Code)
uv run vista-mcp                  # speaks stdio, JSON-RPC

# Browse the store with Datasette (optional [viz] extra)
uv pip install -e '.[viz]'
uv run --with datasette datasette "$VISTA_DATA_DIR/papers.db"
```

`ANTHROPIC_API_KEY` is **only** required for `vista analyze` and `vista pipeline`
without `--skip-analyze`. The MCP path never calls the Anthropic SDK; the
in-conversation Claude does the synthesis.

`OPENALEX_API_KEY` is optional for everything but strongly recommended: keyless
OpenAlex requests share one $0.10 daily budget per IP address, while a free key
has its own $1/day. Searches (`/works?filter=...`) cost $0.001 each, so keyless
access is about 100 searches a day; single-work lookups by id or DOI are free.
See "OpenAlex client" below.

## Architecture

### The synthesis split (load-bearing design choice)

The MCP server in `vista/mcp_server.py` is **mechanical**: it returns raw
section text + metadata as JSON. It does no LLM calls. Synthesis (ranking,
direction extraction, novelty assessment) happens in whatever Claude is on the
other end of the MCP connection.

There is exactly one place that does call the Anthropic SDK:
`vista/pipeline/analyze.py`. That path is opt-in via the `[api]` extra
(`anthropic>=0.97`) and is designed for unattended (cron, CI) runs of `vista
analyze`. The `anthropic` import is lazy inside `_client()` so the package
works without it. The request uses structured outputs (`output_config.format`,
JSON schema `DIRECTIONS_SCHEMA`), `max_tokens=16000` because thinking tokens
count against it, and a plain-string system prompt (it is below the minimum
cacheable length, so `cache_control` would do nothing). `stop_reason ==
"refusal"` raises `AnalyzerRefused` (the paper is marked analyzed);
`"max_tokens"` raises `AnalyzerTruncated` (left for the next run). Tests pass
a fake client, so none of this touches the network.

When adding new MCP tools, **do not add LLM calls to them**. If you need
synthesis, return the raw inputs and let the conversation synthesize. The skill
in `skills/vista/SKILL.md` explains the synthesis pattern callers use.

### Pipeline (discover → fetch → extract → analyze → render)

Each stage is **idempotent and resumable**; the SQLite schema encodes
"unfinished" via the absence of rows in the next table, plus two negative
caches on `papers`. `Store.papers()` takes flags `needs_pdf`,
`needs_extraction`, `needs_analysis` that translate into WHERE clauses:

- `needs_pdf`: no `pdf_path`, no `fetch_failed_at`, and at least one of
  `arxiv_id` / `pdf_url` / `oa_url`. A fetch where every candidate URL fails
  sets `fetch_failed_at` (`Store.mark_fetch_failed`), so bulk runs stop
  retrying dead URLs; `vista fetch --retry-failed` (MCP
  `extract_pending(retry_failed=True)`) clears it. The live MCP path always
  retries, since a user asked for that paper.
- Extraction: a paper whose PDF yields nothing gets a placeholder row with
  empty content (`method="empty"`, or `"error"` when PyMuPDF cannot parse it),
  written by `extract.extract_and_store`. Every sections row records
  `extractor_version` (`extract.EXTRACTOR_VERSION`, currently 2; NULL in
  catalogs from before versioning means 1, the regex-only extractor). One
  predicate, `extract.should_extract(rows, retry_empty=)`, decides
  re-extraction for both `run_extract` and the live `core.fetch_and_extract`:
  yes for no rows, or for placeholder-only papers whose placeholder is an
  `error` or from an older extractor; never for a paper with section text.
  `vista extract --retry-empty` (MCP `extract_pending(retry_empty=True)`)
  forces current-version empty placeholders too. Re-extraction replaces the
  paper's rows (`Store.replace_sections`). **Bump `EXTRACTOR_VERSION`**
  whenever a change could find sections an earlier version missed.
  `Store.papers(needs_extraction=True)` is "PDF, no rows";
  `only_placeholders=True` is "PDF, only empty rows" (then filtered by
  `should_extract`).
- `needs_analysis`: a section with non-empty content, no directions, and no
  `analyzed_at`. `run_analyze` sets `analyzed_at` whenever the model answered
  (even with zero directions, or a refusal), so reruns do not re-bill it.

| Stage | Module | Inputs | Outputs |
|-------|--------|--------|---------|
| discover | `vista/pipeline/discover.py` + `vista/sources/openalex.py` | `FIELDS` config, citation thresholds | `papers` rows |
| fetch | `vista/pipeline/fetch.py` | papers with `arxiv_id` / `pdf_url` / `oa_url` | PDFs in `<data>/pdfs/`, `pdf_path` or `fetch_failed_at` set |
| extract | `vista/pipeline/extract.py` | PDFs | `sections` rows, `method` = outline / font / regex |
| analyze | `vista/pipeline/analyze.py` | sections + abstract | `directions` rows |
| render | `vista/render/markdown.py` | full store | `out/index.md` + per-paper / per-tag markdown |

The `vista/core.py` module wraps fetch + extract for the live MCP path so
on-demand tool calls cache into the same store: `search_works` is the one
live-search function (keyword query, optional FIELDS concepts, arXiv
requirement, year and citation bounds), `research` caches + fetches +
extracts a list of works, and `resolve_identifier` handles DOIs, arXiv ids
and URLs, OpenAlex ids, and exact titles. Every OpenAlexWork becomes a row
through `Paper.from_work`.

### PDF fetch policy

`fetch.py` downloads URLs taken from third-party metadata, so every request
is bounded: http/https only; the host of every hop (redirects are followed
manually, at most `MAX_REDIRECTS`) must resolve only to globally routable
addresses (no private, loopback, link-local, or reserved ranges); a
`MAX_PDF_BYTES` (50 MB) cap checked against `Content-Length` and while
streaming; an overall `DOWNLOAD_DEADLINE_SECONDS` on top of httpx's per-read
timeout; and a `%PDF` magic check. Policy violations raise `FetchRejected`
and are never retried. Transient failures (connection errors, 429, 5xx) are
retried via the shared `vista.net.is_transient`; other 4xx (paywall 403,
404) are not. `pdf_client()` is the only PDF HTTP client factory.

The address check binds the connection: `PublicOnlyTransport` is httpx's
`HTTPTransport` with its pool rebuilt on `PublicOnlyBackend`, an httpcore
network backend whose `connect_tcp` resolves the host via `fetch._resolve`,
rejects it unless every address is public, and connects to a checked IP.
SNI, certificate checks, and the Host header still use the hostname (httpcore
takes them from the request origin). So DNS rebinding between the pre-request
`_check_url` and the connect cannot reach a private address. Swapping `_pool`
touches an httpx internal; `test_dns_rebinding_between_check_and_connect_is_rejected`
drives a real connect through it, so an incompatible httpx upgrade fails
the suite. Tests stub `fetch._resolve` (DNS), `fetch._monotonic`, and
`fetch._sleep`.

### Storage

Single SQLite file. Schema in `vista/storage/schema.sql`. Four tables (`papers`,
`sections`, `directions`, `runs`) plus the `v_directions_full` view that pre-joins
directions to their parent paper for browsing. Foreign keys + WAL mode are on.

`Store.upsert_paper`, `Store.upsert_sections`, `Store.upsert_directions`, and
`Store.replace_directions` are the idempotent write paths; all are safe to
re-run. `upsert_paper` and `upsert_sections` use `ON CONFLICT ... DO UPDATE` on
their natural keys (`papers.id` and `(paper_id, section_type)`).

Directions have a natural key too: `(paper_id, db.direction_key(direction))`,
the text casefolded and whitespace-collapsed. It is enforced in Python (a
paper has few directions), not by a UNIQUE index, so existing catalogs with
near-duplicates still open. `upsert_directions` updates a matching row in
place (its id, `user_status`, and `user_notes` are kept; new non-empty fields
win; field tags are unioned) and inserts the rest. `replace_directions` does
the same and then deletes the paper's other directions **only if uncurated**
(`user_status` is `open` and `user_notes` is null). Curation is never
destroyed by a write path; MCP `submit_directions` defaults to append.

Schema evolution: `init_schema` adds missing columns listed in
`db._ADDED_COLUMNS` (currently `papers.fetch_failed_at`, `papers.analyzed_at`)
with `ALTER TABLE` before running `schema.sql`, and `schema.sql` drops and
recreates `v_directions_full` on every open. Add future columns the same way.
`Store.status_counts()` is the one status query (CLI and MCP).

### Where data lives

By default, **outside the repo**. `vista/config.py` uses
`platformdirs.user_data_dir("vista", appauthor="queelius")` so the catalog
survives plugin updates and is shared between the CLI and MCP server. Override
with environment variables for project-local storage (useful when working from
a checkout):

```bash
export VISTA_DATA_DIR=$PWD/data
export VISTA_OUT_DIR=$PWD/out
```

Code reads paths as `config.DB_PATH` / `config.PDF_DIR` / `config.OUT_DIR`
at call time (never `from vista.config import DB_PATH`), so the test suite's
autouse `tmp_data_dir` fixture in `tests/conftest.py` can redirect every test
to a temporary directory. Keep it that way: a module-level snapshot of a path
would let tests write to the user's real catalog.

### MCP tool surface (three groups)

`vista/mcp_server.py` registers 15 tools via `FastMCP`. They split into:

- **On-demand research** (`topic_followups`, `paper_followups`, `find_seminal`,
  `broad_followups`): live OpenAlex → cache → fetch → extract → return JSON.
  They store papers with `field="ad-hoc"` and a `track` of `topic` / `paper` /
  `legacy` / `broad`, so the catalog tracks ad-hoc lookups separately from
  bulk runs. The three search tools share one body, `_live`.
- **Stored corpus** (`search_directions`, `list_directions`, `get_paper`,
  `submit_directions`, `mark_direction`): query and curate already-built data.
  Both listings go through `_query_directions` over `v_directions_full`, so
  they return one row shape (with `paper_id`, and `field_tags` as a list).
- **Pipeline + escape hatch** (`discover`, `extract_pending`, `render_markdown`,
  `status`, `run_sql`, `get_schema`): bulk operations and read-only SQL.

The server holds one `Store` (`_store()`, opened lazily). Parameter enums are
derived from config, not restated: `FieldName = Literal[tuple(FIELDS)]` and
`UserStatus = Literal[USER_STATUSES]` appear in the tool schemas as JSON-schema
enums. Tests swap `_openalex` and `pdf_client` for MockTransport-backed fakes.

All tools return JSON-stringified payloads (not Python objects); FastMCP
serializes them as MCP responses.

### Field configuration (where to add new domains)

`vista/config.py:FIELDS` is the single source of truth for what gets crawled.
Each entry declares:

- `concept_ids`: OpenAlex concept IDs (filter on `concepts.id`).
- `venue_ids` *(optional)*: canonical OpenAlex source IDs to filter primary
  location.
- `fulltext_filter`: one of `arxiv-required` (require arXiv mirror, best for
  ML/AI), `venue-only` (canonical venues, accept paywalls), or `any` (no
  filter). This is the principled solution to OpenAlex's flaky `is_oa` flag for
  NeurIPS/ICML/ICLR.
- `keywords` *(optional)*: keyword filter for "any"-strategy fields.
- `min_citations_recent` / `min_citations_legacy`: per-track thresholds.

Add a new field by appending to this dict; no code changes elsewhere are
needed. `config.validate_fields` / `concept_ids_for` (used by the CLI, the MCP
`discover` tool, and `core.search_works`) reject unknown names with the valid
list, and the MCP tool schemas enumerate the keys.

### Tracks

A `track` column on `papers` distinguishes how a paper got into the store:

- `recent`: post-2020, top-cited per field. Bulk run default.
- `legacy`: pre-2020, very-highly-cited (the "neglected futures" candidates).
- `seed`: ingested from `.bib` via `vista seed-bib`.
- `topic` / `paper` / `broad`: populated by the matching MCP on-demand tools.

When adding new MCP tools that fetch papers, give them their own track string
so the catalog stays auditable.

### OpenAlex client

`vista/sources/openalex.py:OpenAlexClient` is the only OpenAlex HTTP path.
Contracts worth preserving:

- **Auth**: the key comes from `config.openalex_api_key()` (env
  `OPENALEX_API_KEY`), read at client construction, and is sent as an
  `Authorization: Bearer` header. OpenAlex accepts an `api_key` query param
  equivalently, but httpx error messages include the URL, so a query param
  would leak the key into tracebacks and logs. No key: requests still work and
  one warning goes to stderr (never stdout, which is the MCP transport).
- **Retry policy** (`_is_retryable`, built on the shared
  `vista.net.is_transient`): retry connection errors, 5xx, and per-second 429s, honoring `Retry-After` (capped at 60s), else exponential
  backoff; 4 attempts, then the ORIGINAL error is re-raised (`reraise=True`,
  so callers' `except httpx.HTTPStatusError` for 404 actually fires). Never
  retry other 4xx. A 429 with `x-ratelimit-remaining: 0` is a spent daily
  budget, not throttling: it raises `OpenAlexBudgetExhausted` immediately.
- **Free text in filters**: always build text-search filters with
  `search_filter(field, text)`, never by f-string. A comma separates filters and
  a pipe ORs values, so a raw title like "chess, shogi, and Go" makes OpenAlex
  reject the whole request with a 400.
- **arXiv ids** (bare, `arXiv:`-prefixed, or abs/pdf URLs; new style or old
  style with an optional subject class like `math.AG/0101001`, one shared
  `ARXIV_ID_PATTERN`) resolve through arXiv's DataCite DOI
  (`10.48550/arxiv.<id>`) as one free single-work lookup, instead of a paid
  search that scans arXiv-hosted works for a match.
- **Titles** resolve through `find_by_title`, which accepts only a
  `normalize_title`-equal hit (casefolded alphanumerics). Substring matching
  is deliberately gone: it made "BERT" resolve to RoBERTa. Near misses are
  returned as `TitleMatch.candidates` (MCP `paper_followups` shows them).
- **Live searches keep `is_oa:true`**: `build_filter` defaults `is_oa=True`
  and `core.search_works` does not override it, unlike bulk discovery
  (`is_oa=None`). This predates the current code and is a known open
  question, not a decision.
- **Tests** inject `transport=httpx.MockTransport(...)` and stub the module's
  `_sleep`, so they stay offline and instant.

**Concepts are frozen (open TODO).** `FIELDS[*].concept_ids` filter on
`concepts.id`. OpenAlex replaced concepts with Topics in 2024; concepts still
filter, but they are no longer recomputed, so new works are not tagged with
them and the `recent` track increasingly misses new papers. There is no
one-to-one mapping (concepts are a 6-level tree, topics a 4-level
domain/field/subfield/topic hierarchy), so migrating is a per-field judgment
call: pick `primary_topic.subfield.id` or `topics.id` values that match each
field's intent and verify coverage before switching. Until then, keyword and
paper lookups are unaffected.

### Section extraction

`vista/pipeline/extract.py:extract_paper` opens the PDF with PyMuPDF (a hard
dependency; there is no pdftotext fallback and no text cache) and runs
`STRATEGIES` in order, most structured first. Each section type is taken from
the first strategy that finds it; later strategies only fill missing types.

1. `outline`: `doc.get_toc()` bookmarks (hyperref emits them for most LaTeX
   papers). Each entry's heading line is located on its page by
   `_heading_key` (numbering stripped, alphanumerics only, also across a
   two-line wrap); if not found, the section starts at the page. A section
   ends at the next outline entry of the same or higher level.
2. `font`: lines from `page.get_text("dict")` that are short and either at
   least `HEADING_SIZE_RATIO` (1.15) times the char-weighted body font size or
   entirely bold. A section ends at the next such line.
3. `regex`: `find_sections` walks plain text. Headings are matched on their
   own line with optional numbering (decimal `6.`, `6.1`, or roman `VI.`).
   The walker stops at another tracked heading, `REFS_HEADING`, a
   `GENERIC_HEADING`, three blank lines after 5+ captured lines, or the cap.

In all three, *which* heading names a tracked section is decided by
`classify_heading`, which matches the short title string against
`SECTION_PATTERNS` (first match wins, so "Discussion and Future Work" is
`future_work` and "Conclusions and Limitations" is `limitations`). Bodies are
cut at `REFS_HEADING` and `MAX_SECTION_LINES` (200). The longest match per
type is kept. The chosen strategy is stored in `sections.method`.

If a paper uses creative headings that aren't classified, **add the variant to
`SECTION_PATTERNS`** rather than post-processing. Test PDFs are generated in
memory by `tests/conftest.py:make_pdf` (with or without an outline, with
sized or bold headings); do not check in binary fixtures.

### Models

`DEFAULT_MODEL = claude-sonnet-5-5`, `PREMIUM_MODEL = claude-fable-5-1`.
Override them with `VISTA_MODEL` (legacy name `FOLLOWUPS_MODEL`, still honored)
and `VISTA_PREMIUM_MODEL`. These only matter for the Anthropic-SDK analyzer
path; the MCP path is model-agnostic.

## Tests

Tests in `tests/` cover every module: the three extraction strategies on
generated PDFs, the store (natural-key directions, negative caches,
migration), the fetch policy (retries, size cap, deadline, address checks),
the analyzer request and stop_reason handling against a fake client, OpenAlex
parsing and client policy, identifier resolution, every MCP tool in-process,
discovery filters, BibTeX seeding, rendering, and the CLI. They are standalone
(no API key, no network: MockTransport, fakes, stubbed DNS, and the autouse
`tmp_data_dir` fixture) and run in about two seconds. Coverage:
`uv run --with pytest-cov pytest --cov=vista -q`.

`pytest` lives in the `dev` dependency group (not in `dependencies` or any
extra), which `uv run` installs by default, so `uv run pytest` works.

## Plugin layout (for plugin work)

```
.claude-plugin/plugin.json     plugin manifest (name, author, etc.)
.mcp.json                      MCP server registration; uses ${CLAUDE_PLUGIN_ROOT}
skills/vista/SKILL.md          when-to-call-which-tool routing for the conversation
skills/vista/references/       extended routing examples + JSON schemas
agents/research-synthesizer.md subagent for bulk landscape reports
agents/cross-referencer.md     subagent for intersecting literature with user's prior work
```

The skill is the conversation-side rulebook for the MCP. When MCP tool
contracts change (params, return shape), update both `mcp_server.py` and
`skills/vista/SKILL.md` plus `references/output-shape.md` to keep the routing
guidance honest.

## Conventions specific to this repo

- **Logging**: CLI uses `RichHandler` for colored output; MCP logs to stderr
  only (stdout is the JSON-RPC transport). Don't `print()` from MCP code.
- **OpenAlex IDs**: stripped of the `https://openalex.org/` prefix at parse
  time (`OpenAlexWork.from_api`). The `id` column is the bare `Wxxxxxxx` form.
- **Author identity**: package author and the User-Agent `mailto` contact are
  `lex@metafunctor.com` (`config.CONTACT_EMAIL`). OpenAlex's current docs no longer
  describe a polite pool, so the contact is courtesy only; the API key is what
  sets the budget.
  The User-Agent version comes from package metadata (`config.VERSION`).
- **Read-only SQL**: any new MCP tool that takes a SQL string must run it on
  `mcp_server.readonly_connection(store)`: a separate `mode=ro` connection with
  `PRAGMA query_only=ON` and an authorizer that allows only SELECT / READ /
  FUNCTION / RECURSIVE actions, so writes, DDL, ATTACH, PRAGMA, and VACUUM
  INTO are denied by the engine. Do not filter SQL text with regexes. Row
  limits use `fetchmany`, never by rewriting the query. Execution time is
  bounded by a progress handler (`SQL_TIME_LIMIT_SECONDS`, 3s) that aborts the
  statement and returns a JSON error, so a non-terminating recursive CTE
  cannot hang the server.
