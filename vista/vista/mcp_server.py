"""Vista MCP server.

Exposes mechanical research-lookup tools to MCP clients (Claude Code, etc.).
The server returns structured JSON. Synthesis happens in the conversation.

Run: `vista-mcp` (stdio transport).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
import time
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from vista import config
from vista.config import FIELDS, RunConfig, ensure_dirs, validate_fields
from vista.core import (
    research,
    resolve_identifier,
    search_works,
    summarize_paper,
)
from vista.pipeline.analyze import directions_from_dicts
from vista.pipeline.discover import run_discover
from vista.pipeline.extract import run_extract
from vista.pipeline.fetch import pdf_client, run_fetch
from vista.render.markdown import render_all
from vista.sources.openalex import OpenAlexClient
from vista.storage.db import SCHEMA_PATH, USER_STATUSES, Store

# Logs to stderr only: stdout is the MCP transport.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="vista-mcp %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("vista.mcp")

mcp = FastMCP("vista")

_STORE: Store | None = None

# Parameter types derived from the config, so the tool schemas advertise the
# valid values (as JSON-schema enums) and stay in sync with FIELDS and
# USER_STATUSES without restating them in docstrings.
FieldName = Literal[tuple(FIELDS)]  # type: ignore[valid-type]
UserStatus = Literal[USER_STATUSES]  # type: ignore[valid-type]


def _store() -> Store:
    """The server's one store connection, opened on first use."""
    global _STORE
    if _STORE is None:
        ensure_dirs()
        _STORE = Store.open()
    return _STORE


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _openalex() -> OpenAlexClient:
    return OpenAlexClient()


def _live(echo: dict[str, Any], *, track: str, **search: Any) -> str:
    """Shared body of the on-demand search tools: search, cache, fetch, extract."""
    try:
        with _openalex() as client:
            works = search_works(client, **search)
    except ValueError as e:  # unknown field name
        return _json({**echo, "error": str(e)})
    with pdf_client() as http:
        papers = research(_store(), works, track=track, http=http)
    return _json({**echo, "papers": papers, "paper_count": len(papers)})


# ---------------------------------------------------------------------------
# On-demand research tools
# ---------------------------------------------------------------------------

@mcp.tool()
def topic_followups(
    topic: str,
    max_papers: int = 8,
    year_min: int = 2020,
    min_citations: int = 30,
    require_arxiv: bool = True,
) -> str:
    """Search OpenAlex for highly-cited recent papers matching a topic, fetch
    their PDFs, extract Future Work / Limitations / Discussion / Conclusion
    sections, and return as structured JSON.

    Use this when the user asks about open problems, salient or timely
    follow-up research, or research directions on a specific topic. The caller
    (the conversation) reads the returned section text and synthesizes
    directions; this tool does no LLM analysis itself.

    Args:
        topic: keyword(s); OpenAlex full-text search syntax accepted (use OR / quotes).
        max_papers: papers to fetch (default 8).
        year_min: only papers from this year or later (default 2020).
        min_citations: citation threshold (default 30; raise for popular fields).
        require_arxiv: restrict to papers also on arXiv (reliable PDF). Set False
            to include work we may not be able to fetch the PDF for.
    """
    params = {"max_papers": max_papers, "year_min": year_min,
              "min_citations": min_citations, "require_arxiv": require_arxiv}
    return _live({"topic": topic, "params": params}, track="topic", query=topic, **params)


@mcp.tool()
def paper_followups(identifier: str) -> str:
    """Look up a specific paper and return its Future Work / Limitations /
    Discussion / Conclusion sections.

    Use this when the user asks "what does paper X say about future work" or
    points at a specific reference (DOI, arXiv id, OpenAlex id, or title).

    Args:
        identifier: DOI (10.xxxx/yyy), arXiv id or URL (2106.xxxx, cs/0001234,
            https://arxiv.org/abs/...), OpenAlex id (Wxxxxx), or exact paper
            title. A title with no exact match returns "candidates" instead.
    """
    with _openalex() as client:
        match = resolve_identifier(identifier, client)
    if match.work is None:
        return _json({
            "identifier": identifier,
            "error": "not found",
            "candidates": [
                {"paper_id": w.id, "title": w.title, "year": w.year,
                 "cited_by_count": w.cited_by_count}
                for w in match.candidates
            ],
        })
    with pdf_client() as http:
        return _json(research(_store(), [match.work], track="paper", http=http)[0])


