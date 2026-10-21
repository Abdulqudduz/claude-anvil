"""Seed papers from user BibTeX files.

Resolves each entry to OpenAlex via DOI when present, otherwise via an exact
(normalized) title match.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from pathlib import Path

import bibtexparser  # type: ignore

from vista.sources.openalex import OpenAlexClient, OpenAlexWork, find_by_title
from vista.storage.db import Paper, Store

log = logging.getLogger(__name__)


def parse_bibtex(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        db = bibtexparser.load(fh)
    return [dict(e) for e in db.entries]


def _resolve(entry: dict, client: OpenAlexClient) -> OpenAlexWork | None:
    doi = entry.get("doi") or entry.get("DOI")
    if doi:
        w = client.work_by_doi(doi)
        if w:
            return w
    title = entry.get("title") or entry.get("TITLE")
    if not title:
        return None
    return find_by_title(client, title.strip().strip("{}")).work


def seed_from_bib(
    store: Store,
    paths: Iterable[Path],
    *,
    field: str,
    track: str = "seed",
    client: OpenAlexClient | None = None,
) -> dict[str, int]:
    counts = {"entries": 0, "resolved": 0, "stored": 0, "missing": 0}
    own = client is None
    client = client or OpenAlexClient()
    try:
        for p in paths:
            for e in parse_bibtex(p):
                counts["entries"] += 1
                w = _resolve(e, client)
                if not w:
                    counts["missing"] += 1
                    log.info("could not resolve %s", e.get("title", "?")[:80])
                    continue
                counts["resolved"] += 1
                store.upsert_paper(Paper.from_work(w, field=field, track=track))
                counts["stored"] += 1
    finally:
        if own:
            client.close()
    return counts


def discover_bibs(roots: Iterable[Path]) -> Iterator[Path]:
    """Recursively yield .bib files under each root path."""
    for root in roots:
        if root.exists():
            yield from root.rglob("*.bib")
