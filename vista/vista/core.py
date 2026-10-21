"""Core helpers for on-demand research lookups.

These functions wrap the discover/fetch/extract pipeline for use by the MCP
server. Each call: search OpenAlex live, cache PDFs and extracted sections to
the local store, and return a structured payload the conversation can read.

The MCP layer is mechanical. No LLM calls happen here. Synthesis is the
caller's job.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx

from vista.config import ARXIV_SOURCE_ID, concept_ids_for
from vista.pipeline.extract import extract_and_store, should_extract
from vista.pipeline.fetch import fetch_and_record
from vista.sources.openalex import (
    ARXIV_ID_PATTERN,
    OpenAlexClient,
    OpenAlexWork,
    TitleMatch,
    build_filter,
    find_by_title,
)
from vista.storage.db import Paper, Store

ARXIV_RE = re.compile(
    rf"^(?:arxiv:|(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/)?"
    rf"({ARXIV_ID_PATTERN})(?:v\d+)?(?:\.pdf)?/?$",
    re.IGNORECASE,
)
# arXiv mints a DataCite DOI for every paper; OpenAlex resolves it directly.
ARXIV_DOI_PREFIX = "10.48550/arxiv."
DOI_RE = re.compile(r"^(?:doi:|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/\S+)$", re.IGNORECASE)
OPENALEX_RE = re.compile(r"^(?:https?://openalex\.org/)?(W\d+)$")


# ---------------------------------------------------------------------------
# Identifier resolution
# ---------------------------------------------------------------------------

def resolve_identifier(identifier: str, client: OpenAlexClient) -> TitleMatch:
    """Resolve a free-form paper identifier (DOI, arXiv id or URL, OpenAlex id, or title).

    Exact identifiers are one free lookup. A title is a search that accepts
    only a normalized-equal title; near misses come back as `candidates`.
    """
    s = identifier.strip()
    if m := OPENALEX_RE.match(s):
        return TitleMatch(work=client.work_by_id(m.group(1)))
    if m := DOI_RE.match(s):
        return TitleMatch(work=client.work_by_doi(m.group(1)))
    if m := ARXIV_RE.match(s):
        return TitleMatch(work=client.work_by_doi(ARXIV_DOI_PREFIX + m.group(1).lower()))
    return find_by_title(client, s)


# ---------------------------------------------------------------------------
# Live search
# ---------------------------------------------------------------------------

def search_works(
    client: OpenAlexClient,
    *,
    query: str | None = None,
    fields: Iterable[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    min_citations: int = 0,
    max_papers: int = 10,
    require_arxiv: bool = True,
) -> list[OpenAlexWork]:
    """Top-cited works matching a keyword query and/or FIELDS concepts.

    Raises ValueError for a field name not in config.FIELDS.
    """
    filt = build_filter(
        concept_ids=concept_ids_for(fields or []) or None,
        location_source_ids=[ARXIV_SOURCE_ID] if require_arxiv else None,
        year_min=year_min,
        year_max=year_max,
        min_citations=min_citations,
        keyword_search=query,
    )
    return list(client.works(filter_str=filt, max_results=max_papers))


# ---------------------------------------------------------------------------
# Single-paper roundtrip: cache, fetch, extract
# ---------------------------------------------------------------------------

def cache_work(store: Store, w: OpenAlexWork, *, field: str, track: str) -> None:
    store.upsert_paper(Paper.from_work(w, field=field, track=track))


def fetch_and_extract(store: Store, paper_id: str, *, http: httpx.Client) -> dict[str, Any]:
    """Idempotent: fetch the PDF if missing, extract sections if `should_extract`.

    A paper with section text, or a current-version empty placeholder, is not
    re-parsed; an error or older-extractor placeholder is. Returns the structured summary MCP tools emit.
    """
    row = store.get_paper(paper_id)
    if row is None:
        return {"paper_id": paper_id, "error": "not in store"}

    if not row["pdf_path"] or not Path(row["pdf_path"]).exists():
        if not fetch_and_record(store, row, client=http):
            return summarize_paper(store.get_paper(paper_id), sections=[],
                                   note="pdf_unavailable")
        row = store.get_paper(paper_id)

    sections = store.get_sections(paper_id)
    if should_extract(sections):
        extract_and_store(store, paper_id, Path(row["pdf_path"]))
        sections = store.get_sections(paper_id)
    return summarize_paper(row, sections=sections)


def research(store: Store, works: Iterable[OpenAlexWork], *, track: str,
             http: httpx.Client, field: str = "ad-hoc") -> list[dict[str, Any]]:
    """Cache each work, fetch and extract it, and return the paper summaries."""
    out = []
    for w in works:
        cache_work(store, w, field=field, track=track)
        out.append(fetch_and_extract(store, w.id, http=http))
    return out


def summarize_paper(row, *, sections: list, note: str | None = None) -> dict[str, Any]:
    """Render a paper + its sections to the structured shape MCP tools return."""
    authors = []
    try:
        authors = json.loads(row["authors_json"] or "[]")
    except json.JSONDecodeError:
        pass
    section_payload = [
        {
            "type": s["section_type"],
            "heading": s["heading"],
            "method": s["method"],
            "content": s["content"],
            "char_count": len(s["content"]),
        }
        for s in sections if s["content"]
    ]
    arxiv_id = row["arxiv_id"]
    doi = row["doi"]
    out: dict[str, Any] = {
        "paper_id": row["id"],
        "title": row["title"],
        "authors": [a.get("name") for a in authors if a.get("name")][:8],
        "year": row["year"],
        "venue": row["venue"],
        "cited_by_count": row["cited_by_count"],
        "doi": doi,
        "arxiv_id": arxiv_id,
        "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
        "doi_url": (doi if (doi or "").startswith("http")
                    else (f"https://doi.org/{doi}" if doi else None)),
        "abstract": row["abstract"],
        "field": row["field"],
        "track": row["track"],
        "sections": section_payload,
    }
    if note:
        out["note"] = note
    return out