@mcp.tool()
def find_seminal(
    topic: str | None = None,
    year_max: int = 2019,
    year_min: int = 2000,
    min_citations: int = 1000,
    max_papers: int = 8,
) -> str:
    """Find older highly-cited papers and return their Future Work sections.

    These are the 'neglected futures' candidates: directions flagged years ago
    where the field may not have followed up. Use when the user wants the
    legacy track or asks about under-explored ideas in classical literature.

    Args:
        topic: optional keyword; omit for a citation-only top-N within the year window.
        year_max: latest publication year to include (default 2019).
        year_min: earliest year (default 2000).
        min_citations: floor; legacy papers in popular fields can sit at ~1000-10000+.
        max_papers: limit (default 8).
    """
    params = {"year_min": year_min, "year_max": year_max,
              "min_citations": min_citations, "max_papers": max_papers}
    return _live({"topic": topic, "params": params}, track="legacy",
                 query=topic, require_arxiv=False, **params)


@mcp.tool()
def broad_followups(
    query: str,
    fields: list[FieldName] | None = None,
    year_min: int = 2020,
    min_citations: int = 30,
    max_papers: int = 12,
    require_arxiv: bool = True,
) -> str:
    """Cross-field exploratory search. Useful for serendipity: find directions
    in areas the user hasn't worked in, or surface follow-ups that span ML +
    stats, security + ML, etc.

    Args:
        query: keyword(s); OpenAlex search syntax.
        fields: optional list of configured field names; restricts to their
            concepts. Omit for fully unconstrained search.
        year_min: default 2020.
        min_citations: default 30 (looser than topic_followups for breadth).
        max_papers: default 12.
        require_arxiv: same as topic_followups.
    """
    params = {"year_min": year_min, "min_citations": min_citations,
              "max_papers": max_papers, "require_arxiv": require_arxiv}
    return _live({"query": query, "fields": fields, "params": params}, track="broad",
                 query=query, fields=fields, **params)


# ---------------------------------------------------------------------------
# Stored corpus tools
# ---------------------------------------------------------------------------

_DIRECTION_COLUMNS = (
    "direction_id, direction, rationale, quote, feasibility, novelty, dependencies, "
    "user_status, user_notes, field_tags_json, paper_id, paper_title, year, venue, "
    "field, track, cited_by_count, doi, arxiv_id"
)


def _query_directions(clauses: list[str], params: list[Any], limit: int) -> list[dict]:
    """One shape for every direction listing: v_directions_full, tags decoded."""
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (f"SELECT {_DIRECTION_COLUMNS} FROM v_directions_full{where} "
           "ORDER BY cited_by_count DESC LIMIT ?")
    out = []
    for r in _store().conn.execute(sql, [*params, limit]):
        d = dict(r)
        try:
            d["field_tags"] = json.loads(d.pop("field_tags_json") or "[]")
        except json.JSONDecodeError:
            d["field_tags"] = []
        out.append(d)
    return out


def _filters(field: str | None, track: str | None, feasibility: str | None,
             user_status: str | None) -> tuple[list[str], list[Any]]:
    clauses, params = [], []
    for col, val in (("field", field), ("track", track), ("feasibility", feasibility),
                     ("user_status", user_status)):
        if val:
            clauses.append(f"{col} = ?")
            params.append(val)
    return clauses, params


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@mcp.tool()
def search_directions(
    query: str,
    field: str | None = None,
    feasibility: str | None = None,
    track: str | None = None,
    user_status: UserStatus | None = None,
    limit: int = 25,
) -> str:
    """Search the local catalog of distilled research directions.

    Args:
        query: substring searched in direction text, rationale, and tags.
        field: optional configured field name or "ad-hoc".
        feasibility: optional low | medium | high.
        track: optional recent | legacy | seed | topic | broad | paper.
        user_status: optional curation state.
        limit: default 25.
    """
    clauses, params = _filters(field, track, feasibility, user_status)
    like = f"%{_like_escape(query)}%"
    clauses.insert(0, "(direction LIKE ? ESCAPE '\\' OR rationale LIKE ? ESCAPE '\\' "
                      "OR field_tags_json LIKE ? ESCAPE '\\')")
    params[:0] = [like, like, like]
    rows = _query_directions(clauses, params, limit)
    return _json({"query": query, "count": len(rows), "results": rows})


@mcp.tool()
def list_directions(
    field: str | None = None,
    track: str | None = None,
    user_status: UserStatus | None = "open",
    limit: int = 50,
) -> str:
    """List stored directions, most-cited paper first. Defaults to user_status='open'.
    Same result shape as search_directions."""
    rows = _query_directions(*_filters(field, track, None, user_status), limit)
    return _json({"count": len(rows), "results": rows})


@mcp.tool()
def get_paper(paper_id: str) -> str:
    """Return a stored paper's full record: metadata, sections, and any
    distilled directions."""
    store = _store()
    row = store.get_paper(paper_id)
    if row is None:
        return _json({"paper_id": paper_id, "error": "not found"})
    summary = summarize_paper(row, sections=store.get_sections(paper_id))
    summary["directions"] = [dict(d) for d in store.get_directions(paper_id)]
    return _json(summary)


@mcp.tool()
def submit_directions(
    paper_id: str,
    directions: list[dict],
    mode: Literal["append", "replace"] = "append",
) -> str:
    """Persist synthesized directions for a stored paper.

    A direction matching an existing one for the paper (same text, ignoring
    case and spacing) updates that row in place: its id and curation
    (user_status, user_notes) are kept and field_tags are merged.

    mode="append" (default) adds/updates and never removes anything.
    mode="replace" also removes the paper's other directions, except curated
    ones (user_status other than "open", or user_notes set), which always survive.

    Each direction dict supports: direction (required), rationale, quote,
    field_tags (list), feasibility (low|medium|high), novelty (low|medium|high),
    dependencies.
    """
    store = _store()
    if store.get_paper(paper_id) is None:
        return _json({"paper_id": paper_id, "error": "paper not in store"})
    rows = directions_from_dicts(paper_id, directions)
    write = store.replace_directions if mode == "replace" else store.upsert_directions
    write(paper_id, rows)
    return _json({"paper_id": paper_id, "mode": mode, "stored": len(rows),
                  "total": len(store.get_directions(paper_id))})


@mcp.tool()
def mark_direction(direction_id: int, status: UserStatus, notes: str | None = None) -> str:
    """Update user_status / user_notes on a stored direction.

    Args:
        direction_id: direction_id from search_directions / list_directions.
        status: the new curation state.
        notes: optional free-form note.
    """
    try:
        found = _store().set_direction_status(direction_id, status, notes)
    except ValueError as e:
        return _json({"error": str(e)})
    if not found:
        return _json({"direction_id": direction_id, "error": "no such direction"})
    return _json({"direction_id": direction_id, "status": status, "notes": notes})


# ---------------------------------------------------------------------------
# Bulk pipeline tools
# ---------------------------------------------------------------------------

@mcp.tool()
def discover(
    fields: list[FieldName] | None = None,
    track: Literal["recent", "legacy", "both"] = "recent",
    per_field: int = 25,
    legacy_per_field: int = 8,
    year_min_recent: int = 2020,
) -> str:
    """Run the bulk discovery stage. Stores paper metadata in the local DB."""
    try:
        names = validate_fields(fields or FIELDS)
    except ValueError as e:
        return _json({"error": str(e)})
    cfg = RunConfig(fields=names, track=track, per_field_limit=per_field,
                    legacy_per_field_limit=legacy_per_field, year_min_recent=year_min_recent)
    with _openalex() as client:
        return _json({"counts": run_discover(_store(), cfg, client=client)})


@mcp.tool()
def extract_pending(max_papers: int = 0, retry_failed: bool = False,
                    retry_empty: bool = False) -> str:
    """Fetch PDFs (if missing) and extract sections for any papers not yet
    processed. Idempotent. Papers whose fetch failed before are skipped unless
    retry_failed=True; papers where the current extractor found nothing are
    skipped unless retry_empty=True."""
    store = _store()
    fetched = run_fetch(store, max_papers=max_papers or None, retry_failed=retry_failed)
    extracted = run_extract(store, max_papers=max_papers or None, retry_empty=retry_empty)
    return _json({"fetch": fetched, "extract": extracted})


@mcp.tool()
def render_markdown() -> str:
    """Regenerate the markdown index and per-paper files under out/."""
    return _json({"render": render_all(_store()), "out_dir": str(config.OUT_DIR)})


@mcp.tool()
def status() -> str:
    """Show counts of papers, sections, and directions per field/track."""
    return _json(_store().status_counts())


# ---------------------------------------------------------------------------
# SQL escape hatch
# ---------------------------------------------------------------------------

# Authorizer whitelist: a statement may only read. Everything else (writes,
# DDL, ATTACH, PRAGMA, VACUUM INTO, ...) is denied by the engine at prepare
# time, so there is no keyword filtering of the SQL text.
_READ_ACTIONS = frozenset({
    sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE,
})


# Wall-clock bound on one run_sql call (prepare, step, and fetch), enforced by
# a progress handler that aborts the statement; a recursive CTE without a
# termination condition would otherwise hang the server.
SQL_TIME_LIMIT_SECONDS = 3.0
_PROGRESS_EVERY_N_OPS = 10_000


def _read_only_authorizer(action: int, *_args: Any) -> int:
    return sqlite3.SQLITE_OK if action in _READ_ACTIONS else sqlite3.SQLITE_DENY


def readonly_connection(store: Store) -> sqlite3.Connection:
    """A separate read-only connection to the store's file, guarded three ways:
    mode=ro, PRAGMA query_only, and the read-only authorizer."""
    if store.db_file is None:
        raise RuntimeError("run_sql needs a file-backed store")
    conn = sqlite3.connect(f"file:{store.db_file}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.set_authorizer(_read_only_authorizer)
    return conn


@mcp.tool()
def run_sql(query: str, limit: int = 200) -> str:
    """Run a read-only SQL query against the local store.

    Use the v_directions_full view for the common case (joining directions to
    their parent paper). Only reads are allowed; anything else returns an
    error. At most `limit` rows are returned; `truncated` says if more existed.
    A query running longer than a few seconds is aborted with an error.
    """
    conn = readonly_connection(_store())
    deadline = time.monotonic() + SQL_TIME_LIMIT_SECONDS
    timed_out = False

    def over_deadline() -> int:
        nonlocal timed_out
        timed_out = time.monotonic() > deadline
        return int(timed_out)  # nonzero aborts the running statement

    conn.set_progress_handler(over_deadline, _PROGRESS_EVERY_N_OPS)
    try:
        cur = conn.execute(query)
        rows = [dict(r) for r in cur.fetchmany(int(limit))]
        truncated = cur.fetchone() is not None
    except sqlite3.DatabaseError as e:
        if timed_out:
            return _json({"error": f"query exceeded the {SQL_TIME_LIMIT_SECONDS:g}s time limit"})
        return _json({"error": str(e)})
    finally:
        conn.close()
    return _json({"row_count": len(rows), "truncated": truncated, "rows": rows})


@mcp.tool()
def get_schema() -> str:
    """Return the SQL schema and the v_directions_full view definition."""
    return _json({"schema": SCHEMA_PATH.read_text()})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """stdio MCP entry point. Configured in pyproject as `vista-mcp`."""
    mcp.run()


if __name__ == "__main__":
    main()
